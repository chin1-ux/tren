import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-md bg-white/[0.04] shimmer", className)}
      {...props}
    />
  );
}

export function TrendCardSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-white/[0.02] p-5 space-y-4">
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-24 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      {/* Song details */}
      <div className="space-y-2">
        <Skeleton className="h-7 w-3/4 rounded-lg" />
        <Skeleton className="h-4 w-1/3 rounded-lg" />
      </div>
      {/* Waveform velocity bars */}
      <div className="flex items-end gap-[3px] h-8 pt-2">
        {Array.from({ length: 24 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm shimmer bg-white/[0.04]"
            style={{ height: `${20 + Math.sin(i * 0.7) * 14}px` }}
          />
        ))}
      </div>
      {/* Chips */}
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-12 rounded-full" />
      </div>
      {/* Description */}
      <Skeleton className="h-10 rounded-xl" />
      {/* Button */}
      <Skeleton className="h-11 rounded-xl" />
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="p-4 rounded-xl border border-border bg-white/[0.02] space-y-2">
          <Skeleton className="h-4 w-16 rounded" />
          <Skeleton className="h-6 w-24 rounded-md" />
        </div>
      ))}
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="space-y-6 p-4">
      <div className="flex items-center gap-4">
        <Skeleton className="h-16 w-16 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-5 w-1/2 rounded" />
          <Skeleton className="h-4 w-1/3 rounded" />
        </div>
      </div>
      <div className="space-y-3">
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-12 w-full rounded-xl" />
      </div>
    </div>
  );
}
