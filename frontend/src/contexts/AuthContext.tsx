import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { setAuthToken, API_URL } from "@/lib/api";
import { toast } from "sonner";
import { useUserStore } from "@/store/useAppStore";
import { supabase } from "@/lib/supabase";


interface User {
  email: string;
  niche: string;
  language: string;
  plan: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, phoneNumber: string, niche: string, language: string, stateName: string, tier: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();


  const checkAuth = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("trendrop_session_token");
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(`${API_URL}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_token: token }),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      const data = await response.json();
      
      if (data && data.success && data.valid && data.user) {
        setUser(data.user);
        setAuthToken(token);
        localStorage.setItem("trendrop_user_email", data.user.email);
        localStorage.setItem("trendrop_user_niche", data.user.niche);
        localStorage.setItem("trendrop_user_language", data.user.language);
        localStorage.setItem("trendrop_user_plan", data.user.plan);
        useUserStore.getState().setUser({
          email: data.user.email,
          niche: data.user.niche,
          language: data.user.language,
          plan: data.user.plan,
          authToken: token,
        });
      } else {
        // Server says token is invalid — clear session
        setAuthToken(null);
        localStorage.removeItem("trendrop_session_token");
        localStorage.removeItem("trendrop_user_email");
        localStorage.removeItem("trendrop_user_niche");
        localStorage.removeItem("trendrop_user_language");
        localStorage.removeItem("trendrop_user_plan");
        setUser(null);
      }
    } catch (error: any) {
      // Network error or timeout — do NOT wipe the session.
      // The backend may be temporarily unreachable (cold start, network blip).
      // Keep the user logged in with cached localStorage data instead.
      if (error?.name === "AbortError") {
        console.warn("Auth check timed out, using cached session");
      } else {
        console.warn("Auth check failed (network), using cached session:", error?.message);
      }
      // Restore user from localStorage so the app isn't stuck on "Loading..."
      const cachedEmail = localStorage.getItem("trendrop_user_email");
      if (cachedEmail) {
        setUser({
          email: cachedEmail,
          niche: localStorage.getItem("trendrop_user_niche") || "all",
          language: localStorage.getItem("trendrop_user_language") || "en",
          plan: localStorage.getItem("trendrop_user_plan") || "free",
        });
      } else {
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    // Sign in via Supabase client directly so the supabase-js session is
    // established. Without this, supabase-js fires onAuthStateChange with
    // null (because it has no local session), which was wiping the token
    // from localStorage immediately after the custom-API login set it.
    const { data: sbData, error: sbError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (sbError || !sbData.session) {
      throw new Error(sbError?.message || "Login failed");
    }

    const token = sbData.session.access_token;

    // Persist token for the custom http() helper in api.ts
    setAuthToken(token);
    localStorage.setItem("trendrop_session_token", token);

    // Fetch user profile from the backend to get niche / language / plan
    let niche = "all";
    let language = "en";
    let plan = "free";
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      const profileRes = await fetch(`${API_URL}/api/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_token: token }),
        signal: controller.signal,
      });
      clearTimeout(timeout);
      const profileData = await profileRes.json();
      if (profileData?.success && profileData.valid && profileData.user) {
        niche = profileData.user.niche ?? "all";
        language = profileData.user.language ?? "en";
        plan = profileData.user.plan ?? "free";
      }
    } catch (err) {
      console.warn("Could not fetch user profile after login (non-fatal):", err);
    }

    localStorage.setItem("trendrop_user_email", email);
    localStorage.setItem("trendrop_user_niche", niche);
    localStorage.setItem("trendrop_user_language", language);
    localStorage.setItem("trendrop_user_plan", plan);

    const userData: User = { email, niche, language, plan };
    setUser(userData);

    // Sync into Zustand store
    useUserStore.getState().setUser({
      email,
      niche,
      language,
      plan,
      authToken: token,
    });

    // Navigate to main screen
    navigate({ to: "/" });
  };


  const signup = async (email: string, password: string, phoneNumber: string, niche: string, language: string, stateName: string, tier: string) => {
    const response = await fetch(`${API_URL}/api/auth/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, phone_number: phoneNumber, niche, language, state: stateName, tier }),
    });

    const data = await response.json();
    
    if (data.success) {
      if (data.phone_verification_required) {
        navigate({ 
          to: "/verify-phone",
          search: { phone: phoneNumber }
        });
      } else if (data.session_token) {
        // Auto-login: backend returned a session immediately (admin API path)
        setAuthToken(data.session_token);
        localStorage.setItem("trendrop_session_token", data.session_token);
        localStorage.setItem("trendrop_user_email", data.user.email);
        localStorage.setItem("trendrop_user_niche", data.user.niche);
        localStorage.setItem("trendrop_user_language", data.user.language);
        localStorage.setItem("trendrop_user_plan", data.user.plan);
        setUser(data.user);
        navigate({ to: "/" });
      } else {
        // No session returned — redirect to login so user can sign in
        navigate({ to: "/login" });
      }
    } else {
      throw new Error(data.error || "Signup failed");
    }
  };

  const logout = async () => {
    const sessionToken = localStorage.getItem("trendrop_session_token");
    
    if (sessionToken) {
      try {
        await fetch(`${API_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ session_token: sessionToken }),
        });
      } catch (error) {
        toast.error("Logout failed — please try again");
      }
    }

    setAuthToken(null);
    // Clear all auth and preference keys
    const keysToRemove = [
      "trendrop_session_token",
      "trendrop_user_email",
      "trendrop_user_niche",
      "trendrop_user_language",
      "trendrop_user_plan",
      "trendrop_token",
      "trendrop_email",
      "trendrop_onboarded",
      "trendrop_visited",
      "trendrop_tutorial_done",
      "admin_token",
      "admin_email",
      "admin_role",
    ];
    for (const key of keysToRemove) {
      localStorage.removeItem(key);
    }
    setUser(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}