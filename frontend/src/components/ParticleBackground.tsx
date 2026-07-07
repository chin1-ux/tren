import { useEffect, useRef } from "react";
import * as THREE from "three";

export function ParticleBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene
    const scene = new THREE.Scene();

    // Camera
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.z = 8;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Particles Geometry
    // Optimization: detect mobile or lower resolution and cut particle count
    const isMobile = typeof window !== "undefined" && window.innerWidth < 640;
    const particleCount = isMobile ? 80 : 150;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const color1 = new THREE.Color("#E63946"); // Red
    const color2 = new THREE.Color("#7F77DD"); // Purple/Secondary
    const color3 = new THREE.Color("#EF9F27"); // Amber

    for (let i = 0; i < particleCount; i++) {
      // Spread particles in a box
      positions[i * 3] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 6;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6;

      // Blend colors randomly
      const rand = Math.random();
      let chosenColor = color1;
      if (rand > 0.66) {
        chosenColor = color2;
      } else if (rand > 0.33) {
        chosenColor = color3;
      }

      colors[i * 3] = chosenColor.r;
      colors[i * 3 + 1] = chosenColor.g;
      colors[i * 3 + 2] = chosenColor.b;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    // Particle Texture - create a small circular glowing canvas texture
    const canvas = document.createElement("canvas");
    canvas.width = 16;
    canvas.height = 16;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      const gradient = ctx.createRadialGradient(8, 8, 0, 8, 8, 8);
      gradient.addColorStop(0, "rgba(255, 255, 255, 1)");
      gradient.addColorStop(0.5, "rgba(255, 255, 255, 0.4)");
      gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 16, 16);
    }
    const texture = new THREE.CanvasTexture(canvas);

    // Material
    const material = new THREE.PointsMaterial({
      size: 0.18,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      map: texture,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    // Points Mesh
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // Animation variables
    let animationFrameId: number;
    const startTime = performance.now();

    const animate = () => {
      // Optimization: skip math and render when tab is invisible
      if (document.hidden) {
        animationFrameId = requestAnimationFrame(animate);
        return;
      }

      const elapsedTime = (performance.now() - startTime) / 1000;

      // Rotate points slowly
      points.rotation.y = elapsedTime * 0.05;
      points.rotation.x = elapsedTime * 0.02;

      // Subtle float up and down without looping over all particles in JS
      // We can offset the whole mesh or do lightweight updates
      points.position.y = Math.sin(elapsedTime * 0.5) * 0.1;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!containerRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      texture.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 -z-10 h-full w-full overflow-hidden pointer-events-none opacity-50"
    />
  );
}
