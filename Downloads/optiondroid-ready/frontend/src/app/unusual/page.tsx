"use client";

import { useState, useMemo, useCallback } from "react";
import { useUnusual } from "@/hooks/useOptions";
import TickerInput from "@/components/ui/TickerInput";
import UnusualTable from "@/components/options/UnusualTable";
import UnusualScoreChart from "@/components/charts/UnusualScoreChart";
import SummaryCards from "@/components/options/SummaryCards";
import type { OptionContract, UnusualFilters } from "@/lib/types";
import { fmtNotional, fmtTimestamp } from "@/lib/formatters";
import { ErrorState } from "@/components/ui/Badge";
import clsx from "clsx";
import { useChain } from "@/hooks/useOptions";

const AUTO_REFRESH = 90_000;

const FILTER_CHIPS = [
  { id: "call",     label: "Calls",          color: "border-call/40 text-call" },
  { id: "put",      label: "Puts",           color: "border-put/40 text-put" },
  { id: "nearest",  label: "Nearest Expiry", color: "border-accent/40 text-accent" },
  { id: "weeklies", label: "Weeklies",       color: "border-purple-500/40 text-purple-400" },
  { id: "High Vol/OI",         label: "High Vol/OI",         color: "border-warn/40 text-warn" },
  { id: "Big Premium",         label: "Big Premium",         color: "border-accent/40 text-accent" },
  { id: "Near ATM Aggression", label: "Near ATM",            color: "border-sky-500/40 text-sky-400" },
  { id: "Far OTM Lottery",     label: "Far OTM Lottery",     color: "border-orange-500/40 text-orange-400" },
];

function isWeekly(exp: string): boolean {
  const d = new Date(exp + "T00:00:00");
  return d.getDay() === 5; // Friday = weekly
}

export default function UnusualPage() {
  const [ticker, setTicker] = useState("SPY");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [minScore, setMinScore] = useState(0);
  const [activeChips, setActiveChips] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState<"combined" | "calls" | "puts">("combined");

  const { data, error, isLoading, mutate } = useUnusual(ticker, {
    refreshInterval: autoRefresh ? AUTO_REFRESH : 0,
  });
  const { data: chain, isLoading: chainLoading } = useChain(ticker);

  const toggleChip = (id: string) => {
    setActiveChips(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  const filterContracts = useCallback((contracts: OptionContract[]) => {
    let cs = contracts.filter(c => c.unusual_score >= minScore);

    if (activeChips.has("call")) cs = cs.filter(c => c.option_type === "call");
    if (activeChips.has("put"))  cs = cs.filter(c => c.option_type === "put");

    if (activeChips.has("nearest") && data?.combined?.length) {
      const nearestExp = data.combined[0]?.expiration;
      if (nearestExp) cs = cs.filter(c => c.expiration === nearestExp);
    }

    if (activeChips.has("weeklies")) {
      cs = cs.filter(c => isWeekly(c.expiration));
    }

    // Tag filters
    const tagFilters = [
      "High Vol/OI", "Big Premium", "Near ATM Aggression", "Far OTM Lottery"
    ].filter(t => activeChips.has(t));
    if (tagFilters.length > 0) {
      cs = cs.filter(c => tagFilters.some(tag => c.reason_tags.includes(tag)));
    }

    return cs;
  }, [minScore, activeChips, data]);

  const calls     = useMemo(() => filterContracts(data?.top_calls ?? []), [filterContracts, data]);
  const puts      = useMemo(() => filterContracts(data?.top_puts ?? []),  [filterContracts, data]);
  const combined  = useMemo(() => filterContracts(data?.combined ?? []),  [filterContracts, data]);

  const visible = tab === "calls" ? calls : tab === "puts" ? puts : combined;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Unusual Options</h1>
          {data && (
            <p className="text-sm text-text-muted">
              {`Total unusual flow: `}
              <span className="text-accent font-mono font-medium">
                {fmtNotional(data.total_unusual_flow)}
              </span>
              {` · Updated ${fmtTimestamp(data.timestamp)}`}
            </p>
          )}
        </div>
        <TickerInput
          value={ticker}
          onChange={setTicker}
          onRefresh={mutate}
          loading={isLoading}
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          refreshInterval={90}
        />
      </div>

      {error && <ErrorState message={(error as Error).message} />}

      {/* Summary cards */}
      <SummaryCards
        data={data}
        loading={isLoading}
        underlying={chain?.underlying_price}
        callPutRatio={chain?.call_put_ratio}
        totalCallOI={chain?.total_call_oi}
        totalPutOI={chain?.total_put_oi}
      />

      {/* Score chart */}
      {!error && (
        <UnusualScoreChart
          contracts={combined}
          loading={isLoading}
          limit={20}
        />
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-bg-surface border border-bg-border rounded-xl">
        {/* Score slider */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-text-muted whitespace-nowrap">
            Min Score: <span className="text-text-primary font-mono">{minScore}</span>
          </label>
          <input
            type="range"
            min={0}
            max={90}
            step={5}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-28 accent-accent"
          />
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-1.5">
          {FILTER_CHIPS.map(chip => (
            <button
              key={chip.id}
              onClick={() => toggleChip(chip.id)}
              className={clsx(
                "text-xs px-2.5 py-1 rounded-full border font-medium transition-all",
                activeChips.has(chip.id)
                  ? `${chip.color} bg-current/10`
                  : "border-bg-border text-text-muted hover:border-text-muted"
              )}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs + Table */}
      <div className="space-y-3">
        <div className="flex items-center gap-1 bg-bg-raised rounded-lg p-0.5 w-fit">
          {(["combined", "calls", "puts"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={clsx(
                "text-xs px-4 py-1.5 rounded-md font-medium capitalize transition-colors",
                tab === t
                  ? t === "calls" ? "bg-call text-white"
                    : t === "puts" ? "bg-put text-white"
                    : "bg-accent text-white"
                  : "text-text-muted hover:text-text-primary"
              )}
            >
              {t} {t === "calls" ? `(${calls.length})` : t === "puts" ? `(${puts.length})` : `(${combined.length})`}
            </button>
          ))}
        </div>

        <UnusualTable
          contracts={visible}
          loading={isLoading}
          limit={50}
        />
      </div>
    </div>
  );
}
