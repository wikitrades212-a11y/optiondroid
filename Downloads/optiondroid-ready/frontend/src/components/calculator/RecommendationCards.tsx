"use client";

import clsx from "clsx";
import type { StrikeAnalysis, CalculatorResponse } from "@/lib/types";

interface Props {
  data: CalculatorResponse;
}

const TIER_CONFIG = {
  aggressive: {
    label: "Aggressive",
    sub: "High ROI · Higher risk",
    accent: "text-put",
    bg: "bg-put/10",
    border: "border-put/30",
    dot: "bg-put",
  },
  balanced: {
    label: "Balanced",
    sub: "Best risk/reward",
    accent: "text-accent",
    bg: "bg-accent/10",
    border: "border-accent/30",
    dot: "bg-accent",
  },
  safer: {
    label: "Safer / Liquid",
    sub: "Lower risk · Better fill",
    accent: "text-call",
    bg: "bg-call/10",
    border: "border-call/30",
    dot: "bg-call",
  },
} as const;

function Badge({ label }: { label: string }) {
  return (
    <span className="inline-block text-2xs font-medium px-1.5 py-0.5 rounded-md bg-bg-raised border border-bg-border text-text-muted">
      {label}
    </span>
  );
}

function StrikeCard({ strike, tier }: { strike: StrikeAnalysis; tier: keyof typeof TIER_CONFIG }) {
  const cfg = TIER_CONFIG[tier];
  return (
    <div className={clsx("rounded-xl border p-4 space-y-3 flex flex-col", cfg.bg, cfg.border)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className={clsx("w-2 h-2 rounded-full", cfg.dot)} />
            <span className={clsx("text-xs font-semibold uppercase tracking-wide", cfg.accent)}>{cfg.label}</span>
          </div>
          <p className="text-2xs text-text-muted mt-0.5">{cfg.sub}</p>
        </div>
        <div className="text-right shrink-0">
          <p className={clsx("text-2xl font-bold font-mono", cfg.accent)}>
            ${strike.strike.toFixed(0)}
          </p>
          <p className="text-2xs text-text-muted uppercase">{strike.option_type}</p>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-bg-surface rounded-lg p-2 text-center">
          <p className="text-2xs text-text-muted mb-0.5">Est. ROI</p>
          <p className={clsx("text-base font-bold font-mono", strike.estimated_roi_pct > 0 ? "text-call" : "text-put")}>
            {strike.estimated_roi_pct > 0 ? "+" : ""}{strike.estimated_roi_pct.toFixed(0)}%
          </p>
        </div>
        <div className="bg-bg-surface rounded-lg p-2 text-center">
          <p className="text-2xs text-text-muted mb-0.5">Est. Value</p>
          <p className="text-base font-bold font-mono text-text-primary">${strike.estimated_value_at_target.toFixed(2)}</p>
        </div>
        <div className="bg-bg-surface rounded-lg p-2 text-center">
          <p className="text-2xs text-text-muted mb-0.5">Mid Price</p>
          <p className="text-sm font-mono text-text-primary">${strike.mid.toFixed(2)}</p>
        </div>
        <div className="bg-bg-surface rounded-lg p-2 text-center">
          <p className="text-2xs text-text-muted mb-0.5">Ideal Max</p>
          <p className="text-sm font-mono text-text-primary">${strike.ideal_max_entry.toFixed(2)}</p>
        </div>
      </div>

      {/* Breakeven */}
      <div className="flex items-center justify-between text-2xs text-text-muted border-t border-bg-border pt-2">
        <span>Breakeven</span>
        <span className="font-mono text-text-secondary">
          ${strike.breakeven.toFixed(2)} ({strike.breakeven_move_pct > 0 ? "+" : ""}{strike.breakeven_move_pct.toFixed(1)}%)
        </span>
      </div>

      {/* Greeks */}
      {(strike.delta !== null || strike.gamma !== null) && (
        <div className="flex gap-3 text-2xs text-text-muted">
          {strike.delta !== null && <span>Δ <span className="text-text-secondary font-mono">{strike.delta.toFixed(2)}</span></span>}
          {strike.gamma !== null && <span>Γ <span className="text-text-secondary font-mono">{strike.gamma.toFixed(4)}</span></span>}
          {strike.theta !== null && <span>Θ <span className="text-put font-mono">{strike.theta.toFixed(4)}</span></span>}
          {strike.vega !== null && <span>V <span className="text-text-secondary font-mono">{strike.vega.toFixed(4)}</span></span>}
        </div>
      )}

      {/* Badges */}
      {strike.badges.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {strike.badges.map(b => <Badge key={b} label={b} />)}
        </div>
      )}

      {/* Liquidity */}
      <div className="flex items-center justify-between text-2xs text-text-muted">
        <span>Liquidity</span>
        <div className="flex gap-0.5">
          {[1,2,3,4,5].map(i => (
            <span key={i} className={clsx("w-3 h-1.5 rounded-sm", i <= Math.round(strike.liquidity_score / 2) ? cfg.dot : "bg-bg-raised")} />
          ))}
        </div>
      </div>

      {/* Volume / OI */}
      <div className="flex justify-between text-2xs text-text-muted border-t border-bg-border pt-2">
        <span>Vol <span className="text-text-secondary font-mono">{strike.volume.toLocaleString()}</span></span>
        <span>OI <span className="text-text-secondary font-mono">{strike.open_interest.toLocaleString()}</span></span>
        <span>Spread <span className="text-text-secondary font-mono">{strike.spread_pct.toFixed(1)}%</span></span>
      </div>
    </div>
  );
}

function EmptyCard({ tier }: { tier: keyof typeof TIER_CONFIG }) {
  const cfg = TIER_CONFIG[tier];
  return (
    <div className={clsx("rounded-xl border p-4 flex flex-col items-center justify-center min-h-[220px] opacity-50", cfg.bg, cfg.border)}>
      <span className={clsx("text-xs font-semibold uppercase tracking-wide", cfg.accent)}>{cfg.label}</span>
      <p className="text-2xs text-text-muted mt-1">No suitable strike found</p>
    </div>
  );
}

export default function RecommendationCards({ data }: Props) {
  const cards: [keyof typeof TIER_CONFIG, StrikeAnalysis | null][] = [
    ["aggressive", data.recommended_aggressive],
    ["balanced", data.recommended_balanced],
    ["safer", data.recommended_safer],
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">Recommendations</h2>
        <span className="text-2xs text-text-muted">
          {data.move_pct > 0 ? "+" : ""}{data.move_pct.toFixed(2)}% move · {data.option_type.toUpperCase()} · {data.expiration}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map(([tier, strike]) =>
          strike
            ? <StrikeCard key={tier} strike={strike} tier={tier} />
            : <EmptyCard key={tier} tier={tier} />
        )}
      </div>
    </div>
  );
}
