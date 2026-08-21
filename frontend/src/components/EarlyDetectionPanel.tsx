import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, Clock, AlertCircle, CheckCircle, Calendar, Flame, Zap } from "lucide-react";
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

export function EarlyDetectionPanel() {
  const [earlyTrends, setEarlyTrends] = useState<EarlyDetectionTrend[]>([]);
  const [culturalEvents, setCulturalEvents] = useState<CulturalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'trends' | 'events'>('trends');
  // Read plan from the Zustand store — same source as the rest of the app.
  // The verify endpoint now normalises 'creator'/'agency' → 'pro'/'business'
  // so PlanGate's === 'pro' check will pass correctly.
  const userPlan = useUserStore((s) => s.plan) || 'free';

  useEffect(() => {
    fetchEarlyTrends();
    fetchCulturalEvents();
  }, []);

  const fetchEarlyTrends = async () => {
    try {
      // Use apiFetch (not bare fetch) so the Authorization: Bearer <token> header
      // is injected automatically from inMemoryToken / trendrop_session_token.
      // Without this, get_current_user returns guest@trendrop.app and
      // require_feature("early_detection") raises 401 for every user.
      const res = await apiFetch('/api/trends/emerging');
      if (res.ok) {
        const data = await res.json();
        // Filter out items with missing prediction to avoid TypeError crashes
        setEarlyTrends((data || []).filter((t: EarlyDetectionTrend) => t?.prediction?.combined_score != null));
      } else if (res.status === 401 || res.status === 403) {
        // 401 = unauthenticated (token missing/expired), 403 = plan gate
        // Both mean we cannot show early trends — PlanGate will handle the UI.
        setEarlyTrends([]);
      }
    } catch (err) {
      console.error('Error fetching early trends:', err);
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
    }
    
    // Localized Indian festivals fallback content calendar
    setCulturalEvents([
      { name: "Independence Day Celebration", date: "August 15, 2026", days_until: 6, content_themes: ["Patriotic edits", "Freedom transitions", "Indian flag colors styling"], hashtags: ["independenceday", "india", "harghartiranga"] },
      { name: "Raksha Bandhan", date: "August 28, 2026", days_until: 19, content_themes: ["Sibling comedy reels", "Gift unboxings", "Traditional outfits transitions"], hashtags: ["rakshabandhan", "siblings", "festivevibes"] },
      { name: "Krishna Janmashtami", date: "September 4, 2026", days_until: 26, content_themes: ["Dahi Handi celebrations", "Krishna bhajan transition audio", "Ethnic wear styling"], hashtags: ["janmashtami", "krishna", "festive"] },
      { name: "Ganesh Chaturthi", date: "September 15, 2026", days_until: 37, content_themes: ["Ganesha welcome reels", "Modak making recipe", "Aarti singing challenge"], hashtags: ["ganeshchaturthi", "ganpati", "morya"] }
    ]);
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

      {activeTab === 'trends' ? (
        <div className="space-y-3">
          {earlyTrends.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <TrendingUp className="h-12 w-12 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">No early trends detected</p>
            </div>
          ) : (
            earlyTrends.map((trend, index) => (
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
      ) : FEATURES.CALENDAR_ENABLED ? (
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
      <div className="bg-gradient-to-r from-primary/10 to-indigo-500/10 border border-primary/20 p-4 rounded-2xl">
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