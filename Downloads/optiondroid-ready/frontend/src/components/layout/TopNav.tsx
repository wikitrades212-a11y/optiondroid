"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, BarChart3, Flame, LineChart, Settings, Target, TrendingUp } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { ProviderStatus } from "@/lib/types";

const NAV_ITEMS = [
  { label: "Dashboard",       href: "/",        icon: Activity },
  { label: "Chain Explorer",  href: "/chain",   icon: BarChart3 },
  { label: "Unusual Options", href: "/unusual", icon: Flame },
  { label: "Calculator",      href: "/target",  icon: Target },
  { label: "Charts",          href: "/charts",  icon: LineChart },
  { label: "Settings",        href: "/settings",icon: Settings },
];

const READINESS_DOT: Record<string, string> = {
  live:             "bg-success animate-pulse-fast",
  delayed:          "bg-yellow-400",
  pending_approval: "bg-orange-400",
  misconfigured:    "bg-red-500",
  unavailable:      "bg-red-500",
};

const READINESS_LABEL: Record<string, string> = {
  live:             "Live",
  delayed:          "Delayed",
  pending_approval: "Pending",
  misconfigured:    "No config",
  unavailable:      "Down",
};

function ProviderBadge() {
  const [status, setStatus] = useState<ProviderStatus | null>(null);

  useEffect(() => {
    api.providerStatus().then(setStatus).catch(() => null);
  }, []);

  const provider  = status?.provider ?? "…";
  const readiness = status?.readiness ?? "unavailable";
  const dotClass  = READINESS_DOT[readiness] ?? "bg-text-muted";
  const label     = READINESS_LABEL[readiness] ?? readiness;

  return (
    <div
      title={status?.message ?? ""}
      className="hidden sm:flex items-center gap-2 text-2xs text-text-muted px-2 py-1 rounded-md bg-bg-raised border border-bg-border cursor-default select-none"
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
      <span className="capitalize">{provider}</span>
      <span className="text-text-disabled">·</span>
      <span>{label}</span>
    </div>
  );
}

export default function TopNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-bg-border bg-bg-base/95 backdrop-blur-md">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-14 gap-1">
          {/* Brand */}
          <div className="flex items-center gap-2 mr-6 shrink-0">
            <TrendingUp className="w-5 h-5 text-accent" />
            <span className="text-sm font-semibold text-text-primary tracking-tight">
              Options<span className="text-accent">Flow</span>
            </span>
          </div>

          {/* Nav links */}
          <div className="flex items-center gap-0.5 overflow-x-auto no-scrollbar">
            {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                    active
                      ? "bg-accent/10 text-accent"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Provider badge — live status from /api/provider/status */}
          <ProviderBadge />
        </div>
      </div>
    </nav>
  );
}
