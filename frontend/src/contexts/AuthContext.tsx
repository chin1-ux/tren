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
      const sessionToken = localStorage.getItem("trendrop_session_token");
      if (!sessionToken) {
        setUser(null);
        return;
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ session_token }),
      });

      const data = await response.json();
      
      if (data.success && data.valid) {
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
    } else {
      throw new Error(data.error || "Login failed");
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
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
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