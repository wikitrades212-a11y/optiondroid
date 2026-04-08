"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { fmtNumber, fmtNotional } from "@/lib/formatters";
import { Skeleton } from "@/components/ui/Skeleton";

interface Props {
  callVolume: number;
  putVolume: number;
  callOI: number;
  putOI: number;
  loading: boolean;
}

const RADIAN = Math.PI / 180;
const renderLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
  if (percent < 0.05) return null;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {(percent * 100).toFixed(0)}%
    </text>
  );
};

export default function CallPutChart({ callVolume, putVolume, callOI, putOI, loading }: Props) {
  if (loading) return <Skeleton className="h-64 w-full" />;

  const volData = [
    { name: "Calls", value: callVolume },
    { name: "Puts",  value: putVolume },
  ];
  const oiData = [
    { name: "Calls", value: callOI },
    { name: "Puts",  value: putOI },
  ];

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Call vs Put Imbalance</h3>
      <div className="grid grid-cols-2 gap-4">
        {/* Volume */}
        <div>
          <div className="text-xs text-text-muted text-center mb-2">Volume</div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={volData} dataKey="value" cx="50%" cy="50%"
                   outerRadius={70} labelLine={false} label={renderLabel}>
                <Cell fill="#22c55e" />
                <Cell fill="#ef4444" />
              </Pie>
              <Tooltip
                formatter={(v: number, name: string) => [fmtNumber(v), name]}
                contentStyle={{ background: "#111318", border: "1px solid #242830", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-around text-xs text-center mt-1">
            <div><div className="text-call font-mono">{fmtNumber(callVolume)}</div><div className="text-text-muted">Calls</div></div>
            <div><div className="text-put font-mono">{fmtNumber(putVolume)}</div><div className="text-text-muted">Puts</div></div>
          </div>
        </div>

        {/* OI */}
        <div>
          <div className="text-xs text-text-muted text-center mb-2">Open Interest</div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={oiData} dataKey="value" cx="50%" cy="50%"
                   outerRadius={70} labelLine={false} label={renderLabel}>
                <Cell fill="#22c55e" opacity={0.7} />
                <Cell fill="#ef4444" opacity={0.7} />
              </Pie>
              <Tooltip
                formatter={(v: number, name: string) => [fmtNumber(v), name]}
                contentStyle={{ background: "#111318", border: "1px solid #242830", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-around text-xs text-center mt-1">
            <div><div className="text-call font-mono">{fmtNumber(callOI)}</div><div className="text-text-muted">Calls</div></div>
            <div><div className="text-put font-mono">{fmtNumber(putOI)}</div><div className="text-text-muted">Puts</div></div>
          </div>
        </div>
      </div>
    </div>
  );
}
