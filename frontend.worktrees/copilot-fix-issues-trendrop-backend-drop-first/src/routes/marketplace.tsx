import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  Building2, Users, DollarSign, CheckCircle, Briefcase, MessageSquare, 
  Sparkles, Compass, AlertCircle, Send, ShieldAlert, Award, Loader2, ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { 
  apiFetch, 
  fetchBrandDeals, 
  applyToBrandDeal, 
  fetchCollabMatches, 
  sendCollabRequest,
  BrandDeal,
  BrandDealStats,
  CollabMatch
} from "@/lib/api";

export const Route = createFileRoute("/marketplace")({
  head: () => ({
    meta: [
      { title: "Creator Marketplace — Trendrop" },
      { name: "description", content: "Apply for exclusive brand deals, find creators in your niche, and manage collaborations." },
    ],
  }),
  component: MarketplacePage,
});

interface CreatorProfile {
  instagram_username: string;
  niche: string;
  followers: number;
  engagement_rate: number;
  price_per_post: number;
}

function MarketplacePage() {
  const [activeTab, setActiveTab] = useState<"deals" | "collabs">("deals");
  const email = localStorage.getItem("trendrop_email") || "anonymous@trendrop.app";

  // Brand Deals states
  const [deals, setDeals] = useState<BrandDeal[]>([]);
  const [stats, setStats] = useState<BrandDealStats>({
    total_earnings: 42500,
    active_partnerships: 1,
    pending_applications: 0
  });
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [selectedDeal, setSelectedDeal] = useState<BrandDeal | null>(null);
  const [pitchText, setPitchText] = useState("");
  const [submittingApplication, setSubmittingApplication] = useState(false);

  // Collab Matches states
  const [matches, setMatches] = useState<CollabMatch[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [hasSearchedMatches, setHasSearchedMatches] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<CollabMatch | null>(null);
  const [requestMessage, setRequestMessage] = useState("");
  const [sendingRequest, setSendingRequest] = useState(false);

  // Auto-filled Creator Profile state
  const [profile, setProfile] = useState<CreatorProfile>({
    instagram_username: "trendrop.creator",
    niche: "lifestyle",
    followers: 18500,
    engagement_rate: 5.2,
    price_per_post: 15000
  });

  useEffect(() => {
    loadBrandDeals();
    loadCreatorProfile();
  }, []);

  const loadBrandDeals = async () => {
    setLoadingDeals(true);
    try {
      const data = await fetchBrandDeals(email);
      setDeals(data.deals);
      setStats(data.stats);
    } catch (err) {
      console.error("Failed to load brand deals", err);
      toast.error("Failed to load brand deals from server. Using offline data.");
    } finally {
      setLoadingDeals(false);
    }
  };

  const loadCreatorProfile = async () => {
    try {
      const res = await apiFetch("/api/marketplace/profiles");
      if (res.ok) {
        const data = await res.json();
        const mine = data.find((p: any) => p.user_email === email);
        if (mine) {
          setProfile({
            instagram_username: mine.instagram_username,
            niche: mine.niche,
            followers: mine.followers,
            engagement_rate: mine.engagement_rate,
            price_per_post: mine.price_per_post
          });
        } else {
          // Fallback to local storage if profile was edited there
          const cachedMine = localStorage.getItem("trendrop_marketplace_mine");
          if (cachedMine) {
            const parsed = JSON.parse(cachedMine);
            setProfile({
              instagram_username: parsed.instagram_username || "trendrop.creator",
              niche: parsed.niche || "lifestyle",
              followers: parsed.followers || 18500,
              engagement_rate: parsed.engagement_rate || 5.2,
              price_per_post: parsed.price_per_post || 15000
            });
          }
        }
      }
    } catch (err) {
      console.error("Failed to load profile", err);
    }
  };

  const handleApplyClick = (deal: BrandDeal) => {
    setSelectedDeal(deal);
    setPitchText(
      `Hey ${deal.brand_name}! I love your brand and would be thrilled to collaborate. I plan to create a highly engaging transition Reel highlight-reel with a custom hook optimized for my ${profile.niche} audience of ${profile.followers.toLocaleString()} followers.`
    );
  };

  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeal) return;
    if (!pitchText.trim()) {
      toast.error("Please write a pitch to submit your application.");
      return;
    }

    setSubmittingApplication(true);
    try {
      const res = await applyToBrandDeal(selectedDeal.id, email, pitchText);
      if (res.success) {
        toast.success(`Application submitted to ${selectedDeal.brand_name}!`);
        setSelectedDeal(null);
        setPitchText("");
        // Reload deals to update stats & applied state
        loadBrandDeals();
      } else {
        throw new Error(res.message);
      }
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to submit application. Please try again.");
    } finally {
      setSubmittingApplication(false);
    }
  };

  const handleFindMatches = async () => {
    setLoadingMatches(true);
    setHasSearchedMatches(true);
    try {
      const data = await fetchCollabMatches(email);
      setMatches(data);
    } catch (err) {
      console.error("Failed to find matches", err);
      toast.error("Error finding collab matches. Please check your connection.");
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleSendRequestClick = (match: CollabMatch) => {
    setSelectedMatch(match);
    setRequestMessage(
      `Hey @${match.instagram_username}, I saw we have a ${match.compatibility_score}% compatibility score on Trendrop! I love your content in ${match.niche}. Let's collaborate on a short transition/hook Reel. What do you think?`
    );
  };

  const handleSubmitCollabRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMatch) return;
    if (!requestMessage.trim()) {
      toast.error("Please enter a message to send.");
      return;
    }

    setSendingRequest(true);
    try {
      const res = await sendCollabRequest(email, selectedMatch.user_email, requestMessage);
      if (res.success) {
        toast.success(`Collab request sent to @${selectedMatch.instagram_username}!`);
        setSelectedMatch(null);
        setRequestMessage("");
        // Reload matches to update request_sent state
        if (hasSearchedMatches) {
          const updated = matches.map(m => 
            m.user_email === selectedMatch.user_email ? { ...m, request_sent: true } : m
          );
          setMatches(updated);
        }
      } else {
        throw new Error(res.message);
      }
    } catch (err: any) {
      console.error(err);
      toast.error(err.message || "Failed to send collaboration request.");
    } finally {
      setSendingRequest(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6 max-w-lg mx-auto min-h-screen text-text">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 text-white text-xl font-bold shadow-lg shadow-pink-500/20">
          <Building2 className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold bg-clip-text bg-gradient-to-r from-text via-text/90 to-pink-500 text-transparent">Creator Marketplace</h1>
          <p className="text-xs text-muted-foreground">Monetize content & find co-creators in India</p>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="flex gap-1.5 rounded-xl bg-surface-2 border border-border p-1.5 backdrop-blur-md">
        <button
          onClick={() => setActiveTab("deals")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wider transition-all ${
            activeTab === "deals" 
              ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-600/10" 
              : "text-text-muted hover:text-text"
          }`}
        >
          <Briefcase className="h-3.5 w-3.5" />
          Brand Deals
        </button>
        <button
          onClick={() => setActiveTab("collabs")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wider transition-all ${
            activeTab === "collabs" 
              ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-600/10" 
              : "text-text-muted hover:text-text"
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          Find Collabs
        </button>
      </div>

      {/* BRAND DEALS TAB */}
      {activeTab === "deals" && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-2xl border border-border bg-surface-2 flex flex-col justify-between">
              <span className="text-[9px] uppercase tracking-wider text-text-muted font-bold block mb-1">Total Earnings</span>
              <div>
                <span className="text-base font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">
                  ₹{stats.total_earnings.toLocaleString("en-IN")}
                </span>
                <span className="text-[8px] block text-muted-foreground mt-0.5">Creator Payout</span>
              </div>
            </div>
            <div className="p-3 rounded-2xl border border-border bg-surface-2 flex flex-col justify-between">
              <span className="text-[9px] uppercase tracking-wider text-text-muted font-bold block mb-1">Active Deals</span>
              <div>
                <span className="text-base font-extrabold text-indigo-400">{stats.active_partnerships}</span>
                <span className="text-[8px] block text-muted-foreground mt-0.5">In Progress</span>
              </div>
            </div>
            <div className="p-3 rounded-2xl border border-border bg-surface-2 flex flex-col justify-between">
              <span className="text-[9px] uppercase tracking-wider text-text-muted font-bold block mb-1">Applications</span>
              <div>
                <span className="text-base font-extrabold text-pink-400">{stats.pending_applications}</span>
                <span className="text-[8px] block text-muted-foreground mt-0.5">Pending Review</span>
              </div>
            </div>
          </div>

          {/* Deal Cards List */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Compass className="h-3.5 w-3.5 text-indigo-400" />
              Available Campaigns
            </h3>

            {loadingDeals ? (
              <div className="flex flex-col items-center justify-center py-12 text-text-muted">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
                <p className="text-xs">Fetching active brand opportunities...</p>
              </div>
            ) : deals.length === 0 ? (
              <div className="p-8 text-center rounded-2xl border border-border bg-surface-2 space-y-2">
                <AlertCircle className="h-8 w-8 text-indigo-400 mx-auto" />
                <p className="text-sm font-bold">No active brand deals</p>
                <p className="text-xs text-muted-foreground">Check back later for new campaign opportunities.</p>
              </div>
            ) : (
              deals.map((deal) => (
                <div 
                  key={deal.id} 
                  className="p-5 rounded-2xl border border-border hover:border-indigo-500/30 transition-all duration-300 bg-surface-2 relative overflow-hidden group space-y-4"
                >
                  {/* Decorative background glow */}
                  <div className="absolute top-0 right-0 h-24 w-24 bg-gradient-to-br from-indigo-500/5 to-pink-500/5 rounded-full blur-2xl group-hover:scale-125 transition-all duration-500 pointer-events-none" />

                  {/* Brand & Budget Header */}
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-display font-extrabold text-lg text-text group-hover:text-indigo-500 dark:group-hover:text-indigo-300 transition-colors">{deal.brand_name}</h4>
                      <span className="text-[9px] bg-surface text-text-muted font-bold px-2 py-0.5 rounded-full border border-border capitalize mt-1 inline-block">
                        Campaign
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 block font-bold">Budget</span>
                      <span className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-indigo-400">
                        ₹{deal.deal_amount.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>

                  {/* Campaign details */}
                  <div className="space-y-3">
                    <div className="bg-surface p-3 rounded-xl border border-border">
                      <h5 className="text-[9px] uppercase tracking-wider text-indigo-400 font-bold mb-1">Deliverables & Details</h5>
                      <p className="text-xs text-text leading-relaxed font-medium">"{deal.details}"</p>
                    </div>

                    <div className="bg-surface p-3 rounded-xl border border-border">
                      <h5 className="text-[9px] uppercase tracking-wider text-pink-400 font-bold mb-1">Requirements</h5>
                      <p className="text-xs text-text-muted leading-relaxed italic">{deal.requirements}</p>
                    </div>
                  </div>

                  {/* Apply Button */}
                  <div className="pt-2">
                    {deal.applied ? (
                      <div className="w-full flex items-center justify-center gap-1.5 rounded-xl border border-border bg-surface text-emerald-600 dark:text-emerald-400 text-xs font-bold py-2.5">
                        <CheckCircle className="h-4 w-4" />
                        Application Submitted
                      </div>
                    ) : (
                      <Button 
                        onClick={() => handleApplyClick(deal)}
                        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold h-10 rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-indigo-600/20"
                      >
                        Apply for Campaign
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* FIND COLLABS TAB */}
      {activeTab === "collabs" && (
        <div className="space-y-6">
          {/* Intro Card */}
          <div className="p-6 rounded-3xl border border-indigo-500/20 relative overflow-hidden bg-surface-2">
            <div className="absolute -top-12 -right-12 h-32 w-32 bg-indigo-500/10 rounded-full blur-3xl" />
            
            <div className="space-y-4 relative">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Sparkles className="h-5 w-5" />
              </div>
              
              <div className="space-y-1">
                <h3 className="text-lg font-bold font-display text-text">Find Creator Collaborations</h3>
                <p className="text-xs text-text-muted leading-relaxed">
                  Connect with local creators to co-create Reels and double your search reach. We match profiles based on content niche overlap, followers ratio, and visual styling harmony.
                </p>
              </div>

              <Button
                onClick={handleFindMatches}
                disabled={loadingMatches}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold h-10 px-5 rounded-xl flex items-center gap-1.5 transition-all duration-300 hover:shadow-md hover:shadow-indigo-600/30"
              >
                {loadingMatches ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Finding Matches...
                  </>
                ) : (
                  <>
                    Find Matches
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Collab Matches List */}
          {hasSearchedMatches && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-indigo-400" />
                Your Compatibility Matches
              </h3>

              {loadingMatches ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                  <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-2" />
                  <p className="text-xs">Finding aligned creator profiles...</p>
                </div>
              ) : matches.length === 0 ? (
                <div className="glass-card p-8 text-center rounded-2xl border border-slate-800">
                  <p className="text-xs text-muted-foreground">No creator matches found. Try updating your niche profile.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {matches.map((match, idx) => (
                    <div 
                      key={idx} 
                      className="p-5 rounded-2xl border border-border hover:border-indigo-500/30 transition-all duration-300 bg-surface-2 space-y-4 relative"
                    >
                      {/* Top Info Header */}
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-display font-extrabold text-base text-text">@{match.instagram_username}</h4>
                          <span className="text-[10px] bg-indigo-500/10 text-indigo-300 font-bold px-2.5 py-0.5 rounded-full border border-indigo-500/20 capitalize mt-1 inline-block">
                            {match.niche}
                          </span>
                        </div>

                        {/* Compatibility Score Circle/Pill */}
                        <div className="bg-surface border border-border px-3 py-1.5 rounded-xl text-center">
                          <span className="text-[8px] uppercase tracking-wider text-text-muted font-black block">Score</span>
                          <span className="text-sm font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-indigo-400">
                            {match.compatibility_score}% Match
                          </span>
                        </div>
                      </div>

                      {/* Creator Stats */}
                      <div className="grid grid-cols-3 gap-2 py-3 border-y border-border text-center bg-surface rounded-lg">
                        <div>
                          <span className="block text-[9px] text-text-muted uppercase font-semibold">Followers</span>
                          <span className="font-extrabold text-sm text-text">
                            {match.followers >= 1000 ? `${(match.followers / 1000).toFixed(0)}K` : match.followers}
                          </span>
                        </div>
                        <div>
                          <span className="block text-[9px] text-text-muted uppercase font-semibold">Engagement</span>
                          <span className="font-extrabold text-sm text-text">{match.engagement_rate}%</span>
                        </div>
                        <div>
                          <span className="block text-[9px] text-text-muted uppercase font-semibold">Trend Score</span>
                          <span className="font-extrabold text-sm text-pink-400">{match.trend_score}/100</span>
                        </div>
                      </div>

                      {/* Request Button */}
                      <div>
                        {match.request_sent ? (
                          <div className="w-full flex items-center justify-center gap-1.5 rounded-xl border border-border bg-surface text-indigo-600 dark:text-indigo-400 text-xs font-bold py-2.5">
                            <CheckCircle className="h-4 w-4" />
                            Request Sent
                          </div>
                        ) : (
                          <Button
                            onClick={() => handleSendRequestClick(match)}
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold h-10 border border-indigo-500/20 rounded-xl transition-all duration-300"
                          >
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
        </div>
      )}

      {/* APPLICATION MODAL (BRAND DEALS) */}
      {selectedDeal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md p-6 rounded-3xl border border-border bg-surface shadow-2xl relative space-y-5">
            
            {/* Header */}
            <div>
              <span className="text-[9px] uppercase tracking-wider font-extrabold text-indigo-400">Submit Application</span>
              <h3 className="font-display font-extrabold text-xl text-text mt-0.5">{selectedDeal.brand_name}</h3>
              <p className="text-xs text-text-muted mt-1">Applying for campaign value of ₹{selectedDeal.deal_amount.toLocaleString("en-IN")}</p>
            </div>

            {/* Auto-filled Creator Profile Section */}
            <div className="bg-surface-2 p-4 rounded-2xl border border-border space-y-3">
              <h4 className="text-[9px] uppercase tracking-wider text-text-muted font-bold flex items-center gap-1.5">
                <Award className="h-3.5 w-3.5 text-indigo-400" />
                Verified Creator Profile
              </h4>
              
              <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
                <div>
                  <span className="text-text-muted block text-[9px] uppercase">Instagram handle</span>
                  <span className="font-bold text-text">@{profile.instagram_username}</span>
                </div>
                <div>
                  <span className="text-text-muted block text-[9px] uppercase">Niche category</span>
                  <span className="font-bold text-text capitalize">{profile.niche}</span>
                </div>
                <div>
                  <span className="text-text-muted block text-[9px] uppercase">Verified followers</span>
                  <span className="font-bold text-text">{profile.followers.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-text-muted block text-[9px] uppercase">Pricing rate</span>
                  <span className="font-bold text-indigo-600 dark:text-indigo-300">₹{profile.price_per_post.toLocaleString("en-IN")}</span>
                </div>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmitApplication} className="space-y-4">
              <div>
                <label className="text-[10px] uppercase font-bold text-text-muted block mb-1.5">Your Campaign Pitch</label>
                <textarea
                  rows={4}
                  value={pitchText}
                  onChange={(e) => setPitchText(e.target.value)}
                  placeholder="Explain why you're a great fit for this brand deal..."
                  className="w-full rounded-xl bg-surface border border-border text-text px-3.5 py-3 text-xs placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none font-medium"
                />
              </div>

              <div className="flex gap-2.5">
                <Button 
                  type="button"
                  onClick={() => setSelectedDeal(null)}
                  className="flex-1 bg-surface-2 border border-border hover:bg-surface-2/80 text-text font-bold h-11 rounded-xl"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit"
                  disabled={submittingApplication}
                  className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold h-11 rounded-xl shadow-lg shadow-indigo-600/20"
                >
                  {submittingApplication ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                      Submitting...
                    </>
                  ) : (
                    "Submit App"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REQUEST MODAL (COLLABS) */}
      {selectedMatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md p-6 rounded-3xl border border-border bg-surface shadow-2xl relative space-y-5">
            
            {/* Header */}
            <div>
              <span className="text-[9px] uppercase tracking-wider font-extrabold text-indigo-400">Collaboration Request</span>
              <h3 className="font-display font-extrabold text-xl text-text mt-0.5">Connect with @{selectedMatch.instagram_username}</h3>
              <p className="text-xs text-text-muted mt-1">compatibility score: {selectedMatch.compatibility_score}% ({selectedMatch.niche} niche)</p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmitCollabRequest} className="space-y-4">
              <div>
                <label className="text-[10px] uppercase font-bold text-text-muted block mb-1.5">Collaboration Proposal Message</label>
                <textarea
                  rows={4}
                  value={requestMessage}
                  onChange={(e) => setRequestMessage(e.target.value)}
                  placeholder="Introduce yourself and propose a collab idea..."
                  className="w-full rounded-xl bg-surface border border-border text-text px-3.5 py-3 text-xs placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none font-medium"
                />
              </div>

              <div className="flex gap-2.5">
                <Button 
                  type="button"
                  onClick={() => setSelectedMatch(null)}
                  className="flex-1 bg-surface-2 border border-border hover:bg-surface-2/80 text-text font-bold h-11 rounded-xl"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit"
                  disabled={sendingRequest}
                  className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold h-11 rounded-xl flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/20"
                >
                  {sendingRequest ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      Send Request
                      <Send className="h-3.5 w-3.5" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
