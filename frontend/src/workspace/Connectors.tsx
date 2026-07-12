import type { Projected } from "../types";
import { ACCENT } from "../viewer/palette";

export interface Anchor {
  id: string;
  x: number;
  y: number;
  side: "left" | "right";
}

interface Props {
  width: number;
  height: number;
  anchors: Anchor[];
  projected: Record<string, Projected>;
  colors: Record<string, string>;
  selected: string | null;
}

// Gentle horizontal S curve from the card edge out to the myoma.
function curve(anchor: Anchor, point: Projected): string {
  const pull = Math.max(28, Math.abs(point.x - anchor.x) * 0.42);
  const c1 = anchor.side === "left" ? anchor.x + pull : anchor.x - pull;
  const c2 = anchor.side === "left" ? point.x - pull : point.x + pull;
  return `M ${anchor.x} ${anchor.y} C ${c1} ${anchor.y} ${c2} ${point.y} ${point.x} ${point.y}`;
}

export default function Connectors({
  width,
  height,
  anchors,
  projected,
  colors,
  selected,
}: Props) {
  if (width === 0 || height === 0) return null;

  return (
    <svg
      className="pointer-events-none absolute inset-0"
      width={width}
      height={height}
      aria-hidden="true"
    >
      {anchors.map((anchor) => {
        const point = projected[anchor.id];
        if (!point || !point.visible) return null;

        const isSelected = selected === anchor.id;
        const stroke = isSelected ? ACCENT : "#4d5462";

        return (
          <g key={anchor.id}>
            <path
              d={curve(anchor, point)}
              fill="none"
              stroke={stroke}
              strokeWidth={isSelected ? 1.4 : 1}
              opacity={isSelected ? 0.95 : 0.55}
            />
            <circle
              cx={point.x}
              cy={point.y}
              r={isSelected ? 3 : 2.5}
              fill={isSelected ? ACCENT : colors[anchor.id]}
              opacity={isSelected ? 1 : 0.85}
            />
          </g>
        );
      })}
    </svg>
  );
}
