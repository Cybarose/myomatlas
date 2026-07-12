export type FigoGroup =
  | "Submucosal"
  | "Intramural"
  | "Subserosal"
  | "Transmural"
  | "Other";

export type MenopausalStatus =
  | "premenopausal"
  | "perimenopausal"
  | "postmenopausal"
  | "unknown";
export type BleedingSeverity = "none" | "light" | "moderate" | "heavy";
export type FertilityDesire = "desired" | "not_desired" | "unsure";

// Every field is optional. Nothing here leaves the session.
export interface ClinicalIntake {
  age: number | null;
  menopausalStatus: MenopausalStatus | null;
  bleedingSeverity: BleedingSeverity | null;
  fertilityDesire: FertilityDesire | null;
  riskFactors: string[];
  notes: string;
}
export type Relevance = "high" | "medium" | "low";
export type Confidence = "higher" | "moderate" | "lower";

export interface MyomaMeasurement {
  volumeMl: number;
  maxDiameterMm: number;
  contactsCavity: boolean;
  contactsSerosa: boolean;
  intramuralPct: number;
}

export interface MyomaDetail {
  id: string;
  label: string;
  figoType: string;
  figoTypeName: string;
  figoGroup: FigoGroup;
  confidence: Confidence;
  provisional: boolean;
  relevance: Relevance;
  justification: string;
  measurement: MyomaMeasurement;
  management: string[];
}

export interface CaseReport {
  caseId: string;
  modality: string;
  summary: string;
  malignancyFlag: boolean;
  malignancyReason: string;
  patientExplanation: string;
}

export interface ModelMeta {
  myomaIds: string[];
  sizeMm: [number, number, number];
  hasWall: boolean;
  hasCavity: boolean;
}

// Screen-space position of a myoma, used to draw the connector to its card.
export interface Projected {
  id: string;
  x: number;
  y: number;
  visible: boolean;
}
