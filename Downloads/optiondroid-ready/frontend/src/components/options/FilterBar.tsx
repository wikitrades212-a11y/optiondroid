"use client";

import clsx from "clsx";
import type { ChainFilters, SortMetric } from "@/lib/types";

interface Props {
  filters: ChainFilters;
  onChange: (f: Partial<ChainFilters>) => void;
  expirations: string[];
}

const METRICS: { value: SortMetric; label: string }[] = [
  { value: "unusual_score",  label: "Score" },
  { value: "open_interest",  label: "OI" },
  { value: "oi_notional",    label: "OI $" },
  { value: "volume",         label: "Volume" },
  { value: "vol_notional",   label: "Vol $" },
];

export default function FilterBar({ filters, onChange, expirations }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-bg-surface border border-bg-border rounded-xl">

      {/* Expiry picker */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-text-muted">Expiry</label>
        <select
          className="input text-xs py-1"
          value={filters.expiration}
          onChange={e => onChange({ expiration: e.target.value })}
        >
          <option value="">All</option>
          {expirations.map(exp => (
            <option key={exp} value={exp}>{exp}</option>
          ))}
        </select>
      </div>

      {/* Call / Put / Both */}
      <div className="flex items-center gap-1 bg-bg-raised rounded-lg p-0.5">
        {(["both", "call", "put"] as const).map(t => (
          <button
            key={t}
            onClick={() => onChange({ optionType: t })}
            className={clsx(
              "text-xs px-3 py-1 rounded-md font-medium capitalize transition-colors",
              filters.optionType === t
                ? t === "call" ? "bg-call text-white"
                  : t === "put" ? "bg-put text-white"
                  : "bg-accent text-white"
                : "text-text-muted hover:text-text-primary"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Min OI */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-text-muted">Min OI</label>
        <input
          type="number"
          className="input text-xs py-1 w-24"
          value={filters.minOI}
          min={0}
          onChange={e => onChange({ minOI: parseInt(e.target.value) || 0 })}
        />
      </div>

      {/* Min Volume */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-text-muted">Min Vol</label>
        <input
          type="number"
          className="input text-xs py-1 w-24"
          value={filters.minVolume}
          min={0}
          onChange={e => onChange({ minVolume: parseInt(e.target.value) || 0 })}
        />
      </div>

      {/* Sort */}
      <div className="flex items-center gap-2 ml-auto">
        <label className="text-xs text-text-muted">Sort</label>
        <div className="flex items-center gap-1 bg-bg-raised rounded-lg p-0.5">
          {METRICS.map(m => (
            <button
              key={m.value}
              onClick={() => onChange({ sortBy: m.value })}
              className={clsx(
                "text-xs px-2.5 py-1 rounded-md font-medium transition-colors",
                filters.sortBy === m.value
                  ? "bg-accent text-white"
                  : "text-text-muted hover:text-text-primary"
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
