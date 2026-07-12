import { GroupTag, RelevanceChip } from "../components/Tags";
import type { MyomaDetail } from "../types";

interface Props {
  detail: MyomaDetail;
  color: string;
  hidden: boolean;
  onSelect: () => void;
  cardRef: (element: HTMLButtonElement | null) => void;
}

export default function MyomaCard({ detail, color, hidden, onSelect, cardRef }: Props) {
  return (
    <button
      ref={cardRef}
      type="button"
      onClick={onSelect}
      // Kept in the layout while its bloom is open, so the connector anchor stays put.
      className={`grain-card card-surface relative w-[200px] rounded-lg border border-accent/80 px-3 py-2.5 text-left transition-opacity ${
        hidden ? "pointer-events-none opacity-0" : "opacity-100 hover:border-accent"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
        <span className="text-[13px] font-semibold tracking-tight text-fg">
          {detail.label}
        </span>
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-2">
        <GroupTag group={detail.figoGroup} />
        <RelevanceChip relevance={detail.relevance} />
      </div>
    </button>
  );
}
