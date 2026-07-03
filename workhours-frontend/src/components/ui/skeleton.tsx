import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('skeleton-shimmer rounded-md bg-slate-100 dark:bg-slate-800', className)}
      {...props}
    />
  )
}

/** A skeleton mimicking a data table: header row + N body rows. */
export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="divide-y divide-border">
      <div className="flex gap-4 px-6 py-3 bg-muted/40">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1 max-w-[140px]" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 px-6 py-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cn('h-3.5 flex-1', c === 0 ? 'max-w-[120px]' : 'max-w-[100px]')} />
          ))}
        </div>
      ))}
    </div>
  )
}

/** A skeleton mimicking a grid of stat/KPI cards. */
export function CardGridSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-9 w-9 rounded-lg" />
          </div>
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-2.5 w-24" />
        </div>
      ))}
    </div>
  )
}
