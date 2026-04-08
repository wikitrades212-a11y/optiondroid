"use client";

import { useState, useMemo, useCallback } from "react";
import { useChain } from "@/hooks/useOptions";
import TickerInput from "@/components/ui/TickerInput";
import FilterBar from "@/components/options/FilterBar";
import OptionsTable from "@/components/options/OptionsTable";
import type { ChainFilters, OptionContract } from "@/lib/types";
import { fmtPrice, fmtNumber, fmtTimestamp } from "@/lib/formatters";
import { ErrorState } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import { Download } from "lucide-react";

const DEFAULT_TICKER = "SPY";

const defaultFilters: ChainFilters = {
  expiration: "",
  optionType: "both",
  minOI: 0,
  minVolume: 0,
  sortBy: "unusual_score",
  searchTicker: DEFAULT_TICKER,
};

export default function ChainExplorer() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [filters, setFilters] = useState<ChainFilters>(defaultFilters);

  const { data: chain, error, isLoading, mutate } = useChain(ticker);

  const updateFilters = useCallback((partial: Partial<ChainFilters>) => {
    setFilters(prev => ({ ...prev, ...partial }));
  }, []);

  const filtered = useMemo(() => {
    if (!chain?.contracts) return [];
    let cs = chain.contracts as OptionContract[];

    if (filters.expiration) cs = cs.filter(c => c.expiration === filters.expiration);
    if (filters.optionType !== "both") cs = cs.filter(c => c.option_type === filters.optionType);
    if (filters.minOI)     cs = cs.filter(c => c.open_interest >= filters.minOI);
    if (filters.minVolume) cs = cs.filter(c => c.volume >= filters.minVolume);

    return [...cs].sort((a, b) => {
      const av = (a as any)[filters.sortBy] ?? 0;
      const bv = (b as any)[filters.sortBy] ?? 0;
      return bv - av;
    });
  }, [chain, filters]);

  const handleTickerChange = (t: string) => {
    setTicker(t);
    setFilters(prev => ({ ...prev, expiration: "", searchTicker: t }));
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Chain Explorer</h1>
          <p className="text-sm text-text-muted">
            {chain
              ? `${fmtNumber(chain.contracts.length)} contracts · Spot ${fmtPrice(chain.underlying_price)} · ${fmtTimestamp(chain.timestamp)}`
              : "Full option chain with sorting and filters"
            }
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <TickerInput
            value={ticker}
            onChange={handleTickerChange}
            onRefresh={mutate}
            loading={isLoading}
          />
          <a
            href={api.exportUrl(
              ticker,
              filters.optionType !== "both" ? filters.optionType : undefined,
              filters.minVolume,
              filters.minOI
            )}
            className="btn-ghost flex items-center gap-1.5 text-xs"
            download
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </a>
        </div>
      </div>

      {error && <ErrorState message={(error as Error).message} />}

      {/* Filters */}
      <FilterBar
        filters={filters}
        onChange={updateFilters}
        expirations={chain?.expirations ?? []}
      />

      {/* Count bar */}
      {!isLoading && chain && (
        <div className="flex items-center gap-4 text-xs text-text-muted px-1">
          <span>{fmtNumber(filtered.length)} contracts shown</span>
          <span>·</span>
          <span className="text-call">
            {fmtNumber(filtered.filter(c => c.option_type === "call").length)} calls
          </span>
          <span>·</span>
          <span className="text-put">
            {fmtNumber(filtered.filter(c => c.option_type === "put").length)} puts
          </span>
        </div>
      )}

      {/* Table */}
      <OptionsTable
        contracts={filtered}
        loading={isLoading}
        showScore
      />
    </div>
  );
}
