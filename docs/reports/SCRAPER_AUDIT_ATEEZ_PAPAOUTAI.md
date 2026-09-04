# Scraper Audit: ATEEZ BAD & Papaoutai — Then vs Now

> Strictly observational — no code changes. All evidence pulled from logs, git history, and pipeline records.

---

## 1. When Were These Audios First Scraped?

### ATEEZ — BAD

| Data Point | Value |
|---|---|
| **First appearance in pipeline.log** | `2026-08-15 13:30:49` (trend_engine querying `reels` with `created_at≥2026-08-13T08:00:49`) |
| **Implies first scraped into `reels` table** | **~Aug 13, 08:00 UTC** (the `created_at` lower-bound in that query is the trend's first detection window) |
| **Trend DB events (trend_engine.log)** | `2026-08-31 00:16:01` — trend id=1522 updated `expired → emerging` |
| **Trend refresher (trend_refresher.log)** | `2026-08-28 21:09` — refresher querying reel counts against `Mix: ATEEZ • BAD | capitalbuzz • Original audio` (a remixed version) |
| **Gap before blowup** | ~2.5–3 weeks between first scrape (Aug 13) and it appearing in your feed as going viral |

### Papaoutai (Afro Soul) — Stromae

| Data Point | Value |
|---|---|
| **Trend DB events (trend_engine.log)** | `2026-08-31 00:16:22` and `00:17:05` — trend id=1504 updated `expired → emerging` (twice, from two parallel pipeline runs) |
| **First scraped into `reels`** | Not directly visible in local pipeline.log — the trend existed in the DB with status `expired` before Aug 31, meaning it was originally scraped **before** Aug 31 and went through `emerging → rising → peaked → expired` before being recovered |
| **Notes** | The "Afro Soul" variant label suggests this was scraped under the `#dancechallenge` or `#GLOBAL_DISCOVERY` pool, not the India-trending pool |
| **Gap** | Same pattern — scraped early, went through lifecycle, then revived when momentum returned |

> [!NOTE]
> The pipeline queries ATEEZ BAD with a 48-hour `created_at` window (Aug 13 → queried on Aug 15), which is consistent with the trend being created on Aug 13 and the trend engine detecting it 2 days later after reel count accumulated.

---

## 2. Which Scraper Was Running at Time of Discovery?

### Git State on Aug 13 (ATEEZ scrape day)

The last meaningful scraper commit **before Aug 13** was:

```
70dfabdd  2026-08-09  fix(scraper): 10 data quality improvements across pipeline
fa136d6b  2026-08-09  feat: phase 2 — audio page scraper, personalized ranking, saturation downranking
76b54807  2026-08-07  Implement complete early trend detection system with 3 detection tiers
                      (4 micro-creator hashtag pools: MICRO_DANCE, MICRO_FOOD, MICRO_FASHION, MICRO_COMEDY)
```

The scraper that captured ATEEZ BAD on Aug 13 was running **the Aug 9 version** of `instagram_scraper_browser.py`.

---

## 3. Aug 9 Scraper vs Current Scraper — Key Differences

### A. GLOBAL_DISCOVERY Hashtag Pool (the one that catches cross-language trending audios)

| Version | GLOBAL_DISCOVERY tags |
|---|---|
| **Aug 9 (ATEEZ scrape era)** | `"trending", "viral", "reels", "fyp", "explore", "instareels", "viralreels", "reelsviral", "tiktok", "aesthetic", "music", "travel"` |
| **Aug 16 fix** | `"music", "trendingaudio", "trendingsong", "viralsong", "musictrend", "viralmusic", "reelsound", "dancechallenge", "popmusic", "hiphopreels", "edmmusic", "kpopreels", "viral", "trending"` |
| **Current (HEAD)** | `"trending", "viral", "music", "trendingaudio", "dancechallenge", "trendingsong", "viralsong", "musictrend", "viralmusic", "reelsound", "popmusic", "hiphopreels", "edmmusic", "kpopreels"` |

**Key observation:** In the Aug 9 era, `"viral"`, `"trending"`, `"fyp"`, `"reels"` were at the **front** of `GLOBAL_DISCOVERY`. These are the broadest possible tags — scraping them dumps you into Instagram's genuinely trending feed, which would have surface ATEEZ BAD naturally since it was picking up in South Korea and globally.

The Aug 16 restructure replaced generic viral/trending with **audio-specific tags** (`trendingaudio`, `viralsong`, etc.). These are more precise but **narrower** — they only catch content that's already hashtagged as "trending audio," which creators do *after* something blows up, not while it's building.

`"fyp"`, `"instareels"`, `"reelsviral"`, `"tiktok"` — **all dropped** in the current version.

### B. India-mode Pool Composition (what runs on every cycle)

| Version | India pool (priority_pool) |
|---|---|
| **Aug 9** | `INDIA_TRENDING[:N] + INDIA_VERNACULAR[:N] + GLOBAL_NICHES[:?] + GLOBAL_DISCOVERY[:N]` |
| **Current** | `INDIA_TRENDING[:6] + INDIA_VERNACULAR[:6] + EVENT_HASHTAGS[:5] + FITNESS[:1] + FOOD[:1] + COMEDY[:1] + DANCE[:2] + GLOBAL_DISCOVERY[:5]` |

**Key observation:** The current version runs **only 5 tags from GLOBAL_DISCOVERY** per cycle (`trending`, `viral`, `music`, `trendingaudio`, `dancechallenge`). In the Aug 9 era, the GLOBAL_DISCOVERY pool was scraped more aggressively (broader tags, fewer India-specific ones crowding it out).

Also notable: **`GLOBAL_NICHES` is referenced in the current India pool code but the group doesn't exist** in `hashtag_groups` — it was removed/renamed but the reference remains dead. This silently drops 3 hashtag slots every cycle.

### C. Velocity Formula Changes

| Change | Aug 9 | Current |
|---|---|---|
| **Comment weight** | `comments * 5.0` | `comments * 3.0` (reduced 5x→3x, per commit `94275ebc`) |
| **24h exponential decay** | ❌ Not present | ✅ Added (`decay_factor = 0.5^(hours_live/24)`) |
| **Unknown followers** | Default 2500 used in denominator | ❌ **Skipped entirely** (`scrape_stats["unknown_followers_skipped"] += 1; continue`) |
| **Outlier detection** | Not present | ✅ Added (`CREATOR_OUTLIER_MULTIPLIER=5.0`) |
| **Low-engagement floor** | Applied | Still applied (2000 views OR 50 likes) |

**The follower skip is significant.** In the Aug 9 scraper, when a reel had no follower data, it fell back to 2500 (a modest denominator → higher velocity score → reel passes filter). Now those reels are **completely skipped**. ATEEZ BAD reels from smaller K-pop fan accounts (micro-creators with no baseline yet) would have been skipped entirely under the current formula if their follower count wasn't in `creator_baselines`.

The **24h decay** also matters a lot for early signals: a 6-hour-old reel with 140k views gets `decay_factor = 0.5^(6/24) = 0.84` (modest). But a 48-hour-old reel with 300k views gets `decay_factor = 0.5^(48/24) = 0.25` — **75% penalty**. Old reels that are accumulating normally get killed by decay. This was intentional (prevent stale reels from inflating scores) but it also means a reel that's genuinely building over days loses score every passing hour.

---

## 4. Your Concern About 100K-Follower Creators with 140K Views

You're right that this is "normal" engagement and not viral signal. The velocity formula:

```
velocity = (views + likes*3 + comments*3) / hours_live / log(followers+10) * 100
```

For a 100K follower creator with 140K views in 48 hours:
- `engagement ≈ 140,000 + (likes~5000)*3 + (comments~500)*3 = 157,500`
- `hours_live = 48`
- `normalized_followers = log(100,000+10) ≈ 11.51`
- `velocity_raw = (157,500 / 48 / 11.51) * 100 ≈ 2,851`
- After 48h decay: `velocity_final = 2,851 * 0.25 ≈ 713`

This passes `velocity > 0.3` trivially. The formula does **not** distinguish between "100K creator getting their baseline 140K views" vs "100K creator going 10x viral." The outlier check (`view > 5 * median_views`) is the only defense, but only fires if `creator_baselines` has at least 6 posts for that creator.

**In the ATEEZ era (Aug 9), the same problem existed** — but you were hitting `"viral"` and `"fyp"` as your GLOBAL_DISCOVERY tags, which meant the Instagram algorithm was pre-filtering content for you. The hashtag feed for `#viral` already has IG's own ranking applied, so genuinely viral content naturally surfaced. Now you're scraping more niche audio-specific tags where the curation is different.

---

## 5. What Trend Did You Miss Recently?

You mention a trend building in your feed that the scraper missed. This is consistent with the pattern:

1. **GLOBAL_DISCOVERY is now music-tag focused, not viral-feed focused** — a trend building on `#reels`, `#fyp`, or broad organic reach won't be captured
2. **Unknown-follower reels are fully dropped** — early adopters of a trend are often micro-creators whose follower counts aren't in `creator_baselines`  
3. **Decay penalizes slow-building trends** — a trend that builds over 3-7 days loses score every hour under the current decay formula
4. **DANCE pool only gets 2 tags** (`dancechallenge`, `choreography`) — if the trend is coming from the dance space, only 2 of 10 dance tags are scraped per cycle

---

## 6. Summary: Then vs Now

```
ATEEZ BAD (Aug 13 scrape)         TODAY
─────────────────────────────────  ──────────────────────────────────
GLOBAL_DISCOVERY: "viral", "fyp"   GLOBAL_DISCOVERY: "trendingaudio"
                  "trending",                         "viralsong"
                  "reelsviral"                        (no fyp, no reelsviral)
                  
Comment weight: 5x                 Comment weight: 3x
Unknown followers: fallback 2500   Unknown followers: SKIPPED
Decay: none                        Decay: 50% every 24h
GLOBAL_NICHES: present             GLOBAL_NICHES: dead reference (dropped)
All 15 GLOBAL tags used in global  Only top 5 GLOBAL tags in india mode
Scraper running every 6–8h         Scraper cadence unchanged
```

**The ATEEZ + Papaoutai detections worked because the scraper was hitting `#viral`, `#fyp`, and `#trending` — IG's own curated surfaces — instead of music-specific tags that require creators to self-tag. The shift to audio-specific tags was intended to reduce noise, but it traded discovery breadth for precision.**

---

## 7. Open Questions for You to Consider (No Code Yet)

- Do you want to bring `#fyp`, `#reels`, `#reelsviral` back into GLOBAL_DISCOVERY for at least 2-3 slots?
- Should `GLOBAL_NICHES` be removed from the pool composition line (dead reference), or should the group be reconstituted?
- Is the 24h decay appropriate for the *scraping* stage, or should it only apply in *trend_engine* scoring (after enough reels have been accumulated)?
- Should unknown-follower reels use a fallback (e.g., 2500) instead of being dropped — particularly for the first cycle before baselines exist?

---

## 8. New Research: The TikTok→Instagram Migration Problem (DJ Pika / Daublegum Case Study)

### The Exact Scenario You Described

This is a distinct class of trend that the scraper **fundamentally cannot currently detect**:

1. **Origin account** (`@daublegum`): A dance creator with ~26K IG followers but **600K+ TikTok followers** — a TikTok-first creator. Their IG content averages low views with occasional spikes (1.9M on the viral reel). They cross-post to both platforms but IG is secondary.

2. **The audio** (`DJ Pika – Concrete Veins`): Gained traction on TikTok first. When `@daublegum` posted a dance reel on IG using it, Instagram attributes the audio as **"Original Audio"** because either the music license isn't active on IG, or the creator's upload gets recorded under `original_sound_info.ig_artist = @daublegum`.

3. **Indian creator adoption**: A large Indian creator discovers the trend (likely from TikTok or their global feed) and recreates it using `@daublegum`'s original sound. Instagram displays this as "Original Audio" with a link to `@daublegum`'s page.

4. **Momentum potential**: The TikTok popularity is real but invisible on IG. More Indian creators pile on → what starts as a global TikTok trend becomes a local Indian breakout. This is the exact delayed adoption pattern that creates "trends that blow up 3 weeks later."

---

### Why the Scraper Is Completely Blind — Four Invisibility Layers

#### Layer 1: The Original Audio Hard Block ← **Most Critical**

In [`trend_engine.py` L802–816](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/trend_engine.py#L802-L816):

```python
is_original_audio = (
    title.lower() in ("original audio", "original sound", "")
    or title.lower().startswith("original_audio::")
    or any(r.get("is_original_audio") is True for r in group_reels)
)
if is_original_audio:
    continue  # ← FULL HARD SKIP — never becomes a trend
```

The `@daublegum` reel is recorded as `original_sound_info` by Instagram. In [`instagram_scraper_browser.py` L728–740](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/instagram_scraper_browser.py#L728-L740), `is_orig = True` is set **unless** `use_count >= 50`. On first detection, `use_count` is often below 50 → `is_original_audio = True` → whole audio group dropped.

**The secondary safeguard at L1444–1448** also can't save it: it only flips the flag if 2+ different creators have already posted using the same audio ID. On first encounter, only `@daublegum` has posted → still blocked.

#### Layer 2: Follower Count → Velocity Math (Actually Works in Their Favor)

`@daublegum` has 26K followers. For the 1.9M view reel at 48h old:
- `velocity_raw ≈ (2,215,000 / 48 / log(26010)) * 100 ≈ 453,000`
- After decay: `≈ 113,000`

**This would easily pass `velocity > 0.3`**. The low follower count is actually a *benefit* in the formula — lower denominator = higher ratio. So this layer is not the problem. **The original audio block fires before velocity ever gets calculated for trend detection.**

#### Layer 3: creator_baselines Gap

`@daublegum` has never been scraped via Indian hashtags → no entry in `creator_baselines`. The outlier check (requires `post_count >= 6` in baseline) doesn't fire. They're treated as a generic unknown creator. **Moot, because the audio block fires first.**

#### Layer 4: Hashtag Coverage

A TikTok-migrated trend from a 26K-follower IG creator won't appear in `#trendingindia` or `#trendingaudio`. It appears in `#dancechallenge` or `#choreography` (2 of the current India pool tags). At 5/22 probability of any given run including those, and the pool cycling, detection chance per cycle is low.

---

### What the Instagram API Already Gives You (Being Discarded)

For a reel using `@daublegum`'s original sound, Instagram's `original_sound_info` payload contains:

```json
{
  "audio_asset_id": "<unique_id>",
  "original_audio_title": "Original Audio",
  "ig_artist": {
    "username": "daublegum",          ← Already extracted at L732-733
    "follower_count": 26000           ← Sometimes present
  },
  "consumption_info": {
    "use_count": 847                  ← Already extracted at L770-772
  }
}
```

The `ig_artist.username` is **already being extracted** by the scraper. The `consumption_info.use_count` is **already being extracted**. Both are being thrown away when `is_original_audio = True` is set.

---

### The Core Signal: Views-to-Follower Ratio on the Audio Source Creator

The pattern has a clear fingerprint that differentiates "random original audio" from "TikTok-imported hit":

| Signal | Daublegum value | Interpretation |
|---|---|---|
| `ig_artist` follower count | ~26K | Small IG presence |
| Reel `view_count` | 1.9M | **73x follower count** |
| `original_sound_info.use_count` | Growing → 847+ | Multi-creator adoption in progress |
| `ig_artist` has high TikTok | 600K TikTok | Platform-spillover origin |
| Large Indian creator using the sound | Yes | Cross-cultural adoption beginning |

A **view_count / ig_artist_followers ratio > 15–20x** is a strong TikTok-migration fingerprint. Organic IG-native creators with 26K followers don't get 1.9M views without being surfaced by IG's algorithm responding to cross-platform momentum. This ratio, combined with a growing `use_count`, is the early signal.

Normal IG creator getting their "usual good performance":
- 100K followers × 1.5x = 150K views → ratio = 1.5x → not a signal

TikTok-migrated breakout:
- 26K followers × 73x = 1.9M views → **ratio = 73x → signal**

---

### Design Logic to Detect This (Research Only — No Code)

#### Option A: Tiered Original Audio by use_count

Instead of blanket-blocking all original audio:

```
original_sound_info present?
├── use_count < 10  → SKIP (private audio, single creator)
├── use_count 10–49 → STORE passively (no trend yet, watch for growth)
└── use_count ≥ 50  → TREAT like named audio (eligible for trend detection)
     └── PLUS: if view_count / ig_artist_followers > 15x → BOOST priority
```

The 50-use cutoff is already coded into the scraper's `is_orig` flag (L738–739) but the trend engine ignores it — it hard-blocks anything with `is_original_audio = True` regardless. The fix would be to pass `use_count` context into trend detection and skip the hard-block when count ≥ 50.

#### Option B: ig_artist Ratio Check as Breakout Override

At scraper time, when `ig_artist` is extracted from `original_sound_info`:

```
if ig_artist_username is present:
    check view_count from current reel payload
    if view_count / ig_artist_followers > 15x AND use_count > 20:
        flag reel as "potential_crossplatform_breakout"
        set is_original_audio = False  (override)
        set source_hashtag_pool = "CROSS_PLATFORM"
```

This doesn't require external API calls — `follower_count` is sometimes in the `ig_artist` object, and `view_count` is already in the reel payload. If `follower_count` is missing, a `creator_baselines` lookup could fill it.

#### Option C: use_count Velocity Tracking Across Cycles

For original audio that crosses the 50-use threshold, store `(audio_id, use_count, scraped_at)` — similar to what `audio_official_counts` already does for music-library audio. If `use_count` grew 2x+ in 8 hours → treat as trending original audio, eligible for trend detection. This mirrors the existing infrastructure without requiring a new system.

#### What Would NOT Work

- **Scraping TikTok directly**: No API access, and TikTok scraping is legally/technically hostile
- **Watching all original audio without filtering**: 95%+ of original audio is private one-off content; need the use_count filter
- **Waiting for the big Indian creator to trigger detection**: By then the trend is already established — you'd be late, not early
- **Relying on hashtag discovery alone**: TikTok-import trends don't get tagged with audio-specific hashtags initially; they travel through creator networks, not hashtag feeds

---

### The Missed Trend in Your Feed Right Now — Root Cause

Applying this to `DJ Pika – Concrete Veins` / `@daublegum`:

1. Audio is `original_sound_info` on Instagram → `is_original_audio = True`
2. Even if the reel appears in `#dancechallenge`, trend engine drops the entire audio group at L811
3. Even if `use_count` is 847+ (well past the 50 threshold), the current code never checks this at the trend detection gate
4. The Indian creator's large-follower version using the same original sound → also labeled original audio → also dropped
5. **You see it in your feed** because Instagram's own Reels algorithm aggregates all engagement across every reel using that `audio_asset_id` — an internal signal your scraper never accesses

---

## 9. Updated Full Summary: 7 Root Causes

| # | Problem | Root Cause File | Severity |
|---|---|---|---|
| 1 | No `#fyp`/`#viral` in GLOBAL_DISCOVERY | `instagram_scraper_browser.py` L205–211 | Medium |
| 2 | 24h decay killing slow-build trends | `instagram_scraper_browser.py` L1293–1297 | Medium |
| 3 | Unknown followers hard-skipped | `instagram_scraper_browser.py` L1287–1289 | Medium |
| 4 | `GLOBAL_NICHES` dead reference | `instagram_scraper_browser.py` L1803 | Low (3 slots/cycle) |
| 5 | **Original audio hard-blocked** | **`trend_engine.py` L802–816** | **Critical** |
| 6 | **use_count threshold not honored at trend gate** | **`trend_engine.py` L806–816** | **Critical** |
| 7 | **ig_artist ratio signal ignored** | **`instagram_scraper_browser.py` L732–740** | **High** |

---

## 10. Open Questions (All, No Code Yet)

**From original audit (Section 7):**
- Restore `#fyp`, `#reelsviral` in GLOBAL_DISCOVERY (2–3 slots)?
- Remove or restore `GLOBAL_NICHES` from pool composition?
- Move 24h decay from scraping stage to trend_engine only?
- Restore unknown-follower fallback (2500) instead of hard skip?

**New from TikTok migration research (Section 8):**
- Change original audio from hard-block to tiered: skip <10 use, watch 10–49, admit ≥50?
- Add `ig_artist.view_count / followers > 15x` as breakout override signal?
- Extend `audio_official_counts`-style tracking to original audio IDs that cross 50-use threshold?
- Add `CROSS_PLATFORM` as a new `source_hashtag_pool` label for original-sound breakouts so they can be tracked separately?
