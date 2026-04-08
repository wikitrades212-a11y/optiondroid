"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { OptionContract } from "@/lib/types";
import { fmtNotional } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/Skeleton";

interface Props {
  contracts: OptionContract[];
  loading: boolean;
}

export default function ExpiryDistChart({ contracts, loading }: Props) {
  if (loading) return <Skeleton className="h-48 w-full" />;

  const byExpiry = contracts.reduce((acc, c) => {
    if (!acc[c.expiration]) acc[c.expiration] = { expiry: c.expiration, call: 0, put: 0 };
    if (c.option_type === "call") acc[c.expiration].call += c.vol_notional;
    else acc[c.expiration].put += c.vol_notional;
    return acc;
  }, {} as Record<string, { expiry: string; call: number; put: number }>);

  const data = Object.values(byExpiry).sort((a, b) => a.expiry.localeCompare(b.expiry));

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-text-primary mb-4">
        Volume Flow by Expiry
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ left: 0, right: 0, top: 4, bottom: 24 }}>
          <XAxis
            dataKey="expiry"
            tick={{ fontSize: 9, fill: "#555b6a" }}
            angle={-30}
            textAnchor="end"
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#555b6a" }}
            tickFormatter={fmtNotional}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip
            formatter={(v: number, name: string) => [fmtNotional(v), name]}
            contentStyle={{ background: "#111318", border: "1px solid #242830", borderRadius: 8, fontSize: 12 }}
          />
          <Bar dataKey="call" name="Calls" fill="#22c55e" opacity={0.8} stackId="a" />
          <Bar dataKey="put"  name="Puts"  fill="#ef4444" opacity={0.8} stackId="a" radius={[2,2,0,0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
