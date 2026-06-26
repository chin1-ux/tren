import { motion } from "framer-motion";

interface TrenddropLogoProps {
  /** Show just the icon without the wordmark */
  iconOnly?: boolean;
  /** Size of the icon in pixels (default 36) */
  size?: number;
  /** Additional className for the wrapper */
  className?: string;
  /** Animate on mount */
  animate?: boolean;
}

/**
 * Trendrop brand logo — SVG icon mark + wordmark.
 *
 * Icon concept: A rising trend waveform with an upward arrow peak,
 * symbolising real-time trend detection for Instagram Reels audio.
 */
export function TrenddropLogo({
  iconOnly = false,
  size = 36,
  className = "",
  animate = true,
}: TrenddropLogoProps) {
  const iconRadius = Math.round(size * 0.28);
  const fontSize = Math.round(size * 0.67);

  const content = (
    <>
      {/* ── Icon Mark ── */}
      <div
        style={{
          width: size,
          height: size,
          background: "linear-gradient(135deg, #E63946 0%, #ff006e 100%)",
          borderRadius: iconRadius,
          boxShadow: "0 0 18px rgba(230,57,70,0.45), 0 0 4px rgba(255,0,110,0.3)",
          flexShrink: 0,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 36 36"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Subtle inner gradient overlay */}
          <defs>
            <linearGradient id="trendrop-icon-grad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="rgba(255,255,255,0.18)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0)" />
            </linearGradient>
          </defs>
          <rect width="36" height="36" rx={iconRadius} fill="url(#trendrop-icon-grad)" />

          {/* Rising waveform / bar chart bars */}
          <rect x="5"  y="22" width="3.5" height="8"  rx="1.75" fill="white" opacity="0.5" />
          <rect x="10" y="17" width="3.5" height="13" rx="1.75" fill="white" opacity="0.65" />
          <rect x="15" y="13" width="3.5" height="17" rx="1.75" fill="white" opacity="0.80" />
          <rect x="20" y="7"  width="3.5" height="23" rx="1.75" fill="white" />
          <rect x="25" y="12" width="3.5" height="18" rx="1.75" fill="white" opacity="0.65" />

          {/* Arrow tip pointing up on the tallest bar */}
          <path d="M21.75 5L24.5 7L21.75 9V5Z" fill="white" opacity="0.95" />
        </svg>
      </div>

      {/* ── Wordmark ── */}
      {!iconOnly && (
        <span
          style={{
            fontFamily: "'Space Grotesk', 'Inter', sans-serif",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            fontSize,
            lineHeight: 1,
            background: "linear-gradient(135deg, #E63946 0%, #ff006e 55%, #E63946 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          TRENDROP
        </span>
      )}
    </>
  );

  if (animate) {
    return (
      <motion.div
        className={`flex items-center gap-2.5 select-none ${className}`}
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {content}
      </motion.div>
    );
  }

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {content}
    </div>
  );
}
