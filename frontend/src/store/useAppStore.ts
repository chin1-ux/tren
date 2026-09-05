import { create } from "zustand";
import { supabase } from "../lib/supabase";
import { setAuthToken } from "../lib/api";

interface UserState {
  email: string | null;
  niche: string | null;
  language: string | null;
  plan: string | null;
  authToken: string | null;
  isOnboarded: boolean;
  initializeFromLocalStorage: () => void;
  setUser: (user: Partial<Omit<UserState, "setUser" | "logout" | "initializeFromLocalStorage">>) => void;
  logout: () => void;
}

interface TrendsState {
  activeCategory: string;
  searchQuery: string;
  sortBy: string;
  setActiveCategory: (category: string) => void;
  setSearchQuery: (query: string) => void;
  setSortBy: (sort: string) => void;
}

interface GenerateState {
  files: File[];
  currentJobId: string | null;
  generationProgress: number;
  generationStatus: "idle" | "queued" | "processing" | "complete" | "failed";
  history: Array<{ id: string; timestamp: string; status: string; outputUrl?: string }>;
  setFiles: (files: File[]) => void;
  setCurrentJobId: (jobId: string | null) => void;
  setGenerationProgress: (progress: number) => void;
  setGenerationStatus: (status: "idle" | "queued" | "processing" | "complete" | "failed") => void;
  addHistoryItem: (item: { id: string; status: string; outputUrl?: string }) => void;
  clearFiles: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  email: null,
  niche: null,
  language: null,
  plan: null,
  authToken: null,
  isOnboarded: false,

  initializeFromLocalStorage: () => {
    if (typeof window !== "undefined") {
      const email = localStorage.getItem("trendrop_user_email");
      const niche = localStorage.getItem("trendrop_niche");
      const language = localStorage.getItem("trendrop_language");
      const plan = localStorage.getItem("trendrop_user_plan");
      const authToken = localStorage.getItem("trendrop_token");
      const isOnboarded = localStorage.getItem("trendrop_onboarded") === "true";
      set({ email, niche, language, plan, authToken, isOnboarded });
      if (authToken) setAuthToken(authToken);
    }
  },

  setUser: (updates) =>
    set((state) => {
      const next = { ...state, ...updates };
      if (typeof window !== "undefined") {
        if (updates.email !== undefined) {
          if (updates.email) localStorage.setItem("trendrop_user_email", updates.email);
          else localStorage.removeItem("trendrop_user_email");
        }
        if (updates.niche !== undefined) {
          if (updates.niche) localStorage.setItem("trendrop_niche", updates.niche);
          else localStorage.removeItem("trendrop_niche");
        }
        if (updates.language !== undefined) {
          if (updates.language) localStorage.setItem("trendrop_language", updates.language);
          else localStorage.removeItem("trendrop_language");
        }
        if (updates.plan !== undefined) {
          if (updates.plan) localStorage.setItem("trendrop_user_plan", updates.plan);
          else localStorage.removeItem("trendrop_user_plan");
        }
        if (updates.authToken !== undefined) {
          if (updates.authToken) localStorage.setItem("trendrop_token", updates.authToken);
          else localStorage.removeItem("trendrop_token");
        }
        if (updates.isOnboarded !== undefined) {
          localStorage.setItem("trendrop_onboarded", String(updates.isOnboarded));
        }
      }
      return next;
    }),

  logout: () => {
    // Clear Supabase Session and local cookies/memory
    supabase.auth.signOut().catch((err) => console.error("SignOut error:", err));
    setAuthToken(null);

    if (typeof window !== "undefined") {
      localStorage.removeItem("trendrop_user_email");
      localStorage.removeItem("trendrop_niche");
      localStorage.removeItem("trendrop_language");
      localStorage.removeItem("trendrop_user_plan");
      localStorage.removeItem("trendrop_token");
      localStorage.removeItem("trendrop_onboarded");
      localStorage.removeItem("trendrop_plan");
    }
    set({
      email: null,
      niche: null,
      language: null,
      plan: null,
      authToken: null,
      isOnboarded: false,
    });
  },
}));

export const useTrendsStore = create<TrendsState>((set) => ({
  activeCategory: "all",
  searchQuery: "",
  sortBy: "velocity",
  setActiveCategory: (activeCategory) => set({ activeCategory }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSortBy: (sortBy) => set({ sortBy }),
}));

export const useGenerateStore = create<GenerateState>((set) => ({
  files: [],
  currentJobId: null,
  generationProgress: 0,
  generationStatus: "idle",
  history: [],
  setFiles: (files) => set({ files }),
  setCurrentJobId: (currentJobId) => set({ currentJobId }),
  setGenerationProgress: (generationProgress) => set({ generationProgress }),
  setGenerationStatus: (generationStatus) => set({ generationStatus }),
  addHistoryItem: (item) =>
    set((state) => ({
      history: [
        {
          id: item.id,
          status: item.status,
          outputUrl: item.outputUrl,
          timestamp: new Date().toISOString(),
        },
        ...state.history,
      ],
    })),
  clearFiles: () => set({ files: [] }),
}));
