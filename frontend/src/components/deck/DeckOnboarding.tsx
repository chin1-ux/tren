import React, { useState } from 'react';
import { Check, Globe, Sparkles, X } from 'lucide-react';
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
  { id: 'hi', label: 'Hindi' },
  { id: 'en', label: 'English' },
  { id: 'pa', label: 'Punjabi' },
  { id: 'ta', label: 'Tamil' },
  { id: 'te', label: 'Telugu' },
  { id: 'ml', label: 'Malayalam' },
  { id: 'kn', label: 'Kannada' },
  { id: 'instrumental', label: 'Instrumental' },
];

const GLOBAL_EXTRA_LANGUAGES = [
  { id: 'es', label: 'Spanish' },
  { id: 'pt', label: 'Portuguese' },
  { id: 'ko', label: 'Korean' },
  { id: 'ar', label: 'Arabic' },
  { id: 'other', label: 'Other Global' },
];

export function DeckOnboarding({
  isOpen,
  onComplete,
  onClose,
  initialMode = 'india',
  initialLanguages = ['hi', 'en'],
  initialNiches = [],
}: DeckOnboardingProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [mode, setMode] = useState<string>(initialMode);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(initialLanguages);
  const [selectedNiches, setSelectedNiches] = useState<string[]>(initialNiches);

  if (!isOpen) return null;

  const toggleLanguage = (langId: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(langId) ? prev.filter((l) => l !== langId) : [...prev, langId]
    );
  };

  const toggleNiche = (nicheId: string) => {
    setSelectedNiches((prev) => {
      if (prev.includes(nicheId)) {
        return prev.filter((n) => n !== nicheId);
      }
      if (prev.length >= 3) {
        return [...prev.slice(1), nicheId]; // Keep max 3
      }
      return [...prev, nicheId];
    });
  };

  const handleFinish = async () => {
    const prefs = {
      mode,
      languages: selectedLanguages.length > 0 ? selectedLanguages : ['hi', 'en'],
      niches: selectedNiches,
    };

    // Save locally
    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_deck_mode', mode);
      localStorage.setItem('trendrop_deck_languages', JSON.stringify(prefs.languages));
      localStorage.setItem('trendrop_deck_niches', JSON.stringify(prefs.niches));
      localStorage.setItem('trendrop_deck_onboarded', 'true');
    }

    // Attempt save to API if token present
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
      } catch (err) {
        // Non-blocking fallback
      }
    }

    onComplete(prefs);
  };

  const availableLangs = mode === 'india'
    ? INDIA_LANGUAGES
    : [...INDIA_LANGUAGES, ...GLOBAL_EXTRA_LANGUAGES];

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-sm p-0 sm:p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-t-3xl sm:rounded-3xl p-6 text-zinc-100 shadow-2xl space-y-6">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF3B5C]" />
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              Personalize Your Feed · Tap {step}/3
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-full text-zinc-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Step 1: Mode Selection */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-xl font-bold font-display text-white">Select Regional Scope</h3>
              <p className="text-xs text-zinc-400">
                Choose whether you want verified India trends or Global breakout audios.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                onClick={() => setMode('india')}
                className={`p-4 rounded-2xl border text-left transition-all ${
                  mode === 'india'
                    ? 'border-[#FF3B5C] bg-[#FF3B5C]/10 text-white shadow-lg'
                    : 'border-zinc-800 bg-zinc-950/60 text-zinc-300 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">🇮🇳</span>
                  {mode === 'india' && <Check className="w-4 h-4 text-[#FF3B5C]" />}
                </div>
                <div className="font-bold text-sm">India Focus</div>
                <div className="text-[11px] text-zinc-400 mt-0.5">Top Indian languages</div>
              </button>

              <button
                onClick={() => setMode('global')}
                className={`p-4 rounded-2xl border text-left transition-all ${
                  mode === 'global'
                    ? 'border-[#FF3B5C] bg-[#FF3B5C]/10 text-white shadow-lg'
                    : 'border-zinc-800 bg-zinc-950/60 text-zinc-300 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">🌍</span>
                  {mode === 'global' && <Check className="w-4 h-4 text-[#FF3B5C]" />}
                </div>
                <div className="font-bold text-sm">Global Focus</div>
                <div className="text-[11px] text-zinc-400 mt-0.5">Cross-cultural audios</div>
              </button>
            </div>

            <div className="pt-4 flex items-center justify-between">
              <button
                onClick={handleFinish}
                className="text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Skip for now
              </button>
              <button
                onClick={() => setStep(2)}
                className="px-6 py-2.5 rounded-full bg-[#FF3B5C] hover:bg-[#E02A4A] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
              >
                Next: Languages
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Language Selection */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-xl font-bold font-display text-white">Select Audio Languages</h3>
              <p className="text-xs text-zinc-400">
                Choose the languages you want to hear in your deck stack.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-[260px] overflow-y-auto pr-1">
              {availableLangs.map((lang) => {
                const isSelected = selectedLanguages.includes(lang.id);
                return (
                  <button
                    key={lang.id}
                    onClick={() => toggleLanguage(lang.id)}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                      isSelected
                        ? 'border-[#FF3B5C] bg-[#FF3B5C]/15 text-white'
                        : 'border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <span>{lang.label}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-[#FF3B5C]" />}
                  </button>
                );
              })}
            </div>

            <div className="pt-4 flex items-center justify-between">
              <button
                onClick={() => setStep(1)}
                className="text-xs font-mono text-zinc-400 hover:text-zinc-200"
              >
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="px-6 py-2.5 rounded-full bg-[#FF3B5C] hover:bg-[#E02A4A] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
              >
                Next: Niches
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Niche Selection (up to 3) */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-xl font-bold font-display text-white">Select Niches (Up to 3)</h3>
              <p className="text-xs text-zinc-400">
                Prioritizes audio styles that align with your content niche.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-[260px] overflow-y-auto pr-1">
              {AVAILABLE_NICHES.map((niche) => {
                const isSelected = selectedNiches.includes(niche.id);
                return (
                  <button
                    key={niche.id}
                    onClick={() => toggleNiche(niche.id)}
                    className={`px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all ${
                      isSelected
                        ? 'border-[#FF3B5C] bg-[#FF3B5C]/15 text-white'
                        : 'border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <span>{niche.label}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-[#FF3B5C]" />}
                  </button>
                );
              })}
            </div>

            <div className="pt-4 flex items-center justify-between">
              <button
                onClick={() => setStep(2)}
                className="text-xs font-mono text-zinc-400 hover:text-zinc-200"
              >
                Back
              </button>
              <button
                onClick={handleFinish}
                className="px-6 py-2.5 rounded-full bg-[#FF3B5C] hover:bg-[#E02A4A] text-white text-xs font-semibold shadow-md transition-all active:scale-95 flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Start Swiping
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
