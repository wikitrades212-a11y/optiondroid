"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Clock, WifiOff, Settings2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import type { ProviderStatus } from "@/lib/types";

const READINESS_CONFIG = {
  live: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/10 border-success/20",
    show: false,  // don't show a banner when everything is fine
  },
  delayed: {
    icon: Clock,
    color: "text-yellow-400",
    bg: "bg-yellow-400/10 border-yellow-400/20",
    show: true,
  },
  pending_approval: {
    icon: AlertTriangle,
    color: "text-orange-400",
    bg: "bg-orange-400/10 border-orange-400/20",
    show: true,
  },
  misconfigured: {
    icon: Settings2,
    color: "text-red-400",
    bg: "bg-red-400/10 border-red-400/20",
    show: true,
  },
  unavailable: {
    icon: WifiOff,
    color: "text-red-400",
    bg: "bg-red-400/10 border-red-400/20",
    show: true,
  },
} as const;

export default function ProviderBanner() {
  const [status, setStatus] = useState<ProviderStatus | null>(null);

  useEffect(() => {
    api.providerStatus().then(setStatus).catch(() => null);
  }, []);

  if (!status) return null;

  const cfg = READINESS_CONFIG[status.readiness] ?? READINESS_CONFIG.unavailable;
  if (!cfg.show) return null;

  const Icon = cfg.icon;

  const modeLabel =
    status.readiness === "pending_approval"
      ? "Provider approval pending — live quotes unavailable"
      : status.readiness === "misconfigured"
      ? "Provider misconfigured — live quotes unavailable"
      : status.readiness === "unavailable"
      ? "Provider unreachable — live quotes unavailable"
      : "Data delayed — 15-minute delayed quotes";

  const extraNote = !status.recommendations_enabled
    ? " · Recommendations disabled in test-only mode."
    : "";

  return (
    <div className={`w-full border-b px-4 py-2 text-xs flex items-center gap-2 ${cfg.bg}`}>
      <Icon className={`w-3.5 h-3.5 shrink-0 ${cfg.color}`} />
      <span className={`font-medium ${cfg.color}`}>{modeLabel}</span>
      <span className="text-text-muted">{status.message}{extraNote}</span>
    </div>
  );
}
