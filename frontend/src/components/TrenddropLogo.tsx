import React from 'react';

export function TrenddropIcon({ size = 40, variant = 'coral', className = '' }: { size?: number; variant?: 'coral' | 'acid' | 'ink'; className?: string }) {
  if (variant === 'coral') {
    return (
      <img
        src="/icon-192.png"
        alt="Trendrop"
        width={size}
        height={size}
        className={`inline-block rounded-[22%] object-contain ${className}`}
        data-testid="trendrop-icon"
      />
    );
  }

  const variants = {
    coral: { bg: '#FF4D3D', fg: '#FFFFFF', accent: '#C7F23A' },
    acid:  { bg: '#C7F23A', fg: '#0B0B0F', accent: '#FF4D3D' },
    ink:   { bg: '#0B0B0F', fg: '#F5F1E8', accent: '#C7F23A' },
  };
  const v = variants[variant] || variants.coral;
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" className={className} data-testid="trendrop-icon">
      <rect x="0" y="0" width="120" height="120" rx="28" fill={v.bg}/>
      {/* Uplifting Swoosh T */}
      <path
        d="M 32 50 C 32 46, 36 42, 42 42 L 68 42 C 78 42, 86 36, 92 30 C 94 28, 97 29, 96 32 C 94 40, 84 48, 72 50 L 64 50 L 64 88 C 64 94, 56 94, 56 88 L 56 50 L 42 50 C 36 50, 32 46, 32 50 Z"
        fill={v.fg}
      />
      {/* Cute Droplet */}
      <path
        d="M 80 62 C 84 54, 88 54, 92 62 C 96 70, 96 78, 90 84 C 84 90, 76 86, 74 80 C 72 74, 76 68, 80 62 Z"
        fill={v.accent}
      />
    </svg>
  );
}

interface TrenddropLogoProps {
  iconOnly?: boolean;
  size?: number;
  animate?: boolean;
  variant?: 'default' | 'coral' | 'acid' | 'ink';
  className?: string;
}

export function TrenddropLogo({
  iconOnly = false,
  size = 56,
  animate = false,
  variant = 'default',
  className = '',
}: TrenddropLogoProps) {
  if (iconOnly) {
    const iconVariant = variant === 'default' ? 'coral' : (variant as 'coral' | 'acid' | 'ink');
    return <TrenddropIcon size={size} variant={iconVariant} className={className} />;
  }

  return (
    <div
      className={`trendrop-wordmark ${animate ? 'animate' : ''} variant-${variant} ${className}`}
      style={{ fontSize: size }}
      data-testid="trendrop-wordmark"
    >
      <span className="tr-arrow" aria-hidden="true">
        <svg viewBox="0 0 100 50" preserveAspectRatio="xMinYMax meet">
          <path d="M 6 44 L 32 30 L 56 36 L 88 8" stroke="currentColor" strokeWidth="8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M 76 4 L 94 4 L 94 22" stroke="currentColor" strokeWidth="8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </span>
      <span className="tr-pre">trendr</span>
      <span className="tr-play" aria-hidden="true" />
      <span className="tr-post">p</span>
      <span className="tr-drop" aria-hidden="true">
        <svg viewBox="0 0 44 60" preserveAspectRatio="none">
          <path d="M 22 2 C 22 16, 42 28, 42 44 C 42 54, 33 58, 22 58 C 11 58, 2 54, 2 44 C 2 28, 22 16, 22 2 Z" fill="currentColor"/>
        </svg>
      </span>
    </div>
  );
}
