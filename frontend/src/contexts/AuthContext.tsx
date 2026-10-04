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
  loginWithGoogle: () => Promise<void>;
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
    try {
      const token = localStorage.getItem("trendrop_session_token");
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      // Seed cached user state immediately — 0ms perceived load time
      const cachedEmail = localStorage.getItem("trendrop_user_email");
      const cachedNiche = localStorage.getItem("trendrop_user_niche") || "all";
      const cachedLang = localStorage.getItem("trendrop_user_language") || "hi";
      const cachedPlan = localStorage.getItem("trendrop_user_plan") || "free";
      if (cachedEmail) {
        setUser({ email: cachedEmail, niche: cachedNiche, language: cachedLang, plan: cachedPlan });
        setAuthToken(token);
      }
      setLoading(false);

      // Background: verify with backend to refresh plan/niche data.
      // IMPORTANT: Only clear session if backend explicitly returns { valid: false }.
      // Never clear on network errors, timeouts, or unexpected responses — user stays logged in.
      try {
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

        if (data?.success && data?.valid && data?.user) {
          // Valid — update with latest profile from backend
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
        } else if (data?.valid === false) {
          // Backend explicitly says token is invalid (revoked, expired, etc.) — sign out
          console.warn("[auth] Backend revoked session, signing out");
          setAuthToken(null);
          localStorage.removeItem("trendrop_session_token");
          localStorage.removeItem("trendrop_user_email");
          localStorage.removeItem("trendrop_user_niche");
          localStorage.removeItem("trendrop_user_language");
          localStorage.removeItem("trendrop_user_plan");
          setUser(null);
        }
        // else: unexpected response shape → keep user logged in with cached data
      } catch {
        // Network/timeout — backend unreachable. Keep user logged in, don't touch session.
        console.warn("[auth] Backend verify unreachable, using cached session");
      }
    } catch (error: any) {
      // Outer catch: localStorage read failed or similar — stay logged in if possible
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
        console.warn("Backend logout failed:", error);
      }
    }

    // 1. Terminate Supabase client session to purge active credentials
    try {
      await supabase.auth.signOut({ scope: "local" });
    } catch (e) {
      try {
        await supabase.auth.signOut();
      } catch (err) {
        console.warn("Supabase signOut error:", err);
      }
    }

    // 2. Clear in-memory token
    setAuthToken(null);

    // 3. Clear ALL localStorage items related to trendrop, supabase auth, or admin
    if (typeof window !== "undefined") {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (
          key &&
          (key.startsWith("sb-") ||
            key.startsWith("trendrop_") ||
            key.startsWith("admin_"))
        ) {
          keysToRemove.push(key);
        }
      }
      for (const k of keysToRemove) {
        localStorage.removeItem(k);
      }
      try {
        sessionStorage.clear();
      } catch (e) {}
    }

    // 4. Reset Zustand user store
    useUserStore.setState({
      email: null,
      niche: null,
      language: null,
      plan: null,
      authToken: null,
      isOnboarded: false,
    });

    // 5. Clear AuthContext state
    setUser(null);
  };

  const loginWithGoogle = async () => {
    // Skip Google One Tap entirely — it silently fails in most browsers (third-party
    // cookie restrictions, prompt already dismissed, FedCM issues) and provides zero
    // user feedback while the 2.5s timeout burns. Go straight to the full OAuth
    // redirect which shows the Google account picker reliably.
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/`,
        // Force account chooser every time so user can pick which Google account
        queryParams: { prompt: "select_account" },
      },
    });
    if (error) {
      throw new Error(error.message);
    }
  };

  useEffect(() => {
    // Helper: detect if current page load is an OAuth redirect (has access_token or code in URL)
    const isOAuthCallback = () => {
      if (typeof window === "undefined") return false;
      const hash = window.location.hash;
      const search = window.location.search;
      return (
        hash.includes("access_token") ||
        hash.includes("refresh_token") ||
        search.includes("code=") ||
        search.includes("access_token")
      );
    };

    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        setAuthToken(null);
        setUser(null);
        setLoading(false);
        useUserStore.setState({
          email: null,
          niche: null,
          language: null,
          plan: null,
          authToken: null,
          isOnboarded: false,
        });
        return;
      }

      if ((event === "SIGNED_IN" || event === "INITIAL_SESSION") && session?.access_token) {
        // Trust Supabase's session state — if SIGNED_IN or INITIAL_SESSION fires with
        // a valid session object, the user is authenticated. No ghost session guard needed:
        // our logout() calls supabase.auth.signOut() which purges the Supabase session,
        // so INITIAL_SESSION with a live session always means a legitimate returning user.

        // Valid session: OAuth redirect OR returning user with stored token
        const token = session.access_token;
        const email = session.user.email || "";
        setAuthToken(token);
        localStorage.setItem("trendrop_session_token", token);
        localStorage.setItem("trendrop_user_email", email);
        // Only set defaults if not already stored (preserve existing user prefs)
        if (!localStorage.getItem("trendrop_user_niche")) {
          localStorage.setItem("trendrop_user_niche", "all");
        }
        if (!localStorage.getItem("trendrop_user_language")) {
          localStorage.setItem("trendrop_user_language", "en");
        }
        if (!localStorage.getItem("trendrop_user_plan")) {
          localStorage.setItem("trendrop_user_plan", "pro");
        }
        const userObj = {
          email,
          niche: localStorage.getItem("trendrop_user_niche") || "all",
          language: localStorage.getItem("trendrop_user_language") || "en",
          plan: localStorage.getItem("trendrop_user_plan") || "pro",
        };
        setUser(userObj);
        useUserStore.getState().setUser({ ...userObj, authToken: token });
        setLoading(false);

        // Background: verify token with backend to get actual plan/niche/language
        // (non-blocking — user is already logged in from cached data above)
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        fetch(`${API_URL}/api/auth/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_token: token }),
          signal: controller.signal,
        })
          .then((r) => r.json())
          .then((data) => {
            clearTimeout(timeout);
            if (data?.success && data?.valid && data?.user) {
              const u = data.user;
              localStorage.setItem("trendrop_user_email", u.email);
              localStorage.setItem("trendrop_user_niche", u.niche);
              localStorage.setItem("trendrop_user_language", u.language);
              localStorage.setItem("trendrop_user_plan", u.plan);
              setUser(u);
              useUserStore.getState().setUser({ ...u, authToken: token });
            }
          })
          .catch(() => {
            clearTimeout(timeout);
            // Non-fatal: user stays logged in with cached data
          });

        return;
      }

      if (event === "INITIAL_SESSION" && !session) {
        // No active Supabase session — fall back to checkAuth to handle our custom cached token
        checkAuth();
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, signup, logout, checkAuth }}>
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