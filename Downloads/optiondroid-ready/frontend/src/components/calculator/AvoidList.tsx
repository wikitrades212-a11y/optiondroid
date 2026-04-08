"use client";

import { AlertTriangle } from "lucide-react";
import type { StrikeAnalysis } from "@/lib/types";

interface Props {
  strikes: StrikeAnalysis[];
}

export default function AvoidList({ strikes }: Props) {
  if (strikes.length === 0) return null;

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-put" />
        <h2 className="text-sm font-semibold text-text-primary">Avoid These Strikes</h2>
        <span className="text-2xs text-text-muted ml-auto">{strikes.length} flagged</span>
      </div>

      <div className="space-y-2">
        {strikes.map(s => (
          <div key={`${s.strike}-${s.option_type}`}
            className="flex items-start gap-3 p-3 rounded-lg bg-put/5 border border-put/20">
            <div className="shrink-0 mt-0.5">
              <span className="font-mono text-sm font-semibold text-put">${s.strike}</span>
              <span className="text-2xs text-text-muted ml-1 uppercase">{s.option_type}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap gap-1">
                {s.avoid_reasons.map((r, i) => (
                  <span key={i} className="text-2xs px-1.5 py-0.5 rounded bg-put/15 text-put border border-put/30">
                    {r}
                  </span>
                ))}
              </div>
              <div className="flex gap-4 mt-1.5 text-2xs text-text-muted">
                <span>Mid <span className="text-text-secondary font-mono">${s.mid.toFixed(2)}</span></span>
                <span>Spread <span className="text-text-secondary font-mono">{s.spread_pct.toFixed(1)}%</span></span>
                <span>Vol <span className="text-text-secondary font-mono">{s.volume.toLocaleString()}</span></span>
                <span>OI <span className="text-text-secondary font-mono">{s.open_interest.toLocaleString()}</span></span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
