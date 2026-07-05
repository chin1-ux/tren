import React from "react";

export function ThemeToggle() {
  const [dark, setDark] = React.useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("trendrop_theme");
      if (saved) return saved === "dark";
      return document.documentElement.classList.contains("dark") || document.body.classList.contains("dark");
    }
    return false;
  });

  React.useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    if (dark) {
      root.setAttribute("data-theme", "dark");
      root.classList.add("dark");
      body.setAttribute("data-theme", "dark");
      body.classList.add("dark");
    } else {
      root.removeAttribute("data-theme");
      root.classList.remove("dark");
      body.removeAttribute("data-theme");
      body.classList.remove("dark");
    }
  }, [dark]);

  React.useEffect(() => {
    const handleSync = () => {
      const saved = localStorage.getItem("trendrop_theme");
      if (saved) {
        setDark(saved === "dark");
      }
    };
    window.addEventListener("storage", handleSync);
    window.addEventListener("theme-change", handleSync);
    return () => {
      window.removeEventListener("storage", handleSync);
      window.removeEventListener("theme-change", handleSync);
    };
  }, []);

  const handleToggle = () => {
    const nextDark = !dark;
    setDark(nextDark);
    localStorage.setItem("trendrop_theme", nextDark ? "dark" : "light");
    window.dispatchEvent(new Event("theme-change"));
  };

  return (
    <button
      onClick={handleToggle}
      className="relative rounded-full bg-white/5 p-2 text-foreground transition-colors hover:bg-white/10 active:scale-95 text-xs font-semibold flex items-center justify-center h-8 px-3 gap-1 cursor-pointer border border-border"
      data-testid="theme-toggle"
      aria-label="Toggle theme"
    >
      {dark ? "☀ light" : "◐ dark"}
    </button>
  );
}
