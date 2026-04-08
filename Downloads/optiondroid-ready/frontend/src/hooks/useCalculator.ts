"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { CalculatorParams, CalculatorResponse } from "@/lib/types";

export function useCalculator(params: CalculatorParams | null) {
  const key =
    params &&
    params.ticker &&
    params.current_price > 0 &&
    params.target_price > 0 &&
    params.expiration
      ? `/api/calculator?ticker=${params.ticker}` +
        `&current_price=${params.current_price}` +
        `&target_price=${params.target_price}` +
        `&option_type=${params.option_type}` +
        `&expiration=${params.expiration}` +
        (params.max_premium ? `&max_premium=${params.max_premium}` : "") +
        (params.preferred_strike ? `&preferred_strike=${params.preferred_strike}` : "") +
        (params.account_size ? `&account_size=${params.account_size}` : "") +
        (params.risk_per_trade ? `&risk_per_trade=${params.risk_per_trade}` : "")
      : null;

  return useSWR<CalculatorResponse>(key, fetcher, {
    revalidateOnFocus: false,
    keepPreviousData: true,
  });
}
