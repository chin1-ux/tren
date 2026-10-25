// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, nitro (build-only using cloudflare as a default target),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  tanstackStart: {
    server: { entry: "server" },
  },
  nitro: {
    preset: "vercel",
    output: {
      dir: "../.vercel/output",
      serverDir: "../.vercel/output/functions/__server.func",
      publicDir: "../.vercel/output/static",
    },
  },
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      // Target modern browsers: smaller bundle, no legacy polyfills
      target: 'esnext',
      // Show compressed bundle sizes in build output
      reportCompressedSize: true,
      rollupOptions: {
        output: {
          // Vendor chunk splitting for optimal long-term caching:
          // Users returning to the app get cache hits on all vendor chunks
          // even when app code changes.
          manualChunks(id) {
            if (!id.includes('node_modules')) return;
            // Heavy animation engine — changes rarely, must be cached independently
            if (id.includes('framer-motion') || id.includes('motion')) return 'vendor-motion';
            // Icon library — tree-shaken but still ~30KB, cache independently
            if (id.includes('lucide-react')) return 'vendor-icons';
            // Core React runtime — never changes between deploys
            if (id.includes('react-dom') || id.includes('/react/')) return 'vendor-react';
            // Radix UI primitives — stable, large, cache separately
            if (id.includes('@radix-ui')) return 'vendor-radix';
            // Data/chart libraries
            if (id.includes('recharts') || id.includes('three')) return 'vendor-viz';
            // Supabase client — auth/DB, changes rarely
            if (id.includes('@supabase')) return 'vendor-supabase';
            // TanStack ecosystem (router, query, start)
            if (id.includes('@tanstack')) return 'vendor-tanstack';
          },
        },
      },
    },
    plugins: [
      VitePWA({
        registerType: "autoUpdate",
        injectRegister: "auto",
        filename: "sw.js",
        manifest: {
          name: "Trendrop",
          short_name: "Trendrop",
          description: "Drop the trend before anyone else",
          start_url: "/deck",
          display: "standalone",
          background_color: "#0a0a0f",
          theme_color: "#E63946",
          icons: [
            {
              src: "/icon-192.png",
              sizes: "192x192",
              type: "image/png",
              purpose: "any maskable"
            },
            {
              src: "/icon-512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "any maskable"
            }
          ]
        },
        devOptions: { enabled: false },
        workbox: {
          globPatterns: [],
          // navigateFallback intentionally omitted: TanStack Start/Nitro is SSR —
          // there is no static index.html to fall back to; the server handles all HTML routes.
          runtimeCaching: [
            {
              urlPattern: ({ request }) => request.mode === "navigate",
              handler: "NetworkFirst",
              options: {
                cacheName: "trendrop-html",
                networkTimeoutSeconds: 3,
              },
            },
            {
              urlPattern: ({ url, sameOrigin }) =>
                sameOrigin && /\.(?:js|css|woff2|png|svg|ico)$/.test(url.pathname),
              handler: "CacheFirst",
              options: {
                cacheName: "trendrop-assets",
                expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 30 },
              },
            },
            {
              urlPattern: /\/api\//,
              handler: "NetworkFirst",
              options: {
                cacheName: "trendrop-api",
                networkTimeoutSeconds: 5,
                expiration: { maxEntries: 50, maxAgeSeconds: 60 * 5 },
              },
            },
          ],
        },
      }),
    ],
  },
});
