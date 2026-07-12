import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { MyomaDetail, Projected } from "../types";
import Connectors, { type Anchor } from "./Connectors";
import MyomaBloom from "./MyomaBloom";
import MyomaCard from "./MyomaCard";

interface Props {
  myomas: MyomaDetail[];
  colors: Record<string, string>;
  selected: string | null;
  onSelect: (id: string) => void;
  onClose: () => void;
  projected: Record<string, Projected>;
  meshUrl: string;
}

interface Slot {
  side: "left" | "right";
  y: number;
}

const GUTTER = 24;
const EDGE = 12;

// Half the height of a small card, used to test which cards the docked bloom lands on.
const CARD_HALF_HEIGHT = 34;

// The card is one scroll region, so the cap only decides how much of it is visible at
// rest. It is set to reach roughly the start of the measurements, and the rest is
// scrolled to. Nothing can be cut off, however long the reasoning runs.
const BLOOM_MAX_HEIGHT = 480;

// Cards sit in both gutters around the model, so the connectors fan out to either side.
// The side and the vertical order are captured once from the opening view, so connectors
// stay short and the cards never jump around while the model is rotated.
function splitColumns(items: MyomaDetail[]): [MyomaDetail[], MyomaDetail[]] {
  const half = Math.ceil(items.length / 2);
  return [items.slice(0, half), items.slice(half)];
}

function sameAnchors(a: Anchor[], b: Anchor[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((anchor, i) => {
    const other = b[i];
    return (
      anchor.id === other.id &&
      anchor.side === other.side &&
      Math.abs(anchor.x - other.x) < 0.5 &&
      Math.abs(anchor.y - other.y) < 0.5
    );
  });
}

export default function Overlay({
  myomas,
  colors,
  selected,
  onSelect,
  onClose,
  projected,
  meshUrl,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const bloomRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [slots, setSlots] = useState<Record<string, Slot>>({});
  const [bloomHeight, setBloomHeight] = useState(0);

  useEffect(() => {
    setSlots({});
  }, [myomas]);

  // Capture the arrangement once, as soon as every myoma has been projected.
  useEffect(() => {
    if (Object.keys(slots).length > 0 || myomas.length === 0 || size.width === 0) return;
    if (!myomas.every((m) => projected[m.id])) return;

    // Each card goes to the gutter its myoma already leans toward, so the connectors stay
    // short and the cards spread around the model rather than stacking in one column.
    const next: Record<string, Slot> = {};
    for (const myoma of myomas) {
      const point = projected[myoma.id];
      next[myoma.id] = {
        side: point.x < size.width / 2 ? "left" : "right",
        y: point.y,
      };
    }
    setSlots(next);
  }, [myomas, projected, size, slots]);

  const [left, right] = useMemo(() => {
    if (Object.keys(slots).length === 0) return splitColumns(myomas);
    const bySide = (side: "left" | "right") =>
      myomas
        .filter((m) => slots[m.id]?.side === side)
        .sort((a, b) => slots[a.id].y - slots[b.id].y);
    return [bySide("left"), bySide("right")];
  }, [myomas, slots]);

  const leftIds = useMemo(() => new Set(left.map((m) => m.id)), [left]);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const observer = new ResizeObserver(([entry]) => {
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  // Cards are laid out by flow, so read their edges back once the layout settles. The
  // selected card keeps its slot while its bloom is open, so its anchor stays valid.
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const rootRect = root.getBoundingClientRect();

    const next: Anchor[] = [];
    for (const myoma of myomas) {
      const element = cardRefs.current.get(myoma.id);
      if (!element) continue;
      const rect = element.getBoundingClientRect();
      const side: "left" | "right" = leftIds.has(myoma.id) ? "left" : "right";
      next.push({
        id: myoma.id,
        x: (side === "left" ? rect.right : rect.left) - rootRect.left,
        y: rect.top - rootRect.top + rect.height / 2,
        side,
      });
    }
    setAnchors((prev) => (sameAnchors(prev, next) ? prev : next));
  }, [myomas, leftIds, size]);

  useLayoutEffect(() => {
    setBloomHeight(bloomRef.current?.offsetHeight ?? 0);
  }, [selected, size]);

  const setCardRef = useCallback(
    (id: string) => (element: HTMLButtonElement | null) => {
      if (element) cardRefs.current.set(id, element);
      else cardRefs.current.delete(id);
    },
    [],
  );

  const selectedDetail = selected ? myomas.find((m) => m.id === selected) : undefined;
  const selectedAnchor = anchors.find((a) => a.id === selected);

  const bloomMaxHeight = Math.max(240, Math.min(BLOOM_MAX_HEIGHT, size.height - EDGE * 2));

  // The bloom grows out of the small card, centered on the same connector anchor and
  // kept inside the workspace. The agent badge steps aside while it is open.
  const bloomTop = (() => {
    if (!selectedAnchor || size.height === 0) return EDGE;
    const height = Math.min(bloomHeight || 360, bloomMaxHeight);
    const raw = selectedAnchor.y - height / 2;
    const max = Math.max(EDGE, size.height - EDGE - height);
    return Math.min(Math.max(raw, EDGE), max);
  })();

  // The docked bloom is wider than a card, so it sits over its own column. Cards it lands
  // on step aside with the selected one, rather than being left half clipped by its edge.
  const covered = (() => {
    const ids = new Set<string>();
    if (!selectedAnchor) return ids;
    const height = Math.min(bloomHeight || 360, bloomMaxHeight);
    for (const anchor of anchors) {
      if (anchor.side !== selectedAnchor.side) continue;
      const top = anchor.y - CARD_HALF_HEIGHT;
      const bottom = anchor.y + CARD_HALF_HEIGHT;
      if (bottom > bloomTop && top < bloomTop + height) ids.add(anchor.id);
    }
    return ids;
  })();

  const column = (items: MyomaDetail[], align: string) => (
    <div
      className={`pointer-events-none absolute top-0 bottom-0 flex flex-col justify-center gap-3 ${align}`}
    >
      {items.map((myoma) => (
        <div key={myoma.id} className="pointer-events-auto">
          <MyomaCard
            detail={myoma}
            color={colors[myoma.id]}
            hidden={selected === myoma.id || covered.has(myoma.id)}
            onSelect={() => onSelect(myoma.id)}
            cardRef={setCardRef(myoma.id)}
          />
        </div>
      ))}
    </div>
  );

  return (
    <div ref={rootRef} className="pointer-events-none absolute inset-0 z-10">
      <Connectors
        width={size.width}
        height={size.height}
        anchors={anchors}
        projected={projected}
        colors={colors}
        selected={selected}
      />
      {column(left, "left-6 items-start")}
      {column(right, "right-6 items-end")}

      {selectedDetail && selectedAnchor && (
        <div
          ref={bloomRef}
          className="pointer-events-auto absolute z-20"
          style={{
            top: bloomTop,
            left: selectedAnchor.side === "left" ? GUTTER : undefined,
            right: selectedAnchor.side === "right" ? GUTTER : undefined,
            maxHeight: bloomMaxHeight,
          }}
        >
          <MyomaBloom
            detail={selectedDetail}
            color={colors[selectedDetail.id]}
            side={selectedAnchor.side}
            maxHeight={bloomMaxHeight}
            meshUrl={meshUrl}
            onClose={onClose}
          />
        </div>
      )}
    </div>
  );
}
