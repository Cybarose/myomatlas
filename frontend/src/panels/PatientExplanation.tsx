import type { CaseReport } from "../types";

interface Props {
  report: CaseReport;
}

export default function PatientExplanationPanel({ report }: Props) {
  return (
    <div>
      <p className="text-[14px] leading-[1.8] text-fg2">{report.patientExplanation}</p>

      <div className="card-inset mt-6 rounded-md px-3.5 py-3">
        <p className="text-[12.5px] leading-relaxed text-fg2">
          This summary is written for you, not for your file. It does not replace the
          conversation with your clinician, who decides the next steps with you.
        </p>
      </div>

    </div>
  );
}
