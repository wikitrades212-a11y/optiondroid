"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type {
  OptionChainResponse,
  UnusualOptionsResponse,
  TopContractsResponse,
  ExpirationResponse,
  SortMetric,
} from "@/lib/types";

const BASE = "/api/options";

interface SWROptions {
  refreshInterval?: number;
  revalidateOnFocus?: boolean;
}

export function useChain(ticker: string | null, opts: SWROptions = {}) {
  const key = ticker ? `${BASE}?ticker=${ticker}` : null;
  return useSWR<OptionChainResponse>(key, fetcher, {
    refreshInterval: opts.refreshInterval ?? 0,
    revalidateOnFocus: opts.revalidateOnFocus ?? false,
    keepPreviousData: true,
  });
}

export function useUnusual(ticker: string | null, opts: SWROptions = {}) {
  const key = ticker ? `${BASE}/unusual?ticker=${ticker}` : null;
  return useSWR<UnusualOptionsResponse>(key, fetcher, {
    refreshInterval: opts.refreshInterval ?? 0,
    revalidateOnFocus: opts.revalidateOnFocus ?? false,
    keepPreviousData: true,
  });
}

export function useTop(
  ticker: string | null,
  metric: SortMetric = "unusual_score",
  limit = 25,
  opts: SWROptions = {}
) {
  const key = ticker
    ? `${BASE}/top?ticker=${ticker}&metric=${metric}&limit=${limit}`
    : null;
  return useSWR<TopContractsResponse>(key, fetcher, {
    refreshInterval: opts.refreshInterval ?? 0,
    revalidateOnFocus: opts.revalidateOnFocus ?? false,
    keepPreviousData: true,
  });
}

export function useExpirations(ticker: string | null) {
  const key = ticker ? `${BASE}/expirations?ticker=${ticker}` : null;
  return useSWR<ExpirationResponse>(key, fetcher, {
    revalidateOnFocus: false,
    keepPreviousData: true,
  });
}
