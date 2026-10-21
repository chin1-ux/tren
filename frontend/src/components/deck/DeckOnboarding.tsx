import React, { useState } from 'react';
import { Check, Sparkles, X, Globe, Layers, ArrowRight } from 'lucide-react';
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
  const [step, setStep] = useState<1 | 2>(1);
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
    // Reset to sensible defaults for that market to prevent cross-contamination
    if (newMode === 'india') {
      setSelectedLanguages(['hi', 'en']);
    } else {
      setSelectedLanguages(['en', 'es']);
    }
  };

  const toggleLanguage = (langId: string) => {
    setSelectedLanguages((prev) => {
      if (prev.includes(langId)) {
        // Prevent deselecting everything
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
        return [...prev.slice(1), nicheId]; // Keep max 3
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

    // Save locally
    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_deck_mode', mode);
      localStorage.setItem('trendrop_deck_languages', JSON.stringify(prefs.languages));
      localStorage.setItem('trendrop_deck_niches', JSON.stringify(prefs.niches));
      localStorage.setItem('trendrop_deck_onboarded', 'true');
    }

    // Save to API if token present
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

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-md p-0 sm:p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-t-3xl sm:rounded-3xl p-6 shadow-2xl space-y-6"
        style={{
          background: '#FFF8F5',
          border: '1px solid rgba(255,77,61,0.18)',
        }}
      >
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#FF4D3D' }} />
            <span className="text-xs font-bold uppercase tracking-wider text-[#FF4D3D]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Personalize Your Deck · Step {step} of 2
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded-full text-[#9A9AA8] hover:text-[#0E0E10] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Step 1: Market & Languages (Logically Connected) */}
        {step === 1 && (
          <div className="space-y-5">
            <div className="space-y-1">
              <h3 className="text-xl font-extrabold text-[#0E0E10]" style={{ fontFamily: "'Bricolage Grotesque', system-ui" }}>
                Target Audience & Languages
              </h3>
              <p className="text-xs text-[#6B6B78]" style={{ fontFamily: 'Inter, sans-serif' }}>
                Select where your audience is based to load strictly matching sounds.
              </p>
            </div>

            {/* Market Toggle: India vs Global */}
            <div
              className="grid grid-cols-2 p-1 rounded-2xl border"
              style={{ background: 'rgba(0,0,0,0.03)', borderColor: 'rgba(0,0,0,0.06)' }}
            >
              <button
                type="button"
                onClick={() => handleModeChange('india')}
                className="py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                style={
                  mode === 'india'
                    ? {
                        background: '#FF4D3D',
                        color: '#fff',
                        boxShadow: '0 4px 12px rgba(255,77,61,0.3)',
                      }
                    : {
                        color: '#6B6B78',
                      }
                }
              >
                <span>🇮🇳 India Focus</span>
              </button>

              <button
                type="button"
                onClick={() => handleModeChange('global')}
                className="py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                style={
                  mode === 'global'
                    ? {
                        background: '#FF4D3D',
                        color: '#fff',
                        boxShadow: '0 4px 12px rgba(255,77,61,0.3)',
                      }
                    : {
                        color: '#6B6B78',
                      }
                }
              >
                <span>🌍 Global Focus</span>
              </button>
            </div>

            {/* Language Selection strictly for the chosen market */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-[#6B6B78] uppercase tracking-wider" style={{ fontFamily: 'Inter, sans-serif' }}>
                  {mode === 'india' ? 'Indian Languages' : 'International Languages'}
                </span>
                <span className="text-[11px] text-[#9A9AA8]">
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
                      className="px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all"
                      style={
                        isSelected
                          ? {
                              background: '#FFFFFF',
                              borderColor: '#FF4D3D',
                              color: '#0E0E10',
                              boxShadow: '0 2px 8px rgba(255,77,61,0.12)',
                            }
                          : {
                              background: 'rgba(0,0,0,0.02)',
                              borderColor: 'rgba(0,0,0,0.06)',
                              color: '#6B6B78',
                            }
                      }
                    >
                      <span className="font-semibold">{lang.label}</span>
                      {isSelected && (
                        <div
                          className="w-4 h-4 rounded-full flex items-center justify-center text-white"
                          style={{ background: '#FF4D3D' }}
                        >
                          <Check className="w-2.5 h-2.5" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Footer Navigation */}
            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={handleFinish}
                className="text-xs text-[#9A9AA8] hover:text-[#0E0E10] transition-colors"
                style={{ fontFamily: 'Inter, sans-serif' }}
              >
                Skip for now
              </button>
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-6 py-2.5 rounded-full text-white text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5"
                style={{
                  background: '#FF4D3D',
                  boxShadow: '0 4px 14px rgba(255,77,61,0.3)',
                  fontFamily: "'Bricolage Grotesque', system-ui",
                }}
              >
                <span>Next: Choose Niches</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Content Niches (Pick up to 3) */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="space-y-1">
              <h3 className="text-xl font-extrabold text-[#0E0E10]" style={{ fontFamily: "'Bricolage Grotesque', system-ui" }}>
                Select Niches (Up to 3)
              </h3>
              <p className="text-xs text-[#6B6B78]" style={{ fontFamily: 'Inter, sans-serif' }}>
                Prioritizes breakout audio tailored to your content genre.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-[260px] overflow-y-auto pr-1">
              {AVAILABLE_NICHES.map((niche) => {
                const isSelected = selectedNiches.includes(niche.id);
                return (
                  <button
                    key={niche.id}
                    type="button"
                    onClick={() => toggleNiche(niche.id)}
                    className="px-3 py-2.5 rounded-xl border text-xs font-medium text-left flex items-center justify-between transition-all"
                    style={
                      isSelected
                        ? {
                            background: '#FFFFFF',
                            borderColor: '#FF4D3D',
                            color: '#0E0E10',
                            boxShadow: '0 2px 8px rgba(255,77,61,0.12)',
                          }
                        : {
                            background: 'rgba(0,0,0,0.02)',
                            borderColor: 'rgba(0,0,0,0.06)',
                            color: '#6B6B78',
                          }
                    }
                  >
                    <span className="font-semibold">{niche.label}</span>
                    {isSelected && (
                      <div
                        className="w-4 h-4 rounded-full flex items-center justify-center text-white"
                        style={{ background: '#FF4D3D' }}
                      >
                        <Check className="w-2.5 h-2.5" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Footer Navigation */}
            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-[#9A9AA8] hover:text-[#0E0E10] transition-colors"
                style={{ fontFamily: 'Inter, sans-serif' }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleFinish}
                className="px-6 py-2.5 rounded-full text-white text-xs font-bold transition-all active:scale-95 flex items-center gap-1.5"
                style={{
                  background: '#FF4D3D',
                  boxShadow: '0 4px 14px rgba(255,77,61,0.3)',
                  fontFamily: "'Bricolage Grotesque', system-ui",
                }}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Start Swiping</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
