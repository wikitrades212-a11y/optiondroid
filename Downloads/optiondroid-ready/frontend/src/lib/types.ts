export type OptionType = "call" | "put";

// ── Calculator ────────────────────────────────────────────────────────────────

export type StrikeTier = "aggressive" | "balanced" | "safer" | "avoid";

export interface StrikeAnalysis {
  strike: number;
  expiration: string;
  option_type: OptionType;
  bid: number;
  ask: number;
  mid: number;
  mark: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
  moneyness_pct: number;
  intrinsic_at_target: number;
  estimated_value_at_target: number;
  estimated_roi_pct: number;
  breakeven: number;
  breakeven_move_pct: number;
  liquidity_score: number;
  spread_pct: number;
  tier: StrikeTier;
  avoid_reasons: string[];
  badges: string[];
  ideal_max_entry: number;
  contracts_for_risk: number | null;
}

export interface CalculatorResponse {
  ticker: string;
  current_price: number;
  target_price: number;
  move_pct: number;
  option_type: OptionType;
  expiration: string;
  dte: number;
  expiry_fit_score: number;
  recommended_aggressive: StrikeAnalysis | null;
  recommended_balanced: StrikeAnalysis | null;
  recommended_safer: StrikeAnalysis | null;
  avoid_list: StrikeAnalysis[];
  all_strikes: StrikeAnalysis[];
}

export interface CalculatorParams {
  ticker: string;
  current_price: number;
  target_price: number;
  option_type: "call" | "put" | "auto";
  expiration: string;
  max_premium?: number;
  preferred_strike?: number;
  account_size?: number;
  risk_per_trade?: number;
}

export interface OptionContract {
  ticker: string;
  strike: number;
  expiration: string;
  option_type: OptionType;
  bid: number;
  ask: number;
  mid: number;
  last: number;
  mark: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  oi_notional: number;
  vol_notional: number;
  vol_oi_ratio: number;
  unusual_score: number;
  unusual_rank: number;
  reason_tags: string[];
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
  rho: number | null;
  underlying_price: number | null;
  moneyness: number | null;
}

export interface OptionChainResponse {
  ticker: string;
  underlying_price: number;
  timestamp: string;
  expirations: string[];
  contracts: OptionContract[];
  total_call_oi: number;
  total_put_oi: number;
  total_call_volume: number;
  total_put_volume: number;
  call_put_ratio: number;
}

export interface UnusualOptionsResponse {
  ticker: string;
  underlying_price: number;
  timestamp: string;
  top_calls: OptionContract[];
  top_puts: OptionContract[];
  combined: OptionContract[];
  total_unusual_flow: number;
}

export interface TopContractsResponse {
  ticker: string;
  underlying_price: number;
  timestamp: string;
  metric: string;
  contracts: OptionContract[];
}

export interface ExpirationResponse {
  ticker: string;
  expirations: string[];
  timestamp: string;
}

export type SortMetric =
  | "open_interest"
  | "oi_notional"
  | "volume"
  | "vol_notional"
  | "unusual_score";

export interface ChainFilters {
  expiration: string;
  optionType: "call" | "put" | "both";
  minOI: number;
  minVolume: number;
  sortBy: SortMetric;
  searchTicker: string;
}

export interface UnusualFilters {
  optionType: "call" | "put" | "both";
  minScore: number;
  expiry: "all" | "nearest" | "weeklies";
  tags: string[];
}
