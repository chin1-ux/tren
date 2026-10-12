import { useEffect, useRef } from "react";

export function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let isVisible = true;
    let lastFrameTime = 0;
    const isMobile = window.innerWidth < 640;
    // Target 30fps on mobile, 60fps on desktop
    const frameInterval = isMobile ? 33 : 16;

    let width = (canvas.width = container.clientWidth || window.innerWidth);
    let height = (canvas.height = container.clientHeight || 90);

    const handleResize = () => {
      if (!canvas || !container) return;
      width = canvas.width = container.clientWidth || window.innerWidth;
      height = canvas.height = container.clientHeight || 90;
    };
    window.addEventListener("resize", handleResize, { passive: true });

    // Fewer particles on mobile (down from 35 → 20, desktop 60 → 45)
    const count = isMobile ? 20 : 45;
    const colors = ["#E63946", "#7F77DD", "#EF9F27"];

    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.3,
      radius: Math.random() * 2 + 0.8,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: Math.random() * 0.5 + 0.15,
      pulse: Math.random() * 0.02 + 0.01,
    }));

    const render = (timestamp: number) => {
      if (!isVisible) {
        animId = requestAnimationFrame(render);
        return;
      }

      // Throttle: skip frame if too soon
      if (timestamp - lastFrameTime < frameInterval) {
        animId = requestAnimationFrame(render);
        return;
      }
      lastFrameTime = timestamp;

      ctx.clearRect(0, 0, width, height);

      // NOTE: shadowBlur intentionally removed — it was forcing a full GPU
      // shadow composite layer for every particle on every frame (massive perf cost).
      // Alpha variation alone gives a softer, cheaper twinkling effect.

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha += Math.sin(Date.now() * p.pulse * 0.05) * 0.004;
        p.alpha = Math.max(0.1, Math.min(0.6, p.alpha));

        if (p.x < 0) p.x = width;
        else if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        else if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animId = requestAnimationFrame(render);
    };

    // Pause animation when section is scrolled out of view
    const observer = new IntersectionObserver(
      (entries) => {
        isVisible = entries[0]?.isIntersecting ?? true;
      },
      { threshold: 0 }
    );
    observer.observe(container);

    animId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animId);
      observer.disconnect();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 -z-10 h-full w-full overflow-hidden pointer-events-none opacity-60"
    >
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  );
}
