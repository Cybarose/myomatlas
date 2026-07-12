import type { FigoGroup, Relevance } from "../types";

// One accent, reserved for selection, active state and the agent badge.
export const ACCENT = "#7b91e0";

// A coordinated family: shared muted saturation and value so they sit together, but
// spread far enough around the wheel that no two myomas are ever confused.
const MYOMA_COLORS = [
  "#4f93a6",
  "#c88a55",
  "#7f9b5e",
  "#9d6f9e",
  "#5f7fae",
  "#b06a6a",
  "#6a9a8e",
] as const;

export function myomaColor(index: number): string {
  return MYOMA_COLORS[index % MYOMA_COLORS.length];
}

// Myoma nodes are named myoma_1, myoma_2 and so on, largest first.
export function myomaLabel(id: string): string {
  const match = id.match(/(\d+)/);
  return match ? `Myoma ${match[1]}` : id;
}

export function myomaOrder(id: string): number {
  const match = id.match(/(\d+)/);
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
}

// Solid, flat tag fills. Green is reserved for the Low relevance chip, so no group
// tag uses it, and each group carries its own distinct hue.
export const GROUP_COLOR: Record<FigoGroup, string> = {
  Submucosal: "#a35fb5",
  Intramural: "#4a86b8",
  Subserosal: "#2f6f6b",
  Transmural: "#c25f8a",
  Other: "#6b7280",
};

// Bleeding relevance. Solid clinical signal colors, muted, never neon.
export const RELEVANCE_COLOR: Record<Relevance, string> = {
  high: "#b8463f",
  medium: "#a97a2c",
  low: "#5f8a57",
};

export const RELEVANCE_LABEL: Record<Relevance, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};
