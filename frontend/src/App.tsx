import { useCallback, useEffect, useMemo, useState } from "react";
import { adaptAnalysis, type CaseAnalysis } from "./api/adapt";
import { analyzeCase, fetchCases, meshUrl } from "./api/client";
import { EMPTY_INTAKE, isIntakeProvided, toApiIntake } from "./api/intake";
import AgentIndicator, { type AgentStage } from "./components/AgentIndicator";
import Header from "./components/Header";
import IntakeForm from "./components/IntakeForm";
import CaseReportPanel from "./panels/CaseReport";
import Drawer from "./panels/Drawer";
import PatientExplanationPanel from "./panels/PatientExplanation";
import type { ClinicalIntake, ModelMeta, MyomaDetail, Projected } from "./types";
import Scene from "./viewer/Scene";
import { myomaColor } from "./viewer/palette";
import Overlay from "./workspace/Overlay";

const DEFAULT_CASE = "UMD_221129_003";

type Panel = "report" | "patient" | null;
type Status = "loading" | "ready" | "error";

// The backend runs segmentation, then measurements, then the agent. It cannot stream
// progress, so the badge walks the stages it is known to be working through and holds
// on the last one until the result lands.
const STAGE_STEPS: { stage: AgentStage; at: number }[] = [
  { stage: "measurement", at: 5000 },
  { stage: "figo", at: 13000 },
  { stage: "report", at: 22000 },
];

export default function App() {
  const [caseId, setCaseId] = useState<string>(DEFAULT_CASE);
  const [cases, setCases] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<CaseAnalysis | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<AgentStage>("segmentation");

  const [selected, setSelected] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>(null);
  const [meta, setMeta] = useState<ModelMeta | null>(null);
  const [projected, setProjected] = useState<Record<string, Projected>>({});

  // Kept in state, so it survives panel switches and can be edited and re-run.
  const [intake, setIntake] = useState<ClinicalIntake>(EMPTY_INTAKE);
  const [intakeOpen, setIntakeOpen] = useState(false);

  // Re-runs the agent for the current case. The mesh is untouched, so the 3D and the
  // card layout stay put while the analysis is refreshed with new context.
  const runAnalysis = useCallback(async (id: string, context: ClinicalIntake) => {
    setStatus("loading");
    setStage("segmentation");
    setError(null);
    setAnalysis(null);
    setSelected(null);
    setPanel(null);

    try {
      const response = await analyzeCase(id, toApiIntake(context));
      setAnalysis(adaptAnalysis(response));
      setStatus("ready");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "The analysis failed.");
      setStatus("error");
    } finally {
      setStage("ready");
    }
  }, []);

  const loadCase = useCallback(
    async (id: string, context: ClinicalIntake) => {
      setCaseId(id);
      setMeta(null);
      setProjected({});
      await runAnalysis(id, context);
    },
    [runAnalysis],
  );

  useEffect(() => {
    void loadCase(DEFAULT_CASE, EMPTY_INTAKE);
    fetchCases()
      .then(setCases)
      .catch(() => setCases([]));
    // Runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitIntake = useCallback(
    (next: ClinicalIntake) => {
      setIntake(next);
      setIntakeOpen(false);
      void runAnalysis(caseId, next);
    },
    [caseId, runAnalysis],
  );

  // Walk the pipeline stages while the request is in flight.
  useEffect(() => {
    if (status !== "loading") return;
    const timers = STAGE_STEPS.map((step) =>
      window.setTimeout(() => setStage(step.stage), step.at),
    );
    return () => timers.forEach(window.clearTimeout);
  }, [status, caseId]);

  const handleReady = useCallback((next: ModelMeta) => setMeta(next), []);

  const handleProject = useCallback((points: Projected[]) => {
    const next: Record<string, Projected> = {};
    for (const point of points) next[point.id] = point;
    setProjected(next);
  }, []);

  const handleSelect = useCallback((id: string | null) => setSelected(id), []);
  const selectMyoma = useCallback((id: string) => setSelected(id), []);
  const clearSelection = useCallback(() => setSelected(null), []);

  // Order by the mesh, and keep only myomas that exist in both the mesh and the report.
  const myomas = useMemo<MyomaDetail[]>(() => {
    if (!analysis || !meta) return [];
    const byId = new Map(analysis.myomas.map((m) => [m.id, m]));
    return meta.myomaIds
      .map((id) => byId.get(id))
      .filter((m): m is MyomaDetail => m !== undefined);
  }, [analysis, meta]);

  const colors = useMemo(() => {
    const map: Record<string, string> = {};
    (meta?.myomaIds ?? []).forEach((id, index) => {
      map[id] = myomaColor(index);
    });
    return map;
  }, [meta]);

  const ready = status === "ready" && analysis !== null;
  const drawerTitle = panel === "report" ? "Clinical report" : "Patient explanation";
  const drawerSubtitle =
    panel === "report"
      ? `${analysis?.report.caseId ?? caseId}, ${analysis?.report.modality ?? ""}`
      : "Written in plain language";

  return (
    <div className="flex h-full flex-col bg-bg">
      <Header
        caseId={caseId}
        cases={cases}
        busy={status === "loading"}
        hasContext={isIntakeProvided(intake)}
        onSelectCase={(id) => void loadCase(id, intake)}
        onOpenIntake={() => setIntakeOpen(true)}
      />

      <main className="grain relative min-h-0 flex-1 overflow-hidden bg-bg">
        <Scene
          url={meshUrl(caseId)}
          sourceName={caseId}
          selected={selected}
          onSelect={handleSelect}
          onReady={handleReady}
          onProject={handleProject}
        />

        {ready && (
          <Overlay
            myomas={myomas}
            colors={colors}
            selected={selected}
            onSelect={selectMyoma}
            onClose={clearSelection}
            projected={projected}
          />
        )}

        {intakeOpen && (
          <IntakeForm
            intake={intake}
            onSubmit={submitIntake}
            onClose={() => setIntakeOpen(false)}
          />
        )}

        {status === "error" && (
          <div className="absolute inset-0 z-20 flex items-center justify-center p-8">
            <div className="card-surface max-w-md rounded-xl border border-accent/80 px-6 py-5 text-center">
              <h2 className="font-serif text-[18px] font-semibold text-fg">
                Analysis unavailable
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-fg2">{error}</p>
              <button
                type="button"
                onClick={() => void runAnalysis(caseId, intake)}
                className="mt-4 rounded-lg border border-accent bg-accent px-3.5 py-2 text-[12px] font-medium text-bg transition-opacity hover:opacity-90"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {/* Steps aside whenever a bloom or a panel is open, so it never sits under a card. */}
        <div
          className={`absolute bottom-6 left-6 z-10 transition-opacity duration-200 ${
            selected !== null || panel !== null
              ? "pointer-events-none opacity-0"
              : "opacity-100"
          }`}
        >
          <AgentIndicator stage={stage} />
        </div>

        <div className="absolute bottom-6 left-1/2 z-10 flex -translate-x-1/2 gap-2">
          {(
            [
              ["report", "Clinical report"],
              ["patient", "Patient explanation"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              disabled={!ready}
              onClick={() => setPanel(panel === key ? null : key)}
              className={`rounded-lg border px-3.5 py-2 text-[12px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                panel === key
                  ? "border-accent bg-accent text-bg"
                  : "border-line bg-surface text-fg2 hover:border-fg3 hover:text-fg"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <Drawer
          open={panel !== null && analysis !== null}
          title={drawerTitle}
          subtitle={drawerSubtitle}
          onClose={() => setPanel(null)}
        >
          {analysis &&
            (panel === "report" ? (
              <CaseReportPanel
                report={analysis.report}
                myomas={myomas}
                colors={colors}
                intake={intake}
                onSelect={selectMyoma}
              />
            ) : (
              <PatientExplanationPanel report={analysis.report} />
            ))}
        </Drawer>
      </main>
    </div>
  );
}
