import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  ArrowLeft, 
  Handshake, 
  Sparkles, 
  Calendar, 
  DollarSign, 
  Briefcase,
  Layers,
  Settings,
  FileCheck,
  CheckCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch, logAnalyticsEvent } from "@/lib/api";
import { motion } from "framer-motion";

export const Route = createFileRoute("/deals/new")({
  head: () => ({
    meta: [
      { title: "Generate Brand Deal Contract — Trendrop" },
      { name: "description", content: "Create a new brand collaboration deal, specify deliverables, set milestones, and generate a downloadable contract PDF." },
    ],
  }),
  component: CreateDealPage,
});

function CreateDealPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  // Form Fields
  const [brandName, setBrandName] = useState("");
  const [rateAmount, setRateAmount] = useState("");
  const [currency, setCurrency] = useState("INR");
  
  // Deliverables Checkboxes & Counts
  const [hasReel, setHasReel] = useState(true);
  const [reelCount, setReelCount] = useState("1");
  const [hasStory, setHasStory] = useState(false);
  const [storyCount, setStoryCount] = useState("1");
  const [hasGridPost, setHasGridPost] = useState(false);
  const [gridPostCount, setGridPostCount] = useState("1");
  const [customDeliverables, setCustomDeliverables] = useState("");

  // Contract Scope Details
  const [usageRights, setUsageRights] = useState("3 Months on Creator Socials");
  const [exclusivityClause, setExclusivityClause] = useState("30 Days after post (Direct Competitors)");
  const [timelineStart, setTimelineStart] = useState("");
  const [timeline_end, setTimelineEnd] = useState("");
  const [coverNoteType, setCoverNoteType] = useState("english");

  // Payment Term Preset Selection
  const [paymentPreset, setPaymentPreset] = useState("50_50"); // "50_50", "100_advance", "100_delivery"
  
  // Milestone inputs (calculated or manual)
  const [advanceAmount, setAdvanceAmount] = useState("");
  const [advanceDueDate, setAdvanceDueDate] = useState("");
  const [finalAmount, setFinalAmount] = useState("");
  const [finalDueDate, setFinalDueDate] = useState("");

  // Initialize dates
  useEffect(() => {
    const today = new Date();
    const todayStr = today.toISOString().split("T")[0];
    
    const nextMonth = new Date();
    nextMonth.setDate(today.getDate() + 30);
    const nextMonthStr = nextMonth.toISOString().split("T")[0];
    
    setTimelineStart(todayStr);
    setTimelineEnd(nextMonthStr);
    setAdvanceDueDate(todayStr);
    setFinalDueDate(nextMonthStr);
  }, []);

  // Update milestone amounts when rate changes or preset changes
  useEffect(() => {
    const rate = parseFloat(rateAmount) || 0;
    if (paymentPreset === "50_50") {
      setAdvanceAmount((rate * 0.5).toString());
      setFinalAmount((rate * 0.5).toString());
    } else if (paymentPreset === "100_advance") {
      setAdvanceAmount(rate.toString());
      setFinalAmount("0");
    } else if (paymentPreset === "100_delivery") {
      setAdvanceAmount("0");
      setFinalAmount(rate.toString());
    }
  }, [rateAmount, paymentPreset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) {
      toast.error("Please enter a brand name");
      return;
    }
    const parsedRate = parseFloat(rateAmount);
    if (isNaN(parsedRate) || parsedRate <= 0) {
      toast.error("Please enter a valid rate amount");
      return;
    }

    setSubmitting(true);

    try {
      // 1. Build Deliverables Description string
      const delivParts = [];
      if (hasReel) delivParts.push(`${reelCount}x Instagram Reel(s)`);
      if (hasStory) delivParts.push(`${storyCount}x Instagram Story(ies)`);
      if (hasGridPost) delivParts.push(`${gridPostCount}x Instagram Grid Post(s)`);
      
      let finalDeliverablesText = delivParts.join(", ");
      if (customDeliverables.trim()) {
        finalDeliverablesText += `\nAdditional Details: ${customDeliverables.trim()}`;
      }

      if (!finalDeliverablesText.trim()) {
        toast.error("Please select or type at least one deliverable");
        setSubmitting(false);
        return;
      }

      // 2. Build Milestones List
      const milestones = [];
      const advVal = parseFloat(advanceAmount) || 0;
      if (advVal > 0) {
        milestones.push({
          milestone_name: "Advance Deposit (Pre-filming)",
          amount: advVal,
          due_date: new Date(advanceDueDate).toISOString()
        });
      }

      const finVal = parseFloat(finalAmount) || 0;
      if (finVal > 0) {
        milestones.push({
          milestone_name: "Final Payment (Upon content approval/post)",
          amount: finVal,
          due_date: new Date(finalDueDate).toISOString()
        });
      }

      if (milestones.length === 0) {
        toast.error("Please specify at least one payment milestone");
        setSubmitting(false);
        return;
      }

      // 3. Make POST request to backend API
      const requestData = {
        brand_name: brandName,
        deliverables: finalDeliverablesText,
        rate_amount: parsedRate,
        currency: currency,
        usage_rights: usageRights,
        exclusivity_clause: exclusivityClause,
        timeline_start: new Date(timelineStart).toISOString(),
        timeline_end: new Date(timeline_end).toISOString(),
        cover_note_type: coverNoteType,
        milestones
      };

      const res = await apiFetch("/api/deals", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestData)
      });

      if (res.ok) {
        const deal = await res.json();
        toast.success("Deal contract generated successfully!");
        logAnalyticsEvent("deal_created");
        logAnalyticsEvent("milestone_set");
        navigate({ to: "/deals" });
      } else {
        const err = await res.json();
        toast.error(`Error: ${err.detail || "Failed to generate contract"}`);
      }
    } catch (err) {
      console.error(err);
      toast.error("Network error submitting deal");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pt-6 pb-12 min-h-screen text-foreground">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button 
          onClick={() => navigate({ to: "/deals" })}
          className="p-1 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold tracking-tight font-display">
            Create Campaign Deal
          </h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Fill details to auto-generate contract PDF
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 text-sm">
        {/* Core Deal Details Card */}
        <div className="bg-card border border-border/80 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Briefcase className="h-4 w-4" />
            Core Deal Information
          </div>
          
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Brand Name</label>
            <input 
              type="text" 
              placeholder="e.g. Mamaearth, Nykaa, Spotify India"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Campaign Rate (INR)</label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-xs text-muted-foreground font-bold">₹</span>
                <input 
                  type="number" 
                  placeholder="50,000"
                  value={rateAmount}
                  onChange={(e) => setRateAmount(e.target.value)}
                  className="w-full bg-muted/40 border border-border/60 rounded-xl p-2.5 pl-7 text-xs focus:outline-none focus:border-primary/80 font-semibold"
                  required
                />
              </div>
            </div>
            
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Currency</label>
              <select 
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Deliverables Card */}
        <div className="bg-card border border-border/80 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Layers className="h-4 w-4" />
            Deliverables Scope
          </div>

          <div className="flex flex-col gap-3.5">
            {/* Reels Checkbox */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="hasReel" 
                  checked={hasReel}
                  onChange={(e) => setHasReel(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary h-4.5 w-4.5 accent-primary"
                />
                <label htmlFor="hasReel" className="font-semibold text-xs text-foreground cursor-pointer">Instagram Reel</label>
              </div>
              {hasReel && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">Qty:</span>
                  <input 
                    type="number" 
                    min="1" 
                    value={reelCount}
                    onChange={(e) => setReelCount(e.target.value)}
                    className="w-12 bg-muted/40 border border-border/60 rounded-lg p-1 text-center text-xs focus:outline-none"
                  />
                </div>
              )}
            </div>

            {/* Story Checkbox */}
            <div className="flex items-center justify-between border-t border-border/20 pt-3">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="hasStory" 
                  checked={hasStory}
                  onChange={(e) => setHasStory(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary h-4.5 w-4.5 accent-primary"
                />
                <label htmlFor="hasStory" className="font-semibold text-xs text-foreground cursor-pointer">Instagram Story</label>
              </div>
              {hasStory && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">Qty:</span>
                  <input 
                    type="number" 
                    min="1" 
                    value={storyCount}
                    onChange={(e) => setStoryCount(e.target.value)}
                    className="w-12 bg-muted/40 border border-border/60 rounded-lg p-1 text-center text-xs focus:outline-none"
                  />
                </div>
              )}
            </div>

            {/* Grid Post Checkbox */}
            <div className="flex items-center justify-between border-t border-border/20 pt-3">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="hasGridPost" 
                  checked={hasGridPost}
                  onChange={(e) => setHasGridPost(e.target.checked)}
                  className="rounded border-border text-primary focus:ring-primary h-4.5 w-4.5 accent-primary"
                />
                <label htmlFor="hasGridPost" className="font-semibold text-xs text-foreground cursor-pointer">Instagram Grid Post</label>
              </div>
              {hasGridPost && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">Qty:</span>
                  <input 
                    type="number" 
                    min="1" 
                    value={gridPostCount}
                    onChange={(e) => setGridPostCount(e.target.value)}
                    className="w-12 bg-muted/40 border border-border/60 rounded-lg p-1 text-center text-xs focus:outline-none"
                  />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1.5 border-t border-border/20 pt-3">
              <label className="text-xs font-semibold text-muted-foreground">Additional Deliverables / Details</label>
              <textarea 
                placeholder="Specify format parameters, links/hashtags guidelines, or other formats like YouTube Shorts, etc."
                value={customDeliverables}
                onChange={(e) => setCustomDeliverables(e.target.value)}
                rows={3}
                className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80 resize-none leading-relaxed"
              />
            </div>
          </div>
        </div>

        {/* Timelines & Terms Card */}
        <div className="bg-card border border-border/80 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Settings className="h-4 w-4" />
            Rights & Exclusivity Scope
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Usage Rights Duration</label>
              <input 
                type="text" 
                placeholder="e.g. 3 Months on Creator Socials only"
                value={usageRights}
                onChange={(e) => setUsageRights(e.target.value)}
                className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Exclusivity Period & Category</label>
              <input 
                type="text" 
                placeholder="e.g. 30 Days from post (No other cosmetics brands)"
                value={exclusivityClause}
                onChange={(e) => setExclusivityClause(e.target.value)}
                className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Timeline Start</label>
                <div className="relative">
                  <input 
                    type="date" 
                    value={timelineStart}
                    onChange={(e) => setTimelineStart(e.target.value)}
                    className="w-full bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
                    required
                  />
                </div>
              </div>
              
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Timeline End</label>
                <div className="relative">
                  <input 
                    type="date" 
                    value={timeline_end}
                    onChange={(e) => setTimelineEnd(e.target.value)}
                    className="w-full bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
                    required
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Payment Terms Card */}
        <div className="bg-card border border-border/80 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <DollarSign className="h-4 w-4" />
            Milestone Settings
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Payment Preset Terms</label>
              <select 
                value={paymentPreset}
                onChange={(e) => setPaymentPreset(e.target.value)}
                className="bg-muted/40 border border-border/60 rounded-xl p-2.5 text-xs focus:outline-none focus:border-primary/80"
              >
                <option value="50_50">50% Advance / 50% on Delivery</option>
                <option value="100_advance">100% Advance Payment</option>
                <option value="100_delivery">100% on Campaign Completion</option>
              </select>
            </div>

            {/* Calculated Milestones */}
            <div className="flex flex-col gap-3.5 border-t border-border/20 pt-3">
              {/* Advance Milestone */}
              {(paymentPreset === "50_50" || paymentPreset === "100_advance") && (
                <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/30 rounded-xl">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Milestone 1: Advance Payment</span>
                  <div className="grid grid-cols-2 gap-3 mt-1">
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground">Calculated Amount</span>
                      <span className="text-xs font-bold text-foreground py-2">₹{(parseFloat(advanceAmount) || 0).toLocaleString("en-IN")}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground">Due Date</span>
                      <input 
                        type="date" 
                        value={advanceDueDate}
                        onChange={(e) => setAdvanceDueDate(e.target.value)}
                        className="bg-background border border-border/60 rounded-lg p-1.5 text-[10px] focus:outline-none"
                        required
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Final Milestone */}
              {(paymentPreset === "50_50" || paymentPreset === "100_delivery") && (
                <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/30 rounded-xl">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Milestone 2: Final Delivery</span>
                  <div className="grid grid-cols-2 gap-3 mt-1">
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground">Calculated Amount</span>
                      <span className="text-xs font-bold text-foreground py-2">₹{(parseFloat(finalAmount) || 0).toLocaleString("en-IN")}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-semibold text-muted-foreground">Due Date</span>
                      <input 
                        type="date" 
                        value={finalDueDate}
                        onChange={(e) => setFinalDueDate(e.target.value)}
                        className="bg-background border border-border/60 rounded-lg p-1.5 text-[10px] focus:outline-none"
                        required
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Cover Note Template Card */}
        <div className="bg-card border border-border/80 p-4 rounded-2xl flex flex-col gap-4">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <FileCheck className="h-4 w-4" />
            Contract Cover Note Language
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold">
              <input 
                type="radio" 
                name="coverNoteType" 
                value="english" 
                checked={coverNoteType === "english"}
                onChange={() => setCoverNoteType("english")}
                className="accent-primary h-4 w-4"
              />
              English Cover Note
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold">
              <input 
                type="radio" 
                name="coverNoteType" 
                value="hinglish" 
                checked={coverNoteType === "hinglish"}
                onChange={() => setCoverNoteType("hinglish")}
                className="accent-primary h-4 w-4"
              />
              Hinglish Cover Note (Polite Hindi-English tone)
            </label>
          </div>
        </div>

        {/* Submit */}
        <Button 
          type="submit" 
          size="lg" 
          className="rounded-full shadow-lg h-12 text-sm font-bold w-full bg-primary text-primary-foreground hover:bg-primary/90 mt-2"
          disabled={submitting}
        >
          {submitting ? "Generating Contract PDF & Saving..." : "Generate Contract & Track Milestones"}
        </Button>
      </form>
    </div>
  );
}
