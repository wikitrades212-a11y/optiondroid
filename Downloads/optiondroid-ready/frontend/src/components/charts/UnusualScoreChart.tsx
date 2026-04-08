"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import type { OptionContract } from "@/lib/types";
import { fmtPrice } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/Skeleton";

interface Props {
  contracts: OptionContract[];
  loading: boolean;
  limit?: number;
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-bg-surface border border-bg-border rounded-lg p-3 text-xs shadow-xl space-y-1">
      <div className="font-mono font-semibold">
        {d.option_type === "call" ? "CALL" : "PUT"} {fmtPrice(d.strike)} {d.expiration}
      </div>
      <div className="text-text-muted">Score: <span className="text-text-primary font-medium">{d.unusual_score.toFixed(1)}</span></div>
      <div className="flex flex-wrap gap-1 mt-1">
        {(d.reason_tags as string[]).map((t: string) => (
          <span key={t} className="px-1.5 py-0.5 rounded bg-bg-raised text-text-secondary">
            {t}
          </span>
        ))}
      </div>
    </div>
  );
};

export default function UnusualScoreChart({ contracts, loading, limit = 20 }: Props) {
  if (loading) return <Skeleton className="h-64 w-full" />;

  const data = contracts.slice(0, limit).map(c => ({
    ...c,
    label: `${c.option_type[0].toUpperCase()} $${c.strike}`,
  }));

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        Top Unusual Scores
      </h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 12, top: 0, bottom: 0 }}>
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "#555b6a" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 10, fill: "#8b909e", fontFamily: "monospace" }}
            axisLine={false}
            tickLine={false}
            width={70}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="unusual_score" name="Score" radius={[0,3,3,0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  entry.unusual_score >= 80 ? "#ef4444" :
                  entry.unusual_score >= 60 ? "#f59e0b" :
                  entry.unusual_score >= 40 ? "#6366f1" :
                                              "#374151"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
