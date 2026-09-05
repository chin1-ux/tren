import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  Handshake, 
  Plus, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Calendar, 
  DollarSign, 
  ExternalLink, 
  Copy, 
  Check, 
  ArrowRight,
  TrendingUp,
  Clock,
  Briefcase
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch, logAnalyticsEvent, submitCreatorFeedback } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { FEATURES } from "@/lib/features";

export const Route = createFileRoute("/deals/")({
  head: () => ({
    meta: [
      { title: "Brand Deals Dashboard — Trendrop" },
      { name: "description", content: "Track your active brand deals, generate contracts, and monitor payment milestones." },
    ],
  }),
  component: DealsDashboardPage,
});

interface Milestone {
  id: number;
  deal_id: number;
  milestone_name: string;
  amount: number;
  due_date: string;
  paid_status: "paid" | "unpaid";
  reminder_sent_at: string | null;
}

interface BrandDeal {
  id: number;
  creator_id: string;
  brand_name: string;
  deliverables: string;
  rate_amount: number;
  currency: string;
  usage_rights: string;
  exclusivity_clause: string;
  timeline_start: string | null;
  timeline_end: string | null;
  status: string;
  cover_note_type: string;
  created_at: string;
  milestones: Milestone[];
}

function DealsDashboardPage() {
  // Feature disabled check
  if (!FEATURES.DEALS_ENABLED) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 pb-28 pt-6">
        <div className="text-center space-y-4">
          <div className="h-16 w-16 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground mx-auto">
            <Briefcase className="h-8 w-8" />
          </div>
          <h1 className="text-xl font-bold text-foreground">Deals Launch After Beta</h1>
          <p className="text-sm text-muted-foreground max-w-xs">
            Brand deal tracking isn't part of the beta — it launches right after. For now, focus on
            the trend dashboard.
          </p>
        </div>
      </div>
    );
  }

  const [deals, setDeals] = useState<BrandDeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "active" | "overdue">("all");
  const [selectedMilestoneForFollowUp, setSelectedMilestoneForFollowUp] = useState<{
    milestone: Milestone;
    deal: BrandDeal;
  } | null>(null);
  const [copiedText, setCopiedText] = useState<"english" | "hinglish" | null>(null);

  // Feedback State
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackDealId, setFeedbackDealId] = useState<number | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<"useful" | "not_useful" | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/api/deals");
      if (res.ok) {
        const data = await res.json();
        setDeals(data);
      } else {
        toast.error("Failed to load brand deals");
      }
    } catch (err) {
      console.error("Error loading brand deals:", err);
      toast.error("Network error loading brand deals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, []);

  const handlePayMilestone = async (dealId: number, milestoneId: number) => {
    try {
      const res = await apiFetch(`/api/deals/${dealId}/pay-milestone/${milestoneId}`, {
        method: "POST"
      });
      if (res.ok) {
        toast.success("Milestone marked as paid!");
        // Update local state
        setDeals(prevDeals => 
          prevDeals.map(d => {
            if (d.id !== dealId) return d;
            return {
              ...d,
              milestones: d.milestones.map(m => {
                if (m.id !== milestoneId) return m;
                return { ...m, paid_status: "paid" as const };
              })
            };
          })
        );
      } else {
        toast.error("Failed to update milestone status");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error updating milestone");
    }
  };

  const handleDownloadContract = async (dealId: number, brandName: string) => {
    toast.info("Downloading contract PDF...");
    try {
      const res = await apiFetch(`/api/deals/${dealId}/download`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Contract_${brandName.replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      toast.success("Contract downloaded!");

      // Log event
      logAnalyticsEvent("contract_downloaded");

      // Trigger feedback modal
      const alreadyGaveFeedback = localStorage.getItem(`feedback_given_${dealId}`);
      if (!alreadyGaveFeedback) {
        setFeedbackDealId(dealId);
        setShowFeedbackModal(true);
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to download contract PDF");
    }
  };

  // Metrics calculations
  const now = new Date();
  
  const totalEarnings = deals.reduce((acc, d) => {
    return acc + d.milestones.reduce((mAcc, m) => mAcc + Number(m.amount), 0);
  }, 0);

  const totalOverdue = deals.reduce((acc, d) => {
    return acc + d.milestones.reduce((mAcc, m) => {
      const isOverdue = m.paid_status === "unpaid" && new Date(m.due_date) < now;
      return mAcc + (isOverdue ? Number(m.amount) : 0);
    }, 0);
  }, 0);

  const totalPending = deals.reduce((acc, d) => {
    return acc + d.milestones.reduce((mAcc, m) => {
      const isPending = m.paid_status === "unpaid" && new Date(m.due_date) >= now;
      return mAcc + (isPending ? Number(m.amount) : 0);
    }, 0);
  }, 0);

  const hasOverdueMilestones = (deal: BrandDeal) => {
    return deal.milestones.some(m => m.paid_status === "unpaid" && new Date(m.due_date) < now);
  };

  const filteredDeals = deals.filter(deal => {
    if (activeTab === "active") return deal.status === "active";
    if (activeTab === "overdue") return hasOverdueMilestones(deal);
    return true;
  });

  const handleCopyText = (text: string, type: "english" | "hinglish") => {
    navigator.clipboard.writeText(text);
    setCopiedText(type);
    toast.success("Follow-up template copied to clipboard!");
    logAnalyticsEvent("reminder_clicked");
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackDealId || !feedbackRating) {
      toast.error("Please select a rating");
      return;
    }
    setSubmittingFeedback(true);
    try {
      await submitCreatorFeedback(feedbackDealId, feedbackRating, feedbackComment);
      localStorage.setItem(`feedback_given_${feedbackDealId}`, "true");
      toast.success("Thank you for your feedback!");
      setShowFeedbackModal(false);
      setFeedbackRating(null);
      setFeedbackComment("");
    } catch (err) {
      console.error(err);
      toast.error("Failed to submit feedback");
    } finally {
      setSubmittingFeedback(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pt-6 pb-12 min-h-screen text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-display bg-gradient-to-r from-primary to-rose-400 bg-clip-text text-transparent">
            Brand Deals
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Contracts & milestone tracker
          </p>
        </div>
        <Link to="/deals/new">
          <Button size="sm" className="rounded-full shadow-lg gap-1.5 px-4">
            <Plus className="h-4 w-4" />
            New Deal
          </Button>
        </Link>
      </div>

      {/* Metrics Summary Grid */}
      <div className="grid grid-cols-3 gap-2.5 bg-card/40 border border-border/60 p-3 rounded-2xl">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Total Revenue</span>
          <span className="text-sm font-bold text-foreground">₹{totalEarnings.toLocaleString("en-IN")}</span>
        </div>
        <div className="flex flex-col gap-0.5 border-l border-border/40 pl-3">
          <span className="text-[10px] text-rose-500 uppercase tracking-wider font-semibold">Overdue</span>
          <span className="text-sm font-bold text-rose-500">₹{totalOverdue.toLocaleString("en-IN")}</span>
        </div>
        <div className="flex flex-col gap-0.5 border-l border-border/40 pl-3">
          <span className="text-[10px] text-amber-500 uppercase tracking-wider font-semibold">Pending</span>
          <span className="text-sm font-bold text-amber-500">₹{totalPending.toLocaleString("en-IN")}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border/40 gap-4 text-sm font-medium">
        <button 
          onClick={() => setActiveTab("all")}
          className={`pb-2 border-b-2 transition-colors ${activeTab === "all" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          All Deals ({deals.length})
        </button>
        <button 
          onClick={() => setActiveTab("active")}
          className={`pb-2 border-b-2 transition-colors ${activeTab === "active" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          Active
        </button>
        <button 
          onClick={() => setActiveTab("overdue")}
          className={`pb-2 border-b-2 transition-colors ${activeTab === "overdue" ? "border-primary text-rose-500" : "border-transparent text-muted-foreground hover:text-rose-400"}`}
        >
          Overdue
        </button>
      </div>

      {/* Deals List */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Clock className="h-8 w-8 text-muted-foreground animate-spin" />
          <span className="text-sm text-muted-foreground">Loading brand deals...</span>
        </div>
      ) : filteredDeals.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4 bg-card/20 border border-dashed border-border/60 rounded-3xl text-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground">
            <Briefcase className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-base">No brand deals yet</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs">
              Lock brand campaigns with professional legal contracts in 1 minute.
            </p>
          </div>
          <Link to="/deals/new">
            <Button size="sm" className="rounded-full">
              Create Your First Deal
            </Button>
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {filteredDeals.map((deal) => {
            const dealOverdue = hasOverdueMilestones(deal);
            const totalDealVal = deal.milestones.reduce((acc, m) => acc + Number(m.amount), 0);
            
            return (
              <motion.div 
                key={deal.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-card border border-border/80 rounded-2xl overflow-hidden shadow-sm"
              >
                {/* Deal Header */}
                <div className="p-4 flex items-start justify-between border-b border-border/40 bg-muted/20">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-bold text-sm text-foreground tracking-tight">{deal.brand_name}</span>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                      <Calendar className="h-3 w-3" />
                      {deal.timeline_start ? deal.timeline_start.split("T")[0] : "TBD"} to {deal.timeline_end ? deal.timeline_end.split("T")[0] : "TBD"}
                    </span>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <span className="font-extrabold text-sm text-primary">₹{totalDealVal.toLocaleString("en-IN")}</span>
                    {dealOverdue ? (
                      <span className="bg-rose-500/10 text-rose-500 text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1">
                        <AlertCircle className="h-2.5 w-2.5" /> Overdue
                      </span>
                    ) : (
                      <span className="bg-emerald-500/10 text-emerald-500 text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                        Active
                      </span>
                    )}
                  </div>
                </div>

                {/* Deliverables / Scope */}
                <div className="px-4 py-3 border-b border-border/40">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Deliverables Scope</span>
                  <p className="text-xs text-foreground/80 mt-1 whitespace-pre-line leading-relaxed">
                    {deal.deliverables}
                  </p>
                  {(deal.usage_rights || deal.exclusivity_clause) && (
                    <div className="mt-2.5 grid grid-cols-2 gap-2 text-[10px] border-t border-border/20 pt-2.5">
                      {deal.usage_rights && (
                        <div>
                          <span className="font-medium text-muted-foreground">Usage Rights:</span>
                          <span className="block text-foreground mt-0.5">{deal.usage_rights}</span>
                        </div>
                      )}
                      {deal.exclusivity_clause && (
                        <div>
                          <span className="font-medium text-muted-foreground">Exclusivity:</span>
                          <span className="block text-foreground mt-0.5">{deal.exclusivity_clause}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Milestones Payment Section */}
                <div className="p-4 flex flex-col gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Payment Milestones</span>
                  
                  <div className="flex flex-col gap-2 mt-1">
                    {deal.milestones.map((m) => {
                      const isOverdue = m.paid_status === "unpaid" && new Date(m.due_date) < now;
                      const dueDateFormatted = new Date(m.due_date).toLocaleDateString("en-IN", {
                        day: "numeric", month: "short"
                      });
                      
                      return (
                        <div key={m.id} className="flex items-center justify-between p-2 rounded-xl bg-muted/40 border border-border/30">
                          <div className="flex items-center gap-2">
                            {m.paid_status === "paid" ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                            ) : isOverdue ? (
                              <AlertCircle className="h-4 w-4 text-rose-500 shrink-0" />
                            ) : (
                              <Clock className="h-4 w-4 text-amber-500 shrink-0" />
                            )}
                            <div className="flex flex-col">
                              <span className={`text-xs font-semibold ${m.paid_status === "paid" ? "line-through text-muted-foreground" : "text-foreground"}`}>
                                {m.milestone_name}
                              </span>
                              <span className="text-[9px] text-muted-foreground">
                                Due: {dueDateFormatted} {isOverdue && <span className="text-rose-500 font-bold ml-1">Overdue</span>}
                              </span>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-extrabold mr-1">₹{Number(m.amount).toLocaleString("en-IN")}</span>
                            
                            {m.paid_status === "unpaid" ? (
                              <>
                                <Button 
                                  size="icon" 
                                  variant="ghost" 
                                  className="h-7 w-7 text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 rounded-full shrink-0"
                                  onClick={() => handlePayMilestone(deal.id, m.id)}
                                  title="Mark as paid"
                                >
                                  <CheckCircle2 className="h-4.5 w-4.5" />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-full shrink-0"
                                  onClick={() => setSelectedMilestoneForFollowUp({ milestone: m, deal })}
                                  title="Get follow-up message"
                                >
                                  <Handshake className="h-4 w-4" />
                                </Button>
                              </>
                            ) : (
                              <span className="text-[9px] font-bold text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded-full uppercase tracking-wider">
                                Paid
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Deal Footer / Contract Actions */}
                <div className="px-4 py-3 bg-muted/10 border-t border-border/40 flex justify-between items-center">
                  <span className="text-[10px] text-muted-foreground">Contract finalized</span>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="h-8 text-xs gap-1.5 rounded-full px-3.5 bg-background border-border/80 hover:bg-muted"
                    onClick={() => handleDownloadContract(deal.id, deal.brand_name)}
                  >
                    <FileText className="h-3.5 w-3.5" />
                    Download Contract
                  </Button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Follow-up Messages Modal Dialog */}
      <AnimatePresence>
        {selectedMilestoneForFollowUp && (
          <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="bg-card w-full max-w-sm rounded-3xl p-5 border border-border flex flex-col gap-4 shadow-2xl"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-base tracking-tight">Payment Follow-Up drafts</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    For ₹{Number(selectedMilestoneForFollowUp.milestone.amount).toLocaleString("en-IN")} due from {selectedMilestoneForFollowUp.deal.brand_name}
                  </p>
                </div>
                <button 
                  onClick={() => setSelectedMilestoneForFollowUp(null)}
                  className="text-xs text-muted-foreground hover:text-foreground font-semibold px-2 py-1 rounded-md"
                >
                  Close
                </button>
              </div>

              <div className="flex flex-col gap-4">
                {/* Hinglish Draft */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">Hinglish Template</span>
                    <button 
                      onClick={() => handleCopyText(
                        `Hi team, humare campaign deliverables ke context mein ek chota reminder. Humare agreement ke hisab se milestone payment of ₹${Number(selectedMilestoneForFollowUp.milestone.amount).toLocaleString("en-IN")} (${selectedMilestoneForFollowUp.milestone.milestone_name}) due ho chuka hai / hone wala hai. Please share update on the status. Thanks!`,
                        "hinglish"
                      )}
                      className="text-[10px] text-primary hover:underline font-bold flex items-center gap-1"
                    >
                      {copiedText === "hinglish" ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {copiedText === "hinglish" ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <blockquote className="bg-muted/40 border border-border/40 p-2.5 rounded-xl text-xs text-foreground/80 leading-relaxed italic">
                    {`"Hi team, humare campaign deliverables ke context mein ek chota reminder. Humare agreement ke hisab se milestone payment of ₹${Number(selectedMilestoneForFollowUp.milestone.amount).toLocaleString("en-IN")} (${selectedMilestoneForFollowUp.milestone.milestone_name}) due ho chuka hai / hone wala hai. Please share update on the status. Thanks!"`}
                  </blockquote>
                </div>

                {/* English Draft */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground">English Template</span>
                    <button 
                      onClick={() => handleCopyText(
                        `Hi team, a quick reminder regarding the milestone payment for our campaign. The payment of ₹${Number(selectedMilestoneForFollowUp.milestone.amount).toLocaleString("en-IN")} for '${selectedMilestoneForFollowUp.milestone.milestone_name}' is currently due under our agreement. Could you please share a status update or remittance advice once processed? Thank you!`,
                        "english"
                      )}
                      className="text-[10px] text-primary hover:underline font-bold flex items-center gap-1"
                    >
                      {copiedText === "english" ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {copiedText === "english" ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <blockquote className="bg-muted/40 border border-border/40 p-2.5 rounded-xl text-xs text-foreground/80 leading-relaxed italic">
                    {`"Hi team, a quick reminder regarding the milestone payment for our campaign. The payment of ₹${Number(selectedMilestoneForFollowUp.milestone.amount).toLocaleString("en-IN")} for '${selectedMilestoneForFollowUp.milestone.milestone_name}' is currently due under our agreement. Could you please share a status update or remittance advice once processed? Thank you!"`}
                  </blockquote>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Feedback Modal Dialog */}
      <AnimatePresence>
        {showFeedbackModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-card w-full max-w-sm rounded-3xl p-6 border border-border flex flex-col gap-4 shadow-2xl"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-lg tracking-tight bg-gradient-to-r from-primary to-rose-400 bg-clip-text text-transparent">Was this useful?</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Help us improve our brand contract templates.
                  </p>
                </div>
                <button 
                  onClick={() => setShowFeedbackModal(false)}
                  className="text-xs text-muted-foreground hover:text-foreground font-semibold px-2 py-1 rounded-md"
                >
                  Skip
                </button>
              </div>

              <div className="flex flex-col gap-4 mt-2">
                <div className="flex gap-4">
                  <Button 
                    variant={feedbackRating === "useful" ? "default" : "outline"}
                    className="flex-1 rounded-full py-3 text-xs"
                    onClick={() => setFeedbackRating("useful")}
                  >
                    👍 Yes, useful
                  </Button>
                  <Button 
                    variant={feedbackRating === "not_useful" ? "default" : "outline"}
                    className="flex-1 rounded-full py-3 text-xs"
                    onClick={() => setFeedbackRating("not_useful")}
                  >
                    👎 Needs changes
                  </Button>
                </div>

                <div className="flex flex-col gap-1.5 mt-2">
                  <label htmlFor="feedback-comment" className="text-xs font-semibold text-muted-foreground">What's missing or what can we improve?</label>
                  <textarea
                    id="feedback-comment"
                    placeholder="Enter your comments or suggestions..."
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    className="bg-muted/40 border border-border rounded-2xl p-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary min-h-[80px] resize-none"
                  />
                </div>

                <Button 
                  onClick={handleSubmitFeedback}
                  disabled={submittingFeedback || !feedbackRating}
                  className="w-full rounded-full py-4 mt-2 font-semibold"
                >
                  {submittingFeedback ? "Submitting..." : "Submit Feedback"}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
