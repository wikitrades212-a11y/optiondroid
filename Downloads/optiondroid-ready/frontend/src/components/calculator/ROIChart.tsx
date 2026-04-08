"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { CalculatorResponse, StrikeAnalysis } from "@/lib/types";

interface Props {
  data: CalculatorResponse;
}

const TIER_COLOR: Record<string, string> = {
  aggressive: "#ef4444",
  balanced: "#6366f1",
  safer: "#22c55e",
  avoid: "#555b6a",
};

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as StrikeAnalysis;
  return (
    <div className="bg-bg-surface border border-bg-border rounded-xl p-3 text-xs space-y-1 shadow-2xl">
      <p className="font-semibold text-text-primary font-mono">${d.strike} {d.option_type.toUpperCase()}</p>
      <p className="text-text-muted">Est. ROI: <span className={d.estimated_roi_pct >= 0 ? "text-call" : "text-put"}>{d.estimated_roi_pct.toFixed(1)}%</span></p>
      <p className="text-text-muted">Est. Value: <span className="text-text-secondary">${d.estimated_value_at_target.toFixed(2)}</span></p>
      <p className="text-text-muted">Mid: <span className="text-text-secondary">${d.mid.toFixed(2)}</span></p>
      <p className="text-text-muted">Tier: <span className="capitalize text-text-secondary">{d.tier}</span></p>
    </div>
  );
}

export default function ROIChart({ data }: Props) {
  const strikes = [...data.all_strikes]
    .filter(s => s.tier !== "avoid")
    .sort((a, b) => a.strike - b.strike);

  if (strikes.length === 0) return null;

  const chartData = strikes.map(s => ({
    ...s,
    label: `$${s.strike}`,
  }));

  return (
    <div className="card space-y-4">
      <h2 className="text-sm font-semibold text-text-primary">Estimated ROI by Strike</h2>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#242830" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "#555b6a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#555b6a" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#1e2229" }} />
          <ReferenceLine y={0} stroke="#242830" />
          <Bar dataKey="estimated_roi_pct" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={TIER_COLOR[entry.tier] ?? "var(--color-text-muted)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-2xs text-text-muted">
        {(["aggressive", "balanced", "safer"] as const).map(t => (
          <span key={t} className="flex items-center gap-1.5 capitalize">
            <span className="w-2 h-2 rounded-sm" style={{ background: TIER_COLOR[t] }} />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
