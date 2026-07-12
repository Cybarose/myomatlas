import type { Confidence, FigoGroup, Relevance } from "../types";

// Shapes returned by the backend. Snake case, mapped to the UI types in adapt.ts.

export interface ApiMyoma {
  id: number;
  figo_type: string;
  figo_type_name: string;
  figo_group: FigoGroup;
  bleeding_relevance: Relevance;
  confidence: Confidence;
  provisional: boolean;
  justification: string;
  management_options: string[];
}

export interface ApiClinicianReport {
  myomas: ApiMyoma[];
  malignancy_flag: { flag: boolean; reason: string };
  overall_summary: string;
}

export interface ApiMeasuredMyoma {
  id: number;
  volume_ml: number;
  max_diameter_mm: number;
  contacts_cavity: boolean;
  contacts_serosa: boolean;
  intramural_pct: number;
}

export interface ApiMeasurements {
  case_id: string;
  modality: string;
  myoma_count: number;
  myomas: ApiMeasuredMyoma[];
}

export interface AnalyzeResponse {
  ok: boolean;
  error?: string;
  case_id: string;
  model: string;
  rules_version: string;
  clinician_report: ApiClinicianReport;
  patient_explanation: string;
  measurements: ApiMeasurements;
}
