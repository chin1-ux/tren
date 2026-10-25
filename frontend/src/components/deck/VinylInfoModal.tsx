import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ExternalLink,
  Calendar,
  RefreshCw,
  Disc,
  Layers,
  Sparkles,
  Globe,
  Play,
  Pause,
  Volume2,
  Film,
  Heart,
  Flame,
  Loader2,
  ChevronUp,
  ChevronDown,
  Check,
  Eye,
  Zap,
} from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack } from '@/lib/audio-resolver';
import { API_URL } from '@/lib/api';

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

// Brand Logo Palette Colors
const STAGE_COLORS: Record<string, string> = {
  rising: '#FF4D3D',
  emerging: '#0EA5E9',
  peaked: '#D97706',
  resurging: '#C7F23A',
  expired: '#94A3B8',
};

// Synthesize the unwritten creator pattern formula
function extractEmergentPattern(trend: DeckTrend) {
  const why = (trend.why_this_works || '').toLowerCase();
  const concept = (trend.ideal_content_description || '').toLowerCase();
  const niche = (trend.niche || '').toLowerCase();

  if (
    why.includes('meme') ||
    why.includes('shakal') ||
    why.includes('ew') ||
    why.includes('quote') ||
    why.includes('funny') ||
    why.includes('relatable') ||
    concept.includes('meme') ||
    niche.includes('comedy')
  ) {
    return {
      name: "The 'Prove Them Wrong' Quotation Meme",
      type: 'Meme Hook + Transformation',
      steps: [
        {
          title: 'The Hook (0.0s – 1.8s)',
          desc: "Text overlay quoting a doubter: 🗣️ 'You don't look like...' or 'Ew shakal dekhi hai apni?'",
          badge: 'HOOK',
        },
        {
          title: 'The Pivot (1.8s – 2.4s)',
          desc: '0.5s cut to a thinking monkey or blank stare reaction meme right as music suspends.',
          badge: 'MEME PAUSE',
        },
        {
          title: 'The Payoff (2.4s+)',
          desc: 'Beat drop cuts to your high-contrast transformation (fitness, glow-up, outfit flex).',
          badge: 'BEAT DROP',
        },
      ],
    };
  }

  if (
    why.includes('transition') ||
    why.includes('navratri') ||
    why.includes('outfit') ||
    why.includes('fashion') ||
    why.includes('looks') ||
    concept.includes('transition') ||
    niche.includes('fashion') ||
    niche.includes('dance')
  ) {
    return {
      name: 'The Beat-Drop Reveal Transition',
      type: 'Fast-Cut Visual Transition',
      steps: [
        {
          title: 'The Setup (0.0s – 1.5s)',
          desc: 'Casual look, looking at camera or hand covering the lens before the beat.',
          badge: 'SETUP',
        },
        {
          title: 'The Pivot (1.5s – 2.2s)',
          desc: 'Quick spin, snap, or head turn matching the rhythm buildup.',
          badge: 'SPIN / SNAP',
        },
        {
          title: 'The Glamour Reveal (2.2s+)',
          desc: 'Hard cut on drum drop into full ethnic/festive attire or high-energy choreography.',
          badge: 'GLAMOUR DROP',
        },
      ],
    };
  }

  if (
    why.includes('gym') ||
    why.includes('workout') ||
    why.includes('fitness') ||
    why.includes('motivation') ||
    concept.includes('gym') ||
    niche.includes('fitness')
  ) {
    return {
      name: "The 'Silent Work' Contrast Reel",
      type: 'POV Transformation & Discipline',
      steps: [
        {
          title: 'The Dilemma (0.0s – 1.5s)',
          desc: "Relatable text: 'They told me to quit' or 'Day 1 vs Day 100'.",
          badge: 'TEXT HOOK',
        },
        {
          title: 'The Grind (1.5s – 3.0s)',
          desc: 'Fast 0.4s rhythmic cuts of hard gym sets synced to the bassline.',
          badge: 'FAST CUTS',
        },
        {
          title: 'The Flex (3.0s+)',
          desc: 'Clean physique check / mirror flex on the vocal drop.',
          badge: 'PEAK FLEX',
        },
      ],
    };
  }

  return {
    name: 'The High-Retention Sync Pattern',
    type: 'Rhythmic Audio Sync',
    steps: [
      {
        title: 'The Hook (0.0s – 2.0s)',
        desc: trend.hook_brief || 'Bold statement or question in first 2 seconds to stop the scroll.',
        badge: 'HOOK',
      },
      {
        title: 'The Build (2.0s – 3.5s)',
        desc: '2 to 3 fast kinetic cuts (0.5s each) building visual tension with the audio.',
        badge: 'RHYTHM BUILD',
      },
      {
        title: 'The Payoff (3.5s+)',
        desc: trend.ideal_content_description || 'Clear payoff, punchline, or aesthetic reveal.',
        badge: 'PAYOFF',
      },
    ],
  };
}

export function VinylInfoModal({ trend, onClose, onUse, onSkip }: VinylInfoModalProps) {
  if (!trend) return null;

  const stage = (trend.status || 'emerging').toLowerCase();
  const stageColor = STAGE_COLORS[stage] || '#FF4D3D';
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
  const [mobileTab, setMobileTab] = useState<'blueprint' | 'reels'>('blueprint');
  const [isResolvingAudio, setIsResolvingAudio] = useState(false);
  const [isLoadingReels, setIsLoadingReels] = useState(true);

  // Fetch real scraped top reels for this trend directly from backend
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

  // Prefetch audio track immediately upon opening modal
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

  const pattern = extractEmergentPattern(trend);
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
          background: 'rgba(250, 247, 242, 0.88)',
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
        {/* Subtle Ambient Brand Glow (Coral #FF4D3D and Lime #C7F23A) */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            pointerEvents: 'none',
            background:
              'radial-gradient(circle at 25% 30%, rgba(255, 77, 61, 0.12) 0%, transparent 50%), radial-gradient(circle at 80% 70%, rgba(199, 242, 58, 0.14) 0%, transparent 50%)',
            zIndex: 0,
          }}
        />

        {/* Main Stage Card Container (Native Logo Palette: #FFFFFF, #FAF7F2, #FF4D3D, #C7F23A) */}
        <motion.div
          key="stage-container"
          initial={{ opacity: 0, scale: 0.94, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 15 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-4xl bg-[#FFFFFF] border-2 border-[#FF4D3D]/20 rounded-[28px] shadow-2xl overflow-hidden flex flex-col md:flex-row max-h-[92vh] relative z-10"
          style={{
            boxShadow: '0 20px 60px rgba(255, 77, 61, 0.12), 0 4px 16px rgba(0, 0, 0, 0.04)',
          }}
        >
          {/* ============================================================== */}
          {/* LEFT COLUMN: VINYL + AUDIO INTEL + EMERGENT PATTERN BLUEPRINT   */}
          {/* ============================================================== */}
          <div
            className={`w-full md:w-1/2 flex flex-col overflow-y-auto border-b md:border-b-0 md:border-r border-[#FF4D3D]/12 bg-[#FFFFFF] ${
              mobileTab === 'blueprint' ? 'flex' : 'hidden md:flex'
            }`}
            style={{ maxHeight: '92vh' }}
          >
            {/* Top Bar with Stage Badge, Audio Count & Mobile Toggle */}
            <div className="flex items-center justify-between p-4 border-b border-[#FF4D3D]/10 bg-[#FFFDFB]">
              <div className="flex items-center gap-2">
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
                  onClick={() => setMobileTab('blueprint')}
                  className={`text-[11px] font-bold px-3 py-1 rounded-full transition-all ${
                    mobileTab === 'blueprint'
                      ? 'bg-[#FF4D3D] text-white shadow-sm'
                      : 'text-[#6B6B78] hover:text-[#0E0E10]'
                  }`}
                >
                  Blueprint
                </button>
                <button
                  onClick={() => setMobileTab('reels')}
                  className={`text-[11px] font-bold px-3 py-1 rounded-full transition-all flex items-center gap-1 ${
                    mobileTab === 'reels'
                      ? 'bg-[#FF4D3D] text-white shadow-sm'
                      : 'text-[#6B6B78] hover:text-[#0E0E10]'
                  }`}
                >
                  <span>Reels</span>
                  <span className="w-4 h-4 rounded-full bg-[#FF4D3D]/15 text-[#FF4D3D] text-[9px] font-bold flex items-center justify-center">
                    {rawReels.length}
                  </span>
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
            <div className="p-5 space-y-4 overflow-y-auto flex-1 bg-[#FFFFFF]">
              {/* Vinyl Player Header */}
              <div className="flex items-center gap-4 bg-[#FAF7F2] p-4 rounded-2xl border border-[#FF4D3D]/15 shadow-xs">
                {/* Spinning Mini Vinyl */}
                <div
                  onClick={handleAudioToggle}
                  className={`relative w-16 h-16 shrink-0 rounded-full cursor-pointer flex items-center justify-center ${
                    isThisPlaying ? 'spinning-vinyl' : ''
                  }`}
                  style={{
                    background:
                      'radial-gradient(circle at 45% 45%, #252528 0%, #161618 35%, #0F0F11 75%, #080809 100%)',
                    boxShadow: '0 6px 18px rgba(0,0,0,0.25)',
                    border: '2px solid rgba(255, 77, 61, 0.4)',
                    animation: isThisPlaying ? 'vinyl-spin 18s linear infinite' : 'none',
                  }}
                  title="Click to preview audio"
                >
                  <div className="w-7 h-7 rounded-full bg-[#FAF7F2] border-2 border-[#FF4D3D] flex items-center justify-center text-[#FF4D3D]">
                    {isResolvingAudio ? (
                      <Loader2 size={11} className="animate-spin text-[#FF4D3D]" />
                    ) : isThisPlaying ? (
                      <Pause size={11} fill="#FF4D3D" />
                    ) : (
                      <Play size={11} fill="#FF4D3D" className="ml-0.5" />
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
                    <span className="text-[10px] text-[#2E4000] bg-[#C7F23A] px-2 py-0.5 rounded-md font-extrabold uppercase tracking-wider shadow-xs">
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

              {/* ⚡ Emergent Pattern Formula Box (Warm Ivory + Brand Coral + Lime) */}
              <div className="bg-[#FFF9F8] p-4 rounded-2xl border border-[#FF4D3D]/20 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-[#FF4D3D] text-white flex items-center justify-center shadow-xs">
                      <Zap size={13} fill="white" />
                    </div>
                    <span className="text-xs font-black uppercase tracking-wider text-[#0E0E10]">
                      Emergent Creator Blueprint
                    </span>
                  </div>
                  <span className="text-[10px] font-extrabold text-[#FF4D3D] bg-[#FFF0EE] border border-[#FF4D3D]/30 px-2 py-0.5 rounded-md">
                    {pattern.type}
                  </span>
                </div>

                <div className="text-xs font-bold text-[#0E0E10]">
                  {pattern.name}
                </div>

                {/* 3 Step Formula */}
                <div className="space-y-2 pt-1">
                  {pattern.steps.map((s, idx) => (
                    <div
                      key={idx}
                      className="bg-[#FFFFFF] p-3 rounded-xl border border-[#FF4D3D]/10 shadow-xs flex items-start gap-3"
                    >
                      <div className="w-5 h-5 rounded-full bg-[#FF4D3D] text-white text-[10px] font-black shrink-0 flex items-center justify-center mt-0.5 shadow-xs">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-extrabold text-[#0E0E10]">
                            {s.title}
                          </span>
                          <span className="text-[9px] font-black uppercase text-[#FF4D3D] bg-[#FFF0EE] px-1.5 py-0.5 rounded">
                            {s.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#4A4A55] mt-0.5 leading-relaxed font-normal">
                          {s.desc}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Why This Works & Timeline */}
              <div className="bg-[#FAF7F2] p-3.5 rounded-2xl border border-[#FF4D3D]/12 space-y-2 text-xs">
                <div className="text-[10px] font-black uppercase tracking-wider text-[#FF4D3D]">
                  Viral Intelligence
                </div>
                <p className="text-xs text-[#2C2C35] leading-relaxed font-medium">
                  {trend.why_this_works ||
                    `High algorithmic velocity sound trending across Indian social feeds with ${formatCount(
                      trend.audio_use_count || 1000
                    )} creator reels.`}
                </p>
                <div className="flex items-center justify-between pt-2 border-t border-[#FF4D3D]/10 text-[10px] text-[#6B6B78]">
                  <span>First caught: <strong>{firstCaught}</strong></span>
                  <span>Last verified: <strong>{lastCaught}</strong></span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      onUse();
                      onClose();
                    }}
                    className="py-3 px-4 rounded-xl bg-[#FF4D3D] hover:bg-[#e03d2d] text-white font-extrabold text-xs shadow-lg shadow-[#FF4D3D]/30 flex items-center justify-center gap-1.5 transition-all active:scale-95 cursor-pointer"
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
          {/* RIGHT COLUMN: IN-APP REEL SCROLLER & WATCHER                   */}
          {/* ============================================================== */}
          <div
            className={`w-full md:w-1/2 flex flex-col bg-[#FAF7F2] ${
              mobileTab === 'reels' ? 'flex' : 'hidden md:flex'
            }`}
            style={{ maxHeight: '92vh' }}
          >
            {/* Header: Scroller Controls */}
            <div className="flex items-center justify-between p-4 border-b border-[#FF4D3D]/10 bg-[#FFFDFB]">
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

            {/* In-App Reel Video Stage */}
            <div className="flex-1 p-4 flex flex-col items-center justify-center overflow-y-auto relative min-h-[380px] sm:min-h-[460px] bg-[#FAF7F2]">
              {isLoadingReels ? (
                <div className="flex flex-col items-center justify-center gap-3 text-[#6B6B78] py-12">
                  <Loader2 size={24} className="animate-spin text-[#FF4D3D]" />
                  <span className="text-xs font-medium">Loading top reels from audio page...</span>
                </div>
              ) : currentReel ? (
                <div className="w-full max-w-[340px] flex flex-col items-center gap-3">
                  {/* Reel Player Frame (Phone Proportioned 9:15) */}
                  <div className="w-full relative aspect-[9/15] max-h-[460px] bg-[#0E0E10] rounded-2xl overflow-hidden border-2 border-[#0E0E10] shadow-xl flex flex-col justify-between">
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
                      <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-zinc-900">
                        <Film size={32} className="text-[#FF4D3D] mb-3" />
                        <p className="text-xs font-bold text-white">Reel Preview</p>
                        <p className="text-[11px] text-zinc-400 mt-1">
                          @{currentReel.owner_username}
                        </p>
                      </div>
                    )}

                    {/* Top Overlay Pill: Views & Creator */}
                    <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
                      <div className="bg-[#0E0E10]/80 backdrop-blur-md px-2.5 py-1 rounded-full text-[11px] font-bold text-white flex items-center gap-1.5 border border-white/20">
                        <Eye size={11} className="text-[#FF4D3D]" />
                        <span>{formatCount(currentReel.view_count)} views</span>
                      </div>

                      {currentReel.is_high_engagement && (
                        <div className="bg-[#FF4D3D] text-white px-2.5 py-0.5 rounded-full text-[10px] font-black flex items-center gap-1 shadow-md">
                          <Flame size={10} fill="white" />
                          <span>TOP REEL</span>
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
                      className="px-3 py-1.5 rounded-xl bg-[#FF4D3D] hover:bg-[#e03d2d] text-white text-xs font-extrabold flex items-center gap-1.5 transition-colors shadow-xs"
                    >
                      <span>Watch on IG</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center gap-3 text-center p-8 text-[#6B6B78]">
                  <div className="w-12 h-12 rounded-full bg-[#FFF0EE] flex items-center justify-center text-[#FF4D3D]">
                    <Film size={22} />
                  </div>
                  <p className="text-sm font-bold text-[#0E0E10]">Breakout audio just sighted</p>
                  <p className="text-xs text-[#6B6B78] max-w-xs">
                    This sound is in its early virality window. Be one of the first creators to post with
                    this sound!
                  </p>
                  <a
                    href={instagramUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 px-4 py-2 rounded-xl bg-[#FF4D3D] text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-[#FF4D3D]/30"
                  >
                    <span>Use Audio on Instagram</span>
                    <ExternalLink size={13} />
                  </a>
                </div>
              )}
            </div>

            {/* Reel Scroller Thumbnails Rail (Quick switcher) */}
            {rawReels.length > 1 && (
              <div className="p-3 border-t border-[#FF4D3D]/10 bg-[#FFFDFB] flex items-center justify-center gap-2 overflow-x-auto">
                {rawReels.map((r, idx) => (
                  <button
                    key={r.id || r.reel_id || idx}
                    onClick={() => setActiveReelIdx(idx)}
                    className={`relative w-9 h-12 rounded-lg overflow-hidden border-2 transition-all shrink-0 cursor-pointer ${
                      activeReelIdx === idx
                        ? 'border-[#FF4D3D] scale-105 shadow-md'
                        : 'border-[#FF4D3D]/20 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <img
                      src={
                        r.reel_id
                          ? `${API_URL}/api/deck/thumb/${r.reel_id}`
                          : r.thumbnail_url || ''
                      }
                      alt={r.owner_username}
                      className="w-full h-full object-cover"
                      referrerPolicy="no-referrer"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
