"use client";

import { useState } from "react";
import clsx from "clsx";
import type { StrikeAnalysis, StrikeTier } from "@/lib/types";

interface Props {
  strikes: StrikeAnalysis[];
  currentPrice: number;
  targetPrice: number;
}

const TIER_STYLE: Record<StrikeTier, string> = {
  aggressive: "text-put",
  balanced: "text-accent",
  safer: "text-call",
  avoid: "text-text-muted",
};

const TIER_DOT: Record<StrikeTier, string> = {
  aggressive: "bg-put",
  balanced: "bg-accent",
  safer: "bg-call",
  avoid: "bg-text-muted",
};

type SortKey = "strike" | "estimated_roi_pct" | "mid" | "delta" | "spread_pct" | "volume" | "open_interest";

export default function StrikeTable({ strikes, currentPrice, targetPrice }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("estimated_roi_pct");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showAvoid, setShowAvoid] = useState(false);

  const filtered = showAvoid ? strikes : strikes.filter(s => s.tier !== "avoid");
  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? -Infinity;
    const bv = b[sortKey] ?? -Infinity;
    return sortDir === "asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  function handleSort(key: SortKey) {
    if (key === sortKey) setDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  function setDir(fn: (d: "asc" | "desc") => "asc" | "desc") {
    setSortDir(fn(sortDir));
  }

  const Th = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      className="px-3 py-2.5 text-left text-2xs font-semibold text-text-muted uppercase tracking-wide cursor-pointer hover:text-text-primary transition-colors select-none whitespace-nowrap"
      onClick={() => handleSort(k)}
    >
      {label}
      {sortKey === k && <span className="ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>}
    </th>
  );

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-sm font-semibold text-text-primary">All Strikes</h2>
        <label className="flex items-center gap-2 text-2xs text-text-muted cursor-pointer">
          <input type="checkbox" checked={showAvoid} onChange={e => setShowAvoid(e.target.checked)}
            className="w-3 h-3 accent-accent" />
          Show avoid
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl border border-bg-border">
        <table className="w-full text-xs">
          <thead className="bg-bg-raised border-b border-bg-border">
            <tr>
              <th className="px-3 py-2.5 text-left text-2xs font-semibold text-text-muted uppercase tracking-wide whitespace-nowrap">Tier</th>
              <Th label="Strike" k="strike" />
              <Th label="Mid" k="mid" />
              <Th label="Est. Value" k="estimated_roi_pct" />
              <Th label="ROI %" k="estimated_roi_pct" />
              <Th label="Delta" k="delta" />
              <Th label="Spread%" k="spread_pct" />
              <Th label="Volume" k="volume" />
              <Th label="OI" k="open_interest" />
              <th className="px-3 py-2.5 text-left text-2xs font-semibold text-text-muted uppercase tracking-wide whitespace-nowrap">Badges</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-bg-border">
            {sorted.map(s => (
              <tr key={`${s.strike}-${s.option_type}`}
                className={clsx("transition-colors hover:bg-bg-hover", s.tier === "avoid" && "opacity-50")}>
                <td className="px-3 py-2">
                  <span className={clsx("flex items-center gap-1.5", TIER_STYLE[s.tier])}>
                    <span className={clsx("w-1.5 h-1.5 rounded-full", TIER_DOT[s.tier])} />
                    <span className="capitalize font-medium">{s.tier}</span>
                  </span>
                </td>
                <td className="px-3 py-2 font-mono font-semibold text-text-primary whitespace-nowrap">
                  ${s.strike.toFixed(0)}
                  <span className="ml-1 text-2xs text-text-muted uppercase">{s.option_type}</span>
                </td>
                <td className="px-3 py-2 font-mono text-text-secondary">${s.mid.toFixed(2)}</td>
                <td className="px-3 py-2 font-mono text-text-secondary">${s.estimated_value_at_target.toFixed(2)}</td>
                <td className={clsx("px-3 py-2 font-mono font-semibold", s.estimated_roi_pct > 0 ? "text-call" : "text-put")}>
                  {s.estimated_roi_pct > 0 ? "+" : ""}{s.estimated_roi_pct.toFixed(0)}%
                </td>
                <td className="px-3 py-2 font-mono text-text-secondary">
                  {s.delta !== null ? s.delta.toFixed(2) : "—"}
                </td>
                <td className={clsx("px-3 py-2 font-mono", s.spread_pct > 20 ? "text-put" : s.spread_pct > 10 ? "text-yellow-400" : "text-text-secondary")}>
                  {s.spread_pct.toFixed(1)}%
                </td>
                <td className="px-3 py-2 font-mono text-text-secondary">{s.volume.toLocaleString()}</td>
                <td className="px-3 py-2 font-mono text-text-secondary">{s.open_interest.toLocaleString()}</td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-0.5">
                    {s.badges.map(b => (
                      <span key={b} className="text-2xs px-1 py-0.5 rounded bg-bg-raised border border-bg-border text-text-muted">
                        {b}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-text-muted text-xs">No strikes to display</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
