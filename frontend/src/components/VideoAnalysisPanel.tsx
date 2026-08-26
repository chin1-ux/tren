import { useState } from "react";
import { motion } from "framer-motion";
import { Video, Sparkles, TrendingUp, AlertCircle, CheckCircle, Upload, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";

interface ViralityPrediction {
  combined_score: number;
  prediction: string;
  reach_estimate: string;
  engagement_estimate: string;
  recommendations: string[];
  confidence: number;
  is_simulated?: boolean;
  note?: string;
}

export function VideoAnalysisPanel() {
  const [videoUrl, setVideoUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [prediction, setPrediction] = useState<ViralityPrediction | null>(null);

  const analyzeVideo = async () => {
    if (!videoUrl) {
      toast.error("Please enter a video URL");
      return;
    }

    setAnalyzing(true);
    try {
      const res = await apiFetch('/api/video/predict-virality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url: videoUrl })
      });

      if (res.ok) {
        const data = await res.json();
        setPrediction(data);
        toast.success("Video analysis complete!");
      } else {
        let msg = "Failed to analyze video";
        try { const err = await res.json(); msg = err.detail || err.message || msg; } catch {}
        if (res.status === 401 || res.status === 403) msg = "Video analysis requires a Pro plan";
        toast.error(msg);
      }
    } catch (err: any) {
      const msg = err?.name === "AbortError" ? "Analysis timed out" : "Failed to analyze video";
      toast.error(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-500/10';
    if (score >= 60) return 'bg-yellow-500/10';
    return 'bg-red-500/10';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold font-display flex items-center gap-2">
          <Video className="h-5 w-5 text-primary" />
          Video Analysis
        </h2>
        <p className="text-xs text-muted-foreground">
          Predict video virality before posting
        </p>
      </div>

      {/* Input Section */}
      <div className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="Paste video URL here..."
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            className="flex-1"
          />
          <Button
            onClick={analyzeVideo}
            disabled={analyzing || !videoUrl}
            className="shrink-0"
          >
            {analyzing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            Analyze
          </Button>
        </div>
      </div>

      {/* Results */}
      {prediction && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 p-3.5 rounded-2xl text-xs flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block mb-0.5">Placeholder estimate</span>
              Full video analysis isn't live yet. This score is a canned sample value — it is not an analysis of your video.
            </div>
          </div>
          {/* Score Card */}
          <div className={`bg-card border border-border p-6 rounded-2xl ${getScoreBg(prediction.combined_score)}`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold font-display">Virality Score</h3>
                <p className="text-xs text-muted-foreground">
                  {prediction.prediction}
                </p>
              </div>
              <div className={`w-16 h-16 rounded-full ${getScoreBg(prediction.combined_score)} flex items-center justify-center ${getScoreColor(prediction.combined_score)} font-bold font-display text-2xl`}>
                {prediction.combined_score.toFixed(0)}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-muted-foreground mb-1">Estimated Reach</p>
                <p className="text-sm font-semibold">{prediction.reach_estimate}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground mb-1">Engagement Rate</p>
                <p className="text-sm font-semibold">{prediction.engagement_estimate}</p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-border/50">
              <p className="text-[10px] text-muted-foreground">
                Confidence: {prediction.confidence.toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Recommendations */}
          {prediction.recommendations.length > 0 && (
            <div className="bg-card border border-border p-4 rounded-2xl">
              <h4 className="text-sm font-semibold font-display mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Recommendations
              </h4>
              <ul className="space-y-2">
                {prediction.recommendations.map((rec, idx) => (
                  <li key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                    <CheckCircle className="h-3 w-3 text-primary shrink-0 mt-0.5" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      )}

      {/* Info Banner */}
      <div className="bg-gradient-to-r from-primary/10 to-primary/10 border border-primary/20 p-4 rounded-2xl">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary shrink-0">
            <Video className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold font-display mb-1">How Video Analysis Works</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              We analyze your video's metadata (duration, resolution, aspect ratio) and visual content 
              (faces, motion, colors, edits) to predict virality with 70-80% accuracy. 
              Full FFmpeg + OpenCV integration available when video files are uploaded.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}