import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Lightbulb, Calendar, Sparkles, Clock, Music, CheckCircle2, ChevronRight, RefreshCw, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const Route = createFileRoute("/ideas")({
  head: () => ({
    meta: [
      { title: "Daily Ideas & Autopilot Calendar — Trendrop" },
      { name: "description", content: "Daily personalized viral ideas and 30-day autopilot calendar." },
    ],
  }),
  component: IdeasPage,
});

interface Idea {
  title: string;
  description: string;
  hook: string;
  audio_suggestion: string;
  posting_time: string;
}

interface CalendarDay {
  day: number;
  topic: string;
  hook: string;
  audio_style: string;
  hashtags: string[];
  posting_time: string;
}

function IdeasPage() {
  const [activeTab, setActiveTab] = useState<"daily" | "calendar">("daily");
  const [niche, setNiche] = useState("dance");
  const [language, setLanguage] = useState("hi");
  const [frequency, setFrequency] = useState("daily");
  const [loadingIdeas, setLoadingIdeas] = useState(false);
  const [loadingCalendar, setLoadingCalendar] = useState(false);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);

  // Load user details
  useEffect(() => {
    const email = localStorage.getItem("trendrop_email") || "anonymous@trendrop.app";
    const n = localStorage.getItem("trendrop_niche") || "dance";
    const l = localStorage.getItem("trendrop_language") || "hi";
    setNiche(n);
    setLanguage(l);
    
    // Fetch initial ideas
    fetchIdeas(email);
  }, []);

  const authHeaders = () => {
    const token = localStorage.getItem("trendrop_token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  };

  const fetchIdeas = async (email: string) => {
    setLoadingIdeas(true);
    try {
      const res = await fetch("/api/daily-ideas", { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setIdeas(data);
      } else {
        throw new Error("Failed to load");
      }
    } catch {
      // Mock fallbacks
      setIdeas([
        {
          title: "The Ultimate " + niche.toUpperCase() + " Hack",
          description: "Show a 15-second hack or shortcut in your niche. Record a close-up of the process and final result.",
          hook: "Stop doing it the hard way! 🛑",
          audio_suggestion: "Trending Lofi Beats",
          posting_time: "6:30 PM"
        },
        {
          title: "Expectation vs Reality",
          description: "A funny, relatable comparison of starting out in the niche versus reality. Perfect for high engagement.",
          hook: "What they think I do vs What I actually do 🫠",
          audio_suggestion: "Upbeat Comedy Background",
          posting_time: "8:00 PM"
        },
        {
          title: "My Biggest Mistake in " + niche.toUpperCase(),
          description: "Share a vulnerability and the exact lesson you learned to build authentic trust with your audience.",
          hook: "I lost 10 hours of work doing this...",
          audio_suggestion: "Dramatic build-up, beat drop",
          posting_time: "7:15 PM"
        }
      ]);
    } finally {
      setLoadingIdeas(false);
    }
  };

  const generateCalendar = async () => {
    setLoadingCalendar(true);
    const headers: Record<string, string> = { "Content-Type": "application/json", ...authHeaders() };
    try {
      const res = await fetch("/api/calendar", {
        method: "POST",
        headers,
        body: JSON.stringify({
          niche,
          language,
          frequency
        })
      });
      if (res.ok) {
        const data = await res.json();
        setCalendar(data.calendar || []);
        toast.success("30-Day Autopilot Calendar generated!");
      } else {
        throw new Error("Failed to generate");
      }
    } catch {
      // Mock calendar
      const list: CalendarDay[] = Array.from({ length: 30 }).map((_, i) => ({
        day: i + 1,
        topic: `Stellar ${niche} Concept ${i + 1}`,
        hook: `This one secret changes everything... (${i + 1})`,
        audio_style: "Trending audio compilation",
        hashtags: [`#${niche}`, "#viral", "#creator"],
        posting_time: "7:00 PM"
      }));
      setCalendar(list);
      toast.success("Created locally!");
    } finally {
      setLoadingCalendar(false);
    }
  };

  const loadSavedCalendar = async () => {
    try {
      const res = await fetch("/api/calendar", { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data && data.calendar && data.calendar.length > 0) {
          setCalendar(data.calendar);
        }
      }
    } catch {}
  };

  useEffect(() => {
    loadSavedCalendar();
  }, []);

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white text-xl font-bold shadow-lg shadow-indigo-500/20">
          <Lightbulb className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-white">Ideation Hub</h1>
          <p className="text-xs text-muted-foreground">AI-powered trend-specific content creation</p>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted p-1">
        <button
          onClick={() => setActiveTab("daily")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTab === "daily" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          Daily Idea Drop
        </button>
        <button
          onClick={() => setActiveTab("calendar")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTab === "calendar" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Calendar className="h-3.5 w-3.5" />
          30-Day Autopilot
        </button>
      </div>

      {activeTab === "daily" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Today's Hot Picks</h2>
            <button 
              onClick={() => fetchIdeas(localStorage.getItem("trendrop_email") || "anonymous@trendrop.app")} 
              disabled={loadingIdeas}
              className="text-xs flex items-center gap-1 text-primary hover:underline"
            >
              <RefreshCw className={`h-3 w-3 ${loadingIdeas ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {loadingIdeas ? (
            <div className="text-center py-12 text-muted-foreground">Curating fresh custom ideas...</div>
          ) : (
            ideas.map((idea, index) => (
              <div key={index} className="glass-card p-5 relative border border-border/60 hover:border-primary/40 transition-all rounded-2xl space-y-3">
                <span className="absolute top-4 right-4 bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded-full">
                  Idea #{index + 1}
                </span>
                <div>
                  <h3 className="font-display font-bold text-lg text-white pr-12">{idea.title}</h3>
                  <p className="text-sm text-gray-300 mt-2">{idea.description}</p>
                </div>

                <div className="pt-2 border-t border-white/5 space-y-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-primary font-bold">Hook:</span>
                    <span className="text-gray-400 italic">"{idea.hook}"</span>
                  </div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-1"><Music className="h-3.5 w-3.5" /> {idea.audio_suggestion}</span>
                    <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {idea.posting_time}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "calendar" && (
        <div className="space-y-4">
          <div className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="font-display font-bold text-base text-white">Generate Your 30-Day Plan</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Generate a personalized, fully fleshed-out 30-day calendar complete with daily post concepts, trending audio recommendations, hooks, and optimal posting times aligned with target audiences.
            </p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Niche</label>
                <div className="mt-1 capitalize px-3 py-2 bg-muted rounded-xl">{niche}</div>
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Language</label>
                <div className="mt-1 capitalize px-3 py-2 bg-muted rounded-xl">{language === 'hi' ? 'Hindi' : 'English/Other'}</div>
              </div>
            </div>
            <Button 
              onClick={generateCalendar} 
              disabled={loadingCalendar} 
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold h-11"
            >
              {loadingCalendar ? "Generating..." : "Generate 30-Day Calendar"}
            </Button>
          </div>

          {calendar.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Your 30-Day Schedule</h3>
              <div className="grid grid-cols-5 gap-2">
                {calendar.map((item) => (
                  <button
                    key={item.day}
                    onClick={() => setSelectedDay(item)}
                    className={`aspect-square rounded-xl border flex flex-col justify-center items-center transition-all ${
                      selectedDay?.day === item.day 
                        ? 'border-indigo-500 bg-indigo-500/20 text-indigo-400' 
                        : 'border-border bg-card text-muted-foreground hover:border-muted-foreground'
                    }`}
                  >
                    <span className="text-xs font-bold">Day</span>
                    <span className="text-lg font-extrabold">{item.day}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedDay && (
            <div className="glass-card p-5 border border-indigo-500/40 rounded-2xl space-y-3 animate-in fade-in slide-in-from-bottom-2">
              <div className="flex justify-between items-center">
                <span className="text-indigo-400 font-bold text-sm">Day {selectedDay.day} Details</span>
                <button onClick={() => setSelectedDay(null)} className="text-xs text-muted-foreground hover:text-white">Close</button>
              </div>
              <h4 className="font-display text-lg font-bold text-white">{selectedDay.topic}</h4>
              <div className="space-y-2 text-xs">
                <div className="p-3 bg-white/5 rounded-xl border border-white/5">
                  <span className="block font-bold text-indigo-400 mb-1">RECOMMENDED HOOK</span>
                  <span className="text-sm text-gray-200">"{selectedDay.hook}"</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span className="flex items-center gap-1"><Music className="h-3.5 w-3.5" /> {selectedDay.audio_style}</span>
                  <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {selectedDay.posting_time}</span>
                </div>
                <div className="flex flex-wrap gap-1 pt-1">
                  {selectedDay.hashtags.map((h, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-muted text-muted-foreground text-[10px] font-semibold">{h}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
