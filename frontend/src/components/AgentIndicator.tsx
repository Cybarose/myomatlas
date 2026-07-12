export type AgentStage =
  | "segmentation"
  | "measurement"
  | "figo"
  | "report"
  | "ready";

const STAGE_LABEL: Record<AgentStage, string> = {
  segmentation: "Segmentation",
  measurement: "Measurement",
  figo: "FIGO classification",
  report: "Report",
  ready: "Ready",
};

// Bar heights vary so the circle reads as an equalizer at rest as well as in motion.
const BARS = [
  { height: 7, delay: 0 },
  { height: 11, delay: 140 },
  { height: 15, delay: 280 },
  { height: 11, delay: 90 },
  { height: 8, delay: 220 },
];

interface Props {
  stage: AgentStage;
}

export default function AgentIndicator({ stage }: Props) {
  const working = stage !== "ready";

  // No surrounding card: the ring and the two lines float directly on the stage.
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line">
        <div className="flex items-center gap-[2px]">
          {BARS.map((bar, index) => (
            <span
              key={index}
              className={`w-[2px] rounded-full bg-accent ${
                working ? "agent-bar" : "agent-bar-rest"
              }`}
              style={{ height: bar.height, animationDelay: `${bar.delay}ms` }}
            />
          ))}
        </div>
      </div>

      <div className="min-w-[124px]">
        <div className="text-[11.5px] leading-tight font-medium text-fg2">
          {working ? "Agent thinking" : "Agent"}
        </div>
        <div
          key={stage}
          className="stage-in mt-0.5 text-[10.5px] leading-tight text-fg3"
        >
          {STAGE_LABEL[stage]}
        </div>
      </div>
    </div>
  );
}
