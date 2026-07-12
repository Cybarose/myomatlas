import { useEffect, useRef, type ReactNode } from "react";

interface Props {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}

export default function Drawer({ open, title, subtitle, onClose, children }: Props) {
  const panelRef = useRef<HTMLElement>(null);

  // Click-outside-to-close. A pointer listener rather than a scrim, so the 3D stage and
  // the myoma cards stay live behind an open panel instead of sitting under a blocker.
  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (panelRef.current?.contains(target)) return;
      // The panel toggles own their open/closed state, so let them handle their own click.
      if (target.closest("[data-panel-toggle]")) return;
      onClose();
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open, onClose]);

  return (
    <aside
      ref={panelRef}
      className={`grain-card panel-surface absolute top-0 right-0 bottom-0 z-30 w-[420px] border-l border-accent/80 transition-transform duration-200 ${
        open ? "translate-x-0" : "pointer-events-none translate-x-full"
      }`}
      aria-hidden={!open}
    >
      <div className="flex h-full flex-col">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-accent/25 px-5 py-4">
          <div>
            <h2 className="font-serif text-[19px] leading-tight font-semibold text-fg">
              {title}
            </h2>
            {subtitle && <p className="figure mt-1 text-[11.5px] text-fg3">{subtitle}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="-mt-1 -mr-1 rounded-md px-2 py-1 text-[16px] leading-none text-fg3 transition-colors hover:bg-fg/10 hover:text-fg"
          >
            &times;
          </button>
        </header>

        <div className="scroll-slim min-h-0 flex-1 overflow-y-auto px-5 py-5">
          {children}
        </div>
      </div>
    </aside>
  );
}
