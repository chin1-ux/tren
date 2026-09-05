import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Calendar, MapPin, ChevronRight, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

interface FestivalEvent {
  slug: string;
  name: string;
  local_name?: string;
  start_date: string;
  days_until: number;
  feed_flood_intensity: number;
  niche_opportunities: Record<string, number>;
  hashtags: string[];
  primary_regions: string[];
  duration_days: number;
  content_windows?: Record<string, string>;
}

const STATE_TO_REGION: Record<string, string[]> = {
  KL: ["kerala"],
  KA: ["karnataka"],
  AP: ["andhra_pradesh"],
  TG: ["telangana"],
  TN: ["tamil_nadu"],
  MH: ["maharashtra", "goa"],
  GJ: ["gujarat"],
  PB: ["punjab"],
  WB: ["west_bengal"],
  AS: ["assam"],
  DL: ["north_india", "delhi"],
  UP: ["uttar_pradesh", "north_india"],
};

const INTENSITY_LABEL: (v: number) => { text: string; color: string } = (v) => {
  if (v >= 0.9) return { text: "Feed Flood 🌊", color: "text-red-500" };
  if (v >= 0.7) return { text: "High Buzz ⚡", color: "text-orange-500" };
  return { text: "Moderate", color: "text-yellow-500" };
};

// Static 2026 fallback calendar — keeps UI live even before DB migration
const STATIC_FESTIVALS: FestivalEvent[] = (() => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const daysUntil = (dateStr: string) =>
    Math.max(0, Math.ceil((new Date(dateStr).getTime() - today.getTime()) / 86400000));
  return [
    { slug: "ganesh_chaturthi_2026", name: "Ganesh Chaturthi", local_name: "गणेश चतुर्थी", start_date: "2026-09-14", days_until: daysUntil("2026-09-14"), feed_flood_intensity: 0.92, niche_opportunities: { food: 0.85, dance: 0.8, decor: 0.9, music: 0.85, fashion: 0.75 }, hashtags: ["#GaneshChaturthi2026", "#GanpatiBappaMorya"], primary_regions: ["maharashtra", "goa", "karnataka"], duration_days: 10 } as FestivalEvent,
    { slug: "navratri_2026", name: "Navratri (Sharad)", local_name: "नवरात्रि", start_date: "2026-09-28", days_until: daysUntil("2026-09-28"), feed_flood_intensity: 0.85, niche_opportunities: { dance: 0.95, fashion: 0.9, food: 0.7, beauty: 0.85 }, hashtags: ["#Navratri2026", "#Garba"], primary_regions: ["gujarat", "rajasthan"], duration_days: 9 } as FestivalEvent,
    { slug: "durga_puja_2026", name: "Durga Puja", local_name: "দুর্গাপূজা", start_date: "2026-10-17", days_until: daysUntil("2026-10-17"), feed_flood_intensity: 0.98, niche_opportunities: { fashion: 0.95, food: 0.85, travel: 0.8, dance: 0.85 }, hashtags: ["#DurgaPuja2026", "#Pujo2026"], primary_regions: ["west_bengal", "assam"], duration_days: 5 } as FestivalEvent,
    { slug: "karva_chauth_2026", name: "Karva Chauth", local_name: "करवा चौथ", start_date: "2026-10-29", days_until: daysUntil("2026-10-29"), feed_flood_intensity: 0.9, niche_opportunities: { fashion: 0.95, beauty: 0.95, food: 0.7 }, hashtags: ["#KarvaChauth2026"], primary_regions: ["punjab", "north_india"], duration_days: 1 } as FestivalEvent,
    { slug: "diwali_2026", name: "Diwali", local_name: "दिवाली", start_date: "2026-11-14", days_until: daysUntil("2026-11-14"), feed_flood_intensity: 0.98, niche_opportunities: { decor: 0.95, food: 0.9, fashion: 0.95, travel: 0.7 }, hashtags: ["#Diwali2026", "#FestivalOfLights"], primary_regions: [], duration_days: 5 } as FestivalEvent,
  ].sort((a, b) => a.days_until - b.days_until);
})();

export function RegionalFestivalPanel() {
  const [festivals, setFestivals] = useState<FestivalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const userNiche = useUserStore((s) => s.niche) || "all";
  // State is not yet in the Zustand store, so read from localStorage
  const userState = typeof window !== "undefined"
    ? localStorage.getItem("trendrop_user_state") ?? ""
    : "";
  const userRegions = STATE_TO_REGION[userState] ?? [];

  useEffect(() => {
    fetchFestivals();
  }, []);

  const fetchFestivals = async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/api/india/cultural-events?days_ahead=120");
      if (res.ok) {
        const data = await res.json();
        if (data?.events?.length > 0) {
          setFestivals(data.events);
          return;
        }
      }
    } catch {
      // fall through to static
    }
    setFestivals(STATIC_FESTIVALS);
    setLoading(false);
  };

  // Sort: state-specific festivals first, then pan-india, then others
  const sorted = [...festivals].sort((a, b) => {
    const aMatch = userRegions.some((r) => a.primary_regions.includes(r) || a.primary_regions.length === 0);
    const bMatch = userRegions.some((r) => b.primary_regions.includes(r) || b.primary_regions.length === 0);
    if (aMatch && !bMatch) return -1;
    if (!aMatch && bMatch) return 1;
    return a.days_until - b.days_until;
  });

  const getNicheScore = (f: FestivalEvent): number => {
    if (!userNiche || userNiche === "all") return 0;
    return Math.round((f.niche_opportunities?.[userNiche] ?? 0) * 100);
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold font-display flex items-center gap-2">
            <Calendar className="h-5 w-5 text-orange-500" />
            Regional Festival Feed
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {userState
              ? `Showing festivals relevant to ${userState}`
              : "Set your state in Settings for personalised ordering"}
          </p>
        </div>
      </div>

      {sorted.slice(0, 6).map((festival, idx) => {
        const isRegional = userRegions.some(
          (r) => festival.primary_regions.includes(r) || festival.primary_regions.length === 0
        );
        const intensityInfo = INTENSITY_LABEL(festival.feed_flood_intensity);
        const nicheScore = getNicheScore(festival);
        const urgencyColor =
          festival.days_until <= 3
            ? "border-red-500/40 bg-red-500/5"
            : festival.days_until <= 10
            ? "border-orange-500/40 bg-orange-500/5"
            : "border-border bg-card";

        return (
          <motion.div
            key={festival.slug}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.07 }}
            className={`rounded-2xl border p-4 ${urgencyColor} transition-all hover:shadow-md`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                {/* Title + badges */}
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <h3 className="text-sm font-bold font-display truncate">
                    {festival.name}
                    {festival.local_name && (
                      <span className="ml-1 text-muted-foreground font-normal">
                        ({festival.local_name})
                      </span>
                    )}
                  </h3>
                  {isRegional && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/30">
                      Your Region
                    </span>
                  )}
                </div>

                {/* Date + duration */}
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground mb-2">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(festival.start_date).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                    })}
                    {festival.duration_days > 1 && ` (${festival.duration_days} days)`}
                  </span>
                  {festival.primary_regions.length > 0 && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {festival.primary_regions.slice(0, 2).join(", ")}
                    </span>
                  )}
                  <span className={`font-semibold ${intensityInfo.color}`}>
                    {intensityInfo.text}
                  </span>
                </div>

                {/* Hashtags */}
                <div className="flex flex-wrap gap-1">
                  {festival.hashtags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 text-[10px] bg-primary/10 text-primary rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Right panel */}
              <div className="flex flex-col items-end gap-2 shrink-0">
                <div className="text-right">
                  <p className="text-xs font-bold">
                    {festival.days_until === 0
                      ? "Today 🎉"
                      : festival.days_until === 1
                      ? "Tomorrow"
                      : `In ${festival.days_until}d`}
                  </p>
                  {nicheScore > 0 && (
                    <p className="text-[10px] text-muted-foreground flex items-center gap-0.5 justify-end">
                      <Star className="h-2.5 w-2.5 text-yellow-500" />
                      {nicheScore}% niche fit
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-full text-[10px] h-7 px-3 gap-1"
                  onClick={() => toast.info(`Content ideas for ${festival.name} coming soon!`)}
                >
                  Ideas
                  <ChevronRight className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </motion.div>
        );
      })}

      {sorted.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Calendar className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">No upcoming festivals found</p>
        </div>
      )}
    </div>
  );
}
