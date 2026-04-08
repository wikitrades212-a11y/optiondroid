"use client";

import { useState, useMemo } from "react";
import clsx from "clsx";
import { Search, Zap, Calendar, GitCompare } from "lucide-react";
import type { CalculatorParams } from "@/lib/types";

interface Props {
  params: CalculatorParams;
  expirations: string[];
  onChange: (p: Partial<CalculatorParams>) => void;
  onSubmit: () => void;
  loading: boolean;
  compareMode: boolean;
  onCompareModeChange: (v: boolean) => void;
  compareExpiry: string;
  onCompareExpiryChange: (v: string) => void;
}

const POPULAR = ["SPY","QQQ","AAPL","TSLA","NVDA","AMD","MSFT","AMZN","META","GLD"];

function nearestExpiry(expirations: string[]): string | null {
  return expirations[0] ?? null;
}

/**
 * Next expiration that falls on a Friday (YYYY-MM-DD → UTC noon to avoid DST issues).
 */
function nextWeeklyExpiry(expirations: string[]): string | null {
  for (const exp of expirations) {
    if (new Date(`${exp}T12:00:00Z`).getUTCDay() === 5) return exp;
  }
  return null;
}

function fmtExp(exp: string): string {
  if (!exp) return "";
  return new Date(`${exp}T12:00:00Z`).toLocaleDateString("en-US", {
    month: "short", day: "numeric", timeZone: "UTC",
  });
}

interface QuickBtnProps {
  label: string;
  expiry: string | null;
  active: boolean;
  onSet: (v: string) => void;
}
function QuickBtn({ label, expiry, active, onSet }: QuickBtnProps) {
  if (!expiry) return null;
  return (
    <button
      type="button"
      onClick={() => onSet(expiry)}
      className={clsx(
        "text-2xs px-2 py-1 rounded-md font-medium border transition-colors whitespace-nowrap",
        active
          ? "bg-accent/20 border-accent/50 text-accent"
          : "border-bg-border text-text-muted hover:text-text-primary hover:border-accent/40"
      )}
    >
      {label} <span className="font-mono ml-0.5 opacity-75">{fmtExp(expiry)}</span>
    </button>
  );
}

export default function InputPanel({
  params, expirations, onChange, onSubmit, loading,
  compareMode, onCompareModeChange,
  compareExpiry, onCompareExpiryChange,
}: Props) {
  const [tickerOpen, setTickerOpen] = useState(false);

  const movePct = params.current_price > 0 && params.target_price > 0
    ? ((params.target_price - params.current_price) / params.current_price * 100).toFixed(2)
    : null;

  const impliedDirection = params.target_price > params.current_price
    ? "call" : params.target_price < params.current_price ? "put" : null;

  const nearest = useMemo(() => nearestExpiry(expirations), [expirations]);
  const weekly  = useMemo(() => nextWeeklyExpiry(expirations), [expirations]);

  return (
    <div className="card space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">Configure Move</h2>
        <button
          type="button"
          onClick={() => onCompareModeChange(!compareMode)}
          className={clsx(
            "flex items-center gap-1.5 text-2xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors",
            compareMode
              ? "bg-accent/15 border-accent/40 text-accent"
              : "border-bg-border text-text-muted hover:text-text-primary hover:border-accent/40"
          )}
        >
          <GitCompare className="w-3 h-3" />
          Compare Expiries
        </button>
      </div>

      {/* Row 1: Ticker / Prices / Expiry */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Ticker */}
        <div className="space-y-1.5 relative">
          <label className="text-xs text-text-muted font-medium">Ticker</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
            <input
              className="input pl-8 w-full uppercase font-mono tracking-widest"
              value={params.ticker}
              maxLength={6}
              onChange={e => onChange({ ticker: e.target.value.toUpperCase() })}
              onFocus={() => setTickerOpen(true)}
              onBlur={() => setTimeout(() => setTickerOpen(false), 150)}
            />
          </div>
          {tickerOpen && (
            <div className="absolute top-full mt-1 z-50 bg-bg-surface border border-bg-border rounded-xl p-2 grid grid-cols-5 gap-1 w-56 shadow-2xl">
              {POPULAR.map(t => (
                <button key={t} onMouseDown={() => { onChange({ ticker: t }); setTickerOpen(false); }}
                  className={clsx("text-xs font-mono px-2 py-1 rounded-lg transition-colors",
                    t === params.ticker
                      ? "bg-accent text-white"
                      : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                  )}>
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Current price */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">Current Price</label>
          <input type="number" step="0.01" className="input w-full font-mono"
            value={params.current_price || ""}
            onChange={e => onChange({ current_price: parseFloat(e.target.value) || 0 })}
            placeholder="655.00" />
        </div>

        {/* Target price */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">Target Price</label>
          <div className="relative">
            <input type="number" step="0.01" className="input w-full font-mono pr-16"
              value={params.target_price || ""}
              onChange={e => onChange({ target_price: parseFloat(e.target.value) || 0 })}
              placeholder="670.00" />
            {movePct && (
              <span className={clsx(
                "absolute right-2 top-1/2 -translate-y-1/2 text-xs font-mono font-semibold",
                parseFloat(movePct) > 0 ? "text-call" : "text-put"
              )}>
                {parseFloat(movePct) > 0 ? "+" : ""}{movePct}%
              </span>
            )}
          </div>
        </div>

        {/* Primary expiry */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs text-text-muted font-medium">
            <Calendar className="w-3 h-3" />
            Expiration
          </label>
          <select
            className="input w-full"
            value={params.expiration}
            onChange={e => onChange({ expiration: e.target.value })}
          >
            <option value="">Select expiry…</option>
            {expirations.map(exp => (
              <option key={exp} value={exp}>{exp}</option>
            ))}
          </select>
          {expirations.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              <QuickBtn
                label="Nearest"
                expiry={nearest}
                active={params.expiration === nearest}
                onSet={v => onChange({ expiration: v })}
              />
              <QuickBtn
                label="Weekly"
                expiry={weekly}
                active={params.expiration === weekly}
                onSet={v => onChange({ expiration: v })}
              />
            </div>
          )}
        </div>
      </div>

      {/* Compare expiry selector (only in compare mode) */}
      {compareMode && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 border-t border-bg-border/60">
          <div className="col-start-1 md:col-start-4 space-y-1.5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-accent">
              <GitCompare className="w-3 h-3" />
              Compare With
            </label>
            <select
              className="input w-full border-accent/30 focus:border-accent"
              value={compareExpiry}
              onChange={e => onCompareExpiryChange(e.target.value)}
            >
              <option value="">Select expiry…</option>
              {expirations
                .filter(e => e !== params.expiration)
                .map(exp => (
                  <option key={exp} value={exp}>{exp}</option>
                ))}
            </select>
            {expirations.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                <QuickBtn
                  label="Nearest"
                  expiry={nearest !== params.expiration ? nearest : null}
                  active={compareExpiry === nearest}
                  onSet={onCompareExpiryChange}
                />
                <QuickBtn
                  label="Weekly"
                  expiry={weekly !== params.expiration ? weekly : null}
                  active={compareExpiry === weekly}
                  onSet={onCompareExpiryChange}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Row 2: Direction / Filters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Direction */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">
            Direction
            {impliedDirection && (
              <span className={clsx(
                "ml-2 text-2xs font-medium",
                impliedDirection === "call" ? "text-call" : "text-put"
              )}>
                (auto → {impliedDirection.toUpperCase()})
              </span>
            )}
          </label>
          <div className="flex gap-1 bg-bg-raised rounded-lg p-0.5">
            {(["auto", "call", "put"] as const).map(t => (
              <button key={t} onClick={() => onChange({ option_type: t })}
                className={clsx(
                  "flex-1 text-xs py-1.5 rounded-md font-medium capitalize transition-colors",
                  params.option_type === t
                    ? t === "call" ? "bg-call text-white"
                      : t === "put" ? "bg-put text-white"
                      : "bg-accent text-white"
                    : "text-text-muted hover:text-text-primary"
                )}>
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Max premium */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">Max Premium ($)</label>
          <input type="number" step="0.50" className="input w-full font-mono"
            value={params.max_premium || ""}
            onChange={e => onChange({ max_premium: parseFloat(e.target.value) || undefined })}
            placeholder="Optional" />
        </div>

        {/* Risk per trade */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">Risk per Trade ($)</label>
          <input type="number" step="100" className="input w-full font-mono"
            value={params.risk_per_trade || ""}
            onChange={e => onChange({ risk_per_trade: parseFloat(e.target.value) || undefined })}
            placeholder="e.g. 500" />
        </div>

        {/* Preferred strike */}
        <div className="space-y-1.5">
          <label className="text-xs text-text-muted font-medium">Preferred Strike</label>
          <input type="number" step="0.5" className="input w-full font-mono"
            value={params.preferred_strike || ""}
            onChange={e => onChange({ preferred_strike: parseFloat(e.target.value) || undefined })}
            placeholder="Optional" />
        </div>
      </div>

      <button
        onClick={onSubmit}
        disabled={
          loading ||
          !params.expiration ||
          !params.target_price ||
          !params.current_price ||
          (compareMode && !compareExpiry)
        }
        className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Analyzing…
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            Analyze Strikes{compareMode && compareExpiry ? " · 2 Expiries" : ""}
          </>
        )}
      </button>
    </div>
  );
}
