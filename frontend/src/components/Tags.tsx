import type { FigoGroup, Relevance } from "../types";
import { GROUP_COLOR, RELEVANCE_COLOR, RELEVANCE_LABEL } from "../viewer/palette";

// Solid, flat fills. No transparency, no wash.
export function GroupTag({ group }: { group: FigoGroup }) {
  return (
    <span
      className="rounded px-1.5 py-[3px] text-[10.5px] leading-none font-medium text-card"
      style={{ backgroundColor: GROUP_COLOR[group] }}
    >
      {group}
    </span>
  );
}

export function RelevanceChip({ relevance }: { relevance: Relevance }) {
  return (
    <span
      className="rounded px-1.5 py-[3px] text-[10.5px] leading-none font-medium text-card"
      style={{ backgroundColor: RELEVANCE_COLOR[relevance] }}
    >
      {RELEVANCE_LABEL[relevance]}
    </span>
  );
}
