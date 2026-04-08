"use client";

import { useState, useMemo } from "react";
import clsx from "clsx";
import type { OptionContract, SortMetric } from "@/lib/types";
import { fmtPrice, fmtNotional, fmtNumber, fmtPct, fmtRatio } from "@/lib/formatters";
import { TypeBadge, ScoreBadge, ReasonTag, EmptyState } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ChevronUp, ChevronDown } from "lucide-react";

interface Props {
  contracts: OptionContract[];
  loading: boolean;
  showScore?: boolean;
}

type Col = {
  key: string;
  label: string;
  sortable?: boolean;
  align?: "right" | "left";
  render: (c: OptionContract) => React.ReactNode;
};

const COLUMNS: Col[] = [
  {
    key: "option_type",
    label: "Type",
    render: (c) => <TypeBadge type={c.option_type} />,
  },
  {
    key: "strike",
    label: "Strike",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtPrice(c.strike)}</span>,
  },
  {
    key: "expiration",
    label: "Expiry",
    sortable: true,
    render: (c) => <span className="font-mono text-text-secondary">{c.expiration}</span>,
  },
  {
    key: "mid",
    label: "Mid",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtPrice(c.mid)}</span>,
  },
  {
    key: "bid",
    label: "Bid / Ask",
    align: "right",
    render: (c) => (
      <span className="font-mono text-xs">
        <span className="text-put">{fmtPrice(c.bid)}</span>
        {" / "}
        <span className="text-call">{fmtPrice(c.ask)}</span>
      </span>
    ),
  },
  {
    key: "volume",
    label: "Volume",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtNumber(c.volume)}</span>,
  },
  {
    key: "open_interest",
    label: "OI",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtNumber(c.open_interest)}</span>,
  },
  {
    key: "vol_oi_ratio",
    label: "Vol/OI",
    sortable: true,
    align: "right",
    render: (c) => (
      <span className={clsx("font-mono", c.vol_oi_ratio >= 5 ? "text-warn" : "")}>
        {fmtRatio(c.vol_oi_ratio)}
      </span>
    ),
  },
  {
    key: "vol_notional",
    label: "Vol $",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtNotional(c.vol_notional)}</span>,
  },
  {
    key: "oi_notional",
    label: "OI $",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtNotional(c.oi_notional)}</span>,
  },
  {
    key: "implied_volatility",
    label: "IV",
    sortable: true,
    align: "right",
    render: (c) => <span className="font-mono">{fmtPct(c.implied_volatility)}</span>,
  },
  {
    key: "unusual_score",
    label: "Score",
    sortable: true,
    align: "right",
    render: (c) => <ScoreBadge score={c.unusual_score} />,
  },
];

type SortDir = "asc" | "desc";

export default function OptionsTable({ contracts, loading, showScore = true }: Props) {
  const [sortKey, setSortKey] = useState<string>("unusual_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const cols = showScore ? COLUMNS : COLUMNS.filter(c => c.key !== "unusual_score");

  const handleSort = (key: string) => {
    if (key === sortKey) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sorted = useMemo(() => {
    if (!sortKey) return contracts;
    return [...contracts].sort((a, b) => {
      const av = (a as any)[sortKey] ?? 0;
      const bv = (b as any)[sortKey] ?? 0;
      const cmp = typeof av === "string" ? av.localeCompare(bv) : av - bv;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [contracts, sortKey, sortDir]);

  if (loading) return <TableSkeleton rows={15} cols={cols.length} />;
  if (!contracts.length) return <EmptyState message="No contracts match the current filters." />;

  return (
    <div className="w-full overflow-auto rounded-xl border border-bg-border">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-bg-border bg-bg-raised">
            {cols.map(col => (
              <th
                key={col.key}
                className={clsx(
                  "table-head",
                  col.sortable && "cursor-pointer select-none hover:text-text-secondary transition-colors",
                  col.align === "right" && "text-right"
                )}
                onClick={() => col.sortable && handleSort(col.key)}
              >
                <div className={clsx("flex items-center gap-1", col.align === "right" && "justify-end")}>
                  {col.label}
                  {col.sortable && sortKey === col.key && (
                    sortDir === "asc"
                      ? <ChevronUp className="w-3 h-3" />
                      : <ChevronDown className="w-3 h-3" />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((contract, i) => (
            <tr
              key={`${contract.option_type}-${contract.strike}-${contract.expiration}`}
              className={clsx(
                "border-b border-bg-border last:border-0 transition-colors",
                "hover:bg-bg-hover",
                contract.option_type === "call" ? "hover:bg-call/5" : "hover:bg-put/5"
              )}
            >
              {cols.map(col => (
                <td
                  key={col.key}
                  className={clsx("table-cell", col.align === "right" && "text-right")}
                >
                  {col.render(contract)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
