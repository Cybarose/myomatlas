import { useState } from "react";

interface Props {
  caseId: string;
  cases: string[];
  busy: boolean;
  hasContext: boolean;
  onSelectCase: (caseId: string) => void;
  onOpenIntake: () => void;
}

export default function Header({
  caseId,
  cases,
  busy,
  hasContext,
  onSelectCase,
  onOpenIntake,
}: Props) {
  const [open, setOpen] = useState(false);

  return (
    <header className="z-30 flex shrink-0 items-center justify-between gap-6 border-b border-line bg-surface px-6 py-3">
      <div className="flex items-baseline gap-3.5">
        <h1 className="font-serif text-[22px] leading-none font-semibold tracking-[-0.01em] text-fg">
          Myomatlas
        </h1>
        <span className="hidden h-3.5 w-px self-center bg-line sm:block" />
        <p className="hidden text-[12.5px] text-fg3 sm:block">
          Decision support for abnormal uterine bleeding
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden items-baseline gap-2 md:flex">
          <span className="text-[10px] font-medium tracking-[0.14em] text-fg3 uppercase">
            Case
          </span>
          <span className="figure text-[12.5px] text-fg2">{caseId}</span>
        </div>

        {/* Accent outline and dot once clinical context is in play. */}
        <button
          type="button"
          disabled={busy}
          onClick={onOpenIntake}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
            hasContext
              ? "border-accent text-accent"
              : "border-line text-fg2 hover:border-fg3 hover:text-fg"
          }`}
        >
          {hasContext && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
          Patient details
        </button>

        <div className="relative">
          <button
            type="button"
            disabled={busy || cases.length === 0}
            onClick={() => setOpen((value) => !value)}
            className="rounded-lg border border-line px-3 py-1.5 text-[12px] font-medium text-fg2 transition-colors hover:border-fg3 hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
          >
            Load case
          </button>

          {open && (
            <div className="scroll-slim card-surface absolute top-full right-0 z-40 mt-2 max-h-72 w-56 overflow-y-auto rounded-lg border border-accent/80">
              {cases.map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    if (id !== caseId) onSelectCase(id);
                  }}
                  className={`figure block w-full px-3 py-2 text-left text-[12px] transition-colors hover:bg-fg/[0.06] ${
                    id === caseId ? "text-accent" : "text-fg2"
                  }`}
                >
                  {id}
                </button>
              ))}
            </div>
          )}
        </div>

        <span className="hidden text-[11px] text-fg3 lg:block">
          Decision support, not a diagnosis.
        </span>
      </div>
    </header>
  );
}
