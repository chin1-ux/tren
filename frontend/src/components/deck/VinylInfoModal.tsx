import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack, isInstagramCdnUrlExpired } from '@/lib/audio-resolver';
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

const STAGE_COLORS: Record<string, string> = {
  rising: '#FF4D3D',
  emerging: '#FF6B4A',
  peaked: '#FF9F1C',
  resurging: '#C7F23A',
  expired: '#94A3B8',
};

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
  const [activeReel, setActiveReel] = useState<DeckReel | null>(null);

  // Active view tab for mobile viewports ('vinyl' | 'left' | 'right')
  const [mobileTab, setMobileTab] = useState<'vinyl' | 'left' | 'right'>('vinyl');

  // Fetch real scraped reels for this trend directly from backend
  useEffect(() => {
    if (!trend?.id) return;
    fetch(`${API_URL}/api/deck/${trend.id}/reels`)
      .then((res) => (res.ok ? res.json() : { reels: [] }))
      .then((data) => {
        setRawReels(data.reels || []);
      })
      .catch(() => setRawReels([]));
  }, [trend?.id]);

  // Use only 100% real scraped reels from DB (no simulations/fabrications)
  // Symmetrically balance reels across left and right wings
  const leftReels =
    rawReels.length === 1
      ? rawReels
      : rawReels.length === 2
      ? [rawReels[0]]
      : rawReels.slice(0, Math.ceil(rawReels.length / 2));

  const rightReels =
    rawReels.length <= 1
      ? []
      : rawReels.length === 2
      ? [rawReels[1]]
      : rawReels.slice(Math.ceil(rawReels.length / 2), 6);

  // Check if why_this_works and used_for are genuine (strict zero canned / zero synthetic strings)
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
      l.includes('cultural and emotional climate')
    );
  };

  const isWhyGenuine = !isCannedText(trend.why_this_works);
  const isUsedForGenuine = !isCannedText(trend.used_for_note || trend.used_for);

  const [isResolvingAudio, setIsResolvingAudio] = useState(false);
  const [videoFailedIds, setVideoFailedIds] = useState<Set<number | string>>(new Set());

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
        {/* Subtle Brand Ambient Glow */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            pointerEvents: 'none',
            background:
              'radial-gradient(circle at 50% 50%, rgba(255, 77, 61, 0.10) 0%, rgba(199, 242, 58, 0.08) 40%, transparent 70%)',
            zIndex: 0,
          }}
        />

        {/* 3-Column Pop-Out Stage */}
        <div
          style={{
            position: 'relative',
            zIndex: 1,
            width: '100%',
            maxWidth: 880,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            margin: 'auto',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* ============================================================== */}
          {/* LEFT WING: 3 POPPING OUT REELS (EMERGES FROM VINYL)             */}
          {/* ============================================================== */}
          {leftReels.length > 0 && (
            <motion.div
              key="left-wing-reels"
              initial={{ opacity: 0, x: 220, scale: 0.15 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 220, scale: 0.15 }}
              transition={{ type: 'spring', stiffness: 280, damping: 25, mass: 0.8 }}
              className="hidden md:flex"
              style={{
                width: 140,
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transformOrigin: 'right center',
              }}
            >
              {leftReels.map((reel, idx) => (
                <motion.div
                  key={reel.id || reel.reel_id || idx}
                  initial={{ opacity: 0, x: 180, scale: 0.15 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: 180, scale: 0.15 }}
                  transition={{
                    delay: idx * 0.05,
                    type: 'spring',
                    stiffness: 300,
                    damping: 24,
                  }}
                >
                  <ReelPreviewCard
                    reel={reel}
                    index={idx + 1}
                    onSelect={() => setActiveReel(reel)}
                  />
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* ============================================================== */}
          {/* MIDDLE COLUMN: BLACK VINYL RECORD + AUDIO TELEMETRY             */}
          {/* ============================================================== */}
          <motion.div
            key="middle-stage-vinyl"
            initial={{ opacity: 0, scale: 0.92, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 15 }}
            transition={{ type: 'spring', stiffness: 350, damping: 28 }}
            style={{
              width: '100%',
              maxWidth: 440,
              maxHeight: '92vh',
              background: '#FFFFFF',
              borderRadius: 24,
              border: '2px solid rgba(255, 77, 61, 0.18)',
              boxShadow: '0 16px 50px rgba(255, 77, 61, 0.12)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              flexShrink: 0,
            }}
          >
            {/* Top Bar with Stage Badge & Mobile View Switcher */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px 8px',
                borderBottom: '1px solid rgba(255, 77, 61, 0.10)',
                background: '#FFFDFB',
              }}
            >
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  background: `${stageColor}15`,
                  border: `1.5px solid ${stageColor}40`,
                  borderRadius: 99,
                  padding: '2px 10px',
                }}
              >
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: stageColor,
                    boxShadow: `0 0 6px ${stageColor}`,
                  }}
                />
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    color: stageColor,
                    letterSpacing: 1,
                    textTransform: 'uppercase',
                    fontFamily: 'Inter, sans-serif',
                  }}
                >
                  {trend.stage_label || trend.status}
                </span>
              </div>

              {/* Mobile View Switcher Tabs (Only if reels exist on mobile) */}
              {(leftReels.length > 0 || rightReels.length > 0) && (
                <div
                  className="flex md:hidden"
                  style={{
                    alignItems: 'center',
                    gap: 3,
                    background: '#FAF7F2',
                    padding: '2px 4px',
                    borderRadius: 99,
                    border: '1px solid rgba(255, 77, 61, 0.15)',
                  }}
                >
                  {leftReels.length > 0 && (
                    <button
                      onClick={() => setMobileTab('left')}
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: 99,
                        border: 'none',
                        background: mobileTab === 'left' ? '#FF4D3D' : 'transparent',
                        color: mobileTab === 'left' ? '#fff' : '#6B6B78',
                        cursor: 'pointer',
                      }}
                    >
                      Reels
                    </button>
                  )}
                  <button
                    onClick={() => setMobileTab('vinyl')}
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: 99,
                      border: 'none',
                      background: mobileTab === 'vinyl' ? '#FF4D3D' : 'transparent',
                      color: mobileTab === 'vinyl' ? '#fff' : '#6B6B78',
                      cursor: 'pointer',
                    }}
                  >
                    Audio
                  </button>
                  {rightReels.length > 0 && (
                    <button
                      onClick={() => setMobileTab('right')}
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: 99,
                        border: 'none',
                        background: mobileTab === 'right' ? '#FF4D3D' : 'transparent',
                        color: mobileTab === 'right' ? '#fff' : '#6B6B78',
                        cursor: 'pointer',
                      }}
                    >
                      More Reels
                    </button>
                  )}
                </div>
              )}

              {/* Close Button */}
              <button
                onClick={onClose}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: '50%',
                  background: '#FFF0EE',
                  border: '1.5px solid rgba(255, 77, 61, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  color: '#FF4D3D',
                }}
                title="Close"
              >
                <X size={15} />
              </button>
            </div>

            {/* Mobile Tab Active Display (Only on mobile viewports < md) */}
            <div className="flex md:hidden flex-col">
              {mobileTab === 'left' ? (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    padding: 16,
                    maxHeight: '75vh',
                    overflowY: 'auto',
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#0E0E10', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Film size={13} color="#FF4D3D" />
                    <span>Breakout Reels</span>
                  </div>
                  {leftReels.map((reel, idx) => (
                    <ReelPreviewCard key={reel.id || reel.reel_id || idx} reel={reel} index={idx + 1} onSelect={() => setActiveReel(reel)} />
                  ))}
                </div>
              ) : mobileTab === 'right' ? (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    padding: 16,
                    maxHeight: '75vh',
                    overflowY: 'auto',
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#0E0E10', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Flame size={13} color="#FF4D3D" />
                    <span>More Reels</span>
                  </div>
                  {rightReels.map((reel, idx) => (
                    <ReelPreviewCard key={reel.id || reel.reel_id || idx} reel={reel} index={idx + leftReels.length + 1} onSelect={() => setActiveReel(reel)} />
                  ))}
                </div>
              ) : null}
            </div>

            {/* Center Vinyl & Telemetry Content (Always visible on desktop md+, or on mobile when mobileTab === 'vinyl') */}
            <div
              className={mobileTab === 'vinyl' ? 'flex flex-col' : 'hidden md:flex flex-col'}
              style={{
                padding: '12px 18px 18px',
                gap: 10,
                overflowY: 'auto',
                maxHeight: '82vh',
              }}
            >
                {/* Authentic Black Vinyl Record with Audio Name in Center Label */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '2px 0 6px',
                    position: 'relative',
                  }}
                >
                  {/* Subtle soft backdrop shadow */}
                  <div
                    style={{
                      position: 'absolute',
                      width: 135,
                      height: 135,
                      borderRadius: '50%',
                      background: 'radial-gradient(circle, rgba(0,0,0,0.12) 0%, transparent 70%)',
                      filter: 'blur(6px)',
                    }}
                  />

                  {/* Black Vinyl Record Disc */}
                  <div
                    className={isThisPlaying ? 'spinning-vinyl' : ''}
                    style={{
                      position: 'relative',
                      width: 132,
                      height: 132,
                      borderRadius: '50%',
                      background:
                        'radial-gradient(circle at 45% 45%, #252528 0%, #161618 35%, #0F0F11 75%, #080809 100%)',
                      boxShadow:
                        '0 10px 28px rgba(0,0,0,0.30), inset 0 0 0 1px rgba(255,255,255,0.12)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      animation: 'vinyl-spin 18s linear infinite',
                      animationPlayState: isThisPlaying ? 'running' : 'paused',
                      willChange: 'transform',
                    }}
                  >
                    {/* Concentric etched vinyl sound grooves */}
                    <div
                      style={{
                        position: 'absolute',
                        inset: 6,
                        borderRadius: '50%',
                        border: '1px solid rgba(255,255,255,0.10)',
                        boxShadow:
                          'inset 0 0 0 6px rgba(255,255,255,0.04), inset 0 0 0 12px rgba(0,0,0,0.5), inset 0 0 0 18px rgba(255,255,255,0.06), inset 0 0 0 24px rgba(0,0,0,0.4)',
                        pointerEvents: 'none',
                      }}
                    />

                    {/* Realistic Gloss Sheen Angle */}
                    <div
                      style={{
                        position: 'absolute',
                        inset: 0,
                        borderRadius: '50%',
                        background:
                          'linear-gradient(135deg, rgba(255,255,255,0.14) 0%, transparent 40%, rgba(255,255,255,0.08) 60%, transparent 100%)',
                        pointerEvents: 'none',
                      }}
                    />

                    {/* Center Vinyl Label: Displays Audio Name Instead of App Name */}
                    <div
                      style={{
                        width: 58,
                        height: 58,
                        borderRadius: '50%',
                        background: '#FAF7F2',
                        border: '2px solid #FF4D3D',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '4px',
                        textAlign: 'center',
                        position: 'relative',
                        zIndex: 2,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 8.5,
                          fontWeight: 800,
                          color: '#0E0E10',
                          lineHeight: 1.1,
                          fontFamily: "'Bricolage Grotesque', system-ui",
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          textTransform: 'capitalize',
                        }}
                        title={trend.audio_title}
                      >
                        {trend.audio_title}
                      </span>

                      {/* Center Spindle Hole */}
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: '#FFFFFF',
                          border: '1.5px solid #FF4D3D',
                          marginTop: 2,
                        }}
                      />
                    </div>
                  </div>

                  {/* Audio Title & Artist */}
                  <div style={{ textAlign: 'center', marginTop: 8, maxWidth: '94%' }}>
                    <h2
                      style={{
                        fontFamily: "'Bricolage Grotesque', system-ui",
                        fontWeight: 800,
                        fontSize: 18,
                        color: '#0E0E10',
                        lineHeight: 1.2,
                        margin: 0,
                      }}
                    >
                      {trend.audio_title}
                    </h2>
                    <p
                      style={{
                        fontSize: 12,
                        color: '#6B6B78',
                        marginTop: 2,
                        marginBottom: 0,
                        fontFamily: 'Inter, sans-serif',
                        fontWeight: 600,
                      }}
                    >
                      {trend.audio_artist}
                    </p>
                  </div>
                </div>

                {/* Audio Player Preview Bar */}
                <div
                  style={{
                    background:
                      'linear-gradient(135deg, rgba(255,77,61,0.08) 0%, rgba(199,242,58,0.12) 100%)',
                    border: '1.5px solid rgba(255,77,61,0.18)',
                    borderRadius: 14,
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button
                      onClick={handleAudioToggle}
                      disabled={isResolvingAudio}
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: '50%',
                        background: '#FF4D3D',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: isResolvingAudio ? 'wait' : 'pointer',
                        boxShadow: '0 3px 10px rgba(255,77,61,0.35)',
                        color: '#fff',
                        flexShrink: 0,
                      }}
                      title={isThisPlaying ? 'Pause preview' : 'Play preview'}
                    >
                      {isResolvingAudio ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : isThisPlaying ? (
                        <Pause size={17} fill="#fff" />
                      ) : (
                        <Play size={17} fill="#fff" style={{ marginLeft: 2 }} />
                      )}
                    </button>
                    <div>
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: '#0E0E10',
                          fontFamily: 'Inter, sans-serif',
                        }}
                      >
                        {isThisPlaying ? 'Playing Audio Preview' : 'Listen to Audio'}
                      </div>
                      <div
                        style={{
                          fontSize: 10,
                          color: '#6B6B78',
                          fontFamily: 'Inter, sans-serif',
                        }}
                      >
                        30s Spotify / Instagram preview
                      </div>
                    </div>
                  </div>
                  <div style={{ color: '#FF4D3D' }}>
                    <Volume2 size={16} />
                  </div>
                </div>

                {/* Compact 4-cell facts grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  <CompactInfoCell icon={<Calendar size={12} color="#FF4D3D" />} label="First caught">
                    <span style={{ fontSize: 10 }}>{firstCaught}</span>
                  </CompactInfoCell>

                  <CompactInfoCell icon={<RefreshCw size={12} color="#FF4D3D" />} label="Last verified">
                    <span style={{ fontSize: 10 }}>{lastCaught}</span>
                  </CompactInfoCell>

                  <CompactInfoCell icon={<Layers size={12} color="#FF4D3D" />} label="Instagram uses">
                    {trend.audio_use_count > 0 ? formatCount(trend.audio_use_count) : '—'}
                  </CompactInfoCell>

                  <CompactInfoCell icon={<Disc size={12} color="#FF4D3D" />} label="Reels tracked">
                    {trend.reel_count > 0 ? formatCount(trend.reel_count) : `${rawReels.length} Tracked`}
                  </CompactInfoCell>
                </div>

                {/* Language & Niche */}
                {(trend.language || trend.niche) && (
                  <div
                    style={{
                      background: '#FAF7F2',
                      border: '1px solid rgba(255,77,61,0.12)',
                      borderRadius: 12,
                      padding: '6px 10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <Globe size={12} color="#FF4D3D" />
                      <span
                        style={{
                          fontSize: 9,
                          fontWeight: 800,
                          color: '#FF4D3D',
                          textTransform: 'uppercase',
                          fontFamily: 'Inter, sans-serif',
                        }}
                      >
                        Focus:
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 5 }}>
                      {trend.language && (
                        <span
                          style={{
                            background: '#FF4D3D',
                            color: '#fff',
                            fontWeight: 800,
                            fontSize: 10,
                            padding: '2px 8px',
                            borderRadius: 99,
                            textTransform: 'uppercase',
                          }}
                        >
                          {trend.language}
                        </span>
                      )}
                      {trend.niche && (
                        <span
                          style={{
                            background: '#C7F23A',
                            color: '#2A3A10',
                            fontWeight: 800,
                            fontSize: 10,
                            padding: '2px 8px',
                            borderRadius: 99,
                          }}
                        >
                          {trend.niche}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Unified High-Confidence Creator Intelligence (Zero Contradictions) */}
                {(isUsedForGenuine || isWhyGenuine) && (
                  <div
                    style={{
                      background: '#FFF0EE',
                      border: '1px solid rgba(255,77,61,0.20)',
                      borderRadius: 14,
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <Sparkles size={12} color="#FF4D3D" />
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 800,
                            color: '#FF4D3D',
                            textTransform: 'uppercase',
                            fontFamily: 'Inter, sans-serif',
                            letterSpacing: '0.04em',
                          }}
                        >
                          Creator Intelligence
                        </span>
                      </div>
                      {trend.niche && (
                        <span
                          style={{
                            fontSize: 9.5,
                            fontWeight: 700,
                            padding: '2px 7px',
                            borderRadius: 6,
                            background: 'rgba(255,77,61,0.12)',
                            color: '#FF4D3D',
                            textTransform: 'capitalize',
                          }}
                        >
                          {trend.niche}
                        </span>
                      )}
                    </div>

                    {/* Primary concrete creator use-case format */}
                    <p
                      style={{
                        fontSize: 11.5,
                        color: '#0E0E10',
                        lineHeight: 1.4,
                        margin: 0,
                        fontFamily: 'Inter, sans-serif',
                        fontWeight: 600,
                      }}
                    >
                      {trend.used_for_note || trend.used_for || trend.why_this_works}
                    </p>

                    {/* Secondary editing/hook tip if genuine and non-redundant */}
                    {isWhyGenuine && isUsedForGenuine && trend.why_this_works !== (trend.used_for_note || trend.used_for) && (
                      <p
                        style={{
                          fontSize: 10.5,
                          color: '#555562',
                          lineHeight: 1.35,
                          margin: 0,
                          fontFamily: 'Inter, sans-serif',
                          fontStyle: 'italic',
                        }}
                      >
                        💡 {trend.why_this_works}
                      </p>
                    )}
                  </div>
                )}

                {/* Primary Action Buttons */}
                <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                  <button
                    onClick={() => {
                      onSkip();
                      onClose();
                    }}
                    style={{
                      flex: 1,
                      padding: '10px 0',
                      borderRadius: 12,
                      background: '#FAF7F2',
                      border: '1.5px solid #E8E3DA',
                      color: '#6B6B78',
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: 'pointer',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  >
                    Pass
                  </button>
                  <button
                    onClick={() => {
                      onUse();
                      onClose();
                    }}
                    style={{
                      flex: 2,
                      padding: '10px 0',
                      borderRadius: 12,
                      background: '#FF4D3D',
                      border: 'none',
                      color: '#fff',
                      fontWeight: 800,
                      fontSize: 13,
                      cursor: 'pointer',
                      fontFamily: "'Bricolage Grotesque', system-ui",
                      boxShadow: '0 4px 14px rgba(255,77,61,0.35)',
                    }}
                  >
                    Use It ✓
                  </button>
                </div>

                {/* Instagram Direct Link */}
                <a
                  href={instagramUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 5,
                    padding: '4px 0 0',
                    color: '#FF4D3D',
                    fontSize: 11,
                    fontWeight: 700,
                    fontFamily: 'Inter, sans-serif',
                    textDecoration: 'none',
                  }}
                >
                  <ExternalLink size={11} />
                  <span>Open Audio on Instagram</span>
                </a>
              </div>
          </motion.div>

          {/* ============================================================== */}
          {/* RIGHT WING: POPPING OUT REELS OR SOUND DISCOVERY COMPANION     */}
          {/* ============================================================== */}
          {rightReels.length > 0 ? (
            <motion.div
              key="right-wing-reels"
              initial={{ opacity: 0, x: -220, scale: 0.15 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -220, scale: 0.15 }}
              transition={{ type: 'spring', stiffness: 280, damping: 25, mass: 0.8 }}
              className="hidden md:flex"
              style={{
                width: 140,
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transformOrigin: 'left center',
              }}
            >
              {rightReels.map((reel, idx) => (
                <motion.div
                  key={reel.id || reel.reel_id || idx}
                  initial={{ opacity: 0, x: -180, scale: 0.15 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: -180, scale: 0.15 }}
                  transition={{
                    delay: idx * 0.05,
                    type: 'spring',
                    stiffness: 300,
                    damping: 24,
                  }}
                >
                  <ReelPreviewCard
                    reel={reel}
                    index={idx + leftReels.length + 1}
                    onSelect={() => setActiveReel(reel)}
                  />
                </motion.div>
              ))}
            </motion.div>
          ) : rawReels.length === 1 ? (
            <motion.div
              key="right-wing-audio-discovery"
              initial={{ opacity: 0, x: -220, scale: 0.15 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: -220, scale: 0.15 }}
              transition={{ type: 'spring', stiffness: 280, damping: 25, mass: 0.8 }}
              className="hidden md:flex"
              style={{
                width: 140,
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                transformOrigin: 'left center',
              }}
            >
              <a
                href={instagramUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  textDecoration: 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '18px 12px',
                  borderRadius: 14,
                  background: '#FFFFFF',
                  border: '1.5px solid rgba(255, 77, 61, 0.20)',
                  boxShadow: '0 4px 14px rgba(255, 77, 61, 0.08)',
                  textAlign: 'center',
                  gap: 8,
                  cursor: 'pointer',
                  transition: 'transform 0.18s ease, box-shadow 0.18s ease',
                }}
                className="group hover:scale-[1.04] hover:shadow-md"
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: '#FFF0EE',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#FF4D3D',
                    boxShadow: '0 2px 8px rgba(255,77,61,0.2)',
                  }}
                >
                  <ExternalLink size={16} />
                </div>
                <div style={{ fontSize: 11.5, fontWeight: 800, color: '#0E0E10', lineHeight: 1.25, fontFamily: "'Bricolage Grotesque', system-ui" }}>
                  More Reels on Instagram
                </div>
                <div style={{ fontSize: 9.5, color: '#6B6B78', lineHeight: 1.35, fontFamily: 'Inter, sans-serif' }}>
                  Browse all creator videos made with this sound
                </div>
                <div
                  style={{
                    marginTop: 4,
                    padding: '5px 10px',
                    borderRadius: 99,
                    background: '#FF4D3D',
                    color: '#fff',
                    fontSize: 9.5,
                    fontWeight: 700,
                    boxShadow: '0 2px 8px rgba(255,77,61,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <span>Explore ↗</span>
                </div>
              </a>
            </motion.div>
          ) : null}
        </div>

        {/* ============================================================== */}
        {/* REEL MINIPLAYER MODAL (CLEAN LIGHT THEME - ZERO DARK OVERLAYS)  */}
        {/* ============================================================== */}
        {activeReel && (
          <motion.div
            key="reel-miniplayer-modal"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 75,
              background: 'rgba(250, 247, 242, 0.92)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 16,
            }}
            onClick={() => setActiveReel(null)}
          >
            <div
              style={{
                width: '100%',
                maxWidth: 380,
                background: '#FFFFFF',
                borderRadius: 20,
                overflow: 'hidden',
                border: '2px solid rgba(255, 77, 61, 0.25)',
                boxShadow: '0 20px 60px rgba(255, 77, 61, 0.20)',
                position: 'relative',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Top Bar */}
              <div
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderBottom: '1px solid rgba(255, 77, 61, 0.12)',
                  background: '#FFFDFB',
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 800,
                      color: '#0E0E10',
                      fontFamily: "'Bricolage Grotesque', system-ui",
                    }}
                  >
                    @{activeReel.owner_username}
                  </div>
                  <div
                    style={{
                      fontSize: 10,
                      color: '#FF4D3D',
                      fontFamily: 'Inter, sans-serif',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      fontWeight: 700,
                    }}
                  >
                    <Flame size={11} color="#FF4D3D" fill="#FF4D3D" />
                    <span>{formatCount(activeReel.view_count)} views</span>
                    {activeReel.like_count > 0 && (
                      <>
                        <span>·</span>
                        <span>{formatCount(activeReel.like_count)} likes</span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setActiveReel(null)}
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: '#FFF0EE',
                    border: 'none',
                    color: '#FF4D3D',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                >
                  <X size={15} />
                </button>
              </div>

              {/* Reel Embed / Viewer */}
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  aspectRatio: '9/14',
                  background: '#FAF7F2',
                  overflow: 'hidden',
                }}
              >
                {(() => {
                  const isSafeVideo = Boolean(
                    activeReel.video_url &&
                    !videoFailedIds.has(activeReel.id) &&
                    !isInstagramCdnUrlExpired(activeReel.video_url)
                  );

                  if (isSafeVideo) {
                    return (
                      <video
                        src={activeReel.video_url!}
                        controls
                        autoPlay
                        playsInline
                        loop
                        poster={
                          activeReel.reel_id
                            ? `${API_URL}/api/deck/thumb/${activeReel.reel_id}`
                            : activeReel.thumbnail_url || undefined
                        }
                        onError={() => {
                          setVideoFailedIds(prev => new Set(prev).add(activeReel.id));
                        }}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          background: '#0E0E10',
                        }}
                      />
                    );
                  }

                  if (activeReel.embed_url) {
                    return (
                      <iframe
                        src={activeReel.embed_url}
                        title={`Instagram reel by ${activeReel.owner_username}`}
                        style={{
                          width: '100%',
                          height: '100%',
                          border: 'none',
                        }}
                        allow="autoplay; encrypted-media"
                        allowFullScreen
                      />
                    );
                  }

                  return (
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      padding: 20,
                      textAlign: 'center',
                      color: '#0E0E10',
                      background: 'linear-gradient(135deg, #FFF0EE 0%, #F5FBE6 100%)',
                    }}
                  >
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: '50%',
                        background: '#FF4D3D',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: 10,
                        boxShadow: '0 6px 18px rgba(255,77,61,0.3)',
                      }}
                    >
                      <Film size={22} color="#fff" />
                    </div>
                    <p style={{ fontSize: 14, fontWeight: 800, margin: 0, color: '#0E0E10' }}>
                      Watch Breakout Reel
                    </p>
                    <p style={{ fontSize: 11, color: '#6B6B78', marginTop: 4 }}>
                      @{activeReel.owner_username}
                    </p>
                  </div>
                    );
                  })()}
                </div>

              {/* Action Button */}
              <div style={{ padding: '12px 16px', background: '#FFFDFB' }}>
                <a
                  href={activeReel.instagram_url || `https://www.instagram.com/reel/${activeReel.reel_id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    width: '100%',
                    padding: '10px 0',
                    background: '#FF4D3D',
                    borderRadius: 12,
                    color: '#fff',
                    fontSize: 12,
                    fontWeight: 800,
                    textDecoration: 'none',
                    fontFamily: "'Bricolage Grotesque', system-ui",
                    boxShadow: '0 4px 14px rgba(255,77,61,0.35)',
                  }}
                >
                  <ExternalLink size={13} />
                  <span>Open Reel on Instagram</span>
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}

// Compact Pop-out Reel Card with Real Live Thumbnails (Zero Fabrication)
function ReelPreviewCard({
  reel,
  index,
  onSelect,
}: {
  reel: DeckReel;
  index: number;
  onSelect: () => void;
}) {
  const primaryThumb = reel.reel_id
    ? `${API_URL}/api/deck/thumb/${reel.reel_id}`
    : reel.thumbnail_url || null;

  const [imgSrc, setImgSrc] = useState<string | null>(primaryThumb);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    setImgSrc(
      reel.reel_id
        ? `${API_URL}/api/deck/thumb/${reel.reel_id}`
        : reel.thumbnail_url || null
    );
    setImgFailed(false);
  }, [reel.reel_id, reel.thumbnail_url]);

  return (
    <div
      onClick={onSelect}
      style={{
        position: 'relative',
        width: '100%',
        aspectRatio: '9/11',
        maxHeight: 130,
        borderRadius: 14,
        overflow: 'hidden',
        cursor: 'pointer',
        background: '#FAF7F2',
        border: '1.5px solid rgba(255, 77, 61, 0.20)',
        boxShadow: '0 4px 14px rgba(255, 77, 61, 0.08)',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
      }}
      className="group hover:scale-[1.04] hover:shadow-md"
    >
      {/* Real Scraped Reel Thumbnail */}
      {imgSrc && !imgFailed ? (
        <img
          src={imgSrc}
          alt={`Reel by ${reel.owner_username}`}
          referrerPolicy="no-referrer"
          loading="eager"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
          }}
          onError={() => {
            if (reel.thumbnail_url && imgSrc !== reel.thumbnail_url) {
              setImgSrc(reel.thumbnail_url);
            } else {
              setImgFailed(true);
            }
          }}
        />
      ) : (
        <div
          style={{
            width: '100%',
            height: '100%',
            background: 'linear-gradient(135deg, #FFF0EE 0%, #FAF7F2 50%, #F5FBE6 100%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: '#FF4D3D',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
            }}
          >
            <Film size={14} />
          </div>
          <span
            style={{
              fontSize: 9,
              fontWeight: 800,
              color: '#FF4D3D',
              fontFamily: 'Inter, sans-serif',
            }}
          >
            REEL #{index}
          </span>
        </div>
      )}

      {/* View count pill top left */}
      {reel.view_count > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 5,
            left: 5,
            background: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid rgba(255, 77, 61, 0.2)',
            borderRadius: 99,
            padding: '1px 5px',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            color: '#0E0E10',
            fontSize: 8.5,
            fontWeight: 800,
            fontFamily: 'Inter, sans-serif',
            boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            zIndex: 3,
          }}
        >
          <Flame size={8} color="#FF4D3D" fill="#FF4D3D" />
          <span>{formatCount(reel.view_count)}</span>
        </div>
      )}

      {/* Like count pill top right */}
      {reel.like_count > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 5,
            right: 5,
            background: 'rgba(255, 255, 255, 0.95)',
            border: '1px solid rgba(255, 77, 61, 0.2)',
            borderRadius: 99,
            padding: '1px 5px',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            color: '#0E0E10',
            fontSize: 8.5,
            fontWeight: 800,
            fontFamily: 'Inter, sans-serif',
            boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            zIndex: 3,
          }}
        >
          <Heart size={8} color="#FF4D3D" fill="#FF4D3D" />
          <span>{formatCount(reel.like_count)}</span>
        </div>
      )}

      {/* High engagement breakout badge */}
      {reel.is_high_engagement && (
        <div
          style={{
            position: 'absolute',
            bottom: 24,
            left: 5,
            background: 'linear-gradient(135deg, #FF4D3D 0%, #FF7A00 100%)',
            color: '#fff',
            borderRadius: 99,
            padding: '1px 5px',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            fontSize: 7.5,
            fontWeight: 800,
            boxShadow: '0 2px 6px rgba(255, 77, 61, 0.4)',
            zIndex: 3,
            letterSpacing: 0.5,
          }}
        >
          <Flame size={7} fill="#fff" />
          <span>HIT</span>
        </div>
      )}

      {/* Center Play Button Overlay */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: '#FF4D3D',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          boxShadow: '0 2px 8px rgba(255, 77, 61, 0.40)',
          zIndex: 3,
        }}
      >
        <Play size={12} fill="#fff" style={{ marginLeft: 1 }} />
      </div>

      {/* Creator Bar at the bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'rgba(255, 255, 255, 0.94)',
          backdropFilter: 'blur(6px)',
          borderTop: '1px solid rgba(255, 77, 61, 0.12)',
          padding: '3px 6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 3,
        }}
      >
        <span
          style={{
            fontSize: 8.5,
            fontWeight: 800,
            color: '#0E0E10',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
          }}
        >
          @{reel.owner_username}
        </span>
      </div>
    </div>
  );
}

// Compact Telemetry Info Cell
function CompactInfoCell({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        background: '#FAF7F2',
        border: '1px solid rgba(255, 77, 61, 0.12)',
        borderRadius: 10,
        padding: '6px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {icon}
        <span
          style={{
            fontSize: 8.5,
            fontWeight: 700,
            color: '#9A9AA8',
            letterSpacing: 0.6,
            textTransform: 'uppercase',
            fontFamily: 'Inter, sans-serif',
          }}
        >
          {label}
        </span>
      </div>
      <span
        style={{
          fontSize: 11,
          fontWeight: 800,
          color: '#0E0E10',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        {children}
      </span>
    </div>
  );
}
