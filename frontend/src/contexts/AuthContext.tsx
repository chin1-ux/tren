import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface User {
  email: string;
  niche: string;
  language: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, niche: string, language: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("trendrop_session_token");
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ session_token: token }),
      });

      const data = await response.json();
      
      if (data && data.success && data.valid && data.user) {
        setUser(data.user);
        localStorage.setItem("trendrop_user_email", data.user.email);
        localStorage.setItem("trendrop_user_niche", data.user.niche);
        localStorage.setItem("trendrop_user_language", data.user.language);
      } else {
        // Session invalid, clear it
        localStorage.removeItem("trendrop_session_token");
        localStorage.removeItem("trendrop_user_email");
        localStorage.removeItem("trendrop_user_niche");
        localStorage.removeItem("trendrop_user_language");
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      // Clear session on error
      localStorage.removeItem("trendrop_session_token");
      localStorage.removeItem("trendrop_user_email");
      localStorage.removeItem("trendrop_user_niche");
      localStorage.removeItem("trendrop_user_language");
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();
    
    if (data.success) {
      localStorage.setItem("trendrop_session_token", data.session_token);
      localStorage.setItem("trendrop_user_email", data.user.email);
      localStorage.setItem("trendrop_user_niche", data.user.niche);
      localStorage.setItem("trendrop_user_language", data.user.language);
      setUser(data.user);
      // Navigate to main screen after successful auth
      window.location.href = "/";
    } else {
      throw new Error(data.error || "Login failed");
    }
  };

  const signup = async (email: string, password: string, niche: string, language: string) => {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, niche, language }),
    });

    const data = await response.json();
    
    if (data.success) {
      localStorage.setItem("trendrop_session_token", data.session_token);
      localStorage.setItem("trendrop_user_email", data.user.email);
      localStorage.setItem("trendrop_user_niche", data.user.niche);
      localStorage.setItem("trendrop_user_language", data.user.language);
      setUser(data.user);
      // Navigate to main screen after successful signup
      window.location.href = "/";
    } else {
      throw new Error(data.error || "Signup failed");
    }
  };

  const logout = async () => {
    const sessionToken = localStorage.getItem("trendrop_session_token");
    
    if (sessionToken) {
      try {
        await fetch(`${import.meta.env.VITE_API_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ session_token }),
        });
      } catch (error) {
        console.error("Logout failed:", error);
      }
    }

    localStorage.removeItem("trendrop_session_token");
    localStorage.removeItem("trendrop_user_email");
    localStorage.removeItem("trendrop_user_niche");
    localStorage.removeItem("trendrop_user_language");
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