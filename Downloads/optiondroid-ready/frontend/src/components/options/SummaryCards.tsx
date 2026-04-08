"use client";

import type { UnusualOptionsResponse } from "@/lib/types";
import { fmtPrice, fmtNotional, fmtNumber, fmtPct } from "@/lib/formatters";
import { TypeBadge, ScoreBadge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { TrendingUp, TrendingDown, Zap, DollarSign } from "lucide-react";

interface Props {
  data: UnusualOptionsResponse | undefined;
  loading: boolean;
  underlying?: number;
  callPutRatio?: number;
  totalCallOI?: number;
  totalPutOI?: number;
}

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <div className="card flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">{label}</span>
        <Icon className={`w-4 h-4 ${accent}`} />
      </div>
      <div className="text-2xl font-semibold font-mono text-text-primary">{value}</div>
      {sub && <div className="text-xs text-text-muted">{sub}</div>}
    </div>
  );
}

export default function SummaryCards({
  data,
  loading,
  underlying,
  callPutRatio,
  totalCallOI,
  totalPutOI,
}: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[0,1,2,3].map(i => <CardSkeleton key={i} />)}
      </div>
    );
  }

  if (!data) return null;

  const topUnusual = data.combined[0];
  const topCall    = data.top_calls[0];
  const topPut     = data.top_puts[0];

  return (
    <div className="space-y-4">
      {/* Row 1: Market stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Underlying Price"
          value={fmtPrice(data.underlying_price)}
          sub={`${data.ticker} spot`}
          icon={DollarSign}
          accent="text-text-muted"
        />
        <StatCard
          label="Call/Put Volume Ratio"
          value={callPutRatio ? callPutRatio.toFixed(2) + "x" : "—"}
          sub={callPutRatio && callPutRatio > 1 ? "Bullish lean" : "Bearish lean"}
          icon={callPutRatio && callPutRatio > 1 ? TrendingUp : TrendingDown}
          accent={callPutRatio && callPutRatio > 1 ? "text-call" : "text-put"}
        />
        <StatCard
          label="Total Unusual Flow"
          value={fmtNotional(data.total_unusual_flow)}
          sub="vol × mid × 100"
          icon={Zap}
          accent="text-accent"
        />
        <StatCard
          label="Call OI / Put OI"
          value={totalCallOI && totalPutOI
            ? `${(totalCallOI / Math.max(totalPutOI, 1)).toFixed(2)}x`
            : "—"}
          sub={`${fmtNumber(totalCallOI ?? 0)} / ${fmtNumber(totalPutOI ?? 0)}`}
          icon={TrendingUp}
          accent="text-text-muted"
        />
      </div>

      {/* Row 2: Top contracts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top unusual */}
        {topUnusual && (
          <div className="card">
            <div className="text-xs text-text-muted uppercase tracking-wider mb-2">Top Unusual Contract</div>
            <div className="flex items-center gap-2 mb-2">
              <TypeBadge type={topUnusual.option_type} />
              <span className="font-mono font-semibold text-text-primary text-sm">
                {topUnusual.ticker} ${topUnusual.strike} {topUnusual.expiration}
              </span>
              <ScoreBadge score={topUnusual.unusual_score} />
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <div className="text-text-muted">Vol</div>
                <div className="font-mono font-medium">{fmtNumber(topUnusual.volume)}</div>
              </div>
              <div>
                <div className="text-text-muted">OI</div>
                <div className="font-mono font-medium">{fmtNumber(topUnusual.open_interest)}</div>
              </div>
              <div>
                <div className="text-text-muted">Vol/OI</div>
                <div className="font-mono font-medium">{topUnusual.vol_oi_ratio.toFixed(2)}x</div>
              </div>
              <div>
                <div className="text-text-muted">Mid</div>
                <div className="font-mono font-medium">{fmtPrice(topUnusual.mid)}</div>
              </div>
              <div>
                <div className="text-text-muted">Vol $</div>
                <div className="font-mono font-medium">{fmtNotional(topUnusual.vol_notional)}</div>
              </div>
              <div>
                <div className="text-text-muted">IV</div>
                <div className="font-mono font-medium">{fmtPct(topUnusual.implied_volatility)}</div>
              </div>
            </div>
          </div>
        )}

        {/* Top call */}
        {topCall && (
          <div className="card border-call/20">
            <div className="text-xs text-call uppercase tracking-wider mb-2">Strongest Call Activity</div>
            <div className="flex items-center gap-2 mb-2">
              <TypeBadge type="call" />
              <span className="font-mono font-semibold text-text-primary text-sm">
                ${topCall.strike} {topCall.expiration}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-text-muted">Vol Notional</div>
                <div className="font-mono font-medium text-call">{fmtNotional(topCall.vol_notional)}</div>
              </div>
              <div>
                <div className="text-text-muted">Score</div>
                <div className="font-mono font-medium"><ScoreBadge score={topCall.unusual_score} /></div>
              </div>
              <div>
                <div className="text-text-muted">Vol</div>
                <div className="font-mono font-medium">{fmtNumber(topCall.volume)}</div>
              </div>
              <div>
                <div className="text-text-muted">OI</div>
                <div className="font-mono font-medium">{fmtNumber(topCall.open_interest)}</div>
              </div>
            </div>
          </div>
        )}

        {/* Top put */}
        {topPut && (
          <div className="card border-put/20">
            <div className="text-xs text-put uppercase tracking-wider mb-2">Strongest Put Activity</div>
            <div className="flex items-center gap-2 mb-2">
              <TypeBadge type="put" />
              <span className="font-mono font-semibold text-text-primary text-sm">
                ${topPut.strike} {topPut.expiration}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-text-muted">Vol Notional</div>
                <div className="font-mono font-medium text-put">{fmtNotional(topPut.vol_notional)}</div>
              </div>
              <div>
                <div className="text-text-muted">Score</div>
                <div className="font-mono font-medium"><ScoreBadge score={topPut.unusual_score} /></div>
              </div>
              <div>
                <div className="text-text-muted">Vol</div>
                <div className="font-mono font-medium">{fmtNumber(topPut.volume)}</div>
              </div>
              <div>
                <div className="text-text-muted">OI</div>
                <div className="font-mono font-medium">{fmtNumber(topPut.open_interest)}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
