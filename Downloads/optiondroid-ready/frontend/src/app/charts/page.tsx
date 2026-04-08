"use client";

import { useState } from "react";
import { useChain, useUnusual } from "@/hooks/useOptions";
import TickerInput from "@/components/ui/TickerInput";
import OIBarChart from "@/components/charts/OIBarChart";
import CallPutChart from "@/components/charts/CallPutChart";
import UnusualScoreChart from "@/components/charts/UnusualScoreChart";
import ExpiryDistChart from "@/components/charts/ExpiryDistChart";
import { ErrorState } from "@/components/ui/Badge";
import clsx from "clsx";

export default function ChartsPage() {
  const [ticker, setTicker] = useState("SPY");
  const [oiMetric, setOiMetric] = useState<"open_interest" | "oi_notional">("open_interest");

  const { data: chain, error: chainErr, isLoading: chainLoading, mutate: refreshChain } =
    useChain(ticker);
  const { data: unusual, error: unusualErr, isLoading: unusualLoading, mutate: refreshUnusual } =
    useUnusual(ticker);

  const error = chainErr || unusualErr;

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Charts</h1>
          <p className="text-sm text-text-muted">Visual flow analysis</p>
        </div>
        <TickerInput
          value={ticker}
          onChange={t => { setTicker(t); refreshChain(); refreshUnusual(); }}
          onRefresh={() => { refreshChain(); refreshUnusual(); }}
          loading={chainLoading || unusualLoading}
        />
      </div>

      {error && <ErrorState message={(error as Error).message} />}

      {/* OI chart with metric toggle */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-bg-raised rounded-lg p-0.5 w-fit">
            {(["open_interest", "oi_notional"] as const).map(m => (
              <button
                key={m}
                onClick={() => setOiMetric(m)}
                className={clsx(
                  "text-xs px-3 py-1 rounded-md font-medium transition-colors",
                  oiMetric === m
                    ? "bg-accent text-white"
                    : "text-text-muted hover:text-text-primary"
                )}
              >
                {m === "open_interest" ? "OI Count" : "OI Notional"}
              </button>
            ))}
          </div>
        </div>
        <OIBarChart
          contracts={chain?.contracts ?? []}
          loading={chainLoading}
          underlying={chain?.underlying_price}
          metric={oiMetric}
        />
      </div>

      {/* 2-col grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CallPutChart
          callVolume={chain?.total_call_volume ?? 0}
          putVolume={chain?.total_put_volume ?? 0}
          callOI={chain?.total_call_oi ?? 0}
          putOI={chain?.total_put_oi ?? 0}
          loading={chainLoading}
        />
        <UnusualScoreChart
          contracts={unusual?.combined ?? []}
          loading={unusualLoading}
          limit={20}
        />
      </div>

      <ExpiryDistChart
        contracts={chain?.contracts ?? []}
        loading={chainLoading}
      />
    </div>
  );
}
