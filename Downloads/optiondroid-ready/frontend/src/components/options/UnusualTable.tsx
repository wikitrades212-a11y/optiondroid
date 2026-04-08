"use client";

import { useMemo } from "react";
import clsx from "clsx";
import type { OptionContract } from "@/lib/types";
import { fmtPrice, fmtNotional, fmtNumber, fmtPct, fmtRatio } from "@/lib/formatters";
import { TypeBadge, ScoreBadge, ReasonTag, EmptyState } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface Props {
  contracts: OptionContract[];
  loading: boolean;
  title?: string;
  limit?: number;
}

export default function UnusualTable({ contracts, loading, title, limit = 25 }: Props) {
  const visible = contracts.slice(0, limit);

  if (loading) return (
    <div className="space-y-2">
      {title && <div className="h-5 w-40 bg-bg-raised rounded animate-pulse" />}
      <TableSkeleton rows={8} cols={9} />
    </div>
  );

  return (
    <div className="space-y-2">
      {title && (
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      )}
      {visible.length === 0
        ? <EmptyState message="No unusual options found." />
        : (
          <div className="w-full overflow-auto rounded-xl border border-bg-border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-bg-border bg-bg-raised">
                  {["#", "Type", "Strike", "Expiry", "Score", "Vol", "OI", "Vol/OI", "Vol $", "OI $", "IV", "Tags"].map((h, i) => (
                    <th key={h} className={clsx("table-head", i > 1 && "text-right", i === 11 && "text-left")}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visible.map((c, i) => (
                  <tr
                    key={`${c.option_type}-${c.strike}-${c.expiration}-${i}`}
                    className={clsx(
                      "border-b border-bg-border last:border-0 transition-colors",
                      c.option_type === "call" ? "hover:bg-call/5" : "hover:bg-put/5"
                    )}
                  >
                    <td className="table-cell text-text-muted font-mono text-xs w-8">
                      {c.unusual_rank}
                    </td>
                    <td className="table-cell">
                      <TypeBadge type={c.option_type} />
                    </td>
                    <td className="table-cell text-right font-mono font-semibold">
                      {fmtPrice(c.strike)}
                    </td>
                    <td className="table-cell text-right font-mono text-text-secondary text-xs">
                      {c.expiration}
                    </td>
                    <td className="table-cell text-right">
                      <ScoreBadge score={c.unusual_score} />
                    </td>
                    <td className="table-cell text-right font-mono">
                      {fmtNumber(c.volume)}
                    </td>
                    <td className="table-cell text-right font-mono text-text-secondary">
                      {fmtNumber(c.open_interest)}
                    </td>
                    <td className="table-cell text-right font-mono">
                      <span className={c.vol_oi_ratio >= 5 ? "text-warn" : ""}>
                        {fmtRatio(c.vol_oi_ratio)}
                      </span>
                    </td>
                    <td className="table-cell text-right font-mono">
                      <span className={c.option_type === "call" ? "text-call" : "text-put"}>
                        {fmtNotional(c.vol_notional)}
                      </span>
                    </td>
                    <td className="table-cell text-right font-mono text-text-secondary">
                      {fmtNotional(c.oi_notional)}
                    </td>
                    <td className="table-cell text-right font-mono text-xs text-text-muted">
                      {fmtPct(c.implied_volatility)}
                    </td>
                    <td className="table-cell">
                      <div className="flex flex-wrap gap-1">
                        {c.reason_tags.map(tag => (
                          <ReasonTag key={tag} tag={tag} />
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }
    </div>
  );
}
