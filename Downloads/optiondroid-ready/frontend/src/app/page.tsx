"use client";

import { useState, useCallback } from "react";
import { useChain, useUnusual } from "@/hooks/useOptions";
import TickerInput from "@/components/ui/TickerInput";
import SummaryCards from "@/components/options/SummaryCards";
import UnusualTable from "@/components/options/UnusualTable";
import OIBarChart from "@/components/charts/OIBarChart";
import CallPutChart from "@/components/charts/CallPutChart";
import { fmtTimestamp } from "@/lib/formatters";
import { ErrorState } from "@/components/ui/Badge";

const DEFAULT_TICKER = "SPY";
const AUTO_REFRESH_INTERVAL = 60_000;

export default function Dashboard() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const { data: chain, error: chainErr, isLoading: chainLoading, mutate: refreshChain } =
    useChain(ticker, { refreshInterval: autoRefresh ? AUTO_REFRESH_INTERVAL : 0 });

  const { data: unusual, error: unusualErr, isLoading: unusualLoading, mutate: refreshUnusual } =
    useUnusual(ticker, { refreshInterval: autoRefresh ? AUTO_REFRESH_INTERVAL : 0 });

  const refresh = useCallback(() => {
    refreshChain();
    refreshUnusual();
  }, [refreshChain, refreshUnusual]);

  const loading = chainLoading || unusualLoading;
  const error = chainErr || unusualErr;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
          <p className="text-sm text-text-muted">Options flow overview</p>
        </div>
        <TickerInput
          value={ticker}
          onChange={setTicker}
          onRefresh={refresh}
          loading={loading}
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          refreshInterval={60}
          lastRefresh={
            chain?.timestamp ? fmtTimestamp(chain.timestamp) : undefined
          }
        />
      </div>

      {error && <ErrorState message={`Failed to load data: ${(error as Error).message}`} />}

      {/* Summary cards */}
      <SummaryCards
        data={unusual}
        loading={unusualLoading}
        underlying={chain?.underlying_price}
        callPutRatio={chain?.call_put_ratio}
        totalCallOI={chain?.total_call_oi}
        totalPutOI={chain?.total_put_oi}
      />

      {/* Charts row */}
      {!error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <OIBarChart
            contracts={chain?.contracts ?? []}
            loading={chainLoading}
            underlying={chain?.underlying_price}
          />
          <CallPutChart
            callVolume={chain?.total_call_volume ?? 0}
            putVolume={chain?.total_put_volume ?? 0}
            callOI={chain?.total_call_oi ?? 0}
            putOI={chain?.total_put_oi ?? 0}
            loading={chainLoading}
          />
        </div>
      )}

      {/* Top unusual preview */}
      {!error && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-text-primary">Top Unusual Activity</h2>
            <a href="/unusual" className="text-xs text-accent hover:underline">View all →</a>
          </div>
          <UnusualTable
            contracts={unusual?.combined ?? []}
            loading={unusualLoading}
            limit={10}
          />
        </div>
      )}
    </div>
  );
}
