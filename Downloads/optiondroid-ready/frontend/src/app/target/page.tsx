"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import clsx from "clsx";
import type { CalculatorParams, CalculatorResponse } from "@/lib/types";
import { useExpirations } from "@/hooks/useOptions";
import { useCalculator } from "@/hooks/useCalculator";
import InputPanel from "@/components/calculator/InputPanel";
import RecommendationCards from "@/components/calculator/RecommendationCards";
import ROIChart from "@/components/calculator/ROIChart";
import StrikeTable from "@/components/calculator/StrikeTable";
import AvoidList from "@/components/calculator/AvoidList";
import { ErrorState } from "@/components/ui/Badge";

const DEFAULT_PARAMS: CalculatorParams = {
  ticker: "SPY",
  current_price: 0,
  target_price: 0,
  option_type: "auto",
  expiration: "",
};

// ── Expiry-fit badge ──────────────────────────────────────────────────────────

function ExpiryFitBadge({ score, dte }: { score: number; dte: number }) {
  const pct = Math.round(score * 100);
  const { label, cls } = score >= 0.75
    ? { label: "Good fit", cls: "text-call bg-call/10 border-call/30" }
    : score >= 0.50
    ? { label: "Decent fit", cls: "text-warn bg-warn/10 border-warn/30" }
    : { label: "Poor fit", cls: "text-put bg-put/10 border-put/30" };
  return (
    <span className={clsx("inline-flex items-center gap-1 text-2xs font-medium px-1.5 py-0.5 rounded border", cls)}>
      {label} {pct}% · {dte}d
    </span>
  );
}

// ── Summary bar for one result ────────────────────────────────────────────────

function SummaryBar({ data }: { data: CalculatorResponse }) {
  return (
    <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-text-muted">
      <span>
        <span className="text-text-primary font-semibold font-mono">{data.ticker}</span>
        <span className="ml-2">@ <span className="font-mono text-text-primary">${data.current_price.toFixed(2)}</span></span>
      </span>
      <span>
        Target{" "}
        <span className={clsx("font-mono font-semibold", data.move_pct >= 0 ? "text-call" : "text-put")}>
          ${data.target_price.toFixed(2)} ({data.move_pct > 0 ? "+" : ""}{data.move_pct.toFixed(2)}%)
        </span>
      </span>
      <span>
        Type <span className="text-text-primary font-semibold uppercase">{data.option_type}</span>
      </span>
      <span>
        Expiry <span className="text-text-primary font-semibold font-mono">{data.expiration}</span>
      </span>
      <ExpiryFitBadge score={data.expiry_fit_score} dte={data.dte} />
      <span className="ml-auto text-2xs">
        {data.all_strikes.length} strikes analyzed
      </span>
    </div>
  );
}

// ── Full result block for one expiry ─────────────────────────────────────────

function ResultBlock({ data, label }: { data: CalculatorResponse; label?: string }) {
  return (
    <div className="space-y-5">
      {label && (
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-accent border border-accent/40 bg-accent/10 px-2 py-0.5 rounded-md">
            {label}
          </span>
          <div className="flex-1 h-px bg-bg-border" />
        </div>
      )}
      <SummaryBar data={data} />
      <RecommendationCards data={data} />
      <ROIChart data={data} />
      <StrikeTable strikes={data.all_strikes} currentPrice={data.current_price} targetPrice={data.target_price} />
      {data.avoid_list.length > 0 && <AvoidList strikes={data.avoid_list} />}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TargetPage() {
  const [params, setParams]           = useState<CalculatorParams>(DEFAULT_PARAMS);
  const [submitted, setSubmitted]     = useState<CalculatorParams | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareExpiry, setCompareExpiry]     = useState("");
  const [compareSubmitted, setCompareSubmitted] = useState<CalculatorParams | null>(null);

  const { data: expirations } = useExpirations(params.ticker || null);
  const expirationList = expirations?.expirations ?? [];

  // Reset on ticker change
  const prevTickerRef = useRef(params.ticker);
  useEffect(() => {
    if (params.ticker !== prevTickerRef.current) {
      prevTickerRef.current = params.ticker;
      setParams(p => ({ ...p, expiration: "", current_price: 0, target_price: 0 }));
      setSubmitted(null);
      setCompareExpiry("");
      setCompareSubmitted(null);
    }
  }, [params.ticker]);

  // Reset compare when mode is toggled off
  useEffect(() => {
    if (!compareMode) {
      setCompareExpiry("");
      setCompareSubmitted(null);
    }
  }, [compareMode]);

  const { data, error, isLoading }             = useCalculator(submitted);
  const { data: compareData, error: compareError, isLoading: compareLoading } =
    useCalculator(compareSubmitted);

  const loading = isLoading || compareLoading;

  const handleChange = useCallback((partial: Partial<CalculatorParams>) => {
    setParams(p => ({ ...p, ...partial }));
  }, []);

  const handleSubmit = useCallback(() => {
    const snap = { ...params };
    setSubmitted(snap);
    if (compareMode && compareExpiry) {
      setCompareSubmitted({ ...snap, expiration: compareExpiry });
    } else {
      setCompareSubmitted(null);
    }
  }, [params, compareMode, compareExpiry]);

  const hasResults = data && !error;
  const hasCompare = compareData && !compareError && compareMode;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Target Move Calculator</h1>
        <p className="text-sm text-text-muted">
          Enter a price target to find the best option strikes for your expected move
        </p>
      </div>

      {/* Input panel */}
      <InputPanel
        params={params}
        expirations={expirationList}
        onChange={handleChange}
        onSubmit={handleSubmit}
        loading={loading}
        compareMode={compareMode}
        onCompareModeChange={setCompareMode}
        compareExpiry={compareExpiry}
        onCompareExpiryChange={setCompareExpiry}
      />

      {/* Errors */}
      {error && <ErrorState message={`Analysis failed: ${(error as Error).message}`} />}
      {compareError && (
        <ErrorState message={`Compare analysis failed: ${(compareError as Error).message}`} />
      )}

      {/* Results */}
      {hasResults && (
        <div className="space-y-8">
          {hasCompare ? (
            /* Side-by-side compare layout */
            <div className="space-y-8">
              <ResultBlock data={data} label={`Expiry A · ${data.expiration}`} />
              <ResultBlock data={compareData} label={`Expiry B · ${compareData.expiration}`} />
            </div>
          ) : (
            <ResultBlock data={data} />
          )}
        </div>
      )}

      {/* Empty state */}
      {!hasResults && !isLoading && !error && (
        <div className="card flex flex-col items-center justify-center py-16 text-center space-y-2">
          <p className="text-text-muted text-sm">
            Fill in the form above and click{" "}
            <span className="text-text-primary font-medium">Analyze Strikes</span> to see recommendations.
          </p>
          <p className="text-text-muted text-xs">
            Use <span className="text-text-secondary">Nearest</span> or{" "}
            <span className="text-text-secondary">Weekly</span> quick-select to pick an expiration fast.
          </p>
        </div>
      )}
    </div>
  );
}
