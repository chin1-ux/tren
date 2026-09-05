import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useUserStore } from "@/store/useAppStore";
import { FEATURES } from "@/lib/features";
import {
  Building2, Search, Users, TrendingUp, Star, Send, ExternalLink,
  Filter, Heart, MessageCircle, Eye, X, CheckCircle
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { apiFetch, type CollabMatch } from "@/lib/api";

interface CreatorProfile {
  instagram_username: string;
  niche: string;
  followers: number;
  engagement_rate: number;
  trend_score: number;
  price_per_post: number;
  is_active: boolean;
  user_email?: string;
  portfolio_links?: string;
}

async function fetchCreatorProfiles(niche?: string): Promise<CreatorProfile[]> {
  const params = niche && niche !== "all" ? `?niche=${encodeURIComponent(niche)}` : "";
  const res = await apiFetch(`/api/marketplace/profiles${params}`);
  if (!res.ok) throw new Error("Failed to fetch profiles");
  return res.json();
}

async function fetchCollabMatchesForUser(userEmail: string): Promise<CollabMatch[]> {
  const res = await apiFetch(`/api/collab-matches/${encodeURIComponent(userEmail)}`);
  if (!res.ok) throw new Error("Failed to fetch matches");
  return res.json();
}

async function sendCollabReq(fromEmail: string, toEmail: string, message: string) {
  const res = await apiFetch("/api/send-collab-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from_email: fromEmail, to_email: toEmail, message }),
  });
  if (!res.ok) throw new Error("Failed to send request");
  return res.json();
}

const NICHES = [
  { id: "all", label: "All Niches", emoji: "🔍" },
  { id: "fashion", label: "Fashion", emoji: "👗" },
  { id: "fitness", label: "Fitness", emoji: "💪" },
  { id: "dance", label: "Dance", emoji: "💃" },
  { id: "travel", label: "Travel", emoji: "✈️" },
  { id: "comedy", label: "Comedy", emoji: "😂" },
  { id: "food", label: "Food", emoji: "🍳" },
  { id: "tech", label: "Tech", emoji: "💻" },
  { id: "education", label: "Education", emoji: "📚" },
  { id: "devotional", label: "Devotional", emoji: "🙏" },
  { id: "narrative_edit", label: "Creative Edit", emoji: "🎞️" },
  { id: "romance_relationship", label: "Romance", emoji: "💕" },
];

export const Route = createFileRoute("/marketplace")({
  head: () => ({
    meta: [
      { title: "Creator Marketplace — Trendrop" },
      { name: "description", content: "Apply for exclusive brand deals, find creators in your niche, and manage collaborations." },
    ],
  }),
  component: MarketplacePage,
});

function MarketplacePage() {
  const { user } = useAuth();
  const userEmail = useUserStore((s) => s.email) ?? "";
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!FEATURES.MARKETPLACE_ENABLED) {
      navigate({ to: "/" });
    }
  }, [navigate]);

  if (!FEATURES.MARKETPLACE_ENABLED) return null;

  const [activeTab, setActiveTab] = useState<"discover" | "matches">("discover");
  const [nicheFilter, setNicheFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [collabModal, setCollabModal] = useState<CreatorProfile | null>(null);
  const [collabMessage, setCollabMessage] = useState("");

  useEffect(() => {
    if (!user) navigate({ to: "/login" });
  }, [user, navigate]);

  // Fetch creator profiles
  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: ["marketplace-profiles", nicheFilter],
    queryFn: () => fetchCreatorProfiles(nicheFilter),
    staleTime: 60_000,
  });

  // Fetch collab matches
  const { data: matches = [], isLoading: matchesLoading } = useQuery({
    queryKey: ["collab-matches", userEmail],
    queryFn: () => fetchCollabMatchesForUser(userEmail),
    enabled: !!userEmail && activeTab === "matches",
    staleTime: 60_000,
  });

  // Send collab mutation
  const collabMutation = useMutation({
    mutationFn: ({ toEmail, message }: { toEmail: string; message: string }) =>
      sendCollabReq(userEmail, toEmail, message),
    onSuccess: (data) => {
      toast.success(data.message || "Collaboration request sent!");
      setCollabModal(null);
      setCollabMessage("");
      queryClient.invalidateQueries({ queryKey: ["collab-matches", userEmail] });
    },
    onError: () => toast.error("Failed to send collaboration request"),
  });

  if (!user) return null;

  const filteredProfiles = profiles.filter((p) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      p.instagram_username?.toLowerCase().includes(q) ||
      p.niche?.toLowerCase().includes(q)
    );
  });

  const formatFollowers = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return (
    <div className="flex flex-col min-h-screen bg-bg pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-surface/95 backdrop-blur-lg border-b border-border px-4 pt-4 pb-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-coral to-rose-500 flex items-center justify-center">
              <Building2 className="h-4 w-4 text-white" />
            </div>
            <h1 className="text-lg font-bold tracking-tight font-display">Marketplace</h1>
          </div>
          <span className="text-[10px] text-muted-foreground font-medium">
            {profiles.length} creators
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-muted/40 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab("discover")}
            className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === "discover"
                ? "bg-surface text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Users className="h-3.5 w-3.5 inline mr-1.5" />
            Discover Creators
          </button>
          <button
            onClick={() => setActiveTab("matches")}
            className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === "matches"
                ? "bg-surface text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Heart className="h-3.5 w-3.5 inline mr-1.5" />
            Collab Matches
          </button>
        </div>
      </div>

      {/* Discover Tab */}
      {activeTab === "discover" && (
        <div className="flex flex-col gap-4 px-4 pt-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search creators by name or niche..."
              className="w-full bg-surface border border-border rounded-xl pl-9 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          {/* Niche Filter */}
          <div className="flex gap-2 overflow-x-auto no-scrollbar -mx-4 px-4">
            {NICHES.map((n) => (
              <button
                key={n.id}
                onClick={() => setNicheFilter(n.id)}
                className={`shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                  nicheFilter === n.id
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-surface text-muted-foreground hover:text-foreground"
                }`}
              >
                <span>{n.emoji}</span>
                <span>{n.label}</span>
              </button>
            ))}
          </div>

          {/* Profile Grid */}
          {profilesLoading ? (
            <div className="grid gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="rounded-2xl border border-border bg-surface p-4 animate-pulse">
                  <div className="h-12 w-12 rounded-full bg-muted" />
                  <div className="h-4 w-32 rounded bg-muted mt-3" />
                  <div className="h-3 w-20 rounded bg-muted mt-2" />
                </div>
              ))}
            </div>
          ) : filteredProfiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
              <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center">
                <Users className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-bold text-foreground">No creators found</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {searchQuery ? "Try a different search" : "Be the first to create a profile!"}
                </p>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 pb-4">
              {filteredProfiles.map((profile, i) => (
                <div
                  key={profile.instagram_username + i}
                  className="rounded-2xl border border-border bg-surface hover:border-primary/30 transition-all overflow-hidden"
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-coral to-rose-500 flex items-center justify-center text-white text-sm font-bold">
                          {profile.instagram_username?.[0]?.toUpperCase() || "?"}
                        </div>
                        <div>
                          <p className="font-bold text-foreground text-sm">
                            @{profile.instagram_username || "unknown"}
                          </p>
                          <p className="text-xs text-muted-foreground capitalize">
                            {profile.niche || "General"}
                          </p>
                        </div>
                      </div>
                      {profile.trend_score > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-[10px] font-bold">
                          {profile.trend_score} Score
                        </span>
                      )}
                    </div>

                    {/* Stats */}
                    <div className="flex gap-4 mt-3 pt-3 border-t border-border/50">
                      <div className="flex items-center gap-1.5">
                        <Users className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-bold text-foreground">
                          {formatFollowers(profile.followers || 0)}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <TrendingUp className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-bold text-foreground">
                          {(profile.engagement_rate || 0).toFixed(1)}%
                        </span>
                      </div>
                      {profile.price_per_post > 0 && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-emerald-500">
                            ₹{(profile.price_per_post || 0).toLocaleString("en-IN")}/post
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 mt-3">
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 h-8 text-xs rounded-lg border-border"
                        onClick={() => setCollabModal(profile)}
                      >
                        <Send className="h-3 w-3 mr-1" />
                        Collab
                      </Button>
                      {profile.portfolio_links && (
                        <a
                          href={profile.portfolio_links}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 px-3 h-8 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Portfolio
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Collab Matches Tab */}
      {activeTab === "matches" && (
        <div className="flex flex-col gap-3 px-4 pt-4">
          {matchesLoading ? (
            <div className="grid gap-3">
              {[1, 2].map((i) => (
                <div key={i} className="rounded-2xl border border-border bg-surface p-4 animate-pulse">
                  <div className="h-10 w-10 rounded-full bg-muted" />
                  <div className="h-4 w-24 rounded bg-muted mt-3" />
                </div>
              ))}
            </div>
          ) : matches.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
              <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center">
                <Heart className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-bold text-foreground">No matches yet</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Complete your creator profile to get matched with collaborators
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl text-xs"
                onClick={() => navigate({ to: "/settings" })}
              >
                Set up profile
              </Button>
            </div>
          ) : (
            <div className="grid gap-3 pb-4">
              {matches.map((match) => (
                <div
                  key={match.instagram_username}
                  className="rounded-2xl border border-border bg-surface p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-white text-sm font-bold">
                        {match.instagram_username?.[0]?.toUpperCase() || "?"}
                      </div>
                      <div>
                        <p className="font-bold text-foreground text-sm">
                          @{match.instagram_username || "unknown"}
                        </p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {match.niche || "General"}
                        </p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">
                      {match.compatibility_score}% match
                    </span>
                  </div>

                  <div className="flex gap-4 mt-3 pt-3 border-t border-border/50">
                    <div className="flex items-center gap-1.5">
                      <Users className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs font-bold">
                        {formatFollowers(match.followers || 0)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs font-bold">
                        {(match.engagement_rate || 0).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="mt-3">
                    {match.request_sent ? (
                      <div className="flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
                        <CheckCircle className="h-3.5 w-3.5" />
                        Request sent
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        className="w-full h-8 text-xs rounded-lg bg-primary text-white"
                        onClick={() => setCollabModal({
                          ...match,
                          price_per_post: 0,
                          is_active: true,
                        })}
                      >
                        <Send className="h-3 w-3 mr-1" />
                        Send Collab Request
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Collab Request Modal */}
      {collabModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-foreground">Send Collab Request</h3>
              <button
                onClick={() => { setCollabModal(null); setCollabMessage(""); }}
                className="h-8 w-8 rounded-lg flex items-center justify-center hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-center gap-3 mb-4 p-3 rounded-xl bg-muted/40">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-white text-xs font-bold">
                {collabModal.instagram_username?.[0]?.toUpperCase() || "?"}
              </div>
              <div>
                <p className="text-sm font-bold">@{collabModal.instagram_username}</p>
                <p className="text-xs text-muted-foreground capitalize">{collabModal.niche}</p>
              </div>
            </div>
            <textarea
              value={collabMessage}
              onChange={(e) => setCollabMessage(e.target.value)}
              placeholder="Write a short message about why you'd like to collaborate..."
              rows={4}
              className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none mb-4"
            />
            <Button
              className="w-full rounded-xl bg-primary text-white font-bold h-11"
              disabled={!collabMessage.trim() || collabMutation.isPending}
              onClick={() => collabMutation.mutate({
                toEmail: collabModal.user_email || "",
                message: collabMessage,
              })}
            >
              {collabMutation.isPending ? "Sending..." : "Send Request"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
