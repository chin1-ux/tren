import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Copy, Check, Hash, MessageSquare, Flame, Wand2, RefreshCw } from 'lucide-react';
import { generateReelCaption, type ReelCaptionResponse } from '@/lib/api';
import { toast } from 'sonner';

interface ReelCaptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  trend: {
    id?: number | string;
    song?: string;
    artist?: string;
    audio_title?: string;
    audio_artist?: string;
    niche?: string | null;
    used_for?: string | null;
    why_this_works?: string | null;
  } | null;
}

const QUICK_IDEAS = [
  { label: '🧥 OOTD / Outfit', text: 'Styling a vintage oversized leather jacket with chunky boots for a night street walk' },
  { label: '✨ GRWM / Glowup', text: 'Get ready with me for a Saturday night out, full outfit and makeup transition' },
  { label: '😂 Relatable POV', text: 'POV: Me telling myself I will only buy one thing vs leaving with the whole store' },
  { label: '💪 Workout / Fitness', text: 'High energy leg day workout routine focusing on progressive overload squats' },
  { label: '✈️ Travel & Vibe', text: 'Golden hour cinematic moments exploring hidden street cafes downtown' },
  { label: '💡 Tips & Hack', text: '3 game-changing creator styling rules I wish I knew sooner' },
];

const VIBES = [
  { id: 'aesthetic', label: '✨ Aesthetic' },
  { id: 'relatable', label: '💬 Relatable' },
  { id: 'high-energy', label: '🔥 High Energy' },
  { id: 'humor', label: '😂 Humorous' },
];

export function ReelCaptionModal({ isOpen, onClose, trend }: ReelCaptionModalProps) {
  if (!isOpen || !trend) return null;

  const audioTitle = trend.song || trend.audio_title || 'Trending Audio';
  const audioArtist = trend.artist || trend.audio_artist || 'Original Artist';
  const niche = trend.niche || 'lifestyle';

  const [description, setDescription] = useState('');
  const [selectedVibe, setSelectedVibe] = useState('aesthetic');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ReelCaptionResponse | null>(null);
  const [copiedType, setCopiedType] = useState<'all' | 'caption' | 'tags' | null>(null);

  const handleGenerate = async (customDesc?: string) => {
    const descToUse = (customDesc !== undefined ? customDesc : description).trim();
    setIsLoading(true);
    try {
      const res = await generateReelCaption({
        trend_id: trend.id,
        audio_title: audioTitle,
        audio_artist: audioArtist,
        user_description: descToUse || trend.used_for || `${niche} content video with this sound`,
        niche,
        vibe: selectedVibe,
      });
      setResult(res);
      toast.success('Viral caption & reach hashtags generated!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to generate caption. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string, type: 'all' | 'caption' | 'tags') => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedType(type);
      toast.success(
        type === 'all'
          ? 'Full caption & hashtags copied! Ready to paste into Instagram 🚀'
          : type === 'caption'
          ? 'Caption copied!'
          : 'Hashtags copied!'
      );
      setTimeout(() => setCopiedType(null), 2200);
    });
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-md overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-lg bg-card text-card-foreground border border-border/80 rounded-2xl shadow-2xl overflow-hidden my-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border/60 bg-muted/30">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold tracking-tight">Reel Caption & Reach Generator</h3>
                <p className="text-[11px] text-muted-foreground truncate max-w-[260px] sm:max-w-[320px]">
                  🎵 {audioTitle} · {audioArtist}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
            {/* Input Section */}
            {!result ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-foreground mb-1">
                    What is your reel specifically about?
                  </label>
                  <p className="text-[11px] text-muted-foreground mb-2">
                    Mention your outfit, trend angle, POV, or what you're doing so the AI crafts authentic, high-converting copy.
                  </p>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. vintage oversized black leather jacket with red heels, walking downtown at night..."
                    className="w-full text-xs p-3 rounded-xl bg-background border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all resize-none placeholder:text-muted-foreground/60"
                  />
                </div>

                {/* Quick Ideas Chips */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Quick Reel Ideas (tap to apply):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_IDEAS.map((idea) => (
                      <button
                        key={idea.label}
                        type="button"
                        onClick={() => setDescription(idea.text)}
                        className="text-[10.5px] font-medium px-2.5 py-1 rounded-full border border-border/70 bg-background/60 hover:bg-muted hover:border-primary/40 transition-all text-left"
                      >
                        {idea.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Vibe Selector */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                    Choose Tone & Vibe:
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                    {VIBES.map((v) => (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => setSelectedVibe(v.id)}
                        className={`text-xs font-semibold py-2 px-2 rounded-xl border text-center transition-all ${
                          selectedVibe === v.id
                            ? 'bg-primary text-primary-foreground border-primary shadow-xs'
                            : 'bg-background border-border text-foreground/80 hover:bg-muted'
                        }`}
                      >
                        {v.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Generate Button */}
                <button
                  onClick={() => handleGenerate()}
                  disabled={isLoading}
                  className="w-full py-3 px-4 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-xs flex items-center justify-center gap-2 shadow-md transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Crafting Viral Caption & Hashtags...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      <span>Generate Viral Caption & Hashtags</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              /* Results View */
              <div className="space-y-4">
                {/* Scroll-stopping Hook Banner */}
                {result.hook && (
                  <div className="p-3 rounded-xl bg-primary/10 border border-primary/25">
                    <div className="flex items-center gap-1.5 text-primary text-[10px] font-bold uppercase tracking-wider mb-1">
                      <Flame className="w-3.5 h-3.5" />
                      <span>Scroll-Stopping Hook (First 3s)</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground leading-snug">
                      "{result.hook}"
                    </p>
                  </div>
                )}

                {/* Caption Body */}
                <div className="p-3.5 rounded-xl bg-background border border-border">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      Instagram Caption Body
                    </span>
                    <button
                      onClick={() => copyToClipboard(result.caption, 'caption')}
                      className="text-[10.5px] font-semibold text-primary hover:underline flex items-center gap-1"
                    >
                      {copiedType === 'caption' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Caption</span>
                    </button>
                  </div>
                  <p className="text-xs text-foreground/90 whitespace-pre-line leading-relaxed font-sans">
                    {result.caption}
                  </p>
                </div>

                {/* High Reach Hashtags */}
                <div className="p-3.5 rounded-xl bg-background border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <Hash className="w-3 h-3" />
                      <span>High-Reach SEO Hashtags ({result.hashtags.length})</span>
                    </span>
                    <button
                      onClick={() => copyToClipboard(result.hashtags.join(' '), 'tags')}
                      className="text-[10.5px] font-semibold text-primary hover:underline flex items-center gap-1"
                    >
                      {copiedType === 'tags' ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Tags</span>
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                    {result.hashtags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="text-[10.5px] font-mono px-2 py-0.5 rounded-md bg-muted/60 border border-border/50 text-foreground/80"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Primary Action Button: 1-Tap Copy All */}
                <div className="space-y-2 pt-1">
                  <button
                    onClick={() => copyToClipboard(result.full_post_text, 'all')}
                    className="w-full py-3 px-4 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-xs flex items-center justify-center gap-2 shadow-lg transition-all active:scale-[0.98]"
                  >
                    {copiedType === 'all' ? (
                      <>
                        <Check className="w-4 h-4 text-white" />
                        <span>Copied to Clipboard!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        <span>📋 Copy Full Caption + Hashtags</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setResult(null)}
                    className="w-full py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center gap-1.5"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Tweak Details & Regenerate</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
