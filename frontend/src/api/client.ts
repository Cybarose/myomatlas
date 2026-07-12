import type { ApiIntake } from "./intake";
import type { AnalyzeResponse } from "./types";

// One place for the backend location. Override with VITE_API_URL.
export const API_URL: string =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const UNREACHABLE =
  "Cannot reach the analysis backend. Start it with: cd backend && uvicorn app.main:app --port 8000";

export function meshUrl(caseId: string): string {
  return `${API_URL}/mesh/${caseId}`;
}

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    return typeof body?.error === "string" ? body.error : fallback;
  } catch {
    return fallback;
  }
}

export async function fetchCases(): Promise<string[]> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/cases`);
  } catch {
    throw new Error(UNREACHABLE);
  }
  if (!response.ok) {
    throw new Error(await readError(response, "The backend could not list the cases."));
  }
  const body = await response.json();
  return body.cases as string[];
}

// Runs the real pipeline: segmentation, measurements, then the agent. Slow on a cold
// case, so callers should show a loading state. The intake, when given, is the clinical
// context the agent reasons with.
export async function analyzeCase(
  caseId: string,
  intake?: ApiIntake | null,
): Promise<AnalyzeResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ case_id: caseId, intake: intake ?? undefined }),
    });
  } catch {
    throw new Error(UNREACHABLE);
  }

  if (!response.ok) {
    throw new Error(
      await readError(response, `The analysis of ${caseId} failed on the backend.`),
    );
  }

  const body = (await response.json()) as AnalyzeResponse;
  if (!body.ok) {
    throw new Error(body.error ?? `The analysis of ${caseId} failed.`);
  }
  return body;
}
