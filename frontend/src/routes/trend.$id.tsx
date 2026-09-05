import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft, Copy, CheckCheck, Clock, Flame, Share2, ExternalLink,
  Zap, Volume2, Calendar, ChevronRight, Music2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchTrendById, fetchCaptionKit, fetchSimilarTrends, fetchTrendReels, fetchTrendDecision } from "@/lib/api";
import { FEATURES } from "@/lib/features";
import { Button } from "@/components/ui/button";
import { PlanGate } from "@/components/PlanGate";
import { useState } from "react";
import { useUserStore } from "@/store/useAppStore";
import { toast } from "sonner";
import { z } from "zod";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/trend/$id")({
  head: () => ({
    meta: [
      { title: "Trend Details — Trendrop" },
      { name: "description", content: "Deep dive into this trend: caption kit, timing, strategy." },
    ],
  }),
  errorComponent: RouteErrorBoundary,
  component: TrendDetailPage,
});

function TrendDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const [copiedCaption, setCopiedCaption] = useState<number | null>(null);
  const [copiedHashtags, setCopiedHashtags] = useState(false);
  const [selectedVibe, setSelectedVibe] = useState(0);
  const userPlan = useUserStore((s) => s.plan) || 'free';
  const userNiche = useUserStore((s) => s.niche) || 'all';

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ["trend", id],
    queryFn: () => fetchTrendById(id),
  });

  const { data: captionKit, isLoading: captionLoading } = useQuery({
    queryKey: ["caption-kit", id],
    queryFn: () => fetchCaptionKit(id),
    enabled: !!trend,
  });

  const { data: similarTrends } = useQuery({
    queryKey: ["similar-trends", id],
    queryFn: () => fetchSimilarTrends(id),
    enabled: !!trend,
  });

  const { data: reels } = useQuery({
    queryKey: ["trend-reels", id],
    queryFn: () => fetchTrendReels(id),
    enabled: !!trend,
  });

  const hasCreatorBreakout = reels?.some((r) => r.is_creator_outlier) || false;

  const { data: decision } = useQuery({
    queryKey: ["trend-decision", id],
    queryFn: () => fetchTrendDecision(id),
    enabled: !!trend,
  });

  const copyCaption = (idx: number) => {
    if (!captionKit?.captions[idx]) return;
    navigator.clipboard.writeText(captionKit.captions[idx].text);
    setCopiedCaption(idx);
    toast.success("Caption copied!");
    setTimeout(() => setCopiedCaption(null), 2000);
  };

  const copyHashtags = () => {
    if (!captionKit?.hashtags) return;
    navigator.clipboard.writeText(captionKit.hashtags.map(h => `#${h.replace(/^#/, "")}`).join(" "));
    setCopiedHashtags(true);
    toast.success("All hashtags copied!");
    setTimeout(() => setCopiedHashtags(false), 2000);
  };

  const shareWhatsApp = () => {
    const text = encodeURIComponent(
      `🔥 Trending now: "${trend?.song}" by ${trend?.artist}\n📲 Check on Trendrop → trendrop.ai`
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  const formatHour = (h?: number) => {
    if (h === undefined) return "7 PM";
    const period = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return `${h12} ${period}`;
  };

  if (trendLoading) {
    return (
      <div className="flex flex-col gap-4 px-4 pt-6 pb-24">
        <button onClick={() => navigate({ to: "/" })} className="flex items-center gap-1 text-sm text-muted-foreground">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        {[1, 2, 3].map(i => (
          <div key={i} className="h-24 rounded-2xl shimmer" />
        ))}
      </div>
    );
  }

  if (!trend) {
    return (
      <div className="flex flex-col items-center gap-4 px-4 pt-16 text-center">
        <p className="text-5xl">🔍</p>
        <p className="font-semibold">Trend not found</p>
        <Button onClick={() => navigate({ to: "/" })}>Back to Feed</Button>
      </div>
    );
  }

  const satPct = Math.round((trend.saturationScore ?? 0) * 100);
  const viralPct = Math.min(100, (trend.viralMultiplier / 30) * 100);

  return (
    <div className="flex flex-col gap-5 px-4 pb-28 pt-5">
      {/* Back */}
      <button
        onClick={() => navigate({ to: "/" })}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Feed
      </button>

      {/* Hero */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-primary">
              <Flame className="h-3 w-3" /> {trend.isEmerging ? "Emerging" : "Trending"}
            </span>
            {trend.discoverySource === "unexpected_candidate" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/15 border border-blue-500/30 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-blue-400">
                <Zap className="h-3 w-3" /> Under Radar
              </span>
            )}
            {hasCreatorBreakout && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-emerald-400">
                🚀 Creator Breakout
              </span>
            )}
            {!trend.isClassificationVerified ? (
              <span className="text-sm rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-1 text-amber-300">
                ⏳ Classifying
              </span>
            ) : trend.languageEmoji ? (
              <span className="text-sm">{trend.languageEmoji} {trend.languageLabel}</span>
            ) : null}
          </div>
          <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
            <Clock className="h-3.5 w-3.5" /> {trend.hoursLeft}h left
          </span>
        </div>

        <div>
          <h1 className="font-display text-3xl font-bold leading-tight gradient-text">{trend.song}</h1>
          <p className="text-sm text-muted-foreground mt-1">by {trend.artist}</p>
        </div>

        {/* Waveform bars */}
        <div className="flex items-end gap-1.5 h-10">
          {[7, 4, 9, 6, 10, 5, 8, 3, 7, 5].map((h, i) => (
            <div key={i} className="waveform-bar" style={{ height: `${h * 3}px` }} />
          ))}
          <span className="ml-2 text-xs text-muted-foreground self-center">{trend.viralMultiplier}x viral</span>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2">
          <StatPill label="Saturation" value={`${satPct}%`} color={satPct < 30 ? "text-emerald-400" : satPct < 60 ? "text-amber-400" : "text-red-400"} />
          <StatPill label="Reels" value={`${trend.reelCount ?? "–"}`} />
          <StatPill label="Category" value={`${trend.contentTypeEmoji} ${trend.contentType}`} />
        </div>

        {/* Semantic Niches */}
        {trend.semanticNiches && trend.semanticNiches.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {trend.semanticNiches.map((n) => (
              <span key={n} className="inline-flex items-center gap-1 rounded-full bg-secondary/15 text-secondary border border-secondary/20 px-2.5 py-0.5 text-xs font-semibold">
                # {n}
              </span>
            ))}
          </div>
        )}

        {/* Per-niche Adaptation Brief — injected by niche_relevance_engine */}
        {userNiche && userNiche !== 'all' && trend.adaptation_briefs?.[userNiche] && (
          <div className="rounded-xl bg-primary/5 border border-primary/20 p-4 space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wide text-primary flex items-center gap-1">
              <Zap className="h-3 w-3" /> Your Angle ({userNiche.replace('_', ' ')})
            </p>
            <p className="text-xs text-foreground/80 leading-relaxed">
              {trend.adaptation_briefs[userNiche]}
            </p>
          </div>
        )}

        {/* Niche Relevance Scores */}
        {trend.niche_relevance && Object.keys(trend.niche_relevance).length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Niche Fit</p>
            <div className="grid grid-cols-2 gap-1.5">
              {Object.entries(trend.niche_relevance as Record<string, number>)
                .filter(([, v]) => v > 0.2)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 6)
                .map(([niche, score]) => (
                  <div key={niche} className="flex items-center gap-2 rounded-lg bg-muted/40 px-2.5 py-1.5">
                    <div
                      className="h-1.5 rounded-full bg-primary/60 flex-shrink-0"
                      style={{ width: `${Math.round(score * 100)}%`, maxWidth: '48px', minWidth: '4px' }}
                    />
                    <span className="text-[10px] text-muted-foreground capitalize flex-1 truncate">
                      {niche.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] font-bold text-foreground">
                      {Math.round(score * 100)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {trend.whyThisWorks && (
          <p className="text-xs text-muted-foreground rounded-xl bg-white/[0.03] p-3 border border-border italic">
            💡 <strong>Why it's viral:</strong> {trend.whyThisWorks}
          </p>
        )}

        <div className="flex gap-2">
          <Button
            onClick={shareWhatsApp}
            variant="outline"
            className={`h-10 text-xs border-border ${FEATURES.GENERATE_ENABLED ? "flex-1" : "w-full"}`}
          >
            <Share2 className="h-3.5 w-3.5" /> Share on WhatsApp
          </Button>
          {FEATURES.GENERATE_ENABLED && (
            <Button
              onClick={() => navigate({ to: "/generate", search: { trendId: id } })}
              className="flex-1 h-10 text-xs bg-primary"
            >
              Generate Reel →
            </Button>
          )}
        </div>
      </div>

      {/* Posting Strategy */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-lg font-bold flex items-center gap-2">
          <Calendar className="h-5 w-5 text-primary" /> Posting Strategy
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-muted/50 p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">Best Time (IST)</p>
            <p className="font-display font-bold text-lg text-primary">{formatHour(trend.optimalPostHourIst)}</p>
          </div>
          <div className="rounded-xl bg-muted/50 p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">Post On</p>
            <p className="font-display font-bold text-lg capitalize">
              {trend.bestPlatformFirst === "youtube_shorts" ? "▶ YT Shorts" : "◎ Instagram"}
            </p>
          </div>
        </div>
        {captionKit?.posting_strategy?.reasoning && (
          <p className="text-xs text-muted-foreground italic">{captionKit.posting_strategy.reasoning}</p>
        )}
        {captionKit?.saturation_alert && (
          <div className="rounded-xl bg-primary/5 border border-primary/20 px-3 py-2.5">
            <p className="text-xs text-primary font-semibold">⏰ {captionKit.saturation_alert}</p>
          </div>
        )}
      </div>

      {/* Decision Layer */}
      {decision && (
        <PlanGate
          feature="AI Decision Support"
          requiredPlan="pro"
          currentPlan={userPlan}
          onUpgrade={() => window.location.href = '/pricing'}
        >
          <div className="glass-card p-5 space-y-3">
            <h2 className="font-display text-lg font-bold">🧠 Decision Layer</h2>
            <div className="grid grid-cols-3 gap-2">
              <DecisionPill label="Decision" value={decision.decision.toUpperCase()} />
              <DecisionPill label="Fit" value={`${Math.round((decision.trend.creator_fit_score || 0) * 100)}%`} />
              <DecisionPill label="Hook" value={`${Math.round((decision.trend.hook_retention_score || 0) * 100)}%`} />
            </div>
            <p className="text-sm text-muted-foreground">{decision.rationale}</p>
            <div className="rounded-xl bg-muted/40 p-3 space-y-2">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Trial hook</p>
              <p className="text-sm">{decision.test_hook}</p>
            </div>
            <div className="rounded-xl bg-muted/40 p-3 space-y-2">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Public hook</p>
              <p className="text-sm">{decision.public_hook}</p>
            </div>
          </div>
        </PlanGate>
      )}

      {/* Audio Cue */}
      {(trend.audioCueSecond !== undefined || captionKit?.audio_cue) && (
        <div className="glass-card p-5 space-y-3">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-secondary" /> Audio Cue
          </h2>
          <div className="rounded-xl bg-secondary/10 border border-secondary/20 p-4">
            <p className="text-sm font-semibold text-secondary">
              {captionKit?.audio_cue || `Start filming at the 0:${String(trend.audioCueSecond ?? 7).padStart(2, "0")} mark`}
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            This is the power moment in the song — nail this cue to maximize retention and replays.
          </p>
        </div>
      )}

      {/* Caption Kit */}
      <PlanGate
        feature="AI Caption Generation"
        requiredPlan="pro"
        currentPlan={userPlan}
        onUpgrade={() => window.location.href = '/pricing'}
      >
        <div className="glass-card p-5 space-y-4">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" /> Caption Kit
          </h2>

          {captionLoading ? (
            <div className="space-y-3">
              <div className="h-20 rounded-xl shimmer" />
              <div className="h-20 rounded-xl shimmer" />
            </div>
          ) : Array.isArray(captionKit?.captions) && captionKit.captions.length > 0 ? (
            <>
              {/* Vibe tabs */}
              <div className="flex gap-2">
                {captionKit.captions.map((c, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedVibe(i)}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize transition-all ${
                      selectedVibe === i
                        ? "bg-primary text-white"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {c.vibe}
                  </button>
                ))}
              </div>

              {/* Active caption */}
              <div className="relative rounded-xl bg-white/[0.03] border border-border p-4">
                <p className="text-sm leading-relaxed pr-8">{captionKit.captions[selectedVibe]?.text}</p>
                <button
                  onClick={() => copyCaption(selectedVibe)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                >
                  {copiedCaption === selectedVibe
                    ? <CheckCheck className="h-4 w-4 text-success" />
                    : <Copy className="h-4 w-4" />}
                </button>
              </div>

              {/* Hashtags */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Hashtags</p>
                  <button
                    onClick={copyHashtags}
                    className="flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    {copiedHashtags ? <CheckCheck className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    Copy all
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {captionKit.hashtags.map((tag, i) => (
                    <span key={i} className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                      #{tag.replace(/^#/, "")}
                    </span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              ⏳ Caption generation is coming soon for this trend — check back shortly.
            </p>
          )}
        </div>
      </PlanGate>

      {/* Keywords Strategy & Viral Script */}
      {captionKit?.keyword_strategy && (
        <div className="glass-card p-5 space-y-4">
          <h2 className="font-display text-lg font-bold flex items-center gap-2">
            <Flame className="h-5 w-5 text-amber-500" /> Keywords Strategy & Script 🚀
          </h2>
          
          {/* Target Keywords */}
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Target Keywords</p>
            <div className="flex flex-wrap gap-1.5">
              {captionKit.keyword_strategy.target_keywords?.map((keyword: string, idx: number) => (
                <span key={idx} className="rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20">
                  {keyword}
                </span>
              ))}
            </div>
          </div>

          {/* Keyword Placement Guide */}
          <div className="rounded-xl bg-white/[0.02] border border-border p-4 space-y-3">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Keyword Placement Guide</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="space-y-1">
                <span className="font-bold text-primary">🗣️ Spoken in Audio</span>
                <p className="text-muted-foreground">{captionKit.keyword_strategy.placement_guide?.spoken_audio}</p>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-primary">📺 On-Screen Text (0-3s)</span>
                <p className="text-muted-foreground">{captionKit.keyword_strategy.placement_guide?.on_screen_text}</p>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-primary">📝 Caption (First line)</span>
                <p className="text-muted-foreground">{captionKit.keyword_strategy.placement_guide?.caption}</p>
              </div>
              <div className="space-y-1">
                <span className="font-bold text-primary">🖼️ Alt Text (SEO)</span>
                <p className="text-muted-foreground">{captionKit.keyword_strategy.placement_guide?.alt_text}</p>
              </div>
            </div>
          </div>

          {/* Viral Script Outline */}
          {captionKit.viral_pattern_script && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                  30s Viral Script Flow ({captionKit.viral_pattern_script.hook_style})
                </p>
              </div>
              <div className="space-y-2 text-xs">
                {Object.entries(captionKit.viral_pattern_script.timeline || {}).map(([phase, text]: any, idx) => {
                  const phaseLabel = phase.replace(/_/g, " ").replace("s", "s — ");
                  return (
                    <div key={idx} className="flex gap-3 items-start p-2.5 rounded-lg bg-white/[0.01] hover:bg-white/[0.03] transition-all border border-border/50">
                      <span className="font-mono text-amber-500 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded text-[10px] whitespace-nowrap">
                        {phaseLabel}
                      </span>
                      <p className="text-muted-foreground leading-relaxed">{text}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* What to film */}
      <div className="glass-card p-5 space-y-3">
        <h2 className="font-display text-lg font-bold">🎬 What To Film</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">{trend.idealContentDescription}</p>
        {trend.cameraStyle && (
          <div className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2.5 text-xs font-semibold">
            <span className="text-muted-foreground">Camera style:</span>
            <span className="capitalize text-foreground">{trend.cameraStyle?.replace(/_/g, " ")}</span>
          </div>
        )}
      </div>

      {/* Source Reels — audio deep-link, no post/profile links */}
      {reels && reels.length > 0 && (() => {
        // Build audio deep-link from first reel that has audio_id
        const firstWithId = reels.find((r: any) => r.audio_id);
        const audioId = (firstWithId as any)?.audio_id;
        const audioTitle = reels[0]?.audio_title;
        const audioUrl = audioId
          ? `https://www.instagram.com/reels/audio/${audioId}/`
          : `https://www.instagram.com/explore/tags/${encodeURIComponent(audioTitle || "")}/`;

        return (
          <PlanGate
            feature="Trend Reels Analysis"
            requiredPlan="pro"
            currentPlan={userPlan}
            onUpgrade={() => window.location.href = '/pricing'}
          >
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-bold">📱 Source Reels</h2>
                <span className="text-xs font-semibold text-muted-foreground">{reels.length} found</span>
              </div>

              {/* Save Audio deep-link — the only external CTA */}
              <a
                href={audioUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/40 bg-primary/10 px-3 py-2.5 text-sm font-bold text-primary hover:bg-primary/20 transition-all"
              >
                <Music2 className="h-4 w-4" />
                {audioId ? "Save Audio on Instagram →" : "Search Audio on Instagram →"}
                <ExternalLink className="h-3 w-3 opacity-60" />
              </a>

              <div className="space-y-2">
                {reels.slice(0, 15).map((reel) => (
                  <div
                    key={reel.id}
                    className="flex items-center justify-between rounded-xl bg-muted/40 px-3 py-2.5 border border-transparent"
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs font-bold text-foreground">@{reel.owner_username}</p>
                        {reel.is_creator_outlier && (
                          <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 rounded-full px-1.5 py-0.5">
                            🎯 Breakout
                          </span>
                        )}
                      </div>
                      {reel.caption && (
                        <p className="text-xs text-muted-foreground line-clamp-1 italic mt-0.5">"{reel.caption}"</p>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-muted-foreground shrink-0">
                      {reel.view_count >= 1000 ? `${(reel.view_count / 1000).toFixed(0)}K` : reel.view_count} views
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </PlanGate>
        );
      })()}

      {/* Similar Trends */}
      {similarTrends && similarTrends.length > 0 && (
        <div className="glass-card p-5 space-y-3">
          <h2 className="font-display text-lg font-bold">🔗 Similar Past Trends</h2>
          <div className="space-y-2">
            {similarTrends.map((t) => (
              <button
                key={t.id}
                onClick={() => navigate({ to: "/trend/$id", params: { id: t.id } })}
                className="flex w-full items-center justify-between rounded-xl bg-muted/40 px-3 py-2.5 hover:bg-muted/60 transition-colors text-left"
              >
                <div>
                  <p className="text-sm font-semibold">{t.song}</p>
                  <p className="text-xs text-muted-foreground">{t.artist}</p>
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span>{t.viralMultiplier}x</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Generate CTA */}
      {FEATURES.GENERATE_ENABLED && (
        <Button
          onClick={() => navigate({ to: "/generate", search: { trendId: id } })}
          className="h-14 w-full bg-primary text-base font-bold uppercase tracking-widest shadow-lg shadow-primary/20 hover:scale-[1.01] transition-transform"
        >
          🎤 Generate My Reel For This Trend
        </Button>
      )}
    </div>
  );
}

function StatPill({ label, value, color = "text-foreground" }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl bg-muted/50 p-3 text-center">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-sm font-bold ${color}`}>{value}</p>
    </div>
  );
}

function DecisionPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted/50 p-3 text-center">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="font-display font-bold text-sm">{value}</p>
    </div>
  );
}
