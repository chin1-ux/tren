import React, { useRef, useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, PanInfo, animate } from 'framer-motion';
import { Play, Pause, Loader2 } from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack } from '@/lib/audio-resolver';

interface VinylRecordProps {
  trend: DeckTrend;
  isFront?: boolean;
  stackIndex?: number;
  onSwipe: (action: 'use' | 'skip') => void;
  onClick: () => void;
}

// Stage colours — logo palette
const STAGE_META: Record<string, { color: string; label: string }> = {
  rising:    { color: '#FF4D3D', label: 'RISING' },
  emerging:  { color: '#0EA5E9', label: 'EMERGING' },
  peaked:    { color: '#D97706', label: 'PEAKED' },
  resurging: { color: '#9333EA', label: 'RESURGING' },
  expired:   { color: '#64748B', label: 'EXPIRED' },
};

// Niche groove accent colours
const NICHE_COLORS: Record<string, string> = {
  dance:    '#C7F23A',
  fitness:  '#FF6B35',
  food:     '#FFBE0B',
  comedy:   '#06D6A0',
  fashion:  '#FF85A1',
  travel:   '#48CAE4',
  beauty:   '#FFB4A2',
  business: '#FF4D3D',
  romance:  '#FF6B6B',
};

function getGrooveColor(trend: DeckTrend): string {
  const s = (trend.status || '').toLowerCase();
  if (s === 'expired') return '#64748B';
  const niche = (trend.niche || '').toLowerCase();
  for (const [key, color] of Object.entries(NICHE_COLORS)) {
    if (niche.includes(key)) return color;
  }
  return STAGE_META[s]?.color || '#FF4D3D';
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(n);
}

// Deterministic warm hue from title chars
function titleHue(title: string): number {
  let h = 0;
  for (let i = 0; i < title.length; i++) h = (h * 31 + title.charCodeAt(i)) % 360;
  return h;
}

export function VinylRecord({ trend, isFront = true, stackIndex = 0, onSwipe, onClick }: VinylRecordProps) {
  const y = useMotionValue(0);
  const x = useMotionValue(0);

  const { currentTrack, isPlaying, playTrack, togglePlay } = useAudioStore();
  const isThisPlaying = Boolean(
    isPlaying && currentTrack && String(currentTrack.id) === String(trend.id)
  );
  const [isResolving, setIsResolving] = useState(false);

  const handlePlayAudio = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isThisPlaying) {
      togglePlay();
      return;
    }
    setIsResolving(true);
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
      setIsResolving(false);
    }
  };

  // Prefetch audio preview in background for the active vinyl so play is instant
  useEffect(() => {
    if (!isFront || !trend?.audio_title) return;
    resolveAudioTrack({
      id: trend.id,
      song: trend.audio_title,
      artist: trend.audio_artist,
      audioId: trend.audio_id,
      previewUrl: trend.preview_url || undefined,
    }).catch(() => {});
  }, [isFront, trend?.id, trend?.audio_title, trend?.audio_artist, trend?.audio_id, trend?.preview_url]);

  // Drag-driven 3D tilt
  const rotateX = useTransform(y, [-200, 200], [22, -22]);
  const rotateZ = useTransform(x, [-160, 160], [10, -10]);

  // Gesture label opacities
  const useOpacity  = useTransform(y, [-30, -110], [0, 1]);
  const passOpacity = useTransform(y, [30,  110],  [0, 1]);

  // Continuous spin
  const spin    = useMotionValue(0);
  const spinAnim = useRef<ReturnType<typeof animate> | null>(null);
  const [dragging, setDragging] = useState(false);
  const isDraggingRef = useRef(false);

  useEffect(() => {
    if (!isFront || dragging) return;
    spinAnim.current = animate(spin, 360, {
      duration: 20,
      ease: 'linear',
      repeat: Infinity,
      repeatType: 'loop',
    });
    return () => spinAnim.current?.stop();
  }, [isFront, dragging]);

  const handleDragStart = () => {
    isDraggingRef.current = true;
    setDragging(true);
    spinAnim.current?.stop();
  };

  const handleDragEnd = (_: any, info: PanInfo) => {
    setDragging(false);
    const oy = info.offset.y;
    const vy = info.velocity.y;

    setTimeout(() => {
      isDraggingRef.current = false;
    }, 80);

    if (oy < -100 || vy < -400) { onSwipe('use');  return; }
    if (oy >  100 || vy >  400) { onSwipe('skip'); return; }

    // Snap back
    animate(y, 0, { type: 'spring', stiffness: 420, damping: 32 });
    animate(x, 0, { type: 'spring', stiffness: 420, damping: 32 });
    setDragging(false);
    // Resume spin
    spinAnim.current = animate(spin, spin.get() + 360, {
      duration: 20,
      ease: 'linear',
      repeat: Infinity,
      repeatType: 'loop',
    });
  };

  const handleClick = () => {
    if (!isDraggingRef.current && Math.abs(x.get()) < 18 && Math.abs(y.get()) < 18) {
      onClick();
    }
  };

  const stage = (trend.status || 'emerging').toLowerCase();
  const sm    = STAGE_META[stage] || STAGE_META.emerging;
  const gc    = getGrooveColor(trend);
  const hue   = titleHue(trend.audio_title);
  const labelBg = `hsl(${hue}, 48%, 90%)`;

  // When displayed singly or at front of stack
  const isSingle = stackIndex === 0;
  const scale   = isSingle ? 1 : ([1, 0.87, 0.74][stackIndex] ?? 0.62);
  const yOff    = isSingle ? 0 : ([0, 32, 56][stackIndex] ?? 72);
  const opacity = isSingle ? 1 : ([1, 0.82, 0.6][stackIndex] ?? 0);

  return (
    <motion.div
      key={trend.id}
      initial={{ scale: 0.9, opacity: 0, y: 20 }}
      animate={{ scale, y: yOff, opacity }}
      exit={{
        opacity: 0,
        scale: 0.88,
        y: y.get() < -40 ? -280 : y.get() > 40 ? 280 : -120,
        transition: { duration: 0.22, ease: 'easeOut' },
      }}
      transition={{ type: 'spring', stiffness: 320, damping: 28 }}
      style={{ zIndex: 10 - stackIndex, position: 'absolute', inset: 0 }}
    >
      <motion.div
        style={{
          y: isFront ? y : 0,
          x: isFront ? x : 0,
          rotateX: isFront ? rotateX : 0,
          rotateZ: isFront ? rotateZ : 0,
          transformStyle: 'preserve-3d',
          perspective: 1000,
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: isFront ? 'grab' : 'default',
          gap: 10,
        }}
        drag={isFront}
        dragConstraints={{ top: 0, bottom: 0, left: 0, right: 0 }}
        dragElastic={0.55}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={handleClick}
        whileTap={{ cursor: 'grabbing' }}
      >
        {/* The spinning disc — GPU-accelerated CSS animation */}
        <div
          className={isFront && !dragging ? 'vinyl-spin-gpu' : ''}
          style={{ position: 'relative', flexShrink: 0, willChange: 'transform' }}
        >
          <svg viewBox="0 0 320 320"
            className="w-[210px] h-[210px] sm:w-[270px] sm:h-[270px]"
            style={{ filter: 'drop-shadow(0 18px 44px rgba(255,77,61,0.28)) drop-shadow(0 4px 14px rgba(0,0,0,0.08))' }}
          >
            <defs>
              <radialGradient id={`vinylDisc-${trend.id}`} cx="45%" cy="45%" r="70%">
                <stop offset="0%" stopColor="#FF6B57" />
                <stop offset="45%" stopColor="#FF4D3D" />
                <stop offset="85%" stopColor="#E03A1F" />
                <stop offset="100%" stopColor="#C92E15" />
              </radialGradient>
            </defs>

            {/* Body - Authentic Black Vinyl Disc */}
            <circle cx="160" cy="160" r="156" fill="#141416" />

            {/* Concentric sound groove rings */}
            {[148, 136, 124, 112, 100, 89, 80, 71].map((r, i) => (
              <circle key={r} cx="160" cy="160" r={r}
                fill="none"
                stroke={i % 2 === 0 ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.13)'}
                strokeWidth="1.4"
              />
            ))}

            {/* Niche/stage accent grooves */}
            <circle cx="160" cy="160" r="150" fill="none" stroke={gc} strokeWidth="1.6" opacity="0.65" />
            <circle cx="160" cy="160" r="74"  fill="none" stroke="#FF4D3D" strokeWidth="2" opacity="0.75" />

            {/* Center label */}
            <circle cx="160" cy="160" r="54" fill="#FAF7F2" />
            <circle cx="160" cy="160" r="54" fill="none" stroke="#FF4D3D" strokeWidth="2.5" />

            {/* Audio title in center label */}
            <text x="160" y="150" textAnchor="middle" dominantBaseline="middle"
              fontSize="9" fontWeight="800"
              fontFamily="'Bricolage Grotesque',system-ui,sans-serif"
              fill="#0E0E10"
            >
              {trend.audio_title.length > 15 ? trend.audio_title.slice(0, 13) + '…' : trend.audio_title}
            </text>

            {/* Stage text */}
            <text x="160" y="168" textAnchor="middle" dominantBaseline="middle"
              fontSize="7.5" fontWeight="700" letterSpacing="1.5"
              fontFamily="'Inter',system-ui,sans-serif"
              fill="#FF4D3D"
            >
              {sm.label}
            </text>

            {/* Spindle */}
            <circle cx="160" cy="160" r="5.5" fill="#141416" stroke="#FF4D3D" strokeWidth="1.5" />

            {/* Sheen */}
            <ellipse cx="124" cy="114" rx="42" ry="24"
              fill="rgba(255,255,255,0.12)"
              transform="rotate(-28 124 114)"
            />
          </svg>

          {/* USE IT stamp */}
          {isFront && (
            <motion.div style={{ opacity: useOpacity }}
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <div style={{
                border: '3px solid #C7F23A', color: '#C7F23A',
                background: 'rgba(199,242,58,0.15)',
                fontWeight: 800, fontSize: 16, letterSpacing: 3,
                padding: '7px 16px', borderRadius: 10,
                transform: 'rotate(-16deg)', backdropFilter: 'blur(6px)',
                fontFamily: 'Inter, sans-serif',
              }}>
                USE IT ↑
              </div>
            </motion.div>
          )}

          {/* PASS stamp */}
          {isFront && (
            <motion.div style={{ opacity: passOpacity }}
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <div style={{
                border: '3px solid #FF4D3D', color: '#FF4D3D',
                background: 'rgba(255,77,61,0.15)',
                fontWeight: 800, fontSize: 16, letterSpacing: 3,
                padding: '7px 16px', borderRadius: 10,
                transform: 'rotate(16deg)', backdropFilter: 'blur(6px)',
                fontFamily: 'Inter, sans-serif',
              }}>
                PASS ↓
              </div>
            </motion.div>
          )}
        </div>

        {/* Track metadata strip (below disc, doesn't spin) */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
          pointerEvents: 'none',
          width: '100%',
          maxWidth: 320,
        }}>
          <p style={{
            fontFamily: "'Bricolage Grotesque', system-ui",
            fontWeight: 800, fontSize: 16, color: 'var(--text, #0E0E10)',
            textAlign: 'center', maxWidth: 'min(270px, 82vw)', padding: '0 4px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            margin: 0,
          }}>
            {trend.audio_title}
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-2, #6B6B78)', fontFamily: 'Inter, sans-serif', fontWeight: 500, margin: 0 }}>
            {trend.audio_artist}
          </p>

          {/* Interactive Audio Player Option directly on Vinyl Card */}
          {isFront && (
            <button
              onClick={handlePlayAudio}
              disabled={isResolving}
              style={{
                pointerEvents: 'auto',
                cursor: isResolving ? 'wait' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                borderRadius: 99,
                background: isThisPlaying ? '#FF4D3D' : 'rgba(255,77,61,0.08)',
                color: isThisPlaying ? '#FFFFFF' : '#FF4D3D',
                border: '1px solid rgba(255,77,61,0.22)',
                boxShadow: isThisPlaying ? '0 4px 14px rgba(255,77,61,0.35)' : 'none',
                marginTop: 2,
                transition: 'all 0.15s ease',
              }}
              title={isThisPlaying ? "Pause preview" : "Play preview"}
            >
              {isResolving ? (
                <Loader2 size={13} className="animate-spin" />
              ) : isThisPlaying ? (
                <Pause size={13} fill="currentColor" />
              ) : (
                <Play size={13} fill="currentColor" style={{ marginLeft: 1 }} />
              )}
              <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'Inter, sans-serif' }}>
                {isResolving ? 'Loading…' : isThisPlaying ? 'Playing Audio' : 'Play Audio'}
              </span>
            </button>
          )}

          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
            {/* Stage Badge */}
            <span style={{
              background: trend.status === 'expired' ? 'rgba(100,116,139,0.12)' : `${sm.color}15`,
              color: trend.status === 'expired' ? '#64748B' : sm.color,
              border: `1px solid ${trend.status === 'expired' ? 'rgba(100,116,139,0.3)' : sm.color + '30'}`,
              fontWeight: 700, fontSize: 10,
              padding: '2px 8px', borderRadius: 99,
              letterSpacing: 0.5,
            }}>
              {trend.status === 'expired' ? '⛔ EXPIRED' : sm.label}
            </span>

            <span style={{
              background: '#C7F23A', color: '#0E0E10',
              fontWeight: 700, fontSize: 10,
              padding: '2px 8px', borderRadius: 99,
            }}>
              {formatCount(trend.audio_use_count > 0 ? trend.audio_use_count : trend.reel_count)} uses
            </span>
            {trend.language && (
              <span style={{
                background: 'rgba(255,77,61,0.1)', color: '#FF4D3D',
                fontWeight: 600, fontSize: 10,
                padding: '2px 8px', borderRadius: 99, textTransform: 'uppercase',
              }}>
                {trend.language}
              </span>
            )}
            {trend.niche && (
              <span style={{
                background: 'rgba(199,242,58,0.25)', color: '#2A3A10',
                border: '1px solid rgba(199,242,58,0.5)',
                fontWeight: 600, fontSize: 10,
                padding: '2px 8px', borderRadius: 99,
              }}>
                {trend.niche}
              </span>
            )}
          </div>

          {/* Creator intelligence: Why this works / Used for (Zero Canned Strings) */}
          {(() => {
            const why = (trend.why_this_works || '').trim();
            const used = (trend.used_for_note || trend.used_for || '').trim();
            const concept = (trend.ideal_content_description || '').trim();

            const isCanned = (s: string) => {
              if (!s || s.length < 10) return true;
              const lower = s.toLowerCase();
              return (
                lower.includes('currently driving high engagement') ||
                lower.includes('automated fallback') ||
                lower.includes('sporadic') ||
                lower.includes('creators consistently use this sound') ||
                lower.includes('fast-paced visual storytelling') ||
                lower.includes('resonates with') ||
                lower.includes('positive content during these times') ||
                lower.includes('emotional state') ||
                lower.includes('sentiments about life') ||
                lower.includes('evokes positive emotions') ||
                lower.includes('popular choice for content creators') ||
                lower.includes('cultural and emotional climate') ||
                lower.includes('strong algorithmic audio momentum') ||
                lower.includes('short creator clips that match') ||
                lower.includes('film a high-retention') ||
                lower.includes('post aesthetic clips or photos') ||
                lower.includes('do not use this track expecting') ||
                lower.includes('insufficient reel evidence') ||
                lower.includes('sampled reels show completely discordant themes') ||
                lower.includes('no indexed reel evidence')
              );
            };

            const genuineWhy = !isCanned(why) ? why : null;
            const genuineUsed = !isCanned(used) ? used : null;
            const genuineConcept = !isCanned(concept) ? concept : null;
            // Prioritize concrete creator concept or use case over theoretical why_this_works
            const display = genuineConcept || genuineUsed || genuineWhy;
            if (!display) return null;

            return (
              <div style={{
                width: '100%',
                marginTop: 4,
                padding: '6px 12px',
                borderRadius: 12,
                background: trend.status === 'expired' ? 'rgba(100,116,139,0.08)' : 'var(--surface-2, rgba(255,77,61,0.06))',
                border: trend.status === 'expired' ? '1px solid rgba(100,116,139,0.2)' : '1px solid var(--border, rgba(255,77,61,0.15))',
                textAlign: 'center',
                boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
              }}>
                <p style={{
                  fontSize: 11,
                  lineHeight: 1.35,
                  color: trend.status === 'expired' ? '#64748B' : 'var(--text, #2A2A32)',
                  fontWeight: 500,
                  fontFamily: 'Inter, sans-serif',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  margin: 0,
                }}>
                  <span style={{ fontWeight: 700, color: trend.status === 'expired' ? '#475569' : '#FF4D3D' }}>
                    {genuineWhy ? '💡 Why: ' : '✨ Format: '}
                  </span>
                  {display}
                </p>
              </div>
            );
          })()}
        </div>
      </motion.div>
    </motion.div>
  );
}
