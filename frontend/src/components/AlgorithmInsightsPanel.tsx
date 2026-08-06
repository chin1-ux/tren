import React, { useState } from "react";
import { Lightbulb, Clock, Hash, TrendingUp, CheckCircle, AlertCircle, Info } from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

interface FactorScore {
  [key: string]: number;
}

interface Recommendation {
  category: string;
  priority: string;
  title: string;
  description: string;
  expected_impact: string;
  difficulty: string;
}

interface EngagementMetrics {
  engagement_rate: number;
  like_rate: number;
  comment_rate: number;
  share_rate: number;
  save_rate: number;
}

interface AlgorithmAnalysis {
  virality_score: number;
  viral_potential: string;
  factor_scores: FactorScore;
  engagement_metrics: EngagementMetrics;
  recommendations: Recommendation[];
  algorithm_explanation: string;
}

interface AlgorithmInsightsPanelProps {
  analysis?: AlgorithmAnalysis;
  loading?: boolean;
  onAnalyze?: (contentData: any) => void;
}

export function AlgorithmInsightsPanel({ analysis, loading, onAnalyze }: AlgorithmInsightsPanelProps) {
  const [showExplanation, setShowExplanation] = useState(false);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/20 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-8 w-8 rounded-full bg-violet-500/20 animate-pulse" />
          <div className="h-4 w-32 bg-violet-500/20 rounded animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-3 bg-violet-500/10 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/20 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Lightbulb className="h-6 w-6 text-violet-400" />
          <h3 className="text-lg font-bold text-white">Instagram Algorithm Insights</h3>
        </div>
        <p className="text-sm text-white/70 mb-4">
          Get AI-powered insights about your content's viral potential and actionable recommendations for optimization.
        </p>
        <Button 
          onClick={() => onAnalyze?.({})}
          className="w-full bg-violet-600 hover:bg-violet-700"
        >
          Analyze Content
        </Button>
      </div>
    );
  }

  const getPotentialColor = (potential: string) => {
    if (potential.includes("HIGH")) return "text-emerald-400";
    if (potential.includes("MODERATE")) return "text-amber-400";
    return "text-rose-400";
  };

  const getPriorityColor = (priority: string) => {
    if (priority === "high") return "bg-rose-500/20 text-rose-400 border-rose-500/30";
    if (priority === "medium") return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
  };

  const getPriorityBadge = (priority: string) => {
    return (
      <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${getPriorityColor(priority)}`}>
        {priority.toUpperCase()}
      </span>
    );
  };

  const factorLabels: { [key: string]: string } = {
    watch_time: "Watch Time",
    engagement_rate: "Engagement Rate",
    save_rate: "Save Rate",
    share_rate: "Share Rate",
    relevance_score: "Relevance Score",
    timeliness: "Timeliness",
    relationship: "Relationship"
  };

  return (
    <div className="bg-gradient-to-br from-violet-500/10 to-purple-500/10 border border-violet-500/20 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Lightbulb className="h-6 w-6 text-violet-400" />
          <h3 className="text-lg font-bold text-white">Instagram Algorithm Insights</h3>
        </div>
        <span className={`text-xs font-bold px-2 py-1 rounded-full ${getPotentialColor(analysis.viral_potential)} bg-white/10`}>
          {analysis.viral_potential}
        </span>
      </div>

      {/* Overall Score */}
      <div className="bg-black/30 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-white/80">Overall Virality Score</span>
          <span className="text-2xl font-bold text-violet-400">{analysis.virality_score}/100</span>
        </div>
        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-500"
            style={{ width: `${analysis.virality_score}%` }}
          />
        </div>
      </div>

      {/* Factor Scores */}
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-white/90 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          Performance Factors
        </h4>
        <div className="space-y-2">
          {Object.entries(analysis.factor_scores).map(([factor, score]) => (
            <div key={factor} className="flex items-center justify-between">
              <span className="text-xs text-white/70">{factorLabels[factor] || factor}</span>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-20 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-violet-500 transition-all duration-300"
                    style={{ width: `${score * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-white/60 w-8 text-right">{Math.round(score * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Engagement Metrics */}
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-white/90 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" />
          Engagement Metrics
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-black/20 rounded p-2">
            <div className="text-[10px] text-white/50 uppercase">Engagement Rate</div>
            <div className="text-sm font-bold text-white">{analysis.engagement_metrics.engagement_rate}%</div>
          </div>
          <div className="bg-black/20 rounded p-2">
            <div className="text-[10px] text-white/50 uppercase">Save Rate</div>
            <div className="text-sm font-bold text-white">{analysis.engagement_metrics.save_rate}%</div>
          </div>
          <div className="bg-black/20 rounded p-2">
            <div className="text-[10px] text-white/50 uppercase">Share Rate</div>
            <div className="text-sm font-bold text-white">{analysis.engagement_metrics.share_rate}%</div>
          </div>
          <div className="bg-black/20 rounded p-2">
            <div className="text-[10px] text-white/50 uppercase">Comment Rate</div>
            <div className="text-sm font-bold text-white">{analysis.engagement_metrics.comment_rate}%</div>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {analysis.recommendations.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-bold text-white/90 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Optimization Tips
          </h4>
          <div className="space-y-2">
            {analysis.recommendations.map((rec, idx) => (
              <div key={idx} className="bg-black/20 rounded-lg p-3 border border-white/5">
                <div className="flex items-start justify-between mb-1">
                  <span className="text-xs font-semibold text-white">{rec.title}</span>
                  {getPriorityBadge(rec.priority)}
                </div>
                <p className="text-[11px] text-white/60 mb-2">{rec.description}</p>
                <div className="flex items-center gap-3 text-[10px] text-white/40">
                  <span>Impact: {rec.expected_impact}</span>
                  <span>Difficulty: {rec.difficulty}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Algorithm Explanation */}
      <div className="space-y-2">
        <button
          onClick={() => setShowExplanation(!showExplanation)}
          className="flex items-center gap-2 text-xs text-white/50 hover:text-white/70 transition-colors"
        >
          <Info className="h-3 w-3" />
          {showExplanation ? "Hide" : "Show"} Algorithm Explanation
        </button>
        {showExplanation && (
          <div className="bg-black/20 rounded-lg p-3 text-[11px] text-white/60 leading-relaxed">
            {analysis.algorithm_explanation}
          </div>
        )}
      </div>
    </div>
  );
}