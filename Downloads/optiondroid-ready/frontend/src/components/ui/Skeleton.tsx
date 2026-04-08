import clsx from "clsx";

interface Props {
  className?: string;
  rows?: number;
  cols?: number;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton", className)} />;
}

export function TableSkeleton({ rows = 10, cols = 8 }: Props) {
  return (
    <div className="w-full overflow-hidden rounded-xl border border-bg-border">
      {/* Header */}
      <div className="grid gap-3 px-3 py-2 border-b border-bg-border bg-bg-raised"
           style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-3/4" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r}
             className="grid gap-3 px-3 py-2.5 border-b border-bg-border last:border-0"
             style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3.5" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="card animate-pulse space-y-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-40" />
    </div>
  );
}
