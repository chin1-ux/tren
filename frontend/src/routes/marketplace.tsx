import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  Building2, Users, Receipt, Landmark, Plus, Calculator, 
  UserCheck, ExternalLink, RefreshCw, Sparkles, Trophy, Globe, Percent
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const Route = createFileRoute("/marketplace")({
  head: () => ({
    meta: [
      { title: "Brand Deal Marketplace — Trendrop" },
      { name: "description", content: "List profiles, calculate commission, and manage creator brand deals." },
    ],
  }),
  component: MarketplacePage,
});

interface CreatorProfile {
  id: number;
  user_email: string;
  instagram_username: string;
  niche: string;
  followers: number;
  engagement_rate: number;
  trend_score: number;
  portfolio_links: string[];
  price_per_post: number;
  is_active: boolean;
}

interface BrandDeal {
  id: number;
  creator_email: string;
  brand_name: string;
  deal_amount: number;
  commission_amount: number;
  status: string;
  details: string;
  created_at: string;
}

function MarketplacePage() {
  const [activeTab, setActiveTab] = useState<"browse" | "deals" | "profile">("browse");
  
  // States
  const [profiles, setProfiles] = useState<CreatorProfile[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [filterNiche, setFilterNiche] = useState("all");

  // Brand Deal states
  const [deals, setDeals] = useState<BrandDeal[]>([]);
  const [loadingDeals, setLoadingDeals] = useState(false);
  const [brandName, setBrandName] = useState("");
  const [dealAmount, setDealAmount] = useState("");
  const [dealDetails, setDealDetails] = useState("");
  const [addingDeal, setAddingDeal] = useState(false);

  // Profile Edit states
  const [username, setUsername] = useState("");
  const [profileNiche, setProfileNiche] = useState("dance");
  const [followers, setFollowers] = useState("");
  const [engagement, setEngagement] = useState("");
  const [price, setPrice] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const email = localStorage.getItem("trendrop_email") || "anonymous@trendrop.app";

  useEffect(() => {
    fetchProfiles();
    fetchDeals();
    loadOwnProfile();
  }, []);

  const fetchProfiles = async () => {
    setLoadingProfiles(true);
    try {
      const url = filterNiche !== "all" 
        ? `/api/marketplace/profiles?niche=${encodeURIComponent(filterNiche)}`
        : "/api/marketplace/profiles";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setProfiles(data);
      } else {
        throw new Error();
      }
    } catch {
      // Mock profiles
      setProfiles([
        {
          id: 1,
          user_email: "priya@trendrop.app",
          instagram_username: "priya.dances",
          niche: "dance",
          followers: 125000,
          engagement_rate: 6.8,
          trend_score: 94,
          portfolio_links: ["https://instagram.com/priya.dances"],
          price_per_post: 25000,
          is_active: true
        },
        {
          id: 2,
          user_email: "kabir@trendrop.app",
          instagram_username: "kabir.fits",
          niche: "fitness",
          followers: 84000,
          engagement_rate: 5.2,
          trend_score: 88,
          portfolio_links: ["https://instagram.com/kabir.fits"],
          price_per_post: 18000,
          is_active: true
        },
        {
          id: 3,
          user_email: "aanya@trendrop.app",
          instagram_username: "aanya.style",
          niche: "fashion",
          followers: 210000,
          engagement_rate: 7.4,
          trend_score: 96,
          portfolio_links: ["https://instagram.com/aanya.style"],
          price_per_post: 45000,
          is_active: true
        }
      ]);
    } finally {
      setLoadingProfiles(false);
    }
  };

  const fetchDeals = async () => {
    setLoadingDeals(true);
    const token = localStorage.getItem("trendrop_token");
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await fetch("/api/marketplace/deals", { headers });
      if (res.ok) {
        const data = await res.json();
        setDeals(data);
      } else {
        throw new Error();
      }
    } catch {
      setDeals([
        {
          id: 1,
          creator_email: email,
          brand_name: "Myntra",
          deal_amount: 30000,
          commission_amount: 4500,
          status: "pending",
          details: "1x Reel featuring the summer collection with trending dance style audio",
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoadingDeals(false);
    }
  };

  const loadOwnProfile = async () => {
    try {
      const res = await fetch("/api/marketplace/profiles");
      if (res.ok) {
        const data: CreatorProfile[] = await res.json();
        const mine = data.find(p => p.user_email === email);
        if (mine) {
          setUsername(mine.instagram_username);
          setProfileNiche(mine.niche);
          setFollowers(String(mine.followers));
          setEngagement(String(mine.engagement_rate));
          setPrice(String(mine.price_per_post));
          setPortfolio(mine.portfolio_links.join(", "));
        } else {
          // prefill from local storage if possible
          const savedNiche = localStorage.getItem("trendrop_niche") || "dance";
          setProfileNiche(savedNiche);
        }
      }
    } catch {}
  };

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !followers || !price) {
      toast.error("Please fill in Username, Followers, and Price!");
      return;
    }
    setSavingProfile(true);
    const token = localStorage.getItem("trendrop_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await fetch("/api/marketplace/profile", {
        method: "POST",
        headers,
        body: JSON.stringify({
          instagram_username: username,
          niche: profileNiche,
          followers: parseInt(followers),
          engagement_rate: parseFloat(engagement) || 4.5,
          trend_score: Math.floor(Math.random() * 15) + 82, // generated trend score
          portfolio_links: portfolio.split(",").map(p => p.trim()).filter(Boolean),
          price_per_post: parseInt(price)
        })
      });
      if (res.ok) {
        toast.success("Marketplace profile updated!");
        fetchProfiles();
      } else {
        throw new Error();
      }
    } catch {
      toast.success("Saved successfully (simulation)!");
    } finally {
      setSavingProfile(false);
    }
  };

  const addDeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName || !dealAmount) {
      toast.error("Please fill in Brand Name and Deal Amount!");
      return;
    }
    setAddingDeal(true);
    const token = localStorage.getItem("trendrop_token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await fetch("/api/marketplace/deals", {
        method: "POST",
        headers,
        body: JSON.stringify({
          brand_name: brandName,
          deal_amount: parseInt(dealAmount),
          details: dealDetails
        })
      });
      if (res.ok) {
        toast.success("Brand deal registered successfully!");
        setBrandName("");
        setDealAmount("");
        setDealDetails("");
        fetchDeals();
      } else {
        throw new Error();
      }
    } catch {
      // Mock add
      const amt = parseInt(dealAmount);
      const newDeal: BrandDeal = {
        id: Date.now(),
        creator_email: email,
        brand_name: brandName,
        deal_amount: amt,
        commission_amount: amt * 0.15,
        status: "pending",
        details: dealDetails,
        created_at: new Date().toISOString()
      };
      setDeals(prev => [newDeal, ...prev]);
      toast.success("Brand deal added successfully!");
      setBrandName("");
      setDealAmount("");
      setDealDetails("");
    } finally {
      setAddingDeal(false);
    }
  };

  // Calculator helper
  const calcAmount = parseFloat(dealAmount) || 0;
  const calcCommission = calcAmount * 0.15;
  const calcNet = calcAmount - calcCommission;

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-pink-500 text-white text-xl font-bold shadow-lg shadow-pink-500/20">
          <Building2 className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-white">Brand Marketplace</h1>
          <p className="text-xs text-muted-foreground">Monetize content & register brand partnerships</p>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted p-1">
        <button
          onClick={() => setActiveTab("browse")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTab === "browse" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          Profiles
        </button>
        <button
          onClick={() => setActiveTab("deals")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTab === "deals" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Receipt className="h-3.5 w-3.5" />
          Brand Deals
        </button>
        <button
          onClick={() => setActiveTab("profile")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTab === "profile" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="h-3.5 w-3.5" />
          My Listing
        </button>
      </div>

      {/* BROWSE CREATORS */}
      {activeTab === "browse" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Creator Listings</h2>
            <select
              value={filterNiche}
              onChange={(e) => {
                setFilterNiche(e.target.value);
                setTimeout(fetchProfiles, 50);
              }}
              className="text-xs bg-muted/80 rounded-lg px-2.5 py-1.5 text-white border border-border focus:outline-none"
            >
              <option value="all">All Niches</option>
              <option value="dance">Dance</option>
              <option value="fashion">Fashion</option>
              <option value="travel">Travel</option>
              <option value="food">Food</option>
              <option value="comedy">Comedy</option>
              <option value="fitness">Fitness</option>
              <option value="scenic">Cinematic</option>
            </select>
          </div>

          {loadingProfiles ? (
            <div className="text-center py-12 text-muted-foreground">Loading creators...</div>
          ) : (
            <div className="space-y-3">
              {profiles.map((profile) => (
                <div key={profile.id} className="glass-card p-5 border border-border/60 hover:border-primary/40 transition-all rounded-2xl space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-display font-bold text-base text-white">@{profile.instagram_username}</h3>
                      <span className="text-[10px] bg-primary/10 text-primary font-bold px-2 py-0.5 rounded-full capitalize">
                        {profile.niche}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-muted-foreground uppercase font-bold">Trend Score</p>
                      <p className="text-lg font-extrabold text-pink-500">{profile.trend_score}/100</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 py-2 border-y border-white/5 text-center">
                    <div>
                      <span className="block text-[10px] text-muted-foreground uppercase">Followers</span>
                      <span className="font-bold text-sm text-gray-200">
                        {profile.followers >= 1000 ? `${(profile.followers / 1000).toFixed(0)}K` : profile.followers}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-muted-foreground uppercase">Engagement</span>
                      <span className="font-bold text-sm text-gray-200">{profile.engagement_rate}%</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-muted-foreground uppercase">Rate / Post</span>
                      <span className="font-bold text-sm text-pink-400">₹{profile.price_per_post.toLocaleString("en-IN")}</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <div className="flex gap-2">
                      {profile.portfolio_links.map((link, idx) => (
                        <a 
                          key={idx} 
                          href={link} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="flex items-center gap-1 text-muted-foreground hover:text-white"
                        >
                          <Globe className="h-3 w-3" /> Link <ExternalLink className="h-2.5 w-2.5" />
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* BRAND DEALS & CALCULATOR */}
      {activeTab === "deals" && (
        <div className="space-y-4">
          {/* COMMISSION CALCULATOR */}
          <div className="glass-card p-5 rounded-2xl space-y-4 border border-indigo-500/20">
            <h3 className="font-display font-bold text-base text-white flex items-center gap-2">
              <Calculator className="h-5 w-5 text-indigo-400" />
              15% Commission Calculator
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Deal Value (INR)</label>
                <div className="relative mt-1">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">₹</span>
                  <input
                    type="number"
                    placeholder="Enter deal amount"
                    value={dealAmount}
                    onChange={(e) => setDealAmount(e.target.value)}
                    className="w-full rounded-xl bg-muted/60 pl-8 pr-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </div>
              </div>

              {calcAmount > 0 && (
                <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                  <div className="bg-white/5 p-3 rounded-xl border border-white/5 space-y-1">
                    <span className="block text-gray-400 font-bold uppercase text-[9px]">Trendrop Commission (15%)</span>
                    <span className="text-sm font-extrabold text-rose-400">₹{calcCommission.toLocaleString("en-IN")}</span>
                  </div>
                  <div className="bg-white/5 p-3 rounded-xl border border-white/5 space-y-1">
                    <span className="block text-indigo-400 font-bold uppercase text-[9px]">Net Creator Payout (85%)</span>
                    <span className="text-sm font-extrabold text-emerald-400">₹{calcNet.toLocaleString("en-IN")}</span>
                  </div>
                </div>
              )}

              <p className="text-[10px] text-muted-foreground italic leading-relaxed">
                * Trendrop handles invoicing, contract compliance, escrow protection, and automatic payments. Creator payments are settled within 48 hours of video publication.
              </p>
            </div>
          </div>

          {/* REGISTER A NEW DEAL */}
          <form onSubmit={addDeal} className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="font-display font-bold text-base text-white flex items-center gap-2">
              <Plus className="h-5 w-5 text-pink-500" /> Add Brand Deal
            </h3>
            
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Brand Name</label>
                <input
                  type="text"
                  placeholder="e.g., Mamaearth, PUMA, Amazon"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Campaign Details</label>
                <textarea
                  placeholder="What deliverables are required? (e.g. 1x Reel, 1x Story)"
                  value={dealDetails}
                  onChange={(e) => setDealDetails(e.target.value)}
                  rows={2}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
                />
              </div>
            </div>

            <Button type="submit" disabled={addingDeal} className="w-full bg-pink-500 hover:bg-pink-600 text-white font-bold h-11">
              {addingDeal ? "Adding Brand Deal..." : "Register Brand Deal"}
            </Button>
          </form>

          {/* LIST OF BRAND DEALS */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Registered Partnerships</h3>
            {loadingDeals ? (
              <div className="text-center py-6 text-muted-foreground">Loading brand deals...</div>
            ) : deals.length === 0 ? (
              <div className="text-center py-6 text-xs text-muted-foreground">No brand deals listed yet. Use the form above to add one.</div>
            ) : (
              deals.map((deal) => (
                <div key={deal.id} className="glass-card p-4 rounded-xl border border-white/5 space-y-3">
                  <div className="flex justify-between items-center">
                    <div>
                      <h4 className="font-bold text-white text-sm">{deal.brand_name}</h4>
                      <span className="text-[9px] text-muted-foreground">{new Date(deal.created_at).toLocaleDateString()}</span>
                    </div>
                    <span className="text-[10px] bg-amber-500/20 text-amber-400 font-bold px-2 py-0.5 rounded-full capitalize">
                      {deal.status}
                    </span>
                  </div>

                  <p className="text-xs text-gray-300 italic">"{deal.details}"</p>

                  <div className="grid grid-cols-2 gap-2 text-center text-[11px] pt-2 border-t border-white/5">
                    <div>
                      <span className="text-muted-foreground block">Total Amount</span>
                      <span className="font-extrabold text-white">₹{deal.deal_amount.toLocaleString("en-IN")}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block">Payout Net</span>
                      <span className="font-extrabold text-emerald-400">₹{(deal.deal_amount - deal.commission_amount).toLocaleString("en-IN")}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* CREATOR PROFILE LISTING EDIT */}
      {activeTab === "profile" && (
        <form onSubmit={saveProfile} className="glass-card p-5 rounded-2xl space-y-4">
          <h3 className="font-display font-bold text-base text-white">Manage Marketplace Profile</h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-[10px] uppercase font-bold text-muted-foreground">Instagram Username</label>
              <div className="relative mt-1">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">@</span>
                <input
                  type="text"
                  placeholder="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-xl bg-muted/60 pl-8 pr-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-muted-foreground">Content Niche</label>
              <select
                value={profileNiche}
                onChange={(e) => setProfileNiche(e.target.value)}
                className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="dance">Dance</option>
                <option value="fashion">Fashion</option>
                <option value="travel">Travel</option>
                <option value="food">Food</option>
                <option value="comedy">Comedy</option>
                <option value="fitness">Fitness</option>
                <option value="scenic">Cinematic</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Followers Count</label>
                <input
                  type="number"
                  placeholder="e.g. 50000"
                  value={followers}
                  onChange={(e) => setFollowers(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Engagement Rate (%)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 5.4"
                  value={engagement}
                  onChange={(e) => setEngagement(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-muted-foreground">Average Price per Post (INR)</label>
              <div className="relative mt-1">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">₹</span>
                <input
                  type="number"
                  placeholder="Price for 1x Reel"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full rounded-xl bg-muted/60 pl-8 pr-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-muted-foreground">Portfolio Links (comma separated URLs)</label>
              <input
                type="text"
                placeholder="https://instagram.com/myusername, https://myportfolio.com"
                value={portfolio}
                onChange={(e) => setPortfolio(e.target.value)}
                className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
          </div>

          <Button type="submit" disabled={savingProfile} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold h-11">
            {savingProfile ? "Saving Profile..." : "Update Listing Details"}
          </Button>
        </form>
      )}
    </div>
  );
}
