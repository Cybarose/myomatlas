import type { ReactNode } from "react";

interface Props {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}

export default function Drawer({ open, title, subtitle, onClose, children }: Props) {
  return (
    <aside
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

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">{children}</div>
      </div>
    </aside>
  );
}
