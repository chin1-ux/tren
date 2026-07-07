import React from 'react';

export function TrenddropIcon({ size = 40, variant = 'coral', className = '' }: { size?: number; variant?: 'coral' | 'acid' | 'ink'; className?: string }) {
  const variants = {
    coral: { bg: '#FF4D3D', fg: '#FFFFFF', accent: '#C7F23A' },
    acid:  { bg: '#C7F23A', fg: '#0B0B0F', accent: '#FF4D3D' },
    ink:   { bg: '#0B0B0F', fg: '#F5F1E8', accent: '#C7F23A' },
  };
  const v = variants[variant] || variants.coral;
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" className={className} data-testid="trendrop-icon">
      <rect x="0" y="0" width="120" height="120" rx="28" fill={v.bg}/>
      <path d="M 22 84 L 50 64 L 70 74 L 96 36" stroke={v.fg} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      <path d="M 86 34 L 100 32 L 98 46" stroke={v.fg} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      <path d="M 36 96 C 36 88, 44 80, 44 70 C 44 80, 52 88, 52 96 C 52 102, 47 106, 44 106 C 41 106, 36 102, 36 96 Z" fill={v.accent}/>
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
