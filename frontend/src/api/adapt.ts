import type { CaseReport, FigoGroup, MyomaDetail, Relevance } from "../types";
import type { AnalyzeResponse } from "./types";

export interface CaseAnalysis {
  myomas: MyomaDetail[];
  report: CaseReport;
}

const GROUPS: FigoGroup[] = [
  "Submucosal",
  "Intramural",
  "Subserosal",
  "Transmural",
  "Other",
];
const RELEVANCES: Relevance[] = ["high", "medium", "low"];

// The model is asked for these as enums. Coerce anyway, so an off-schema answer degrades
// into a readable tag instead of an undefined colour lookup.
function toGroup(value: string): FigoGroup {
  return GROUPS.find((group) => group === value) ?? "Other";
}

function toRelevance(value: string): Relevance {
  const text = (value ?? "").toLowerCase();
  return RELEVANCES.find((level) => text === level) ?? "medium";
}

// The agent reasons about each myoma and the measurement pass produces its numbers.
// Both are keyed by the same id, because the mesh and the measurements come from the
// same predicted mask.
export function adaptAnalysis(response: AnalyzeResponse): CaseAnalysis {
  const measured = new Map(response.measurements.myomas.map((m) => [m.id, m]));

  const myomas: MyomaDetail[] = response.clinician_report.myomas.map((myoma) => {
    const numbers = measured.get(myoma.id);
    return {
      id: `myoma_${myoma.id}`,
      label: `Myoma ${myoma.id}`,
      figoType: myoma.figo_type,
      figoTypeName: myoma.figo_type_name,
      figoGroup: toGroup(myoma.figo_group),
      confidence: myoma.confidence,
      provisional: myoma.provisional,
      relevance: toRelevance(myoma.bleeding_relevance),
      justification: myoma.justification,
      management: myoma.management_options,
      measurement: {
        volumeMl: numbers?.volume_ml ?? 0,
        maxDiameterMm: numbers?.max_diameter_mm ?? 0,
        contactsCavity: numbers?.contacts_cavity ?? false,
        contactsSerosa: numbers?.contacts_serosa ?? false,
        intramuralPct: numbers?.intramural_pct ?? 0,
      },
    };
  });

  const report: CaseReport = {
    caseId: response.case_id,
    modality: response.measurements.modality,
    summary: response.clinician_report.overall_summary,
    malignancyFlag: response.clinician_report.malignancy_flag.flag,
    malignancyReason: response.clinician_report.malignancy_flag.reason,
    patientExplanation: response.patient_explanation,
  };

  return { myomas, report };
}
