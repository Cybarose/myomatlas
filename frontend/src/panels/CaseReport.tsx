import { intakeSummary } from "../api/intake";
import { RelevanceChip } from "../components/Tags";
import type { CaseReport, ClinicalIntake, MyomaDetail } from "../types";

interface Props {
  report: CaseReport;
  myomas: MyomaDetail[];
  colors: Record<string, string>;
  intake: ClinicalIntake;
  onSelect: (id: string) => void;
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[9.5px] font-semibold tracking-[0.14em] text-fg3 uppercase">
      {children}
    </h3>
  );
}

export default function CaseReportPanel({
  report,
  myomas,
  colors,
  intake,
  onSelect,
}: Props) {
  const context = intakeSummary(intake);

  return (
    <div>
      {context.length > 0 && (
        <section className="mb-6">
          <Heading>Patient context</Heading>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {context.map((item) => (
              <span
                key={item}
                className="rounded border border-accent/40 px-1.5 py-[3px] text-[10.5px] leading-none font-medium text-fg2"
              >
                {item}
              </span>
            ))}
          </div>
        </section>
      )}

      <section>
        <Heading>Summary</Heading>
        <p className="mt-2.5 text-[13px] leading-[1.7] text-fg2">{report.summary}</p>
      </section>

      <section className="mt-6">
        <Heading>Findings</Heading>
        <ul className="mt-2.5 divide-y divide-accent/20 overflow-hidden rounded-md border border-accent/25">
          {myomas.map((myoma) => (
            <li key={myoma.id}>
              <button
                type="button"
                onClick={() => onSelect(myoma.id)}
                className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-fg/[0.06]"
              >
                <span className="flex items-center gap-2.5">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colors[myoma.id] }}
                  />
                  <span className="text-[13px] font-medium text-fg">{myoma.label}</span>
                  <span className="figure text-[11.5px] text-fg3">
                    Type {myoma.figoType}
                  </span>
                </span>
                <RelevanceChip relevance={myoma.relevance} />
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-6">
        <Heading>Malignancy</Heading>
        <div className="card-inset mt-2.5 rounded-md px-3 py-2.5">
          <div className="text-[13px] font-medium text-fg">
            {report.malignancyFlag ? "Flagged for exclusion" : "Not flagged"}
          </div>
          <p className="mt-1 text-[12px] leading-relaxed text-fg2">
            {report.malignancyReason}
          </p>
        </div>
      </section>

    </div>
  );
}
