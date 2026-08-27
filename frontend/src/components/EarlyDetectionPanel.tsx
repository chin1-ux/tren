import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, Clock, AlertCircle, CheckCircle, Calendar, Flame, Zap, Music2, Newspaper, PartyPopper, Layout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { PlanGate } from "./PlanGate";
import { FEATURES } from "@/lib/features";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

interface EarlyDetectionTrend {
  id: number;
  audio_title: string;
  audio_artist: string;
  prediction: {
    combined_score: number;
    prediction: string;
    optimal_timing: string;
    reach_multiplier: string;
    recommended_action: string;
  };
}

interface CulturalEvent {
  name: string;
  date: string;
  days_until: number;
  content_themes: string[];
  hashtags: string[];
}

// The /trends/emerging endpoint returns a flat trend shape (creator_fit_score,
// hook_retention_score, saturation_penalty, window_hours_remaining,
// optimal_post_hour_ist) — not the nested `prediction` object this panel
// renders. Derive the display fields from the real values instead of
// filtering everything out.
function mapEarlyTrend(t: any): EarlyDetectionTrend | null {
  if (!t || t.id == null) return null;
  if (t?.prediction?.combined_score != null) return t as EarlyDetectionTrend;
  if (t.status !== 'emerging' && t.status !== 'rising') return null;
  const fit = typeof t.creator_fit_score === 'number' ? t.creator_fit_score : null;
  const hook = typeof t.hook_retention_score === 'number' ? t.hook_retention_score : null;
  const sat = typeof t.saturation_penalty === 'number' ? t.saturation_penalty : null;
  if (fit == null || hook == null || sat == null) return null;
  const score = Math.round(100 * Math.min(1, Math.max(0, 0.4 * fit + 0.35 * hook + 0.25 * (1 - sat))));
  const hoursLeft = Number.isFinite(t.window_hours_remaining) ? Math.max(0, Math.round(t.window_hours_remaining)) : null;
  const timing = Number.isFinite(t.optimal_post_hour_ist)
    ? `${String(Math.floor(t.optimal_post_hour_ist)).padStart(2, '0')}:00 IST`
    : 'N/A';
  return {
    id: t.id,
    audio_title: t.audio_title ?? 'Unknown audio',
    audio_artist: t.audio_artist ?? '',
    prediction: {
      combined_score: score,
      prediction: t.status ?? '',
      optimal_timing: timing,
      reach_multiplier: hoursLeft != null ? `${hoursLeft}h` : '—',
      recommended_action:
        hoursLeft == null || hoursLeft <= 0 ? 'WINDOW CLOSED' : hoursLeft < 12 ? 'POST SOON' : 'CREATE CONTENT NOW',
    },
  };
}

export function EarlyDetectionPanel() {
  const [earlyTrends, setEarlyTrends] = useState<EarlyDetectionTrend[]>([]);
  const [culturalEvents, setCulturalEvents] = useState<CulturalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'trends' | 'events'>('trends');
  // Signal type filter (E9 — Notification Center filter)
  type SignalFilter = 'all' | 'audio' | 'format' | 'news' | 'festival';
  const [signalFilter, setSignalFilter] = useState<SignalFilter>('all');
  // Read plan and niche from the Zustand store — same source as the rest of the app.
  const userPlan = useUserStore((s) => s.plan) || 'free';
  const userNiche = useUserStore((s) => s.niche) || 'all';

  useEffect(() => {
    fetchEarlyTrends();
    fetchCulturalEvents();
  }, []);

  const fetchEarlyTrends = async () => {
    if (userPlan === "free") {
      setEarlyTrends([]);
      setLoading(false);
      return;
    }
    try {
      // Use apiFetch (not bare fetch) so the Authorization: Bearer <token> header
      // is injected automatically from inMemoryToken / trendrop_session_token.
      // Without this, get_current_user returns guest@trendrop.app and
      // require_feature("early_detection") raises 401 for every user.
      const res = await apiFetch('/api/trends/emerging');
      if (res.ok) {
        const data = await res.json();
        // Map flat API rows into the display shape; drop rows we can't derive.
        setEarlyTrends((data || []).map(mapEarlyTrend).filter(Boolean));
      } else if (res.status === 401 || res.status === 403) {
        // 401 = unauthenticated (token missing/expired), 403 = plan gate
        // Both mean we cannot show early trends — PlanGate will handle the UI.
        setEarlyTrends([]);
      }
    } catch (err) {
      console.error('Error fetching early trends:', err);
      toast.error("Could not load early trend data");
    } finally {
      setLoading(false);
    }
  };

  const fetchCulturalEvents = async () => {
    try {
      const res = await apiFetch('/api/india/cultural-events?days_ahead=90');
      if (res.ok) {
        const data = await res.json();
        if (data.events && data.events.length > 0) {
          setCulturalEvents(data.events);
          return;
        }
      }
    } catch (err) {
      console.error('Error fetching cultural events:', err);
      toast.error("Could not load cultural events");
    }
    
    // Localized Indian festivals fallback content calendar — days_until computed dynamically
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const calcDays = (monthDay: string, year?: number) => {
      const d = new Date(`${monthDay}, ${year ?? today.getFullYear()}`);
      return Math.max(0, Math.ceil((d.getTime() - today.getTime()) / 86400000));
    };
    const festivals = [
      { name: "Independence Day Celebration", monthDay: "August 15", content_themes: ["Patriotic edits", "Freedom transitions", "Indian flag colors styling"], hashtags: ["independenceday", "india", "harghartiranga"] },
      { name: "Raksha Bandhan", monthDay: "August 28", content_themes: ["Sibling comedy reels", "Gift unboxings", "Traditional outfits transitions"], hashtags: ["rakshabandhan", "siblings", "festivevibes"] },
      { name: "Krishna Janmashtami", monthDay: "September 4", content_themes: ["Dahi Handi celebrations", "Krishna bhajan transition audio", "Ethnic wear styling"], hashtags: ["janmashtami", "krishna", "festive"] },
      { name: "Ganesh Chaturthi", monthDay: "September 15", content_themes: ["Ganesha welcome reels", "Modak making recipe", "Aarti singing challenge"], hashtags: ["ganeshchaturthi", "ganpati", "morya"] },
    ];
    setCulturalEvents(
      festivals
        .map((f) => ({
          ...f,
          date: `${f.monthDay}, ${today.getFullYear()}`,
          days_until: calcDays(f.monthDay),
        }))
        .sort((a, b) => a.days_until - b.days_until)
        .filter((f) => f.days_until >= 0)
    );
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

  const getUrgencyBadge = (days: number) => {
    if (days <= 7) return { text: 'URGENT', color: 'bg-red-500' };
    if (days <= 30) return { text: 'SOON', color: 'bg-yellow-500' };
    return { text: 'UPCOMING', color: 'bg-blue-500' };
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <PlanGate 
      feature="Early Detection" 
      requiredPlan="pro" 
      currentPlan={userPlan}
      onUpgrade={() => window.location.href = '/pricing'}
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold font-display flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Early Detection
            </h2>
            <p className="text-xs text-muted-foreground">
              Trends before they go viral
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={activeTab === 'trends' ? 'default' : 'outline'}
              onClick={() => setActiveTab('trends')}
              className="rounded-full text-xs"
            >
              <TrendingUp className="h-3 w-3 mr-1" />
              Trends
            </Button>
            {FEATURES.CALENDAR_ENABLED && (
              <Button
                size="sm"
                variant={activeTab === 'events' ? 'default' : 'outline'}
                onClick={() => setActiveTab('events')}
                className="rounded-full text-xs"
              >
                <Calendar className="h-3 w-3 mr-1" />
                Events
              </Button>
            )}
          </div>
        </div>

        {/* Signal Type Filter Pills (E9) */}
        {activeTab === 'trends' && (
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
            {([
              { key: 'all',      label: 'All',      icon: <Sparkles className="h-3 w-3" /> },
              { key: 'audio',    label: 'Audio',    icon: <Music2 className="h-3 w-3" /> },
              { key: 'format',   label: 'Format',   icon: <Layout className="h-3 w-3" /> },
              { key: 'news',     label: 'News',     icon: <Newspaper className="h-3 w-3" /> },
              { key: 'festival', label: 'Festival', icon: <PartyPopper className="h-3 w-3" /> },
            ] as { key: SignalFilter; label: string; icon: React.ReactNode }[]).map((f) => (
              <button
                key={f.key}
                onClick={() => setSignalFilter(f.key)}
                className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border transition-all ${
                  signalFilter === f.key
                    ? 'bg-primary text-white border-primary shadow-sm shadow-primary/20'
                    : 'bg-muted/50 text-muted-foreground border-border/40 hover:bg-muted hover:text-foreground'
                }`}
              >
                {f.icon}
                {f.label}
              </button>
            ))}
          </div>
        )}

      {activeTab === 'trends' ? (() => {
        const filtered = signalFilter === 'all' ? earlyTrends : earlyTrends.filter((t: any) => {
          if (signalFilter === 'audio')    return (t.content_type ?? '').toLowerCase().includes('audio') || t.niche_tag == null;
          if (signalFilter === 'format')   return (t.content_type ?? '').toLowerCase().includes('format') || (t.niche_tag ?? '').includes('format');
          if (signalFilter === 'news')     return (t.niche_tag ?? '').includes('news') || (t.content_type ?? '').includes('news');
          if (signalFilter === 'festival') return (t.niche_tag ?? '').includes('festival') || (t.niche_tag ?? '').includes('cultural');
          return true;
        });
        return (
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <TrendingUp className="h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">
                {signalFilter === 'all' ? 'No early trends detected' : `No ${signalFilter} trends right now`}
              </p>
            </div>
          ) : (
            filtered.map((trend, index) => (
              <motion.div
                key={trend.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-card border border-border p-4 rounded-2xl hover:border-primary/20 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-sm font-semibold font-display truncate">
                        {trend.audio_title}
                      </h3>
                      <span className={`px-2 py-0.5 text-[10px] font-bold ${getScoreBg(trend.prediction?.combined_score ?? 0)} ${getScoreColor(trend.prediction?.combined_score ?? 0)} rounded-full`}>
                        {(trend.prediction?.combined_score ?? 0).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">
                      {trend.audio_artist}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      <span>{trend.prediction?.optimal_timing ?? 'N/A'}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className={`w-10 h-10 rounded-full ${getScoreBg(trend.prediction.combined_score)} flex items-center justify-center ${getScoreColor(trend.prediction.combined_score)} font-bold font-display text-sm`}>
                      {trend.prediction.reach_multiplier}
                    </div>
                    <span className={`text-[9px] font-bold ${trend.prediction.recommended_action === 'CREATE CONTENT NOW' ? 'text-green-500' : 'text-yellow-500'}`}>
                      {trend.prediction.recommended_action}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
        );
      })() : FEATURES.CALENDAR_ENABLED ? (
        <div className="space-y-3">
          {culturalEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Calendar className="h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">No upcoming cultural events</p>
            </div>
          ) : (
            culturalEvents.map((event, index) => (
              <motion.div
                key={event.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-card border border-border p-4 rounded-2xl hover:border-primary/20 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-sm font-semibold font-display">
                        {event.name}
                      </h3>
                      <span className={`px-2 py-0.5 text-[10px] font-bold ${getUrgencyBadge(event.days_until).color} text-white rounded-full`}>
                        {getUrgencyBadge(event.days_until).text}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">
                      {event.date} ({event.days_until} days away)
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {event.content_themes.slice(0, 3).map((theme, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 text-[10px] bg-primary/10 text-primary rounded-full"
                        >
                          {theme}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => toast.info(`Content ideas for ${event.name} coming soon!`)}
                      className="rounded-full text-xs"
                    >
                      <Flame className="h-3 w-3 mr-1" />
                      Ideas
                    </Button>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      ) : null}

      {/* Info Banner */}
      <div className="bg-gradient-to-r from-primary/10 to-primary/10 border border-primary/20 p-4 rounded-2xl">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary shrink-0">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold font-display mb-1">Why Early Detection Matters</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Joining trends early while they're still rising gives you 3x more reach. 
              Most tools only show trends AFTER they're viral - we predict them BEFORE.
            </p>
          </div>
        </div>
      </div>
    </div>
    </PlanGate>
  );
}