import React from "react";

interface SparklineChartProps {
  data: number[];
  color?: "green" | "amber" | "red";
  height?: number;  // NEW: Optional height prop (default 24px for sparkline, larger for proof view)
}

export const SparklineChart = ({ data, color = "green", height = 24 }: SparklineChartProps) => {
  if (!data || data.length < 2) {
    return (
      <div className="flex h-6 items-center justify-center text-[10px] text-white/40 italic">
        Tracking started...
      </div>
    );
  }

  const width = 80;
  const padding = 2;

  const minVal = Math.min(...data);
  const maxVal = Math.max(...data);
  const range = maxVal - minVal || 1;

  const points = data
    .map((val, index) => {
      const x = padding + (index / (data.length - 1)) * (width - padding * 2);
      const y =
        height -
        padding -
        ((val - minVal) / range) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const strokeColor =
    color === "green"
      ? "#34d399" // emerald-400
      : color === "amber"
      ? "#fbbf24" // amber-400
      : "#f87171"; // red-400

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
};