import { GroupTag, RelevanceChip } from "../components/Tags";
import type { MyomaDetail } from "../types";
import MyomaMiniView from "../viewer/MyomaMiniView";

interface Props {
  detail: MyomaDetail;
  color: string;
  side: "left" | "right";
  maxHeight: number;
  meshUrl: string;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-4">
      <h4 className="text-[9.5px] font-semibold tracking-[0.14em] text-fg3 uppercase">
        {title}
      </h4>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="card-inset rounded-md px-2.5 py-2">
      <div className="text-[10.5px] text-fg3">{label}</div>
      <div className="figure mt-0.5 text-[15px] font-medium text-fg">
        {value}
        {unit && <span className="ml-0.5 text-[10.5px] text-fg3">{unit}</span>}
      </div>
    </div>
  );
}

export default function MyomaBloom({
  detail,
  color,
  side,
  maxHeight,
  meshUrl,
  onClose,
}: Props) {
  const m = detail.measurement;
  const contact =
    [m.contactsCavity && "Cavity", m.contactsSerosa && "Serosa"]
      .filter(Boolean)
      .join(", ") || "None";

  return (
    // The cap has to be a real length. A percentage max-height would resolve against the
    // auto-height wrapper and be dropped, which is what let the card run the full stage.
    <div
      className="bloom-in grain-card card-surface relative flex w-[320px] flex-col overflow-hidden rounded-xl border border-accent/80 shadow-xl shadow-black/40"
      style={{
        maxHeight,
        transformOrigin: side === "left" ? "left center" : "right center",
      }}
    >
      {/* One continuous scroll region. Everything from the title to the management options
          moves together, so no part of the card can end up unreachable. */}
      <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span
              className="h-3 w-3 shrink-0 rounded-full"
              style={{ backgroundColor: color }}
            />
            <h3 className="font-serif text-[19px] leading-none font-semibold text-fg">
              {detail.label}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Collapse"
            className="-mt-1 -mr-1 rounded px-1.5 py-0.5 text-[16px] leading-none text-fg3 transition-colors hover:bg-fg/10 hover:text-fg"
          >
            &times;
          </button>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-1.5">
          <GroupTag group={detail.figoGroup} />
          <RelevanceChip relevance={detail.relevance} />
          {detail.provisional && (
            <span className="rounded border border-accent/40 px-1.5 py-[3px] text-[10.5px] leading-none font-medium text-fg2">
              Provisional
            </span>
          )}
        </div>

        <div className="mt-3">
          <MyomaMiniView
            key={detail.id}
            url={meshUrl}
            myomaId={detail.id}
            color={color}
          />
        </div>

        <Section title="FIGO classification">
          <div className="flex items-baseline gap-2">
            <span className="figure text-[20px] font-medium tracking-tight text-fg">
              Type {detail.figoType}
            </span>
            <span className="text-[11px] text-fg3">confidence: {detail.confidence}</span>
          </div>
          <p className="mt-1 text-[12.5px] leading-relaxed text-fg2">
            {detail.figoTypeName}
          </p>
        </Section>

        <Section title="Reasoning">
          <p className="text-[12.5px] leading-relaxed text-fg2">{detail.justification}</p>
        </Section>

        <Section title="Measurements">
          <div className="grid grid-cols-2 gap-1.5">
            <Metric label="Volume" value={m.volumeMl.toFixed(2)} unit="mL" />
            <Metric label="Max diameter" value={m.maxDiameterMm.toFixed(1)} unit="mm" />
            <Metric label="Intramural" value={m.intramuralPct.toFixed(0)} unit="%" />
            <Metric label="Contact" value={contact} />
          </div>
        </Section>

        <Section title="Management options">
          <ul className="space-y-1">
            {detail.management.map((option) => (
              <li
                key={option}
                className="flex gap-2 text-[12.5px] leading-relaxed text-fg2"
              >
                <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-fg3" />
                {option}
              </li>
            ))}
          </ul>
        </Section>
      </div>
    </div>
  );
}
