# PWA Setup for Trendrop

Make Trendrop installable on mobile with home-screen support, an install prompt UI, and a guarded service worker for offline caching.

## 1. Manifest & head tags

- Create `public/manifest.webmanifest` with the specified fields (name, short_name, description, start_url `/`, display `standalone`, background `#0a0a0f`, theme `#E63946`, two icon entries).
- Add to the head (via `__root.tsx` `head()` since this project uses TanStack head metadata, not a static `index.html`):
  - `<link rel="manifest" href="/manifest.webmanifest">`
  - `<meta name="theme-color" content="#E63946">`
  - `<meta name="apple-mobile-web-app-capable" content="yes">`
  - `<meta name="apple-mobile-web-app-status-bar-style" content="black">`
  - `<link rel="apple-touch-icon" href="/icon-192.png">`

## 2. Icons

Generate two PNG icons (192x192 and 512x512): solid `#E63946` red background with a centered white "T" in Inter Bold. Place at `public/icon-192.png` and `public/icon-512.png`. (Public files are served as-is — no asset CDN externalization needed for PWA icons since the manifest must reference origin-relative paths.)

## 3. Install banner component

New `src/components/InstallBanner.tsx`:
- Listens for `beforeinstallprompt` (stashes the event, calls `preventDefault`).
- Shows a bottom sheet 30 s after mount, only if:
  - the event fired (or iOS Safari detected for an instruction variant),
  - `localStorage.trendrop_install_dismissed` is not set,
  - app is not already in `display-mode: standalone`.
- Sheet content: title "Install Trendrop on your home screen", subtitle "Get instant trend alerts", primary button **Install** → calls `prompt()` then awaits `userChoice`, secondary button **Not now** → sets the localStorage flag and hides.
- Slide-up animation via existing Tailwind/tw-animate utilities; positioned above the `BottomTabBar`.
- Mounted once in `__root.tsx`.

## 4. Service worker (vite-plugin-pwa, guarded)

Per the PWA skill rules (must not register in Lovable preview/dev):

- Install `vite-plugin-pwa` and add it to `vite.config.ts` with:
  - `registerType: "autoUpdate"`
  - `injectRegister: null` (we register manually from a wrapper)
  - `devOptions: { enabled: false }`
  - `filename: "sw.js"`
  - `manifest: false` (we ship our own `public/manifest.webmanifest`)
  - Workbox: precache built assets; runtime caching:
    - Navigations (HTML): `NetworkFirst`
    - Same-origin hashed assets: `CacheFirst`
    - `/api/*` requests to `VITE_API_URL`: `NetworkFirst` with short timeout
    - Exclude `/~oauth` from navigation fallback
- Create `src/lib/pwa-register.ts` wrapper that refuses to register when:
  - `!import.meta.env.PROD`, inside iframe, hostname matches `id-preview--*`, `preview--*`, `*.lovableproject.com`, `*.lovableproject-dev.com`, `*.beta.lovable.dev`, or URL has `?sw=off`.
  - In refused contexts, unregister any existing `/sw.js`.
- Call the wrapper from `src/router.tsx` or `__root.tsx` client mount.

## Technical notes

- The project has no `index.html` to edit directly (TanStack Start shellComponent owns `<head>`), so manifest + meta tags go through `__root.tsx`'s `head()`.
- Service worker only activates on the published deployment; preview will not register one — this is expected and matches Lovable PWA guardrails.
- Tell the user after build: installed-app manifest fields are cached at install time; future changes to `start_url`/`name` may require reinstall.

## Files

- create `public/manifest.webmanifest`
- create `public/icon-192.png`, `public/icon-512.png` (via imagegen)
- create `src/components/InstallBanner.tsx`
- create `src/lib/pwa-register.ts`
- edit `src/routes/__root.tsx` (head tags + mount `<InstallBanner />`)
- edit `vite.config.ts` (add VitePWA plugin)
- run `bun add -d vite-plugin-pwa`
