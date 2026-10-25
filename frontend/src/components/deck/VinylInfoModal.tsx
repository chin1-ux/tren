import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ExternalLink,
  Calendar,
  RefreshCw,
  Layers,
  Sparkles,
  Globe,
  Film,
  Flame,
  Loader2,
  ChevronUp,
  ChevronDown,
  Check,
  Eye,
  Play,
  Pause,
  Volume2,
} from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack } from '@/lib/audio-resolver';
import { API_URL } from '@/lib/api';
import { TrenddropIcon } from '@/components/TrenddropLogo';

interface VinylInfoModalProps {
  trend: DeckTrend | null;
  onClose: () => void;
  onUse: () => void;
  onSkip: () => void;
}

export interface DeckReel {
  id: number;
  reel_id: string;
  owner_username: string;
  view_count: number;
  like_count: number;
  thumbnail_url?: string | null;
  video_url?: string | null;
  is_high_engagement?: boolean;
  instagram_url?: string | null;
  embed_url?: string | null;
}

function formatCount(n: number): string {
  if (n >= 10_000_000) return `${(n / 10_000_000).toFixed(1)}Cr`;
  if (n >= 100_000) return `${(n / 100_000).toFixed(1)}L`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(n);
}

function fmtDate(s: string | null | undefined): string {
  if (!s) return '—';
  try {
    const d = new Date(s);
    const datePart = d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
    const timePart = d.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
    return `${datePart}, ${timePart}`;
  } catch {
    return '—';
  }
}

// Brand Logo Palette Constants
const CORAL_FLAME = '#FF4D3D';
const ELECTRIC_LIME = '#C7F23A';

const STAGE_COLORS: Record<string, string> = {
  rising: '#FF4D3D',
  emerging: '#0EA5E9',
  peaked: '#D97706',
  resurging: '#C7F23A',
  expired: '#94A3B8',
};

// Check if string is a canned automated fallback string
const isCannedText = (s?: string | null) => {
  if (!s || s.trim().length < 8) return true;
  const l = s.toLowerCase();
  return (
    l.includes('currently driving high engagement') ||
    l.includes('automated fallback') ||
    l.includes('sporadic') ||
    l.includes('creators consistently use this sound') ||
    l.includes('fast-paced visual storytelling') ||
    l.includes('adapt the visual style') ||
    l.includes('popular audio for creator other reels') ||
    l.includes('popular in general creator reels') ||
    l.includes('resonates with') ||
    l.includes('positive content during these times') ||
    l.includes('emotional state') ||
    l.includes('sentiments about life') ||
    l.includes('evokes positive emotions') ||
    l.includes('popular choice for content creators') ||
    l.includes('cultural and emotional climate') ||
    l.includes('strong algorithmic audio momentum') ||
    l.includes('short creator clips that match') ||
    l.includes('film a high-retention') ||
    l.includes('post aesthetic clips or photos') ||
    l.includes('do not use this track expecting') ||
    l.includes('insufficient reel evidence') ||
    l.includes('sampled reels show completely discordant themes') ||
    l.includes('no indexed reel evidence')
  );
};

export function VinylInfoModal({ trend, onClose, onUse, onSkip }: VinylInfoModalProps) {
  if (!trend) return null;

  const stage = (trend.status || 'emerging').toLowerCase();
  const stageColor = STAGE_COLORS[stage] || CORAL_FLAME;
  const instagramUrl = trend.audio_id
    ? `https://www.instagram.com/reels/audio/${trend.audio_id}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(
        trend.audio_title + ' ' + trend.audio_artist
      )}`;

  const firstCaught = fmtDate(trend.first_detected_at);
  const lastCaught = fmtDate(trend.last_seen_at);

  const { currentTrack, isPlaying, playTrack, togglePlay } = useAudioStore();
  const isThisPlaying = Boolean(
    isPlaying && currentTrack && String(currentTrack.id) === String(trend.id)
  );

  const [rawReels, setRawReels] = useState<DeckReel[]>([]);
  const [activeReelIdx, setActiveReelIdx] = useState(0);
  const [mobileTab, setMobileTab] = useState<'intel' | 'reels'>('reels');
  const [isResolvingAudio, setIsResolvingAudio] = useState(false);
  const [isLoadingReels, setIsLoadingReels] = useState(true);

  // Fetch real top reels directly from backend for this trend's audio page
  useEffect(() => {
    if (!trend?.id) return;
    setIsLoadingReels(true);
    fetch(`${API_URL}/api/deck/${trend.id}/reels`)
      .then((res) => (res.ok ? res.json() : { reels: [] }))
      .then((data) => {
        setRawReels(data.reels || []);
        setActiveReelIdx(0);
      })
      .catch(() => setRawReels([]))
      .finally(() => setIsLoadingReels(false));
  }, [trend?.id]);

  // Prefetch audio preview track immediately
  useEffect(() => {
    if (!trend?.audio_title) return;
    resolveAudioTrack({
      id: trend.id,
      song: trend.audio_title,
      artist: trend.audio_artist,
      audioId: trend.audio_id,
      previewUrl: trend.preview_url || undefined,
    }).catch(() => {});
  }, [trend?.id, trend?.audio_title, trend?.audio_artist, trend?.audio_id, trend?.preview_url]);

  const handleAudioToggle = async () => {
    if (isThisPlaying) {
      togglePlay();
      return;
    }

    setIsResolvingAudio(true);
    try {
      const resolved = await resolveAudioTrack({
        id: trend.id,
        song: trend.audio_title,
        artist: trend.audio_artist,
        audioId: trend.audio_id,
        previewUrl: trend.preview_url || undefined,
      });

      if (!resolved.previewUrl) {
        if (trend.audio_id) {
          window.open(`https://www.instagram.com/reels/audio/${trend.audio_id}/`, '_blank');
        }
        return;
      }

      playTrack({
        id: trend.id,
        title: resolved.title,
        artist: resolved.artist,
        coverUrl: resolved.coverUrl || undefined,
        instagramAudioId: trend.audio_id || undefined,
        viralStartSec: resolved.viralStartSec,
        viralDurationSec: resolved.viralDurationSec,
        previewUrl: resolved.previewUrl,
        sourceType: resolved.sourceType,
      });
    } finally {
      setIsResolvingAudio(false);
    }
  };

  // Real Database Creator Intelligence (Preserve 100% original fields)
  const cleanWhy = !isCannedText(trend.why_this_works) ? trend.why_this_works?.trim() : null;
  const cleanConcept = !isCannedText(trend.ideal_content_description)
    ? trend.ideal_content_description?.trim()
    : null;
  const cleanUsed = !isCannedText(trend.used_for_note || trend.used_for)
    ? (trend.used_for_note || trend.used_for)?.trim()
    : null;
  const cleanHookBrief = trend.hook_brief?.trim() || null;
  const hasCreatorIntel = Boolean(cleanConcept || cleanWhy || cleanUsed || cleanHookBrief);

  const currentReel = rawReels[activeReelIdx] || null;

  return (
    <AnimatePresence>
      <motion.div
        key="vinyl-stage-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 60,
          background: 'rgba(250, 247, 242, 0.92)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '16px 12px',
        }}
        onClick={onClose}
      >
        {/* Subtle Ambient Brand Halo Glow (Coral #FF4D3D and Lime #C7F23A) */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            pointerEvents: 'none',
            background:
              'radial-gradient(circle at 20% 25%, rgba(255, 77, 61, 0.12) 0%, transparent 45%), radial-gradient(circle at 85% 75%, rgba(199, 242, 58, 0.15) 0%, transparent 45%)',
            zIndex: 0,
          }}
        />

        {/* Main Stage Card Container (Native Logo Palette: #FFFFFF, #FAF7F2, #FF4D3D, #C7F23A) */}
        <motion.div
          key="stage-container"
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ type: 'spring', stiffness: 360, damping: 28 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-4xl bg-[#FFFFFF] border-2 border-[#FF4D3D]/25 rounded-[32px] shadow-2xl overflow-hidden flex flex-col md:flex-row max-h-[92vh] relative z-10"
          style={{
            boxShadow: '0 24px 64px rgba(255, 77, 61, 0.14), 0 4px 16px rgba(0, 0, 0, 0.04)',
          }}
        >
          {/* ============================================================== */}
          {/* LEFT COLUMN: VINYL + AUDIO INTEL + REAL CREATOR INTELLIGENCE   */}
          {/* ============================================================== */}
          <div
            className={`w-full md:w-1/2 flex flex-col overflow-y-auto border-b md:border-b-0 md:border-r border-[#FF4D3D]/12 bg-[#FFFFFF] ${
              mobileTab === 'intel' ? 'flex' : 'hidden md:flex'
            }`}
            style={{ maxHeight: '92vh' }}
          >
            {/* Top Bar with Brand Logo, Stage Badge & Mobile Switcher */}
            <div className="flex items-center justify-between p-4 border-b border-[#FF4D3D]/10 bg-gradient-to-r from-[#FFFFFF] via-[#FFFDFB] to-[#FFF7F5]">
              <div className="flex items-center gap-2">
                <TrenddropIcon size={26} variant="coral" />
                <div
                  className="px-2.5 py-1 rounded-full flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider"
                  style={{
                    background: `${stageColor}15`,
                    border: `1.5px solid ${stageColor}40`,
                    color: stageColor,
                  }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: stageColor, boxShadow: `0 0 6px ${stageColor}` }}
                  />
                  <span>{trend.stage_label || trend.status}</span>
                </div>

                <div className="text-[11px] font-bold text-[#6B6B78] bg-[#FAF7F2] px-2.5 py-1 rounded-full border border-[#FF4D3D]/15 flex items-center gap-1.5">
                  <Film size={11} className="text-[#FF4D3D]" />
                  <span>{formatCount(trend.audio_use_count || 1000)} reels</span>
                </div>
              </div>

              {/* Mobile Tabs Switcher */}
              <div className="flex md:hidden items-center bg-[#FAF7F2] p-1 rounded-full border border-[#FF4D3D]/20">
                <button
                  onClick={() => setMobileTab('intel')}
                  className={`text-[11px] font-bold px-3 py-1 rounded-full transition-all ${
                    mobileTab === 'intel'
                      ? 'bg-[#FF4D3D] text-white shadow-sm'
                      : 'text-[#6B6B78] hover:text-[#0E0E10]'
                  }`}
                >
                  Intel
                </button>
                <button
                  onClick={() => setMobileTab('reels')}
                  className={`text-[11px] font-bold px-3 py-1 rounded-full transition-all flex items-center gap-1 ${
                    mobileTab === 'reels'
                      ? 'bg-[#FF4D3D] text-white shadow-sm'
                      : 'text-[#6B6B78] hover:text-[#0E0E10]'
                  }`}
                >
                  <span>Top Reels</span>
                  {rawReels.length > 0 && (
                    <span className="w-4 h-4 rounded-full bg-[#FF4D3D]/15 text-[#FF4D3D] text-[9px] font-bold flex items-center justify-center">
                      {rawReels.length}
                    </span>
                  )}
                </button>
              </div>

              {/* Close Button on Desktop */}
              <button
                onClick={onClose}
                className="hidden md:flex w-8 h-8 rounded-full bg-[#FAF7F2] hover:bg-[#FFF0EE] border border-[#FF4D3D]/20 items-center justify-center text-[#FF4D3D] hover:scale-105 transition-all cursor-pointer"
                title="Close"
              >
                <X size={15} />
              </button>
            </div>

            {/* Left Content Scroll Area */}
            <div className="p-5 space-y-3.5 overflow-y-auto flex-1 bg-[#FFFFFF]">
              {/* Designer Mini Vinyl Header */}
              <div className="flex items-center gap-4 bg-[#FAF7F2] p-4 rounded-2xl border border-[#FF4D3D]/15 shadow-xs">
                {/* Vinyl Record with Coral Rim and Lime Center Label */}
                <div
                  onClick={handleAudioToggle}
                  className={`relative w-16 h-16 shrink-0 rounded-full cursor-pointer flex items-center justify-center ${
                    isThisPlaying ? 'spinning-vinyl' : ''
                  }`}
                  style={{
                    background:
                      'radial-gradient(circle at 45% 45%, #2A2524 0%, #1A1616 40%, #120E0E 75%, #0B0808 100%)',
                    boxShadow: '0 6px 18px rgba(255, 77, 61, 0.25)',
                    border: '2.5px solid #FF4D3D',
                    animation: isThisPlaying ? 'vinyl-spin 18s linear infinite' : 'none',
                  }}
                  title="Click to preview audio"
                >
                  {/* Subtle Vinyl Grooves */}
                  <div className="absolute inset-1.5 rounded-full border border-white/10 pointer-events-none" />
                  <div className="absolute inset-3 rounded-full border border-white/10 pointer-events-none" />

                  {/* Brand Lime Center Label with Audio Play / Pause */}
                  <div className="w-7 h-7 rounded-full bg-[#C7F23A] border-2 border-[#FFFFFF] flex items-center justify-center text-[#0E0E10] shadow-sm">
                    {isResolvingAudio ? (
                      <Loader2 size={11} className="animate-spin text-[#0E0E10]" />
                    ) : isThisPlaying ? (
                      <Pause size={11} fill="#0E0E10" />
                    ) : (
                      <Play size={11} fill="#0E0E10" className="ml-0.5" />
                    )}
                  </div>
                </div>

                {/* Track Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-extrabold text-[#0E0E10] truncate font-display">
                    {trend.audio_title}
                  </h3>
                  <p className="text-xs text-[#6B6B78] truncate mt-0.5 font-medium">
                    {trend.audio_artist}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] text-[#203000] bg-[#C7F23A] px-2 py-0.5 rounded-md font-extrabold uppercase tracking-wider shadow-xs border border-[#B5E025]">
                      {trend.language?.toUpperCase() || 'AUDIO'}
                    </span>
                    {trend.niche && (
                      <span className="text-[10px] text-[#6B6B78] bg-[#FFFFFF] px-2 py-0.5 rounded-md font-semibold border border-[#FF4D3D]/15">
                        #{trend.niche}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* 4-Fact Telemetry Cells (Parity with Original Card) */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#FAF7F2] p-2.5 rounded-xl border border-[#FF4D3D]/10 flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-[#9A9AA8]">
                    <Calendar size={11} className="text-[#FF4D3D]" />
                    <span>First Caught</span>
                  </div>
                  <span className="text-[11px] font-extrabold text-[#0E0E10] truncate">
                    {firstCaught}
                  </span>
                </div>

                <div className="bg-[#FAF7F2] p-2.5 rounded-xl border border-[#FF4D3D]/10 flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-[#9A9AA8]">
                    <RefreshCw size={11} className="text-[#FF4D3D]" />
                    <span>Last Verified</span>
                  </div>
                  <span className="text-[11px] font-extrabold text-[#0E0E10] truncate">
                    {lastCaught}
                  </span>
                </div>

                <div className="bg-[#FAF7F2] p-2.5 rounded-xl border border-[#FF4D3D]/10 flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-[#9A9AA8]">
                    <Layers size={11} className="text-[#FF4D3D]" />
                    <span>Instagram Uses</span>
                  </div>
                  <span className="text-[11px] font-extrabold text-[#0E0E10]">
                    {formatCount(trend.audio_use_count || 1000)} reels
                  </span>
                </div>

                <div className="bg-[#FAF7F2] p-2.5 rounded-xl border border-[#FF4D3D]/10 flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-[#9A9AA8]">
                    <Flame size={11} className="text-[#FF4D3D]" />
                    <span>Opportunity</span>
                  </div>
                  <span className="text-[11px] font-extrabold text-[#FF4D3D]">
                    {Math.round(trend.opportunity_score || 85)} / 100
                  </span>
                </div>
              </div>

              {/* Real Database Creator Intelligence (Content Concept + Why This Works + Hook) */}
              {hasCreatorIntel ? (
                <div className="bg-[#FFF8F7] p-4 rounded-2xl border border-[#FF4D3D]/20 shadow-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-[#FF4D3D]/10 pb-2">
                    <div className="flex items-center gap-2">
                      <Sparkles size={14} className="text-[#FF4D3D]" />
                      <span className="text-xs font-black uppercase tracking-wider text-[#FF4D3D]">
                        Creator Intelligence
                      </span>
                    </div>
                    {trend.niche && (
                      <span className="text-[10px] font-extrabold text-[#203000] bg-[#C7F23A] px-2 py-0.5 rounded-md border border-[#B5E025]">
                        #{trend.niche}
                      </span>
                    )}
                  </div>

                  {/* 💡 Content Concept */}
                  {cleanConcept && (
                    <div className="space-y-1">
                      <p className="text-[10px] font-extrabold text-[#FF4D3D] uppercase tracking-wider flex items-center gap-1">
                        <span>💡 Content Concept</span>
                      </p>
                      <p className="text-xs text-[#0E0E10] font-semibold leading-relaxed">
                        {cleanConcept}
                      </p>
                    </div>
                  )}

                  {/* 🪝 Hook (First 3 Seconds) / Why This Works */}
                  {cleanWhy && cleanWhy !== cleanConcept && (
                    <div className="space-y-1 pt-1">
                      <p className="text-[10px] font-extrabold text-[#6B6B78] uppercase tracking-wider flex items-center gap-1">
                        <span>🪝 Hook (First 3 Seconds)</span>
                      </p>
                      <p className="text-xs text-[#2C2C35] font-medium leading-relaxed italic bg-white/60 p-2.5 rounded-xl border border-[#FF4D3D]/10">
                        "{cleanWhy}"
                      </p>
                    </div>
                  )}

                  {/* 🎬 Hook Brief */}
                  {cleanHookBrief && (
                    <div className="space-y-1 pt-1">
                      <p className="text-[10px] font-extrabold text-[#6B6B78] uppercase tracking-wider flex items-center gap-1">
                        <span>🎬 Hook Brief</span>
                      </p>
                      <p className="text-xs text-[#4A4A55] font-normal leading-relaxed">
                        {cleanHookBrief}
                      </p>
                    </div>
                  )}

                  {/* ⚡ Used For (Fallback if no concept or why exists) */}
                  {!cleanConcept && !cleanWhy && cleanUsed && (
                    <div className="space-y-1 pt-1">
                      <p className="text-[10px] font-extrabold text-[#FF4D3D] uppercase tracking-wider">
                        ⚡ How Creators Use This Sound
                      </p>
                      <p className="text-xs text-[#0E0E10] font-semibold leading-relaxed">
                        {cleanUsed}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-[#FAF7F2] p-3.5 rounded-2xl border border-[#FF4D3D]/12 space-y-1.5 text-xs">
                  <div className="text-[10px] font-black uppercase tracking-wider text-[#FF4D3D]">
                    Viral Trajectory
                  </div>
                  <p className="text-xs text-[#2C2C35] leading-relaxed font-medium">
                    High algorithmic velocity audio currently pacing across Indian social feeds with{' '}
                    {formatCount(trend.audio_use_count || 1000)} active creator reels.
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      onUse();
                      onClose();
                    }}
                    className="py-3 px-4 rounded-xl bg-[#FF4D3D] hover:bg-[#e03d2d] text-white font-extrabold text-xs shadow-lg shadow-[#FF4D3D]/25 flex items-center justify-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                  >
                    <Check size={14} className="stroke-[3]" />
                    <span>Use It (Save)</span>
                  </button>

                  <button
                    onClick={() => {
                      onSkip();
                      onClose();
                    }}
                    className="py-3 px-4 rounded-xl bg-[#FAF7F2] hover:bg-[#F0ECE4] text-[#6B6B78] hover:text-[#0E0E10] border border-[#FF4D3D]/15 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <X size={14} />
                    <span>Pass</span>
                  </button>
                </div>

                <a
                  href={instagramUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 rounded-xl bg-[#FAF7F2] hover:bg-[#FFF0EE] border border-[#FF4D3D]/25 text-[#FF4D3D] font-extrabold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <ExternalLink size={12} />
                  <span>Open Audio on Instagram</span>
                </a>
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* RIGHT COLUMN: IN-APP REEL SCROLLER (THE REELS DISPLAY PART)     */}
          {/* ============================================================== */}
          <div
            className={`w-full md:w-1/2 flex flex-col bg-[#FAF7F2] ${
              mobileTab === 'reels' ? 'flex' : 'hidden md:flex'
            }`}
            style={{ maxHeight: '92vh' }}
          >
            {/* Header: Scroller Controls */}
            <div className="flex items-center justify-between p-4 border-b border-[#FF4D3D]/10 bg-gradient-to-r from-[#FFFDFB] to-[#FFFFFF]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase tracking-wider text-[#0E0E10] flex items-center gap-1.5">
                  <Film size={14} className="text-[#FF4D3D]" />
                  <span>Top Audio Page Reels</span>
                </span>
                {rawReels.length > 0 && (
                  <span className="text-[11px] font-bold text-[#FF4D3D] bg-[#FFF0EE] px-2.5 py-0.5 rounded-full border border-[#FF4D3D]/25">
                    {activeReelIdx + 1} of {rawReels.length}
                  </span>
                )}
              </div>

              {/* Navigation Up / Down Buttons */}
              {rawReels.length > 1 && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setActiveReelIdx((prev) => Math.max(0, prev - 1))}
                    disabled={activeReelIdx === 0}
                    className="w-7 h-7 rounded-full bg-[#FFFFFF] hover:bg-[#FFF0EE] border border-[#FF4D3D]/20 disabled:opacity-30 disabled:pointer-events-none text-[#0E0E10] flex items-center justify-center transition-colors cursor-pointer shadow-xs"
                    title="Previous Reel"
                  >
                    <ChevronUp size={16} />
                  </button>
                  <button
                    onClick={() =>
                      setActiveReelIdx((prev) => Math.min(rawReels.length - 1, prev + 1))
                    }
                    disabled={activeReelIdx === rawReels.length - 1}
                    className="w-7 h-7 rounded-full bg-[#FFFFFF] hover:bg-[#FFF0EE] border border-[#FF4D3D]/20 disabled:opacity-30 disabled:pointer-events-none text-[#0E0E10] flex items-center justify-center transition-colors cursor-pointer shadow-xs"
                    title="Next Reel"
                  >
                    <ChevronDown size={16} />
                  </button>
                </div>
              )}

              {/* Close Button on Mobile in Reels view */}
              <button
                onClick={onClose}
                className="flex md:hidden w-8 h-8 rounded-full bg-[#FFFFFF] border border-[#FF4D3D]/20 items-center justify-center text-[#FF4D3D] cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            {/* In-App Reel Video Stage (Light Ivory & Coral Silhouette) */}
            <div className="flex-1 p-4 flex flex-col items-center justify-center overflow-y-auto relative min-h-[380px] sm:min-h-[460px] bg-[#FAF7F2]">
              {isLoadingReels ? (
                <div className="flex flex-col items-center justify-center gap-3 text-[#6B6B78] py-12">
                  <Loader2 size={24} className="animate-spin text-[#FF4D3D]" />
                  <span className="text-xs font-semibold text-[#0E0E10]">
                    Loading top reels from audio page...
                  </span>
                  <span className="text-[11px] text-[#6B6B78]">
                    Extracting highest engagement benchmark reels
                  </span>
                </div>
              ) : currentReel ? (
                <div className="w-full max-w-[340px] flex flex-col items-center gap-3">
                  {/* Smartphone Styled Video Stage Frame */}
                  <div className="w-full relative aspect-[9/15] max-h-[460px] bg-[#FFFFFF] rounded-[24px] overflow-hidden border-4 border-[#FFFFFF] shadow-2xl ring-2 ring-[#FF4D3D]/20 flex flex-col justify-between">
                    {/* Native Instagram Embed iframe or HTML5 Video */}
                    {currentReel.video_url ? (
                      <video
                        key={currentReel.video_url}
                        src={currentReel.video_url}
                        controls
                        autoPlay
                        loop
                        playsInline
                        className="w-full h-full object-cover"
                        poster={
                          currentReel.reel_id
                            ? `${API_URL}/api/deck/thumb/${currentReel.reel_id}`
                            : currentReel.thumbnail_url || undefined
                        }
                      />
                    ) : currentReel.reel_id ? (
                      <iframe
                        src={`https://www.instagram.com/reel/${currentReel.reel_id}/embed/`}
                        title={`Instagram reel by ${currentReel.owner_username}`}
                        className="w-full h-full border-0"
                        allow="autoplay; encrypted-media"
                        allowFullScreen
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-[#FFF8F7]">
                        <Film size={32} className="text-[#FF4D3D] mb-3" />
                        <p className="text-xs font-bold text-[#0E0E10]">Top Reel Preview</p>
                        <p className="text-[11px] text-[#6B6B78] mt-1">
                          @{currentReel.owner_username}
                        </p>
                      </div>
                    )}

                    {/* Top Overlay Pill: Views & High Engagement Indicator */}
                    <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
                      <div className="bg-white/95 backdrop-blur-md px-3 py-1 rounded-full text-[11px] font-bold text-[#0E0E10] flex items-center gap-1.5 border border-[#FF4D3D]/20 shadow-sm">
                        <Eye size={11} className="text-[#FF4D3D]" />
                        <span>{formatCount(currentReel.view_count)} views</span>
                      </div>

                      {currentReel.is_high_engagement && (
                        <div className="bg-[#C7F23A] text-[#1E2E00] px-2.5 py-0.5 rounded-full text-[10px] font-black flex items-center gap-1 border border-[#B5E025] shadow-sm">
                          <Flame size={10} fill="#1E2E00" />
                          <span>TOP BENCHMARK</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Reel Creator & Deep Link Footer */}
                  <div className="w-full flex items-center justify-between px-1">
                    <div className="text-left">
                      <span className="text-[11px] text-[#6B6B78] font-medium">Top creator</span>
                      <p className="text-xs font-extrabold text-[#0E0E10]">
                        @{currentReel.owner_username}
                      </p>
                    </div>

                    <a
                      href={
                        currentReel.instagram_url ||
                        `https://www.instagram.com/reel/${currentReel.reel_id}/`
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3.5 py-1.5 rounded-xl bg-[#FF4D3D] hover:bg-[#e03d2d] text-white text-xs font-extrabold flex items-center gap-1.5 transition-colors shadow-xs"
                    >
                      <span>Watch on IG</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>

                  {/* Thumbnail Carousel for Fast Jumping Between Reels */}
                  {rawReels.length > 1 && (
                    <div className="w-full flex items-center gap-1.5 overflow-x-auto py-1 px-0.5 scrollbar-none">
                      {rawReels.map((r, idx) => (
                        <button
                          key={r.id || idx}
                          onClick={() => setActiveReelIdx(idx)}
                          className={`relative shrink-0 w-11 h-14 rounded-lg overflow-hidden border-2 transition-all cursor-pointer ${
                            activeReelIdx === idx
                              ? 'border-[#FF4D3D] scale-105 shadow-md ring-1 ring-[#FF4D3D]'
                              : 'border-white/80 opacity-60 hover:opacity-100'
                          }`}
                        >
                          <img
                            src={
                              r.reel_id
                                ? `${API_URL}/api/deck/thumb/${r.reel_id}`
                                : r.thumbnail_url || '/icons/sound-placeholder.png'
                            }
                            alt={`Reel ${idx + 1}`}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-x-0 bottom-0 bg-[#0E0E10]/80 text-[8px] font-black text-white text-center py-0.5">
                            {formatCount(r.view_count)}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center gap-3 text-center p-8 text-[#6B6B78]">
                  <div className="w-12 h-12 rounded-full bg-[#FFF0EE] flex items-center justify-center text-[#FF4D3D]">
                    <Film size={22} />
                  </div>
                  <p className="text-sm font-bold text-[#0E0E10]">Early Viral Audio</p>
                  <p className="text-xs text-[#6B6B78] max-w-xs">
                    Top reels for this sound are being indexed directly from Instagram. Tap below to
                    view on Instagram!
                  </p>
                  <a
                    href={instagramUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 px-4 py-2 rounded-xl bg-[#FF4D3D] text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-[#FF4D3D]/25"
                  >
                    <span>Open Audio Page</span>
                    <ExternalLink size={13} />
                  </a>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
