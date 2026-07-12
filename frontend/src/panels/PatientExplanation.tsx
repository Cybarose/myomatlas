import type { CaseReport } from "../types";

interface Props {
  report: CaseReport;
}

export default function PatientExplanationPanel({ report }: Props) {
  return (
    <div>
      <p className="text-[14px] leading-[1.8] text-fg2">{report.patientExplanation}</p>
    </div>
  );
}
