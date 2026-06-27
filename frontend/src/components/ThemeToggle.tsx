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
      localStorage.setItem("trendrop_theme", "dark");
    } else {
      root.removeAttribute("data-theme");
      root.classList.remove("dark");
      body.removeAttribute("data-theme");
      body.classList.remove("dark");
      localStorage.setItem("trendrop_theme", "light");
    }
    // Dispatch a storage event so other components or roots can sync if needed
    window.dispatchEvent(new Event("storage"));
  }, [dark]);

  return (
    <button
      onClick={() => setDark(!dark)}
      className="relative rounded-full bg-white/5 p-2 text-foreground transition-colors hover:bg-white/10 active:scale-95 text-xs font-semibold flex items-center justify-center h-8 px-3 gap-1 cursor-pointer border border-border"
      data-testid="theme-toggle"
      aria-label="Toggle theme"
    >
      {dark ? "☀ light" : "◐ dark"}
    </button>
  );
}
