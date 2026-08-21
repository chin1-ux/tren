import { useState } from "react";
import { SparklineChart } from "./SparklineChart";
import { useQuery } from "@tanstack/react-query";
import { Button } from "./ui/button";
import { apiFetch } from "@/lib/api";

interface TrendProofSectionProps {
  trendId: string;  // Changed to string to match UiTrend.id type
  isPeaking: boolean;
}

export function TrendProofSection({ trendId, isPeaking }: TrendProofSectionProps) {
  const [expanded, setExpanded] = useState(false);

  // Fetch timeline data
  const { data: timeline, isLoading } = useQuery({
    queryKey: ['trend-timeline', trendId],
    queryFn: async () => {
      const response = await apiFetch(`/api/trends/${trendId}/timeline`);
      return response.json();
    },
    enabled: expanded && isPeaking
  });

  if (!isPeaking) return null;

  // Extract velocity data for sparkline
  const velocityData = timeline?.velocity_history?.map((point: any) => point.velocity) || [];

  return (
    <div className="proof-section mt-4 p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-orange-400 font-bold">🔥 Currently Peaking</span>
          {timeline && (
            <span className="text-sm text-gray-400">
              +{timeline.velocity_acceleration_pct}% velocity
            </span>
          )}
        </div>
        <Button 
          onClick={() => setExpanded(!expanded)}
          variant="ghost"
          size="sm"
        >
          {expanded ? "Hide Proof" : "Show Proof"}
        </Button>
      </div>

      {expanded && (isLoading ? (
        <div className="mt-4 animate-pulse bg-gray-200 rounded h-32" />
      ) : timeline ? (
        <div className="mt-4 space-y-4">
          {/* Timestamp Trail */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">First Detected:</span>
              <span className="ml-2 font-mono">
                {new Date(timeline.first_detected_at).toLocaleString()}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Trend Age:</span>
              <span className="ml-2 font-mono">{timeline.trend_age_hours}h</span>
            </div>
            <div>
              <span className="text-gray-400">Window Remaining:</span>
              <span className="ml-2 font-mono">{timeline.window_hours_remaining}h</span>
            </div>
            <div>
              <span className="text-gray-400">Peak Velocity:</span>
              <span className="ml-2 font-mono">
                {timeline.peak_velocity?.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Velocity Chart - use extended SparklineChart with height prop */}
          <div>
            <h4 className="text-sm font-semibold mb-2">
              Velocity History ({timeline.snapshot_count} checkpoints)
            </h4>
            {velocityData.length >= 2 ? (
              <div className="overflow-hidden rounded-lg">
                <SparklineChart data={velocityData} color="amber" height={100} />
              </div>
            ) : (
              <p className="text-sm text-gray-400">
                Insufficient data for chart ({timeline.snapshot_count} snapshots)
              </p>
            )}
          </div>
        </div>
      ) : null)}
    </div>
  );
}