"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";
import type { OptionContract } from "@/lib/types";
import { fmtNotional, fmtNumber } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/Skeleton";

interface Props {
  contracts: OptionContract[];
  loading: boolean;
  underlying?: number;
  metric?: "open_interest" | "oi_notional";
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-bg-surface border border-bg-border rounded-lg p-3 text-xs shadow-xl">
      <div className="font-mono font-semibold mb-1">${label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.fill }} />
          <span className="text-text-muted">{p.name}:</span>
          <span className="font-mono font-medium">{
            p.dataKey.includes("notional")
              ? fmtNotional(p.value)
              : fmtNumber(p.value)
          }</span>
        </div>
      ))}
    </div>
  );
};

export default function OIBarChart({ contracts, loading, underlying, metric = "open_interest" }: Props) {
  if (loading) return <Skeleton className="h-64 w-full" />;

  const byStrike = contracts.reduce((acc, c) => {
    const key = c.strike;
    if (!acc[key]) acc[key] = { strike: key, call: 0, put: 0 };
    const val = metric === "open_interest" ? c.open_interest : c.oi_notional;
    if (c.option_type === "call") acc[key].call += val;
    else acc[key].put += val;
    return acc;
  }, {} as Record<number, { strike: number; call: number; put: number }>);

  const data = Object.values(byStrike)
    .sort((a, b) => a.strike - b.strike)
    .slice(0, 40); // keep chart readable

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">
          {metric === "open_interest" ? "Open Interest by Strike" : "OI Notional by Strike"}
        </h3>
        {underlying && (
          <span className="text-xs text-text-muted font-mono">Spot: ${underlying.toFixed(2)}</span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ left: 0, right: 0, top: 4, bottom: 4 }}>
          <XAxis
            dataKey="strike"
            tick={{ fontSize: 10, fill: "#555b6a" }}
            tickFormatter={v => `$${v}`}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#555b6a" }}
            tickFormatter={v =>
              metric === "oi_notional" ? fmtNotional(v) : fmtNumber(v)
            }
            axisLine={false}
            tickLine={false}
            width={55}
          />
          <Tooltip content={<CustomTooltip />} />
          {underlying && (
            <ReferenceLine
              x={underlying}
              stroke="#6366f1"
              strokeDasharray="3 3"
              label={{ value: "ATM", fill: "#6366f1", fontSize: 10 }}
            />
          )}
          <Bar dataKey="call" name="Calls" fill="#22c55e" opacity={0.8} radius={[2,2,0,0]} />
          <Bar dataKey="put"  name="Puts"  fill="#ef4444" opacity={0.8} radius={[2,2,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
