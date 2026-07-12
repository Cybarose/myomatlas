import { useState } from "react";
import {
  BLEEDING_LABEL,
  EMPTY_INTAKE,
  FERTILITY_LABEL,
  MENOPAUSAL_LABEL,
  RISK_FACTORS,
} from "../api/intake";
import type {
  BleedingSeverity,
  ClinicalIntake,
  FertilityDesire,
  MenopausalStatus,
} from "../types";

interface Props {
  intake: ClinicalIntake;
  onSubmit: (intake: ClinicalIntake) => void;
  onClose: () => void;
}

const FIELD =
  "w-full rounded-md border border-accent/25 bg-bg/60 px-2.5 py-2 text-[13px] text-fg outline-none transition-colors focus:border-accent";

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="mb-1.5 block text-[9.5px] font-semibold tracking-[0.14em] text-fg3 uppercase">
      {children}
    </span>
  );
}

export default function IntakeForm({ intake, onSubmit, onClose }: Props) {
  const [draft, setDraft] = useState<ClinicalIntake>(intake);

  const toggleRisk = (factor: string) =>
    setDraft((current) => ({
      ...current,
      riskFactors: current.riskFactors.includes(factor)
        ? current.riskFactors.filter((f) => f !== factor)
        : [...current.riskFactors, factor],
    }));

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center p-8">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/50"
      />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(draft);
        }}
        className="card-surface relative flex max-h-full w-[420px] flex-col overflow-hidden rounded-xl border border-accent/80 shadow-xl shadow-black/40"
      >
        <div className="shrink-0 px-5 pt-5">
          <h2 className="font-serif text-[19px] leading-none font-semibold text-fg">
            Patient details
          </h2>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-fg3">
            All fields are optional. Anything you leave blank is treated as not provided.
            Nothing is stored beyond this session.
          </p>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5">
          <div>
            <Label>Age</Label>
            <input
              type="number"
              min={10}
              max={100}
              value={draft.age ?? ""}
              placeholder="Not provided"
              onChange={(event) =>
                setDraft({
                  ...draft,
                  age: event.target.value === "" ? null : Number(event.target.value),
                })
              }
              className={`figure ${FIELD}`}
            />
          </div>

          <div>
            <Label>Menopausal status</Label>
            <select
              value={draft.menopausalStatus ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  menopausalStatus:
                    event.target.value === ""
                      ? null
                      : (event.target.value as MenopausalStatus),
                })
              }
              className={FIELD}
            >
              <option value="">Not provided</option>
              {(Object.keys(MENOPAUSAL_LABEL) as MenopausalStatus[]).map((key) => (
                <option key={key} value={key}>
                  {MENOPAUSAL_LABEL[key]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label>Bleeding severity</Label>
            <select
              value={draft.bleedingSeverity ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  bleedingSeverity:
                    event.target.value === ""
                      ? null
                      : (event.target.value as BleedingSeverity),
                })
              }
              className={FIELD}
            >
              <option value="">Not provided</option>
              {(Object.keys(BLEEDING_LABEL) as BleedingSeverity[]).map((key) => (
                <option key={key} value={key}>
                  {BLEEDING_LABEL[key]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label>Fertility desire</Label>
            <select
              value={draft.fertilityDesire ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  fertilityDesire:
                    event.target.value === ""
                      ? null
                      : (event.target.value as FertilityDesire),
                })
              }
              className={FIELD}
            >
              <option value="">Not provided</option>
              {(Object.keys(FERTILITY_LABEL) as FertilityDesire[]).map((key) => (
                <option key={key} value={key}>
                  {FERTILITY_LABEL[key]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label>Risk factors</Label>
            <div className="space-y-1.5">
              {RISK_FACTORS.map((factor) => (
                <label
                  key={factor}
                  className="flex cursor-pointer items-center gap-2.5 text-[12.5px] text-fg2"
                >
                  <input
                    type="checkbox"
                    checked={draft.riskFactors.includes(factor)}
                    onChange={() => toggleRisk(factor)}
                    className="h-3.5 w-3.5 accent-accent"
                  />
                  {factor}
                </label>
              ))}
            </div>
          </div>

          <div>
            <Label>Notes</Label>
            <textarea
              rows={2}
              value={draft.notes}
              placeholder="Anything else the agent should know"
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
              className={`${FIELD} resize-none`}
            />
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-between gap-2 border-t border-accent/25 px-5 py-4">
          <button
            type="button"
            onClick={() => setDraft(EMPTY_INTAKE)}
            className="text-[12px] font-medium text-fg3 transition-colors hover:text-fg"
          >
            Clear
          </button>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-line px-3.5 py-2 text-[12px] font-medium text-fg2 transition-colors hover:border-fg3 hover:text-fg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg border border-accent bg-accent px-3.5 py-2 text-[12px] font-medium text-bg transition-opacity hover:opacity-90"
            >
              Analyze with context
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
