import type {
  OptionChainResponse,
  UnusualOptionsResponse,
  TopContractsResponse,
  ExpirationResponse,
  ProviderStatus,
  SortMetric,
} from "./types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");
const BASE = `${API_BASE_URL}/api/options`;

function toApiUrl(path: string): string {
  if (!API_BASE_URL) return path;
  return `${API_BASE_URL}${path}`;
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(toApiUrl(url), { next: { revalidate: 0 } });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  chain: (ticker: string): Promise<OptionChainResponse> =>
    fetchJSON(`${BASE}?ticker=${encodeURIComponent(ticker)}`),

  unusual: (ticker: string): Promise<UnusualOptionsResponse> =>
    fetchJSON(`${BASE}/unusual?ticker=${encodeURIComponent(ticker)}`),

  top: (ticker: string, metric: SortMetric, limit = 25): Promise<TopContractsResponse> =>
    fetchJSON(
      `${BASE}/top?ticker=${encodeURIComponent(ticker)}&metric=${metric}&limit=${limit}`
    ),

  expirations: (ticker: string): Promise<ExpirationResponse> =>
    fetchJSON(`${BASE}/expirations?ticker=${encodeURIComponent(ticker)}`),

  providerStatus: (): Promise<ProviderStatus> =>
    fetchJSON(toApiUrl("/api/provider/status")),

  exportUrl: (ticker: string, optionType?: "call" | "put", minVolume = 0, minOI = 0): string => {
    const params = new URLSearchParams({ ticker });
    if (optionType) params.set("option_type", optionType);
    if (minVolume) params.set("min_volume", String(minVolume));
    if (minOI) params.set("min_oi", String(minOI));
    return toApiUrl(`/api/options/export?${params.toString()}`);
  },
};

export const fetcher = <T>(url: string) => fetchJSON<T>(url);
export { API_BASE_URL, toApiUrl };
