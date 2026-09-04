# Global Trend Discovery Investigation Report

## STEP 1: Audio Use Count Population Analysis

### Findings:

**✗ CHICKEN-AND-EGG BUG CONFIRMED**

After analyzing the scraper code in `instagram_scraper_browser.py`, I found that `audio_use_count` is populated through a complex fallback mechanism:

1. **Primary Source (Lines 686-716):** Attempts to extract `use_count` from Instagram's API response via:
   - `music_info -> music_consumption_info -> use_count`
   - `music_info -> music_asset_info -> use_count/usage_count/reel_count`
   - `original_sound_info -> consumption_info -> use_count`

2. **Fallback 1 (Lines 718-736):** Uses previously scraped `audio_official_counts` from the `tracked_audio` table if available.

3. **Fallback 2 (Lines 738-777):** Calculates a proxy based on existing reels in the database for that `audio_id`.

**Critical Issue:** The `tracked_audio` table (Lines 1533-1548) only gets populated when:
- An audio is non-original (`is_original_audio = False`)
- The audio has **≥2 reels** in the database already
- The scraper has already scraped at least 2 reels for that audio

**The Chicken-and-Egg Problem:**
- A new global trend (like "Beretta") cannot reach the 2-reel threshold to get into `tracked_audio`
- Without being in `tracked_audio`, it won't get official count scraping via `scrape_official_audio_counts` (Lines 1646-1701)
- Without official counts, `audio_use_count` falls back to proxy calculation or 0
- With 0 or low proxy counts, it can't reach the emerging threshold in `trend_engine.py`

**Independent Fix Required:** This bug needs to be fixed separately from the Beretta case. The `tracked_audio` enrollment logic should be more aggressive for high-velocity emerging content, and the official count scraping should not be gated on the 2-reel threshold.

---

## STEP 2: Global Discovery Build Plan (Option 1 - Proper Scale)

### Architecture Overview:

Build a systematic global trend discovery system that:
1. Pulls candidates from Spotify and YouTube across ALL major markets (not India-specific)
2. Validates against real Instagram usage via existing Camoufox/Playwright scraper
3. Groups derivative/remix versions under base trends
4. Only feeds into `trend_engine.py` once Instagram usage is confirmed
5. Maintains separate discovery tracking for global vs India-originated trends

### Phase 1: External Platform Integration

**File:** `backend/global_trend_sources.py` (NEW)

```python
# Major markets to cover:
MARKETS = [
    # Americas
    "US", "BR", "MX", "AR", "CO", "CL", "PE",
    # Europe
    "GB", "DE", "FR", "IT", "ES", "NL", "PL", "SE",
    # Asia-Pacific
    "JP", "KR", "AU", "ID", "PH", "TH", "VN", "MY",
    # Middle East
    "SA", "AE", "TR",
    # Africa
    "ZA", "NG", "EG"
]

# Spotify endpoints:
- GET /v1/browse/categories/{category_id}/playlists
- GET /v1/playlists/{playlist_id}/tracks
- Viral 50 playlists for each region
- New Releases by region
- Top 50 by region

# YouTube endpoints:
- GET /youtube/v3/videos?part=snippet,contentDetails,statistics
- GET /youtube/v3/search?part=snippet&type=video&order=viewCount
- Region-specific trending: /youtube/v3/videos?part=snippet&chart=mostPopular&regionCode={region}
- Music category filters
```

### Phase 2: Instagram Validation Layer

**File:** `backend/global_trend_validator.py` (NEW)

```python
# For each external candidate:
1. Audio search via existing Camoufox scraper
2. Extract reel_count and growth metrics
3. Check for derivative versions (slowed+reverb, sped up, remixes)
4. Indian creator crossover detection:
   - Check if top creators have Indian names/bios
   - Cross-reference with existing creator_profiles
   - Geographic analysis of reel locations
```

### Phase 3: Derivative Grouping System

**File:** `backend/trend_normalization.py` (NEW)

```python
# Group related audio tracks:
- Base track vs remix/cover detection
- Version grouping (original, slowed+reverb, sped up, nightcore)
- Fingerprint-based grouping using audio metadata
- Master trend record with sub-variants
```

### Phase 4: Integration with trend_engine.py

**File:** `backend/trend_engine.py` (MODIFY)

```python
# Add discovery_source field to trend lifecycle:
- "hashtag_pool" (existing India-focused)
- "global_external" (new global discovery)
- "manual_entry" (admin-added)

# Separate scoring logic per source:
- Global candidates get higher initial velocity thresholds
- India-specific signals only apply to hashtag_pool sources
- Global trends require broader creator diversity
```

### Phase 5: Database Schema Updates

**File:** `backend/database_setup.py` (MODIFY)

```sql
-- Add discovery tracking
ALTER TABLE trends ADD COLUMN discovery_source VARCHAR(50) DEFAULT 'hashtag_pool';
ALTER TABLE trends ADD COLUMN external_platform VARCHAR(50); -- 'spotify', 'youtube', 'manual'
ALTER TABLE trends ADD COLUMN external_rank INTEGER; -- Position in chart
ALTER TABLE trends ADD COLUMN external_region VARCHAR(10); -- Market code
ALTER TABLE trends ADD COLUMN base_trend_id INTEGER REFERENCES trends(id); -- For derivative grouping

-- Create external candidates table
CREATE TABLE external_trend_candidates (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50), -- 'spotify', 'youtube'
    track_id VARCHAR(100), -- Spotify track ID or YouTube video ID
    track_name TEXT,
    artist_name TEXT,
    region VARCHAR(10),
    chart_position INTEGER,
    chart_type VARCHAR(50), -- 'viral_50', 'top_50', 'trending'
    scraped_at TIMESTAMP DEFAULT NOW(),
    validated BOOLEAN DEFAULT FALSE,
    instagram_reel_count INTEGER DEFAULT 0,
    indian_creator_count INTEGER DEFAULT 0,
    promoted_to_trend BOOLEAN DEFAULT FALSE,
    UNIQUE(platform, track_id, region, chart_type)
);
```

### Phase 6: Deployment Architecture

**File:** `.github/workflows/global-discovery.yml` (NEW)

```yaml
# Separate daily workflow (independent of 8h scraper.yml)
# Runs at 00:00 UTC daily
# - Pulls external platform data (Spotify + YouTube)
# - Validates against Instagram
# - Promotes validated candidates to trend_engine
# - Archives rejected candidates
```

---

## STEP 3: Cost/Infrastructure Impact Analysis

### Spotify API Costs:

**Free Tier (Development Mode):**
- **Quota:** Per developer account (shared across all apps)
- **Rate Limit:** Rolling 30-second window (specific limits not publicly disclosed)
- **Restrictions (Feb 2026 changes):**
  - Requires Spotify Premium subscription ($10.99/month)
  - 1 Client ID per developer (increased to 25 in July 2026)
  - Max 5 authorized users per app
  - `limit` parameter max reduced from 50 to 10

**Estimated Daily Usage:**
- Viral 50 playlists: ~50 markets × 1 playlist = 50 calls
- Top 50 playlists: ~50 markets × 1 playlist = 50 calls  
- New Releases: ~50 markets × 1 playlist = 50 calls
- Playlist track details: ~150 playlists × 50 tracks/playlist = 7,500 calls
- **Total: ~7,650 calls/day**

**Verdict:** Free tier may be insufficient. Recommend applying for Extended Quota Mode once usage patterns are established.

### YouTube API Costs:

**Free Tier:**
- **Default Quota:** 10,000 units/day
- **Search.list:** 100 units/call (limit: 100 calls/day)
- **Videos.list:** 1 unit/call
- **Other endpoints:** 1-50 units/call

**Estimated Daily Usage:**
- Trending videos by region: ~20 regions × 1 call = 20 units
- Video details for trending: ~500 videos × 1 unit = 500 units
- Search for music-specific content: ~50 searches × 100 units = 5,000 units
- **Total: ~5,520 units/day**

**Verdict:** Free tier is adequate for initial implementation. Monitor usage and request quota extension if needed.

### GitHub Actions Impact:

**Current Usage:** ~1,145 minutes/month (scraper.yml)
**New Workflow:** `global-discovery.yml` (daily, ~15-20 minutes/run)

**Estimated Additional Cost:**
- Daily execution: 20 minutes × 30 days = 600 minutes/month
- **Total: ~1,745 minutes/month**

**Plan Considerations:**
- **GitHub Free:** 2,000 minutes/month (headroom: 255 minutes)
- **GitHub Pro:** 3,000 minutes/month (headroom: 1,255 minutes)
- **Public Repository:** Free unlimited minutes

**Verdict:** If using private repo, upgrade to GitHub Pro recommended for headroom. If public repo, no additional cost.

### Monthly Cost Summary:

| Service | Tier | Monthly Cost | Notes |
|---------|------|---------------|-------|
| Spotify API | Free (with Premium) | $10.99 | Required for Dev Mode |
| YouTube API | Free | $0 | Within 10k quota |
| GitHub Actions | Free tier | $0 | If public repo |
| GitHub Actions | Pro tier | $4/month | If private repo |
| **Total (Public)** | - | **$10.99** | Spotify Premium only |
| **Total (Private)** | - | **$14.99** | Spotify + GitHub Pro |

---

## STEP 4: Implementation Recommendation

### Priority Actions:

1. **Fix Chicken-and-Egg Bug (Independent):**
   - Modify `tracked_audio` enrollment logic to be more aggressive
   - Remove 2-reel threshold for high-velocity content
   - Implement queue-based official count scraping for new audio

2. **Build Global Discovery System:**
   - Start with 5-10 key markets (US, GB, BR, MX, JP, KR, DE, FR, AU, IN)
   - Implement Spotify Viral 50 integration first (higher signal-to-noise)
   - Add YouTube trending music after Spotify is stable
   - Deploy as separate daily workflow to preserve scraper.yml optimization

3. **Derivative Grouping:**
   - Implement basic title/artist normalization first
   - Add audio fingerprint grouping in Phase 2
   - Manual curation interface for edge cases

4. **Monitoring & Iteration:**
   - Track validation rate (external candidates → confirmed trends)
   - Monitor false positive rate
   - Adjust velocity thresholds based on regional patterns

### Timeline Estimate:

- **Phase 1 (Fix Bug):** 2-3 days
- **Phase 2 (Spotify Integration):** 5-7 days
- **Phase 3 (Instagram Validation):** 3-5 days
- **Phase 4 (Derivative Grouping):** 5-7 days
- **Phase 5 (trend_engine Integration):** 3-5 days
- **Phase 6 (Deployment):** 2-3 days

**Total: 20-30 days for full implementation**

### Risk Mitigation:

- Start with limited market set, expand gradually
- Implement rate limiting and quota monitoring
- Use caching to reduce redundant API calls
- Manual approval workflow for auto-promoted trends
- Rollback mechanism to disable global discovery if issues arise

---

## Next Steps:

1. **Approval Required:** Confirm if you want to proceed with this global-scale implementation
2. **Budget Approval:** Confirm budget for Spotify Premium ($10.99/month) and potential GitHub Pro upgrade ($4/month)
3. **Market Selection:** Confirm initial market set (recommend 10 markets to start)
4. **Priority Decision:** Should we fix the chicken-and-egg bug first, or proceed with global discovery in parallel?

**Awaiting your go-ahead before implementing.**