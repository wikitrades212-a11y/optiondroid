"use client";

import { useState, useRef, useEffect } from "react";
import { Search, RefreshCw } from "lucide-react";
import clsx from "clsx";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onRefresh?: () => void;
  loading?: boolean;
  autoRefresh?: boolean;
  onAutoRefreshChange?: (v: boolean) => void;
  refreshInterval?: number;
  lastRefresh?: string;
}

const POPULAR = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMD", "MSFT", "AMZN", "META", "GLD"];

export default function TickerInput({
  value,
  onChange,
  onRefresh,
  loading,
  autoRefresh,
  onAutoRefreshChange,
  refreshInterval = 60,
  lastRefresh,
}: Props) {
  const [draft, setDraft] = useState(value);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { setDraft(value); }, [value]);

  const submit = (v: string) => {
    const t = v.trim().toUpperCase();
    if (t && t !== value) onChange(t);
    setOpen(false);
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
        <input
          ref={inputRef}
          className="input pl-9 pr-3 w-48 uppercase font-mono tracking-widest"
          placeholder="SPY"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value.toUpperCase());
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit(draft);
            if (e.key === "Escape") { setDraft(value); setOpen(false); }
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          maxLength={6}
        />
        {/* Quick picker */}
        {open && (
          <div className="absolute top-full mt-1 left-0 z-50 bg-bg-surface border border-bg-border rounded-xl shadow-2xl p-2 grid grid-cols-5 gap-1 w-56">
            {POPULAR.map((t) => (
              <button
                key={t}
                onMouseDown={() => submit(t)}
                className={clsx(
                  "text-xs font-mono px-2 py-1 rounded-lg transition-colors",
                  t === value
                    ? "bg-accent text-white"
                    : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                )}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Refresh button */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={loading}
          className="btn-ghost flex items-center gap-1.5"
        >
          <RefreshCw className={clsx("w-3.5 h-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      )}

      {/* Auto-refresh toggle */}
      {onAutoRefreshChange && (
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <div
            onClick={() => onAutoRefreshChange(!autoRefresh)}
            className={clsx(
              "relative w-8 h-4 rounded-full transition-colors",
              autoRefresh ? "bg-accent" : "bg-bg-border"
            )}
          >
            <div
              className={clsx(
                "absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform",
                autoRefresh ? "translate-x-4" : "translate-x-0.5"
              )}
            />
          </div>
          <span className="text-xs text-text-muted">Auto ({refreshInterval}s)</span>
        </label>
      )}

      {/* Last refresh */}
      {lastRefresh && (
        <span className="text-2xs text-text-muted">
          Updated {lastRefresh}
        </span>
      )}
    </div>
  );
}
