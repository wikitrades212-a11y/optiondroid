import clsx from "clsx";
import type { OptionType } from "@/lib/types";

export function TypeBadge({ type }: { type: OptionType }) {
  return (
    <span className={type === "call" ? "badge-call" : "badge-put"}>
      {type}
    </span>
  );
}

const TAG_STYLES: Record<string, string> = {
  "High Vol/OI":          "border-warn/40 text-warn bg-warn/5",
  "Big Premium":          "border-accent/40 text-accent bg-accent/5",
  "Expiry Concentration": "border-purple-500/40 text-purple-400 bg-purple-500/5",
  "Call Dominance":       "border-call/40 text-call bg-call/5",
  "Put Hedge":            "border-put/40 text-put bg-put/5",
  "Near ATM Aggression":  "border-sky-500/40 text-sky-400 bg-sky-500/5",
  "Far OTM Lottery":      "border-orange-500/40 text-orange-400 bg-orange-500/5",
  "Unusual Activity":     "border-text-muted/40 text-text-secondary bg-bg-raised",
};

export function ReasonTag({ tag }: { tag: string }) {
  const style = TAG_STYLES[tag] ?? "border-bg-border text-text-muted";
  return (
    <span className={clsx("tag", style)}>{tag}</span>
  );
}

export function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? "text-red-400 bg-red-500/10 border-red-500/30" :
    score >= 60 ? "text-warn bg-warn/10 border-warn/30" :
    score >= 40 ? "text-accent bg-accent/10 border-accent/30" :
                  "text-text-muted bg-bg-raised border-bg-border";
  return (
    <span className={clsx("tag font-mono font-semibold", color)}>
      {score.toFixed(1)}
    </span>
  );
}

export function EmptyState({ message = "No data available" }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center gap-2">
      <div className="w-12 h-12 rounded-full bg-bg-raised flex items-center justify-center text-2xl">
        📭
      </div>
      <p className="text-text-secondary text-sm">{message}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center gap-2">
      <div className="w-12 h-12 rounded-full bg-put-bg flex items-center justify-center text-2xl">
        ⚠
      </div>
      <p className="text-put text-sm font-medium">{message}</p>
    </div>
  );
}
