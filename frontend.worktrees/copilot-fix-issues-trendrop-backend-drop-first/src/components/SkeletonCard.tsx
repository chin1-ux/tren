export function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-border bg-white/[0.02] p-5 space-y-4">
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className="h-6 w-24 rounded-full shimmer" />
        <div className="h-5 w-16 rounded-full shimmer" />
      </div>
      {/* Song name */}
      <div className="space-y-2">
        <div className="h-7 w-3/4 rounded-lg shimmer" />
        <div className="h-4 w-1/3 rounded-lg shimmer" />
      </div>
      {/* Waveform velocity bars */}
      <div className="flex items-end gap-[3px] h-8">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm shimmer"
            style={{ height: `${20 + Math.sin(i * 0.8) * 14}px` }}
          />
        ))}
      </div>
      {/* Chips */}
      <div className="flex gap-2">
        <div className="h-6 w-16 rounded-full shimmer" />
        <div className="h-6 w-20 rounded-full shimmer" />
        <div className="h-6 w-12 rounded-full shimmer" />
      </div>
      {/* Description */}
      <div className="h-10 rounded-xl shimmer" />
      {/* Button */}
      <div className="h-12 rounded-xl shimmer" />
    </div>
  );
}
