import React, { useState } from 'react';
import {
  Check,
  Sparkles,
  X,
  Globe,
  Layers,
  ArrowRight,
  ArrowLeft,
  Disc3,
  Bookmark,
  Compass,
  Play,
  Flame,
  Volume2,
} from 'lucide-react';
import { API_URL, getAuthToken } from '@/lib/api';

interface DeckOnboardingProps {
  isOpen: boolean;
  onComplete: (prefs: { mode: string; languages: string[]; niches: string[] }) => void;
  onClose?: () => void;
  initialMode?: string;
  initialLanguages?: string[];
  initialNiches?: string[];
}

const AVAILABLE_NICHES = [
  { id: 'fitness', label: '💪 Fitness' },
  { id: 'food', label: '🍜 Food' },
  { id: 'comedy', label: '😂 Comedy' },
  { id: 'fashion', label: '👗 Fashion' },
  { id: 'business', label: '💼 Business' },
  { id: 'travel', label: '✈️ Travel' },
  { id: 'beauty', label: '💄 Beauty' },
  { id: 'devotional', label: '🙏 Devotional' },
  { id: 'tech', label: '💻 Tech' },
  { id: 'dance', label: '💃 Dance' },
  { id: 'narrative_edit', label: '🎞️ Creative Edit' },
  { id: 'romance_relationship', label: '💕 Romance' },
];

const INDIA_LANGUAGES = [
  { id: 'hi', label: '🇮🇳 Hindi' },
  { id: 'pa', label: '🌾 Punjabi' },
  { id: 'ta', label: '🌴 Tamil' },
  { id: 'te', label: '🌟 Telugu' },
  { id: 'ml', label: '🥥 Malayalam' },
  { id: 'kn', label: '🎯 Kannada' },
  { id: 'mr', label: '🦁 Marathi' },
  { id: 'gu', label: '🪔 Gujarati' },
  { id: 'bn', label: '🐯 Bengali' },
  { id: 'instrumental', label: '🎼 Instrumental' },
];

const GLOBAL_LANGUAGES = [
  { id: 'en', label: '🇬🇧 Global English' },
  { id: 'es', label: '🇪🇸 Spanish' },
  { id: 'pt', label: '🇧🇷 Portuguese (Brazil)' },
  { id: 'ko', label: '🇰🇷 Korean' },
  { id: 'instrumental', label: '🎼 BGM / Instrumental' },
];

export function DeckOnboarding({
  isOpen,
  onComplete,
  onClose,
  initialMode = 'india',
  initialLanguages = ['hi', 'pa'],
  initialNiches = [],
}: DeckOnboardingProps) {
  // Step 1: Walkthrough (How to use) | Step 2: Market & Languages | Step 3: Niches
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [mode, setMode] = useState<string>(initialMode === 'global' ? 'global' : 'india');
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(() => {
    if (initialLanguages && initialLanguages.length > 0) return initialLanguages;
    return initialMode === 'global' ? ['en', 'es'] : ['hi', 'pa'];
  });
  const [selectedNiches, setSelectedNiches] = useState<string[]>(initialNiches);

  if (!isOpen) return null;

  const currentLanguagesList = mode === 'india' ? INDIA_LANGUAGES : GLOBAL_LANGUAGES;

  const handleModeChange = (newMode: 'india' | 'global') => {
    if (newMode === mode) return;
    setMode(newMode);
    if (newMode === 'india') {
      setSelectedLanguages(['hi', 'en']);
    } else {
      setSelectedLanguages(['en', 'es']);
    }
  };

  const toggleLanguage = (langId: string) => {
    setSelectedLanguages((prev) => {
      if (prev.includes(langId)) {
        if (prev.length <= 1) return prev;
        return prev.filter((l) => l !== langId);
      }
      return [...prev, langId];
    });
  };

  const toggleNiche = (nicheId: string) => {
    setSelectedNiches((prev) => {
      if (prev.includes(nicheId)) {
        return prev.filter((n) => n !== nicheId);
      }
      if (prev.length >= 3) {
        return [...prev.slice(1), nicheId];
      }
      return [...prev, nicheId];
    });
  };

  const handleFinish = async () => {
    const prefs = {
      mode,
      languages: selectedLanguages.length > 0 ? selectedLanguages : (mode === 'india' ? ['hi', 'en'] : ['en']),
      niches: selectedNiches,
    };

    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_deck_mode', mode);
      localStorage.setItem('trendrop_deck_languages', JSON.stringify(prefs.languages));
      localStorage.setItem('trendrop_deck_niches', JSON.stringify(prefs.niches));
      localStorage.setItem('trendrop_deck_onboarded', 'true');
      localStorage.setItem('trendrop_deck_walkthrough_v1', 'true');
    }

    const token = getAuthToken();
    if (token) {
      try {
        await fetch(`${API_URL}/api/users/preferences`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            niches: prefs.niches,
            languages: prefs.languages,
            global_enabled: mode === 'global',
          }),
        });
      } catch {
        // Non-blocking fallback
      }
    }

    onComplete(prefs);
  };

  const handleClose = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_deck_onboarded', 'true');
      localStorage.setItem('trendrop_deck_walkthrough_v1', 'true');
    }
    onClose?.();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/75 backdrop-blur-md p-0 sm:p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-t-3xl sm:rounded-3xl p-6 shadow-2xl space-y-5 bg-surface text-foreground border border-border backdrop-blur-2xl relative overflow-hidden max-h-[92vh] overflow-y-auto">
        {/* Subtle Brand Accent Glow */}
        <div
          className="absolute -top-24 -left-24 w-52 h-52 rounded-full pointer-events-none opacity-20 blur-3xl"
          style={{ background: '#FF4D3D' }}
        />
        <div
          className="absolute -bottom-24 -right-24 w-52 h-52 rounded-full pointer-events-none opacity-20 blur-3xl"
          style={{ background: '#C7F23A' }}
        />

        {/* Top Header */}
        <div className="flex items-center justify-between relative z-10 border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_8px_rgba(255,77,61,0.6)]" />
            <span className="text-xs font-bold uppercase tracking-wider text-primary font-display">
              {step === 1 ? 'Quick Walkthrough' : `Deck Setup · Step ${step - 1} of 2`}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Step Indicators */}
            <div className="flex items-center gap-1.5">
              {[1, 2, 3].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStep(s as 1 | 2 | 3)}
                  aria-label={`Go to step ${s}`}
                  className={`h-1.5 rounded-full transition-all ${
                    step === s
                      ? 'w-6 bg-primary'
                      : 'w-2 bg-muted hover:bg-muted-foreground/40'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={handleClose}
              className="p-1 rounded-full text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── STEP 1: INTERACTIVE WALKTHROUGH ────────────────────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-4 relative z-10">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-primary" />
                <h3 className="text-xl font-extrabold text-foreground font-display tracking-tight">
                  How To Use The Vinyl Deck
                </h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Your fast radar for breakout audio trends before they saturate Instagram.
              </p>
            </div>

            {/* Gesture & Feature Guide Cards */}
            <div className="grid grid-cols-1 gap-2.5 pt-1">
              {/* Swipe Right */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-surface-2 border border-border transition-all">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-emerald-500/15 border border-emerald-500/30 text-emerald-500 dark:text-emerald-400">
                  <Bookmark className="w-5 h-5" />
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">👉 Swipe Right or Tap "Use It"</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-emerald-500/15 text-emerald-500 dark:text-emerald-400">SAVE</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Saves the audio to your <strong>Picks & Workspace</strong> with direct Instagram reels links ready for creating.
                  </p>
                </div>
              </div>

              {/* Swipe Left */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-surface-2 border border-border transition-all">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-rose-500/15 border border-rose-500/30 text-rose-500 dark:text-rose-400">
                  <X className="w-5 h-5" />
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">👈 Swipe Left or Tap "Skip"</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-rose-500/15 text-rose-500 dark:text-rose-400">PASS</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Passes to the next candidate track. The algorithm instantly tunes recommendations to your style.
                  </p>
                </div>
              </div>

              {/* Center Vinyl Tap */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-surface-2 border border-border transition-all">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-primary/15 border border-primary/30 text-primary">
                  <Disc3 className="w-5 h-5 animate-[spin_6s_linear_infinite]" />
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">🎵 Tap Vinyl Record</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-primary/15 text-primary">PREVIEW</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Tap the spinning vinyl in the center to play & preview the audio snippet with real-time waveform grooves.
                  </p>
                </div>
              </div>

              {/* Card Details & Live Reels */}
              <div className="flex items-start gap-3 p-3 rounded-2xl bg-surface-2 border border-border transition-all">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 bg-amber-500/15 border border-amber-500/30 text-amber-500">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">📊 Tap Card for Viral Intelligence</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Opens real creator reels, why this audio is surging, velocity curves, and recommended creator formats.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick Switcher Tip */}
            <div className="p-3 rounded-2xl bg-muted/40 border border-border/80 flex items-center gap-2.5">
              <Compass className="w-4 h-4 text-primary shrink-0" />
              <p className="text-[11px] text-muted-foreground leading-snug">
                <strong>Deck vs Feed:</strong> Use the top switcher anytime to toggle between fast 15-card <strong>Deck</strong> swiping and the full chronological <strong>Feed</strong>.
              </p>
            </div>

            {/* Step 1 Footer */}
            <div className="pt-2 flex items-center justify-between border-t border-border/60">
              <button
                type="button"
                onClick={handleFinish}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
              >
                Start Swiping Now
              </button>
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-5 py-2.5 rounded-full text-white text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5 shadow-md bg-primary hover:bg-primary/90"
              >
                <span>Personalize Feed</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: TARGET MARKET & LANGUAGES ──────────────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-4 relative z-10">
            <div className="space-y-1">
              <h3 className="text-xl font-extrabold text-foreground font-display tracking-tight">
                Target Audience & Languages
              </h3>
              <p className="text-xs text-muted-foreground">
                Select where your audience is based to load strictly matching sounds.
              </p>
            </div>

            {/* Market Toggle */}
            <div className="grid grid-cols-2 p-1 rounded-2xl bg-surface-2 border border-border">
              <button
                type="button"
                onClick={() => handleModeChange('india')}
                className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  mode === 'india'
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <span>🇮🇳 India Focus</span>
              </button>

              <button
                type="button"
                onClick={() => handleModeChange('global')}
                className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  mode === 'global'
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <span>🌍 Global Focus</span>
              </button>
            </div>

            {/* Languages Grid */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                  {mode === 'india' ? 'Indian Languages' : 'International Languages'}
                </span>
                <span className="text-[11px] text-muted-foreground font-mono">
                  {selectedLanguages.length} selected
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 max-h-[220px] overflow-y-auto pr-1">
                {currentLanguagesList.map((lang) => {
                  const isSelected = selectedLanguages.includes(lang.id);
                  return (
                    <button
                      key={lang.id}
                      type="button"
                      onClick={() => toggleLanguage(lang.id)}
                      className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                        isSelected
                          ? 'bg-surface border-primary text-foreground shadow-xs'
                          : 'bg-surface-2 border-border text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <span className="font-semibold">{lang.label}</span>
                      {isSelected && (
                        <div className="w-4 h-4 rounded-full flex items-center justify-center bg-primary text-white">
                          <Check className="w-2.5 h-2.5" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Step 2 Footer */}
            <div className="pt-2 flex items-center justify-between border-t border-border/60">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors font-medium flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Walkthrough</span>
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="px-5 py-2.5 rounded-full text-white text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5 shadow-md bg-primary hover:bg-primary/90"
              >
                <span>Next: Niches</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: CONTENT NICHES ────────────────────────────────────────────────────── */}
        {step === 3 && (
          <div className="space-y-4 relative z-10">
            <div className="space-y-1">
              <h3 className="text-xl font-extrabold text-foreground font-display tracking-tight">
                Select Niches (Up to 3)
              </h3>
              <p className="text-xs text-muted-foreground">
                Prioritizes breakout audio tailored to your content genre.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-[250px] overflow-y-auto pr-1">
              {AVAILABLE_NICHES.map((niche) => {
                const isSelected = selectedNiches.includes(niche.id);
                return (
                  <button
                    key={niche.id}
                    type="button"
                    onClick={() => toggleNiche(niche.id)}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                      isSelected
                        ? 'bg-surface border-primary text-foreground shadow-xs'
                        : 'bg-surface-2 border-border text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <span className="font-semibold">{niche.label}</span>
                    {isSelected && (
                      <div className="w-4 h-4 rounded-full flex items-center justify-center bg-primary text-white">
                        <Check className="w-2.5 h-2.5" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Step 3 Footer */}
            <div className="pt-2 flex items-center justify-between border-t border-border/60">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors font-medium flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
              <button
                type="button"
                onClick={handleFinish}
                className="px-6 py-2.5 rounded-full text-white text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5 shadow-md bg-primary hover:bg-primary/90"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Start Swiping The Deck</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
