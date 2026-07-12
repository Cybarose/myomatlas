import type {
  BleedingSeverity,
  ClinicalIntake,
  FertilityDesire,
  MenopausalStatus,
} from "../types";

// Payload the backend's ClinicalIntake expects. Only provided fields are sent.
export interface ApiIntake {
  age?: number;
  menopausal_status?: string;
  bleeding_severity?: string;
  fertility_desire?: string;
  risk_factors?: string[];
  notes?: string;
}

export const EMPTY_INTAKE: ClinicalIntake = {
  age: null,
  menopausalStatus: null,
  bleedingSeverity: null,
  fertilityDesire: null,
  riskFactors: [],
  notes: "",
};

export const MENOPAUSAL_LABEL: Record<MenopausalStatus, string> = {
  premenopausal: "Premenopausal",
  perimenopausal: "Perimenopausal",
  postmenopausal: "Postmenopausal",
  unknown: "Menopausal status unknown",
};

export const BLEEDING_LABEL: Record<BleedingSeverity, string> = {
  none: "No bleeding",
  light: "Light bleeding",
  moderate: "Moderate bleeding",
  heavy: "Heavy bleeding",
};

export const FERTILITY_LABEL: Record<FertilityDesire, string> = {
  desired: "Fertility desired",
  not_desired: "Fertility not desired",
  unsure: "Fertility wish unsure",
};

export const RISK_FACTORS: string[] = [
  "Rapid growth",
  "Postmenopausal bleeding",
  "Tamoxifen use",
  "Bleeding persists despite treatment",
];

export function isIntakeProvided(intake: ClinicalIntake): boolean {
  return (
    intake.age !== null ||
    intake.menopausalStatus !== null ||
    intake.bleedingSeverity !== null ||
    intake.fertilityDesire !== null ||
    intake.riskFactors.length > 0 ||
    intake.notes.trim().length > 0
  );
}

// Omit anything not provided, so the agent sees only real context.
export function toApiIntake(intake: ClinicalIntake): ApiIntake | null {
  if (!isIntakeProvided(intake)) return null;

  const payload: ApiIntake = {};
  if (intake.age !== null) payload.age = intake.age;
  if (intake.menopausalStatus) payload.menopausal_status = intake.menopausalStatus;
  if (intake.bleedingSeverity) payload.bleeding_severity = intake.bleedingSeverity;
  if (intake.fertilityDesire) payload.fertility_desire = intake.fertilityDesire;
  if (intake.riskFactors.length > 0) payload.risk_factors = intake.riskFactors;
  if (intake.notes.trim()) payload.notes = intake.notes.trim();
  return payload;
}

// Short chips for the report panel, so it is visible that context was used.
export function intakeSummary(intake: ClinicalIntake): string[] {
  const parts: string[] = [];
  if (intake.age !== null) parts.push(`Age ${intake.age}`);
  if (intake.menopausalStatus) parts.push(MENOPAUSAL_LABEL[intake.menopausalStatus]);
  if (intake.bleedingSeverity) parts.push(BLEEDING_LABEL[intake.bleedingSeverity]);
  if (intake.fertilityDesire) parts.push(FERTILITY_LABEL[intake.fertilityDesire]);
  parts.push(...intake.riskFactors);
  if (intake.notes.trim()) parts.push(intake.notes.trim());
  return parts;
}
