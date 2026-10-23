import React, { useEffect, useRef } from 'react';

/**
 * VinylBackground — fills the page with:
 * 1. Expanding translucent groove rings (coral + lime) that radiate outward from center
 * 2. A bottom equalizer bar that softly pulses
 * Purely decorative / pointer-events: none
 */
export function VinylBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // From here canvas and ctx are narrowed — capture as non-null refs
    const c = canvas as HTMLCanvasElement;
    const g = ctx as CanvasRenderingContext2D;

    let animId: number;
    let w = 0, h = 0;

    const rings: { r: number; maxR: number; alpha: number; color: string; speed: number }[] = [];
    const RING_COLORS = ['#FF4D3D', '#C7F23A', '#FF4D3D', '#C7F23A', '#FF4D3D'];
    let ringSpawnTimer = 0;

    // Equalizer bars
    const BAR_COUNT = 28;
    const barPhases = Array.from({ length: BAR_COUNT }, (_, i) => i * 0.45 + Math.random() * 1.5);
    const barSpeeds = Array.from({ length: BAR_COUNT }, () => 0.8 + Math.random() * 1.2);

    function resize() {
      w = c.offsetWidth;
      h = c.offsetHeight;
      c.width  = w * window.devicePixelRatio;
      c.height = h * window.devicePixelRatio;
      g.scale(window.devicePixelRatio, window.devicePixelRatio);
    }
    resize();
    window.addEventListener('resize', resize);

    let t = 0;
    function frame() {
      t += 0.016;
      g.clearRect(0, 0, w, h);

      // --- Groove rings ---
      ringSpawnTimer += 0.016;
      if (ringSpawnTimer > 2.2) {
        ringSpawnTimer = 0;
        const maxR = Math.max(w, h) * 0.72;
        rings.push({
          r: 40,
          maxR,
          alpha: 0.22,
          color: RING_COLORS[rings.length % RING_COLORS.length],
          speed: 28 + Math.random() * 18,
        });
      }

      const cx = w / 2;
      const cy = h * 0.44;

      for (let i = rings.length - 1; i >= 0; i--) {
        const ring = rings[i];
        ring.r += ring.speed * 0.016;
        ring.alpha = 0.22 * (1 - ring.r / ring.maxR);

        if (ring.r >= ring.maxR) {
          rings.splice(i, 1);
          continue;
        }

        g.beginPath();
        g.arc(cx, cy, ring.r, 0, Math.PI * 2);
        g.strokeStyle = ring.color;
        g.lineWidth = 1.5;
        g.globalAlpha = ring.alpha;
        g.stroke();
        g.globalAlpha = 1;
      }

      // Static groove texture
      [80, 120, 165, 215, 270, 330, 395, 465].forEach((r, i) => {
        g.beginPath();
        g.arc(cx, cy, r, 0, Math.PI * 2);
        g.strokeStyle = i % 2 === 0 ? '#FF4D3D' : '#C7F23A';
        g.lineWidth = 0.6;
        g.globalAlpha = 0.04;
        g.stroke();
        g.globalAlpha = 1;
      });

      // --- Equalizer bars ---
      const barAreaW = w * 0.7;
      const barX0    = (w - barAreaW) / 2;
      const barW     = (barAreaW / BAR_COUNT) * 0.55;
      const barGap   = (barAreaW / BAR_COUNT) * 0.45;
      const barMaxH  = h * 0.09;
      const barY     = h - 28;

      for (let i = 0; i < BAR_COUNT; i++) {
        const phase = barPhases[i] + t * barSpeeds[i];
        const raw   = (Math.sin(phase) * 0.5 + 0.5);
        const barH  = 4 + raw * barMaxH;
        const bx    = barX0 + i * (barW + barGap);

        const grad = g.createLinearGradient(0, barY, 0, barY - barH);
        grad.addColorStop(0, 'rgba(255,77,61,0.55)');
        grad.addColorStop(1, 'rgba(199,242,58,0.55)');

        g.fillStyle = grad;
        g.globalAlpha = 0.15;
        g.beginPath();
        g.roundRect(bx, barY - barH, barW, barH, 3);
        g.fill();
        g.globalAlpha = 1;
      }


      animId = requestAnimationFrame(frame);
    }

    animId = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}
