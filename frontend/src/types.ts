export type FigoGroup =
  | "Submucosal"
  | "Intramural"
  | "Subserosal"
  | "Transmural"
  | "Other";
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
