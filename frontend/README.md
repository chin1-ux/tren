# ⚡ Trendrop — India's Trend Intelligence Platform

Trendrop is an AI-powered trend intelligence platform tailored for the Indian creator economy. It helps creators, brands, and agencies identify emerging audio tracks, content formats, and viral hooks before they saturate social networks.

---

## 🚀 Key Features

### 1. **AI Trend Feed**
- Real-time tracking of emerging regional and national trends.
- Detailed metrics including compatibility, velocity, and cross-cultural reach.
- Beautiful interactive visual previews with reels fallbacks.

### 2. **Creator Studio**
- **Pre-Post Audit**: Evaluate posting time, audio alignment, hashtags, and SEO keywords.
- **Hook Formulas**: Instantly generate 5 high-converting hook patterns for your niche.
- **SEO Caption Optimizer**: Tailored descriptions, accessibility alt text, and search keywords.

### 3. **Creator Marketplace**
- **Brand Deals Portal**: Submit applications for active sponsor campaigns.
- **Co-Creator Matchmaking**: Connect with local creators based on audience overlap, follower ratios, and aesthetic harmony.

### 4. **Adaptive Theme Engine**
- Seamless dark and light mode toggle.
- Synchronized globally across all application states via window event messaging to prevent flashes or style desyncs.

---

## 🛠️ Technology Stack

- **Frontend Core**: React 18, TypeScript, TanStack Start (Vite + Router + SSR)
- **Styling**: Tailwind CSS v4 (incorporating `@theme` variables inside `styles.css`), Framer Motion
- **Database & Auth**: Supabase JS Client integration
- **Backend Service**: Serverless Python API mapping DB schemas, Cron scraper loops, and Instagram scrapers.

---

## ⚙️ Getting Started

### Prerequisites
- Node.js (v18 or higher)
- npm or yarn

### Development Server
Run the app locally with live reloading:
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

### Production Build
Compile client-side chunks and server-side Edge functions optimized for Vercel deployment:
```bash
npm run build
```

---

## 📂 Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI parts (BottomTabBar, ThemeToggle, TrendCard)
│   ├── lib/             # API services & Supabase client setup
│   ├── routes/          # TanStack file-based routes (__root, generate, marketplace)
│   └── styles.css       # Global design tokens and tailwind configurations
├── vercel.json          # Deployment configurations
└── package.json         # Scripts and dependencies
```

---

*Made with 💖 for the next generation of Indian Creators.*
