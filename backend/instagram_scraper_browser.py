import os
import json
import logging
import os
import re
import time
import math
import signal
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from classification_rules import build_source_hashtag_pool, classify_content_tone, classify_niche
import requests

# Camoufox stealth browser (install with: pip install 'camoufox[geoip]' && python -m camoufox fetch)
try:
    from camoufox.async_api import AsyncCamoufox as CamoufoxBrowser
    _CAMOUFOX_AVAILABLE = True
except ImportError:
    CamoufoxBrowser = None  # type: ignore
    _CAMOUFOX_AVAILABLE = False

try:
    logging.basicConfig(
        filename="instagram_scraper_browser.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass
logger = logging.getLogger(__name__)

def calculate_saturation(audio_use_count: int, india_use_count: int) -> dict:
    global_pct = min(100.0, (audio_use_count / 100_000) * 100)
    india_pct = min(100.0, (india_use_count / 8_000) * 100)
    return {
        "global": round(global_pct, 1),
        "india": round(india_pct, 1),
    }

def calculate_window_hours(audio_use_count: int, velocity_pct: float) -> int:
    if audio_use_count > 100_000:
        return 0
    if velocity_pct > 300 and audio_use_count < 20_000:
        return 8
    if velocity_pct > 150 and audio_use_count < 50_000:
        return 16
    if velocity_pct > 100 and audio_use_count < 80_000:
        return 24
    return 4


_INDIAN_ORIGIN_HINTS = (
    # Bollywood / Indian artists
    "arijit", "alka", "pritam", "rahman", "sachin", "amit", "neha", "vishal",
    "anirudh", "diljit", "shreya", "armaan", "badshah", "dhvani", "jubin",
    "neh", "ap dhillon", "from \"", "(from ", "from the movie",
    "anu malik", "hema sardesai", "sai abhyankkar", "gana muthu", "vishnu edavan",
    "jyotica tangri", "shaarib toshi", "kumaar", "tanishk", "bagchi", "badshah",
    "shreya ghoshal", "sonu nigam", "sunidhi", "shankar", "ehsaan", "loy", "udit narayan",
    "kumar sanu", "lata", "asha bhosle", "kishore", "rafi", "malik", "sardesai",
    "abhyankkar", "muthu", "edavan", "tangri", "toshi",
    # Music labels (India-specific)
    "t-series", "zee music", "sony music india", "tips music", "saregama",
    "speed records", "venus music", "jio saavn", "gaana", "hungama",
    "t series", "tseries", "lahari music", "aditya music",
    # Film industries
    "bollywood", "kollywood", "tollywood", "mollywood", "sandalwood",
    # Language-explicit song names
    "hindi song", "punjabi song", "tamil song", "telugu song", "kannada song",
    "hindi music", "punjabi music",
)

# Maps language keywords (in audio title / caption / hashtags) → ISO 639-1 code
LANG_KEYWORD_MAP: dict[str, str] = {
    "hindi": "hi", "bhojpuri": "hi", "hindisong": "hi", "hindireels": "hi",
    "hindi song": "hi", "hindi music": "hi",
    "punjabi": "pa", "punjabisong": "pa", "punjabisongs": "pa",
    "punjabi song": "pa", "punjabi music": "pa",
    "tamil": "ta", "tamilreels": "ta", "kollywood": "ta",
    "tamil song": "ta", "tamilsong": "ta",
    "telugu": "te", "telugureels": "te", "tollywood": "te",
    "telugu song": "te", "telugusong": "te",
    "kannada": "kn", "kannadareels": "kn", "sandalwood": "kn",
    "kannada song": "kn",
    "marathi": "mr", "marathireels": "mr", "marathisong": "mr",
    "marathi song": "mr",
    "malayalam": "ml", "mollywood": "ml", "malayalamsong": "ml",
    "bengali": "bn", "bengalireels": "bn", "bengalisong": "bn",
    "english": "en",
}

# Maps specific hashtags used as pool seeds → guaranteed language code (highest priority)
VERNACULAR_HASHTAG_LANG: dict[str, str] = {
    "hindireels": "hi", "bhojpurisong": "hi",
    "punjabisongs": "pa",
    "tamilreels": "ta",
    "telugureels": "te",
    "kannadareels": "kn",
    "marathireels": "mr",
    "bengalireels": "bn",
}

_INDIAN_LANG_CODES = {"hi", "pa", "ta", "te", "kn", "mr", "ml", "bn"}


def _detect_audio_language(
    audio_text: str,
    caption_text: str,
    hashtags: list[str] | None = None,
    source_hashtag_pool: str | None = None,
) -> str:
    """
    Detect audio language with a reliable priority chain:
    1. Vernacular hashtag (e.g. #tamilreels → ta) — most reliable
    2. Individual hashtag keyword match
    3. audio_text keyword match (song title / artist name)
    4. caption_text keyword match
    5. Devanagari script in caption → hi
    6. Default → en
    """
    # Priority 1: vernacular pool hashtag (100% reliable)
    for tag in (hashtags or []):
        clean = tag.lower().lstrip("#").replace(" ", "")
        if clean in VERNACULAR_HASHTAG_LANG:
            return VERNACULAR_HASHTAG_LANG[clean]

    # Priority 2: hashtag keyword → language map
    for tag in (hashtags or []):
        clean = tag.lower().lstrip("#")
        if clean in LANG_KEYWORD_MAP:
            return LANG_KEYWORD_MAP[clean]

    # Priority 3: audio title / artist text keyword match
    audio_lower = audio_text.lower() if audio_text else ""
    for keyword, lang_code in LANG_KEYWORD_MAP.items():
        if keyword in audio_lower:
            return lang_code

    # Priority 4: caption keyword match
    caption_lower = caption_text.lower() if caption_text else ""
    for keyword, lang_code in LANG_KEYWORD_MAP.items():
        if keyword in caption_lower:
            return lang_code

    # Priority 5: Devanagari script → Hindi
    if any("\u0900" <= ch <= "\u097f" for ch in caption_lower):
        return "hi"

    # Default
    return "en"


def _looks_indian_audio(title: str | None, artist: str | None, caption: str | None = None) -> bool:
    text = f"{title or ''} {artist or ''} {caption or ''}".lower()
    return any(hint in text for hint in _INDIAN_ORIGIN_HINTS)


def _normalize_trend_origin(meta: dict, reel: dict) -> dict:
    title = reel.get("audio_title") or reel.get("audio_name") or ""
    artist = reel.get("audio_artist") or ""
    caption = reel.get("caption") or ""
    caption_text = caption.lower()
    audio_text = f"{title} {artist}".lower()

    if _looks_indian_audio(title, artist, caption):
        meta["trend_origin"] = "IN"
        meta["creator_country"] = "IN"
        if "hindi" in caption_text or "देवनागरी" in caption_text:
            meta["audio_language"] = "hindi"
    elif meta.get("trend_origin") in {"KR", "BR", "RU", "US", "GB"} and "original audio" in audio_text:
        meta["trend_origin"] = "unknown"
        if meta.get("creator_country") == "unknown":
            meta["creator_country"] = "unknown"
    return meta

class InstagramScraper:
    def __init__(self):
        load_dotenv()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
        self._skip_instagram_warmup = os.getenv("CAMOUFOX_SKIP_INSTAGRAM_WARMUP", "1").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self._last_cookie_check = "not checked"
        self._last_browser_init = "not started"
        self._last_scrape_result = "not started"
        self._last_scrape_stats = {}
        
        # Dynamically create cookies.json from INSTAGRAM_COOKIES_B64 env var if missing
        cookies_path = os.path.join(script_dir, "cookies.json")
        if not os.path.exists(cookies_path):
            cookies_b64 = os.getenv("INSTAGRAM_COOKIES_B64")
            if cookies_b64:
                import base64
                try:
                    decoded = base64.b64decode(cookies_b64.strip()).decode("utf-8")
                    # Validate JSON
                    json.loads(decoded)
                    with open(cookies_path, "w", encoding="utf-8") as f:
                        f.write(decoded)
                    logger.info("Successfully reconstructed cookies.json from INSTAGRAM_COOKIES_B64 environment variable.")
                except Exception as b64_err:
                    logger.error(f"Failed to decode or write cookies from INSTAGRAM_COOKIES_B64: {b64_err}")
            else:
                logger.warning("cookies.json not found and INSTAGRAM_COOKIES_B64 environment variable is empty.")

        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self._camoufox_browser = None  # SyncCamoufox instance
        self._camoufox_ctx = None       # Playwright browser context
        self._camoufox_page = None      # Active page for scraping
        
        self.hashtag_groups = {
            "INDIA_TRENDING": [
                "trendingindia", "reelsindia", "instagramindia", "indiansong",
                "reelkarofeelkaro", "desimemes", "exploreindia"
            ],
            "INDIA_VERNACULAR": [
                "hindireels", "punjabisongs", "tamilreels", "telugureels",
                "kannadareels", "bhojpurisong", "marathireels"
            ],
            "GLOBAL_NICHES": [
                "fitnessreels", "foodreels", "comedyreels", "fashionreels",
                "travelreels", "beautyreels", "artreels"
            ],
            "GLOBAL_DISCOVERY": [
                "trending", "viral", "reels", "fyp",
                "explore", "instareels", "viralreels", "reelsviral",
                "tiktok", "aesthetic", "music", "travel",
                "fashion", "beauty", "art"
            ]
        }

        override = os.getenv("SCRAPER_HASHTAGS", "").strip()
        if override:
            custom_tags = [tag.strip().lstrip("#") for tag in override.split(",") if tag.strip()]
            if custom_tags:
                self.hashtag_groups = {"CUSTOM": custom_tags}
        self._hashtag_pool_lookup = {}
        for pool_name, tags in self.hashtag_groups.items():
            for tag in tags:
                self._hashtag_pool_lookup[tag.lower()] = pool_name

    def _source_hashtag_pool_for_hashtags(self, hashtags: list[str]) -> str | None:
        for tag in hashtags or []:
            pool = self._hashtag_pool_lookup.get(tag.lower().lstrip("#"))
            if pool:
                return pool
        return build_source_hashtag_pool(hashtags)

    def _classify_caption_niches(self, caption: str, hashtags: list[str], source_hashtag_pool: str | None) -> list[str]:
        return [classify_niche(caption, hashtags, source_hashtag_pool=source_hashtag_pool)]

    async def scrape_audio_page_async(self, audio_id: str) -> int | None:
        """Navigates to Instagram Audio page and extracts the reel count."""
        if not self._camoufox_browser or not self._camoufox_browser.is_connected():
            await self._close_browser_async()
            if not await self._init_browser_async():
                logger.error("Failed to initialize browser session for audio page scrape.")
                return None

        ctx = None
        page = None
        try:
            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
            with open(cookies_path, "r") as f:
                cookies = json.load(f)

            formatted_cookies = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                }
                for c in cookies
            ]

            ctx = await self._camoufox_browser.new_context(no_viewport=True)
            await ctx.add_cookies(formatted_cookies)
            page = await ctx.new_page()

            url = f"https://www.instagram.com/reels/audio/{audio_id}/"
            logger.info(f"Navigating to audio page: {url}")
            await page.goto(url, wait_until="networkidle", timeout=20000)

            try:
                await page.wait_for_selector("span", timeout=5000)
            except Exception:
                pass

            content = await page.content()
            match = re.search(r'([\d,.\w]+)\s*(?:reels|posts|videos)', content, re.IGNORECASE)
            if match:
                raw_count = match.group(1).lower()
                multiplier = 1
                if 'k' in raw_count:
                    multiplier = 1000
                    raw_count = raw_count.replace('k', '')
                elif 'm' in raw_count:
                    multiplier = 1000000
                    raw_count = raw_count.replace('m', '')
                
                raw_count = raw_count.replace(',', '').strip()
                val = int(float(raw_count) * multiplier)
                logger.info(f"Extracted count for audio_id {audio_id}: {val}")
                return val

            logger.warning(f"Could not extract reels count from audio page {audio_id}")
            return None

        except Exception as e:
            logger.error(f"Error scraping audio page {audio_id}: {e}")
            return None
        finally:
            if page:
                await page.close()
            if ctx:
                await ctx.close()

    async def _scrape_creator_profile_playwright_async(self, username: str) -> dict | None:
        """Helper to navigate to creator profile using Playwright and intercept XHR response."""
        if not self._camoufox_browser or not self._camoufox_browser.is_connected():
            await self._close_browser_async()
            if not await self._init_browser_async():
                logger.error("Failed to initialize browser session for creator profile scrape.")
                return None

        ctx = None
        page = None
        try:
            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
            with open(cookies_path, "r") as f:
                cookies = json.load(f)

            formatted_cookies = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                }
                for c in cookies
            ]

            ctx = await self._camoufox_browser.new_context(no_viewport=True)
            await ctx.add_cookies(formatted_cookies)
            await ctx.set_extra_http_headers({
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.instagram.com/",
            })

            captured_data = {
                "profile": None,
                "feed": None
            }

            async def handle_response(response):
                url = response.url
                if "api/v1/users/web_profile_info" in url:
                    try:
                        captured_data["profile"] = await response.json()
                    except Exception:
                        pass
                elif "graphql/query" in url:
                    try:
                        res_json = await response.json()
                        if "xdt_api__v1__clips__user__connection_v2" in str(res_json):
                            captured_data["feed"] = res_json
                    except Exception:
                        pass

            page = await ctx.new_page()
            page.on("response", handle_response)

            url = f"https://www.instagram.com/{username}/reels/"
            logger.info(f"Navigating Camoufox to profile reels page: {url}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(6000)
            except Exception as e:
                logger.warning(f"Navigation issue for @{username} profile reels: {e}")

            if not captured_data["profile"]:
                logger.warning(f"XHR profile not captured for @{username} — trying direct API endpoint inside page context...")
                try:
                    direct_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
                    await page.goto(direct_url, wait_until="domcontentloaded", timeout=15000)
                    body_text = await page.inner_text("body")
                    if body_text.startswith("for (;;);"):
                        body_text = body_text[9:]
                    captured_data["profile"] = json.loads(body_text)
                except Exception as e:
                    logger.error(f"Direct API fetch in page context failed for @{username}: {e}")

            return captured_data

        except Exception as e:
            logger.error(f"Error scraping profile for @{username} in Playwright: {e}", exc_info=True)
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass

    async def scrape_creator_baseline(self, username: str) -> dict | None:
        """Fetch a creator's profile page and extract their last 12 reels,
        computing the median views/likes/comments and caching them in creator_baselines."""
        logger.info(f"Scraping creator baseline for @{username}...")
        try:
            captured = await self._scrape_creator_profile_playwright_async(username)
            if not captured or not captured.get("profile"):
                logger.warning(f"Failed to scrape profile json for @{username}")
                return None
            
            user_data = captured["profile"].get("data", {}).get("user") or {}
            followers = user_data.get("edge_followed_by", {}).get("count") or 0
            
            media_edges = []
            feed_data = captured.get("feed") or {}
            feed_conn = feed_data.get("data", {}).get("xdt_api__v1__clips__user__connection_v2", {})
            if feed_conn.get("edges"):
                media_edges = feed_conn["edges"]
                logger.info(f"Using modern GraphQL clips connection query for @{username} reels (edges={len(media_edges)})")
            else:
                media_edges = user_data.get("edge_owner_to_timeline_media", {}).get("edges") or []
                logger.info(f"Using legacy timeline_media fallback for @{username} reels (edges={len(media_edges)})")
                
            posts = []
            for edge in media_edges:
                node = edge.get("node") or {}
                # In modern clips query, node has a "media" nested dict containing the stats
                media = node.get("media") if "media" in node else node
                if media.get("is_video") or media.get("media_type") == 2 or media.get("view_count") is not None or media.get("play_count") is not None or media.get("video_view_count") is not None:
                    views = media.get("play_count") or media.get("view_count") or media.get("video_view_count") or 0
                    likes = media.get("like_count") or media.get("edge_media_preview_like", {}).get("count") or media.get("edge_liked_by", {}).get("count") or 0
                    comments = media.get("comment_count") or media.get("edge_media_to_comment", {}).get("count") or 0
                    posts.append({
                        "views": views,
                        "likes": likes,
                        "comments": comments
                    })
            
            post_count = len(posts)
            logger.info(f"Found {post_count} video posts for @{username}")
            
            def get_median(lst):
                if not lst:
                    return 0.0
                sorted_lst = sorted(lst)
                n = len(sorted_lst)
                if n % 2 == 1:
                    return float(sorted_lst[n // 2])
                else:
                    return float(sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) / 2.0

            median_views = get_median([p["views"] for p in posts])
            median_likes = get_median([p["likes"] for p in posts])
            median_comments = get_median([p["comments"] for p in posts])
            
            baseline = {
                "username": username,
                "follower_count": followers,
                "median_views": median_views,
                "median_likes": median_likes,
                "median_comments": median_comments,
                "post_count": post_count,
                "last_scraped_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase.table("creator_baselines").upsert(baseline).execute()
            logger.info(f"Successfully cached baseline for @{username}: median_views={median_views}, followers={followers}, post_count={post_count}")
            return baseline
        except Exception as e:
            logger.error(f"Failed to scrape baseline for @{username}: {e}", exc_info=True)
            return None

    async def _init_browser_async(self) -> bool:
        """Launch a Camoufox stealth Firefox browser and verify cookies."""
        import sys
        logger.info(f"CI Diagnostics - Python version: {sys.version}")
        try:
            import playwright
            logger.info(f"CI Diagnostics - Playwright version: {playwright.__version__}")
        except Exception as pe:
            logger.warning(f"Could not import playwright version: {pe}")
        try:
            import camoufox
            logger.info(f"CI Diagnostics - Camoufox version: {getattr(camoufox, '__version__', 'unknown')}")
        except Exception as ce:
            logger.warning(f"Could not import camoufox version: {ce}")

        if not _CAMOUFOX_AVAILABLE:
            logger.error("Camoufox not installed. Run: pip install 'camoufox[geoip]' && python -m camoufox fetch")
            return False
        _has_sigalrm = hasattr(signal, "SIGALRM")
        try:
            if _has_sigalrm:
                def _browser_init_timeout(signum, frame):
                    raise TimeoutError("Camoufox browser init timed out after 120s")
                signal.signal(signal.SIGALRM, _browser_init_timeout)
                signal.alarm(120)

            logger.info("Initializing Camoufox stealth browser with Instagram cookies...")

            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
            if not os.path.exists(cookies_path):
                logger.error("cookies.json not found! See cookie_exporter_guide.md for export instructions.")
                return False

            try:
                with open(cookies_path, "r") as f:
                    content = f.read()
                cookies = json.loads(content)
            except json.JSONDecodeError as jde:
                logger.error(
                    f"CRITICAL ERROR: cookies.json is malformed or corrupted JSON! Details: {jde}. "
                    "This is typically due to shell quote-escaping issues in the GitHub Secrets environment. "
                    f"Content preview (first 100 chars): {content[:100]!r}"
                )
                return False

            formatted_cookies = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                }
                for c in cookies
            ]

            # Launch Camoufox browser
            self._camoufox_cm = CamoufoxBrowser(headless=True, geoip=False)
            self._camoufox_browser = await self._camoufox_cm.__aenter__()

            # Verify cookies by creating a temporary validation context
            temp_ctx = await self._camoufox_browser.new_context(no_viewport=True)
            try:
                await temp_ctx.add_cookies(formatted_cookies)
                await temp_ctx.set_extra_http_headers({
                    "X-IG-App-ID": "936619743392459",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.instagram.com/",
                })

                active_cookies = await temp_ctx.cookies("https://www.instagram.com")
                sessionid_present = any(c["name"] == "sessionid" for c in active_cookies)
                self._last_cookie_check = "sessionid present" if sessionid_present else "sessionid absent"
                if not sessionid_present:
                    raise RuntimeError(
                        "INSTAGRAM COOKIE EXPIRED/INVALID: sessionid not found in injected cookies. "
                        "Please refresh cookies.json using cookie_exporter_guide.md."
                    )

                if self._skip_instagram_warmup:
                    logger.info(
                        "Skipping Instagram warm-up navigation by config; "
                        f"cookie check passed ({len(active_cookies)} Instagram cookies loaded, sessionid present)."
                    )
                else:
                    logger.info("Warming up Camoufox session on Instagram home...")
                    warmup_page = await temp_ctx.new_page()
                    try:
                        await warmup_page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
                        await warmup_page.wait_for_timeout(2000)
                        if "/accounts/login/" in warmup_page.url:
                            raise RuntimeError(
                                "INSTAGRAM COOKIE EXPIRED/INVALID: Redirected to login page. Please refresh cookies.json using cookie_exporter_guide.md."
                            )
                    finally:
                        try:
                            await warmup_page.close()
                        except Exception:
                            pass
            finally:
                await temp_ctx.close()

            self._last_browser_init = "initialized"
            logger.info("Camoufox stealth browser verified and ready.")
            return True
        except Exception as e:
            self._last_browser_init = "crashed"
            logger.error(f"Failed to initialize Camoufox session: {e}", exc_info=True)
            return False
        finally:
            if _has_sigalrm:
                signal.alarm(0)

    async def _close_browser_async(self):
        """Async close helper used by the async scrape path."""
        try:
            if hasattr(self, '_camoufox_cm') and self._camoufox_cm:
                try:
                    await self._camoufox_cm.__aexit__(None, None, None)
                except Exception:
                    pass
                self._camoufox_cm = None
            else:
                if self._camoufox_ctx:
                    try:
                        await self._camoufox_ctx.close()
                    except Exception:
                        pass
                if self._camoufox_browser:
                    try:
                        await self._camoufox_browser.close()
                    except Exception:
                        pass
            self._camoufox_ctx = None
            self._camoufox_browser = None
        except Exception as e:
            logger.warning(f"Error closing Camoufox browser: {e}")

    def _extract_audio_info(self, media: dict) -> tuple[str | None, str | None, str | None, bool]:
        try:
            # 1. Try standard clips_metadata first
            clips_metadata = media.get("clips_metadata", {}) or {}
            music_info = clips_metadata.get("music_info")
            if music_info:
                minfo = music_info.get("music_info") if music_info.get("music_info") else music_info
                asset = minfo.get("music_asset_info") or {}
                audio_id = asset.get("id") or asset.get("audio_cluster_id")
                audio_title = asset.get("title")
                audio_artist = asset.get("display_artist")
                if audio_id:
                    is_orig = ("original audio" in audio_title.lower()) if audio_title else False
                    return str(audio_id), audio_title, audio_artist, is_orig
                    
            # 2. Try direct music_info
            music_info = media.get("music_info")
            if music_info:
                minfo = music_info.get("music_info") if music_info.get("music_info") else music_info
                asset = minfo.get("music_asset_info") or {}
                audio_id = asset.get("id") or asset.get("audio_cluster_id")
                audio_title = asset.get("title")
                audio_artist = asset.get("display_artist")
                if audio_id:
                    is_orig = ("original audio" in audio_title.lower()) if audio_title else False
                    return str(audio_id), audio_title, audio_artist, is_orig

            # 3. Fallback to original_sound_info
            orig = clips_metadata.get("original_sound_info") or media.get("original_sound_info") or {}
            audio_id = orig.get("audio_asset_id") or orig.get("id")
            audio_title = orig.get("original_audio_title")
            ig_artist = orig.get("ig_artist") or {}
            audio_artist = ig_artist.get("username") or ig_artist.get("full_name")
            if audio_id:
                # Check use count for user-uploaded audio tracks.
                # If it has 50+ uses, treat it as a reused trend sound rather than personal original audio.
                use_cnt = self._extract_audio_use_count(media)
                is_orig = True
                if use_cnt >= 50:
                    is_orig = False
                return str(audio_id), audio_title, audio_artist, is_orig
        except Exception as e:
            logger.warning(f"Error extracting audio info: {e}")
        return None, None, None, False

    def _extract_audio_use_count(self, media: dict, audio_id: str | None = None) -> int:
        if not media:
            return 0
        try:
            clips_metadata = media.get("clips_metadata", {}) or {}
            
            # 1. Check music_info -> music_consumption_info -> use_count
            music_info = clips_metadata.get("music_info") or media.get("music_info") or {}
            minfo = music_info.get("music_info") if music_info.get("music_info") else music_info
            if not minfo:
                minfo = {}
            m_cons = minfo.get("music_consumption_info") or {}
            if "use_count" in m_cons and m_cons["use_count"] is not None:
                return int(m_cons["use_count"])
                
            # 2. Check music_info -> music_asset_info -> use_count/usage_count/reel_count
            for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
                if key in minfo and minfo[key] is not None:
                    return int(minfo[key])
                asset = minfo.get("music_asset_info") or {}
                if key in asset and asset[key] is not None:
                    return int(asset[key])
            
            # 3. Check original_sound_info -> consumption_info -> use_count
            orig = clips_metadata.get("original_sound_info") or media.get("original_sound_info") or {}
            o_cons = orig.get("consumption_info") or {}
            if "use_count" in o_cons and o_cons["use_count"] is not None:
                return int(o_cons["use_count"])
                
            # 4. Check original_sound_info key fallbacks
            for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
                if key in orig and orig[key] is not None:
                    return int(orig[key])
                if key in o_cons and o_cons[key] is not None:
                    return int(o_cons[key])
        except Exception:
            pass
        
        # 5. DB fallback: Instagram removed use_count from their API circa mid-2025.
        #    If we've already fetched the official count for this audio via
        #    scrape_official_audio_counts, use that as the best available proxy.
        official_count = 0
        if audio_id:
            try:
                res = self.supabase.table("audio_official_counts") \
                    .select("official_use_count") \
                    .eq("audio_id", audio_id) \
                    .order("checked_at", desc=True) \
                    .limit(1) \
                    .execute()
                if res.data and res.data[0].get("official_use_count") is not None:
                    official_count = int(res.data[0]["official_use_count"])
            except Exception:
                pass
        
        if official_count > 0:
            return official_count

        # Proxy Calculation fallback:
        if audio_id:
            try:
                res = self.supabase.table("reels") \
                    .select("owner_username, scraped_at, velocity_score") \
                    .eq("audio_id", audio_id) \
                    .execute()
                reels_list = res.data or []
                if reels_list:
                    import math
                    from datetime import datetime, timezone
                    unique_creators = len({r.get("owner_username") for r in reels_list if r.get("owner_username")})
                    total_reels = len(reels_list)
                    avg_vel = sum(r.get("velocity_score", 0.0) or 0.0 for r in reels_list) / total_reels
                    
                    now = datetime.now(timezone.utc)
                    reels_last_12h = 0
                    for r in reels_list:
                        scraped_str = r.get("scraped_at")
                        if scraped_str:
                            try:
                                if scraped_str.endswith("Z"):
                                    scraped_str = scraped_str[:-1] + "+00:00"
                                scraped_dt = datetime.fromisoformat(scraped_str)
                                if scraped_dt.tzinfo is None:
                                    scraped_dt = scraped_dt.replace(tzinfo=timezone.utc)
                                age_h = (now - scraped_dt).total_seconds() / 3600.0
                                if age_h <= 12:
                                    reels_last_12h += 1
                            except Exception:
                                pass
                    
                    base_count = unique_creators * 800 + total_reels * 400
                    growth_ratio = reels_last_12h / total_reels
                    growth_mult = 1.0 + (growth_ratio * 2.5) * (1.0 + math.log1p(avg_vel / 1000.0))
                    return max(100, int(base_count * growth_mult))
            except Exception as e:
                logger.warning(f"Error calculating proxy audio_use_count for {audio_id}: {e}")

        return 0

    def _load_instagram_cookie_headers(self) -> tuple[dict, dict]:
        """Load Instagram headers and cookies for direct HTTP fallbacks."""
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/",
        }
        cookies: dict[str, str] = {}

        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                raw_cookies = json.load(f)
            for cookie in raw_cookies:
                name = cookie.get("name")
                value = cookie.get("value")
                if name and value is not None:
                    cookies[name] = value
        except Exception as e:
            logger.warning(f"Could not load cookies.json for direct API fallback: {e}")

        return headers, cookies

    async def _scrape_hashtag_page_async(self, hashtag: str) -> list[dict]:
        """Navigate to the Instagram hashtag explore page with the Camoufox stealth browser
        and capture the API JSON response via XHR interception."""
        if not self._camoufox_browser or not self._camoufox_browser.is_connected():
            logger.warning(f"Camoufox browser disconnected or uninitialized. Initializing browser session...")
            await self._close_browser_async()
            if not await self._init_browser_async():
                logger.error("Failed to initialize browser session.")
                return []

        ctx = None
        page = None
        try:
            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
            if not os.path.exists(cookies_path):
                logger.error("cookies.json not found! See cookie_exporter_guide.md for export instructions.")
                return []

            with open(cookies_path, "r") as f:
                cookies = json.load(f)

            formatted_cookies = [
                {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                }
                for c in cookies
            ]

            logger.info(f"Creating a fresh browser context for #{hashtag}...")
            ctx = await self._camoufox_browser.new_context(no_viewport=True)
            await ctx.add_cookies(formatted_cookies)
            await ctx.set_extra_http_headers({
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.instagram.com/",
            })

            captured_json: list = [None]

            def handle_response(response):
                """Intercept the Instagram tags API XHR response."""
                if "api/v1/tags/web_info" in response.url:
                    try:
                        captured_json[0] = response.json()
                    except Exception:
                        pass

            page = await ctx.new_page()
            page.on("response", handle_response)

            try:
                logger.info(f"Navigating Camoufox to explore page for #{hashtag}...")
                await page.goto(
                    f"https://www.instagram.com/explore/tags/{hashtag}/",
                    wait_until="domcontentloaded",  # was: networkidle (waits 30s+ on Instagram SPA)
                    timeout=15000,
                )
                await page.wait_for_timeout(800)
            except Exception as e:
                logger.warning(f"Navigation issue for #{hashtag}: {e}")
            finally:
                try:
                    page.remove_listener("response", handle_response)
                except Exception:
                    pass

            # Fallback: directly navigate to the API URL if the XHR was not captured
            if not captured_json[0]:
                logger.warning(f"XHR not captured for #{hashtag} — trying direct API endpoint...")
                for attempt in range(2):
                    try:
                        headers, cookies = self._load_instagram_cookie_headers()
                        response = requests.get(
                            f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={hashtag}",
                            headers=headers,
                            cookies=cookies,
                            timeout=20,
                        )
                        response.raise_for_status()
                        captured_json[0] = response.json()
                        break
                    except Exception as e:
                        if attempt == 0:
                            logger.warning(
                                f"Direct API fetch failed for #{hashtag}: {e}. Reinitializing browser and retrying once..."
                            )
                        else:
                            logger.error(f"Direct API fetch also failed for #{hashtag}: {e}")
                            return []

            # Detect login wall / challenge after navigation
            current_url = page.url
            if "/accounts/login/" in current_url or "/challenge/" in current_url:
                raise RuntimeError(f"INSTAGRAM COOKIE EXPIRED/INVALID: Redirected to login/challenge page ({current_url}) during scrape. Please refresh cookies.json.")

            data = captured_json[0]
            if not data:
                logger.warning(f"No data returned for #{hashtag}")
                return []

            raw_data = data.get("data", {})
            top_sections = raw_data.get("top", {}).get("sections", [])
            recent_sections = raw_data.get("recent", {}).get("sections", [])
            
            medias = []
            for section in top_sections + recent_sections:
                layout_content = section.get("layout_content") or {}
                
                # Standard list of medias
                for m_wrapper in layout_content.get("medias", []):
                    media = m_wrapper.get("media")
                    if media:
                        medias.append(media)
                
                # Nested layout (like 1x2 grid or other containers)
                for key, val in layout_content.items():
                    if isinstance(val, dict) and "media" in val:
                        medias.append(val["media"])
                    elif isinstance(val, list):
                        for subval in val:
                            if isinstance(subval, dict) and "media" in subval:
                                    medias.append(subval["media"])
                            elif isinstance(subval, dict) and "clips" in subval:
                                clips = subval.get("clips") or {}
                                media = clips.get("media")
                                if media:
                                    medias.append(media)
            
            items = []
            for media in medias:
                media_type = media.get("media_type")
                if media_type not in (2, 8):  # Must be video or video-carousel
                    continue
                
                owner = media.get("user") or {}
                caption_data = media.get("caption") or {}
                caption_text = caption_data.get("text") or ""
                
                taken_at = media.get("taken_at", 0)
                timestamp = datetime.fromtimestamp(taken_at, tz=timezone.utc).isoformat() if taken_at else datetime.now(timezone.utc).isoformat()
                
                # Extract video url from video_versions
                video_url = media.get("video_url")
                if not video_url and media.get("video_versions"):
                    video_url = media["video_versions"][0].get("url")

                # Standardize format to match our pipeline expectancies
                items.append({
                    "shortCode": media.get("code"),
                    "videoViewCount": media.get("play_count") or media.get("view_count") or 0,
                    "likesCount": media.get("like_count") or 0,
                    "commentsCount": media.get("comment_count") or 0,
                    "ownerFollowersCount": owner.get("follower_count") or 0,
                    "timestamp": timestamp,
                    "ownerUsername": owner.get("username"),
                    "caption": caption_text[:500],
                    "videoUrl": video_url,
                    "thumbnailUrl": (media.get("image_versions2") or {}).get("candidates", [{}])[0].get("url"),
                    "media_dict": media,
                    "pk": media.get("pk")
                })
                
            logger.info(f"Extracted {len(items)} eligible video/reel posts for #{hashtag}")
            return items
            
        except Exception as e:
            logger.error(f"API request failed for #{hashtag}: {e}", exc_info=True)
            err_str = str(e).lower()
            if "connection closed" in err_str or "target closed" in err_str or "playwright driver" in err_str:
                logger.warning("Detected connection closed or target closed error. Tearing down browser completely to recover...")
                await self._close_browser_async()
            return []
        finally:
            if page:
                try:
                    page.remove_all_listeners()
                except Exception:
                    pass
                try:
                    await page.close()
                except Exception:
                    pass
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass

    def _is_top_20_for_audio(self, audio_id: str, view_count: int) -> bool:
        if not audio_id:
            return False
        try:
            res = self.supabase.table("reels").select("id", count="exact").eq("audio_id", audio_id).gt("view_count", view_count).execute()
            count = res.count if hasattr(res, 'count') else (len(res.data) if res.data else 0)
            return count < 20
        except Exception as e:
            logger.error(f"Error checking top 20 for audio {audio_id}: {e}")
            return True

    def _store_reel_video(self, reel_id: str, video_url: str, audio_id: str) -> str | None:
        # VIDEO UPLOADS PERMANENTLY DISABLED — thumbnail-only storage policy.
        # Full MP4 uploads caused a 16GB quota blowout (2,625 videos up to 50MB each).
        # Returning None here skips all video storage; thumbnail path is handled separately.
        logger.debug(f"_store_reel_video skipped for {reel_id} — thumbnail-only policy active.")
        return None

    def detect_reel_metadata(self, reel: dict, source_hashtag_pool: str | None = None) -> dict:
        caption = reel.get("caption", "") or ""
        audio_name = reel.get("audio_title", "") or reel.get("audio_name", "") or ""
        hashtags: list[str] = reel.get("hashtags") or []
        caption_text = caption.lower()
        audio_text = audio_name.lower()

        # Detect caption language (for caption_language field)
        is_devanagari = any("\u0900" <= ch <= "\u097f" for ch in caption_text)
        caption_lang = "hi" if is_devanagari else "en"

        # Detect audio language using priority chain (the bug fix)
        audio_lang = _detect_audio_language(audio_text, caption_text, hashtags, source_hashtag_pool)

        looks_indian = _looks_indian_audio(audio_name, reel.get("audio_artist"), caption)

        # If audio language is an Indian language code, force origin to IN
        # This fixes the case where a Tamil/Telugu artist isn't in _INDIAN_ORIGIN_HINTS
        if audio_lang in _INDIAN_LANG_CODES:
            trend_origin = "IN"
            creator_country = "IN"
            confidence = 0.92
            if source_hashtag_pool == "GLOBAL_DISCOVERY":
                source_hashtag_pool = "INDIA_VERNACULAR"
        elif looks_indian:
            trend_origin = "IN"
            creator_country = "IN"
            confidence = 0.90
            if source_hashtag_pool == "GLOBAL_DISCOVERY":
                source_hashtag_pool = "INDIA_VERNACULAR"
        else:
            trend_origin = "unknown"
            creator_country = "unknown"
            confidence = 0.35

        meta = {
            "caption_language": caption_lang,
            "audio_language": audio_lang,
            "trend_origin": trend_origin,
            "creator_country": creator_country,
            "is_cross_cultural": False,
            "confidence": confidence,
            "content_tone": classify_content_tone(caption, hashtags),
            "source_hashtag_pool": source_hashtag_pool,
        }
        return _normalize_trend_origin(meta, reel)

    def _run_hook_analysis(self, audio_title: str, reels_batch: list[dict]) -> dict:
        lines = []
        for r in reels_batch[:10]:
            cap = (r.get("caption") or "")[:200]
            views = r.get("view_count", 0)
            lines.append(f"- Views: {views:,} | Caption: {cap}")
        reels_data = "\n".join(lines) if lines else "No captions available."
        
        hook_prompt = f"""You are analysing the top performing Instagram Reels using a specific trending audio.
Here are the captions and metadata of the top 10 reels:

{reels_data}

Return ONLY valid JSON, no markdown, no explanation:
{{
  "dominant_hook_type": "text_overlay" | "talking_head" | "transition" | "broll" | "pov",
  "hook_opening_patterns": ["pattern 1", "pattern 2", "pattern 3"],
  "optimal_length_seconds": 30,
  "visual_format": "before_after" | "pov" | "outfit_reveal" | "talking" | "montage" | "other",
  "hook_brief_one_line": "string under 15 words",
  "niche_tags": ["fitness", "food", "comedy", "fashion", "business", "travel", "beauty", "other"]
}}"""
        
        return {
            "dominant_hook_type": "text_overlay" if any("pov" in (r.get("caption") or "").lower() for r in reels_batch) else "broll",
            "hook_opening_patterns": ["start with the beat", "use a fast hook", "keep captions short"],
            "optimal_length_seconds": 20,
            "visual_format": "montage",
            "hook_brief_one_line": "Open with the strongest visual immediately.",
            "niche_tags": [classify_niche(reels_batch[0].get("caption") or "", reels_batch[0].get("hashtags") or [], self._source_hashtag_pool_for_hashtags(reels_batch[0].get("hashtags") or []))] if reels_batch else ["general"],
        }

    def _persist_hook_analysis(self, audio_title: str, audio_artist: str, hook_data: dict) -> None:
        if not hook_data:
            return
        
        niche_tags = hook_data.get("niche_tags") or []
        niche_tag = niche_tags[0] if niche_tags else "general"
        
        hook_brief = [{
            "dominant_hook_type": hook_data.get("dominant_hook_type"),
            "hook_opening_patterns": hook_data.get("hook_opening_patterns", []),
            "hook_brief_one_line": hook_data.get("hook_brief_one_line", ""),
            "optimal_length_seconds": hook_data.get("optimal_length_seconds", 30),
        }]
        
        format_patterns = [{
            "visual_format": hook_data.get("visual_format"),
            "dominant_hook_type": hook_data.get("dominant_hook_type"),
        }]
        
        try:
            self.supabase.table("reels").update({
                "hook_brief": json.dumps(hook_brief),
                "format_patterns": json.dumps(format_patterns),
                "niche_tag": niche_tag,
                "avg_reel_length_seconds": hook_data.get("optimal_length_seconds", 0),
            }).eq("audio_title", audio_title).eq("audio_artist", audio_artist).execute()
            logger.info(f"Hook analysis persisted for '{audio_title}' â†’ niche={niche_tag}")
        except Exception as e:
            logger.error(f"Failed to persist hook analysis for '{audio_title}': {e}")

    def _update_trend_lifecycle(self, audio_title: str, creator_country: str, scraped_at: str) -> None:
        if not audio_title:
            return
        try:
            existing = self.supabase.table("trend_lifecycle").select("*").eq("trend_id", audio_title).execute()
            if not existing.data:
                self.supabase.table("trend_lifecycle").insert({
                    "trend_id": audio_title,
                    "first_seen_country": creator_country,
                    "first_seen_at": scraped_at,
                    "spread_timeline": [{"country": creator_country, "at": scraped_at}],
                    "saturation_by_region": {creator_country: 1}
                }).execute()
            else:
                row = existing.data[0]
                timeline = row.get("spread_timeline") or []
                saturation = row.get("saturation_by_region") or {}
                
                timeline.append({"country": creator_country, "at": scraped_at})
                saturation[creator_country] = saturation.get(creator_country, 0) + 1
                
                self.supabase.table("trend_lifecycle").update({
                    "spread_timeline": timeline,
                    "saturation_by_region": saturation,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("trend_id", audio_title).execute()
        except Exception as e:
            logger.error(f"Error updating trend lifecycle: {e}", exc_info=True)

    async def scrape_trending_reels_async(self) -> int:
        if not _CAMOUFOX_AVAILABLE:
            logger.error("Camoufox not installed. Run: pip install 'camoufox[geoip]' && python -m camoufox fetch")
            self._last_scrape_result = "camoufox not installed"
            return 0

        total_scraped = 0
        baseline_fetches_this_cycle = 0
        saved_count = 0
        high_velocity = []
        scrape_stats = {
            "missing_reel_id": 0,
            "missing_timestamp": 0,
            "low_engagement": 0,
            "velocity_failed": 0,
            "duplicate": 0,
            "insert_attempts": 0,
            "insert_saved": 0,
            "item_errors": 0,
            "stored_videos": 0,
            "failed_video_stores": 0,
        }

        if not await self._init_browser_async():
            logger.error("Failed to initialize Camoufox stealth session. Aborting scrape.")
            self._last_scrape_result = "browser init failed"
            return 0
        
        try:
            scrape_mode = os.getenv("SCRAPER_MODE", "india").strip().lower()
            if "CUSTOM" in self.hashtag_groups:
                priority_pool = self.hashtag_groups["CUSTOM"]
            elif scrape_mode == "global":
                priority_pool = self.hashtag_groups.get("GLOBAL_DISCOVERY", [])[:15]
            else:
                priority_pool = (
                    self.hashtag_groups.get("INDIA_TRENDING", [])[:6]
                    + self.hashtag_groups.get("INDIA_VERNACULAR", [])[:6]
                    + self.hashtag_groups.get("GLOBAL_NICHES", [])[:3]
                )
            
            seen = set()
            selected = []
            for h in priority_pool:
                if h not in seen:
                    seen.add(h)
                    selected.append(h)
            
            logger.info(f"Scraping {len(selected)} hashtags: {selected}")
            scraped_at = datetime.now(timezone.utc).isoformat()
            audio_groups: dict[tuple, list[dict]] = {}
            # Global wall-clock guard: abort scrape if pipeline runs >15 minutes total
            _SCRAPE_TIMEOUT_S = 15 * 60
            _scrape_start = time.monotonic()
            
            for tag_idx, tag in enumerate(selected):
                # Global timeout check before each hashtag
                if time.monotonic() - _scrape_start > _SCRAPE_TIMEOUT_S:
                    logger.error(f"Scrape global timeout ({_SCRAPE_TIMEOUT_S}s) reached at hashtag {tag_idx+1}/{len(selected)}. Aborting.")
                    break
                if tag_idx > 0:
                    wait_time = 3 + (tag_idx % 3)
                    logger.info(f"Rate limiting: waiting {wait_time}s before next hashtag...")
                    time.sleep(wait_time)
                
                logger.info(f"Scraping #{tag} ({tag_idx + 1}/{len(selected)})...")

                # --- OS-level per-hashtag timeout (60s) ---
                # Playwright-internal timeouts are worthless when the Firefox/Node.js
                # driver process crashes â€” all Playwright calls then block forever.
                # SIGALRM fires from the OS regardless of Python's blocking state.
                # Only available on Linux (GitHub Actions ubuntu-latest). Safe to skip on Windows.
                _has_sigalrm = hasattr(signal, "SIGALRM")
                if _has_sigalrm:
                    def _hashtag_timeout(signum, frame):
                        raise TimeoutError(f"#{tag} scrape timed out after 60s â€” Playwright driver likely crashed")
                    signal.signal(signal.SIGALRM, _hashtag_timeout)
                    signal.alarm(60)  # 60 second wall-clock hard limit per hashtag

                try:
                    items = await self._scrape_hashtag_page_async(tag)
                except TimeoutError as te:
                    logger.error(f"{te}. Reinitializing browser for remaining hashtags...")
                    await self._close_browser_async()
                    if not await self._init_browser_async():
                        logger.error("Browser reinitialization failed after timeout. Aborting scrape.")
                        break
                    items = []
                finally:
                    if _has_sigalrm:
                        signal.alarm(0)  # Cancel the alarm

                total_scraped += len(items)
                
                for item in items:
                    try:
                        reel_id = item.get("shortCode")
                        if not reel_id:
                            logger.info("Skipping item with missing reel_id")
                            scrape_stats["missing_reel_id"] += 1
                            continue
                        
                        view = int(item.get("videoViewCount") or 0)
                        likes = int(item.get("likesCount") or 0)
                        comments = int(item.get("commentsCount") or 0)
                        followers = int(item.get("ownerFollowersCount") or 0)
                        
                        timestamp = item.get("timestamp")
                        if not timestamp:
                            logger.info(f"Skipping reel {reel_id}: missing timestamp")
                            scrape_stats["missing_timestamp"] += 1
                            continue
                        
                        posted = datetime.fromisoformat(timestamp)
                        hours_live = max((datetime.now(timezone.utc) - posted).total_seconds() / 3600.0, 0.5)
                        
                        # Calculate velocity
                        engagement = (view * 1.0) + (likes * 3.0) + (comments * 5.0)
                        normalized_followers = math.log(followers + 10)
                        velocity = (engagement / hours_live / normalized_followers) * 100
                        
                        # Filter low-engagement
                        if view < 10000 and likes < 200:
                            logger.info(
                                f"Skipping reel {reel_id}: low engagement (views={view}, likes={likes}, comments={comments})"
                            )
                            scrape_stats["low_engagement"] += 1
                            continue
                        
                        if not (velocity > 0.3 or (view > 15000 and hours_live < 6)):
                            logger.info(
                                f"Skipping reel {reel_id}: velocity threshold failed "
                                f"(velocity={velocity:.3f}, hours_live={hours_live:.2f}, views={view})"
                            )
                            scrape_stats["velocity_failed"] += 1
                            continue
                        
                        # Check duplicates
                        dup = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                        if dup.data:
                            logger.info(f"Skipping reel {reel_id}: already exists in reels table")
                            scrape_stats["duplicate"] += 1
                            continue
                        
                        # Extract data
                        owner = item.get("ownerUsername")
                        caption = (item.get("caption") or "")[:500]
                        hashtags = re.findall(r"#(\w+)", caption)
                        video_url = item.get("videoUrl")
                        thumbnail_url = item.get("thumbnailUrl")
                        
                        # Extract audio using the raw media dictionary
                        media_dict = item.get("media_dict")
                        audio_id, audio_title, audio_artist, is_original_audio = self._extract_audio_info(media_dict)
                        audio_use = self._extract_audio_use_count(media_dict, audio_id=audio_id)
                        
                        # Secondary database-level safeguard:
                        # If another creator has already used this audio_id, treat it as non-original.
                        if audio_id and is_original_audio:
                            try:
                                creators_res = self.supabase.table("reels").select("owner_username").eq("audio_id", audio_id).execute()
                                if creators_res.data:
                                    unique_creators = {c.get("owner_username") for c in creators_res.data if c.get("owner_username")}
                                    unique_creators.add(owner)
                                    if len(unique_creators) >= 2:
                                        is_original_audio = False
                            except Exception as ex:
                                logger.warning(f"Error checking secondary safeguard for audio_id {audio_id}: {ex}")

                        source_hashtag_pool = self._source_hashtag_pool_for_hashtags([tag] + hashtags) or "GLOBAL_DISCOVERY"

                        reel = {
                            "platform": "instagram",
                            "reel_id": reel_id,
                            "view_count": view,
                            "like_count": likes,
                            "comment_count": comments,
                            "posted_at": posted.isoformat(),
                            "owner_username": owner,
                            "owner_follower_count": followers,
                            "caption": caption,
                            "hashtags": hashtags,
                            "source_hashtag_pool": source_hashtag_pool,
                            "video_url": video_url,
                            "thumbnail_url": thumbnail_url,
                            "audio_title": audio_title,
                            "audio_artist": audio_artist,
                            "audio_id": audio_id,
                            "audio_use_count": audio_use,
                            "is_original_audio": is_original_audio,
                            "velocity_score": velocity,
                            "scraped_at": scraped_at,
                            "pk": item.get("pk"),
                            # Audio backfill queue: flag rows where IG returned no audio metadata
                            "audio_backfill_status": (
                                "needs_audio_backfill"
                                if not audio_id or not audio_title
                                else None
                            ),
                            "audio_backfill_attempts": 0,
                        }
                        
                        # Metadata tagging — pass source_hashtag_pool so language
                        # detection uses the strongest available signal first
                        meta = self.detect_reel_metadata(reel, source_hashtag_pool=source_hashtag_pool)
                        source_hashtag_pool = meta.get("source_hashtag_pool", source_hashtag_pool)
                        reel["source_hashtag_pool"] = source_hashtag_pool
                        creator_country = meta.get("creator_country", "unknown")
                        
                        # Calculate India saturation
                        india_use = 0
                        try:
                            if audio_id:
                                res = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_id", audio_id).eq("creator_country", "IN").execute()
                                india_use = res.count or 0
                            elif audio_title:
                                res = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_title", audio_title).eq("creator_country", "IN").execute()
                                india_use = res.count or 0
                        except Exception as e:
                            logger.warning(f"Error querying India reels count: {e}")
                        
                        if creator_country == "IN":
                            india_use += 1
                        
                        sat = calculate_saturation(audio_use, india_use)
                        window = calculate_window_hours(audio_use, velocity * 100)
                        
                        reel.update({
                            "audio_language": meta.get("audio_language", "unknown"),
                            "caption_language": meta.get("caption_language", "unknown"),
                            "trend_origin": meta.get("trend_origin", "unknown"),
                            "creator_country": creator_country,
                            "is_cross_cultural": meta.get("is_cross_cultural", False),
                            "language_confidence": meta.get("confidence", 0.0),
                            "global_saturation_pct": sat["global"],
                            "india_saturation_pct": sat["india"],
                            "window_hours_remaining": window,
                            "content_tone": meta.get("content_tone", "unknown"),
                            "niche_tag": classify_niche(caption, hashtags, source_hashtag_pool=source_hashtag_pool),
                        })
                        
                        # Video storage
                        is_trend = (velocity > 0.5) or self._is_top_20_for_audio(audio_id, view)
                        if is_trend:
                            stored = self._store_reel_video(reel_id, video_url, audio_id)
                            if stored:
                                reel["preview_url"] = stored
                                reel["video_storage_status"] = "stored"
                                reel["video_stored_at"] = datetime.now(timezone.utc).isoformat()
                                scrape_stats["stored_videos"] += 1
                            else:
                                reel["preview_url"] = None
                                reel["video_storage_status"] = "failed"
                                reel["video_stored_at"] = None
                                scrape_stats["failed_video_stores"] += 1
                        else:
                            reel["video_storage_status"] = "pending"
                        
                        # Classify semantic niches
                        reel["semantic_niches"] = self._classify_caption_niches(caption, hashtags, source_hashtag_pool)

                        # Creator baseline caching and outlier tagging
                        multiplier = float(os.getenv("CREATOR_OUTLIER_MULTIPLIER", "5.0"))
                        is_outlier = None
                        
                        try:
                            cached_res = self.supabase.table("creator_baselines").select("*").eq("username", owner).execute()
                            cached_data = cached_res.data
                        except Exception as ex:
                            logger.warning(f"Error querying creator baseline for @{owner}: {ex}")
                            cached_data = []

                        baseline = None
                        if cached_data:
                            baseline = cached_data[0]
                            last_scraped_str = baseline.get("last_scraped_at")
                            if last_scraped_str:
                                last_scraped = datetime.fromisoformat(last_scraped_str.replace("Z", "+00:00"))
                                if (datetime.now(timezone.utc) - last_scraped).days >= 7:
                                    baseline = None

                        if not baseline and view > 30000 and baseline_fetches_this_cycle < 5:
                            new_baseline = await self.scrape_creator_baseline(owner)
                            if new_baseline:
                                baseline = new_baseline
                                baseline_fetches_this_cycle += 1

                        if baseline:
                            post_count = baseline.get("post_count") or 0
                            if post_count < 6:
                                is_outlier = None
                            else:
                                median_v = baseline.get("median_views") or 0.0
                                if view > multiplier * median_v:
                                    is_outlier = True
                                else:
                                    is_outlier = False

                        reel["is_creator_outlier"] = is_outlier

                        # Insert to DB
                        logger.info(f"Inserting reel {reel_id} for @{owner} into Supabase...")
                        scrape_stats["insert_attempts"] += 1
                        self.supabase.table("reels").insert(reel).execute()
                        logger.info(f"Saved reel {reel_id} by @{owner} (velocity={velocity:.3f}, lang={meta.get('caption_language')}, outlier={is_outlier})")
                        scrape_stats["insert_saved"] += 1

                        # Snapshots and delta computation
                        try:
                            # 1. Fetch most recent snapshot for this reel
                            prev_snap_res = self.supabase.table("reel_snapshots") \
                                .select("view_count, like_count, audio_use_count") \
                                .eq("reel_id", reel_id) \
                                .order("snapshotted_at", desc=True) \
                                .limit(1) \
                                .execute()
                            
                            views_delta = 0
                            likes_delta = 0
                            audio_delta = 0
                            
                            if prev_snap_res.data:
                                last_snap = prev_snap_res.data[0]
                                views_delta = max(0, view - (last_snap.get("view_count") or 0))
                                likes_delta = max(0, likes - (last_snap.get("like_count") or 0))
                                audio_delta = max(0, audio_use - (last_snap.get("audio_use_count") or 0))
                            
                            # 2. Insert new snapshot
                            self.supabase.table("reel_snapshots").insert({
                                "reel_id": reel_id,
                                "audio_id": audio_id,
                                "view_count": view,
                                "like_count": likes,
                                "comment_count": comments,
                                "audio_use_count": audio_use
                            }).execute()

                            # 3. Update deltas on the reels row
                            if views_delta > 0 or likes_delta > 0 or audio_delta > 0:
                                self.supabase.table("reels").update({
                                    "views_delta_last_run": views_delta,
                                    "likes_delta_last_run": likes_delta,
                                    "audio_delta_last_run": audio_delta
                                }).eq("reel_id", reel_id).execute()
                                
                        except Exception as snap_ex:
                            logger.warning(f"Error updating snapshots/deltas for reel {reel_id}: {snap_ex}")


                        # Check unique creator count for original audio contaminant check
                        unique_creators_count = 1
                        if audio_id:
                            try:
                                creators_res = self.supabase.table("reels").select("owner_username").eq("audio_id", audio_id).execute()
                                if creators_res.data:
                                    unique_creators = {c.get("owner_username") for c in creators_res.data if c.get("owner_username")}
                                    unique_creators.add(owner)
                                    unique_creators_count = len(unique_creators)
                            except Exception as ex:
                                logger.warning(f"Error checking creators for audio_id {audio_id}: {ex}")
                        elif audio_title:
                            try:
                                creators_res = self.supabase.table("reels").select("owner_username").eq("audio_title", audio_title).execute()
                                if creators_res.data:
                                    unique_creators = {c.get("owner_username") for c in creators_res.data if c.get("owner_username")}
                                    unique_creators.add(owner)
                                    unique_creators_count = len(unique_creators)
                            except Exception as ex:
                                logger.warning(f"Error checking creators for audio_title {audio_title}: {ex}")

                        is_contaminant = is_original_audio and unique_creators_count == 1
                        is_unrecoverable = reel.get("audio_backfill_status") == "unrecoverable"

                        if is_contaminant:
                            logger.info(f"Skipping tracked_audio and trend_lifecycle for original audio contaminant '{audio_title}' (creator count: {unique_creators_count})")
                        elif is_unrecoverable:
                            logger.info(f"Skipping tracked_audio and trend_lifecycle for unrecoverable audio reel {reel_id} (audio missing after max retries)")
                        else:
                            # Track audio if it is a real (non-original) audio
                            if audio_id:
                                try:
                                    exist = self.supabase.table("tracked_audio").select("audio_id").eq("audio_id", audio_id).execute()
                                    if not exist.data:
                                        # Ensure we have at least 2 reels in the DB for this audio (including the one just inserted)
                                        reels_res = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_id", audio_id).execute()
                                        reel_count = reels_res.count or 0
                                        if reel_count >= 2:
                                            self.supabase.table("tracked_audio").insert({
                                                "audio_id": audio_id,
                                                "audio_title": audio_title,
                                                "audio_artist": audio_artist,
                                                "first_seen_at": datetime.now(timezone.utc).isoformat()
                                            }).execute()
                                            logger.info(f"Added audio_id {audio_id} ('{audio_title}') to tracked_audio (signal count: {reel_count})")
                                        else:
                                            logger.info(f"Skipped tracking audio_id {audio_id} ('{audio_title}'): only has {reel_count} reel(s) in DB (floor is 2+)")
                                except Exception as tae:
                                    logger.error(f"Failed to insert tracked_audio for {audio_id}: {tae}")
                            
                            # Trend lifecycle
                            self._update_trend_lifecycle(
                                audio_title=audio_title or "unknown_trend",
                                creator_country=creator_country,
                                scraped_at=scraped_at,
                            )
                        
                        saved_count += 1
                        high_velocity.append(velocity)
                        
                        # Group for hook analysis
                        if audio_title:
                            key = (audio_title.strip(), (audio_artist or "").strip())
                            audio_groups.setdefault(key, []).append(reel)
                        
                    except Exception as e:
                        logger.error(f"Error processing reel {reel_id if 'reel_id' in locals() else 'unknown'}: {e}", exc_info=True)
                        scrape_stats["item_errors"] += 1
            
            high_velocity.sort(reverse=True)
            top3 = [round(v, 4) for v in high_velocity[:3]]
            print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")
            logger.info(f"Browser scraping complete: {total_scraped} items processed, {saved_count} saved")
            logger.info(
                "Scrape diagnostics: "
                f"insert_attempts={scrape_stats['insert_attempts']}, "
                f"insert_saved={scrape_stats['insert_saved']}, "
                f"duplicate_skips={scrape_stats['duplicate']}, "
                f"low_engagement_skips={scrape_stats['low_engagement']}, "
                f"velocity_failed_skips={scrape_stats['velocity_failed']}, "
                f"missing_timestamp_skips={scrape_stats['missing_timestamp']}, "
                f"missing_reel_id_skips={scrape_stats['missing_reel_id']}, "
                f"video_store_success={scrape_stats['stored_videos']}, "
                f"video_store_fail={scrape_stats['failed_video_stores']}, "
                f"item_errors={scrape_stats['item_errors']}"
            )
            
            # Hook analysis
            if saved_count:
                # 1. Filter and sort audio groups by max velocity of their reels
                scored_groups = []
                for (title, artist), reels in audio_groups.items():
                    max_vel = max((r.get("velocity_score") or 0.0) for r in reels)
                    scored_groups.append(((title, artist), reels, max_vel))
                
                # Sort by max velocity descending
                scored_groups.sort(key=lambda x: x[2], reverse=True)
                
                # Filter out low signal: velocity floor >= 1.5
                VELOCITY_FLOOR = 1.5
                filtered_groups = [g for g in scored_groups if g[2] >= VELOCITY_FLOOR]
                
                logger.info(f"Hook analysis selection: total_groups={len(audio_groups)}, filtered (velocity >= {VELOCITY_FLOOR})={len(filtered_groups)}")
                
                # Cap to top 5
                MAX_HOOK_ANALYSES = 5
                target_groups = filtered_groups[:MAX_HOOK_ANALYSES]
                
                logger.info(f"Running Groq hook analysis for top {len(target_groups)} high-signal audio groups...")
                
                hook_start_time = time.monotonic()
                MAX_HOOK_TIME_S = 5 * 60  # 5 minutes wall-clock time limit
                
                for idx, ((title, artist), group, max_vel) in enumerate(target_groups):
                    # Check time budget
                    if time.monotonic() - hook_start_time > MAX_HOOK_TIME_S:
                        logger.warning(f"Hook analysis time budget exceeded ({MAX_HOOK_TIME_S}s). Skipping remaining analyses.")
                        break
                        
                    if idx > 0:
                        stagger_delay = 2.0
                        logger.info(f"Rate limiting: sleeping {stagger_delay}s before next Groq hook analysis...")
                        time.sleep(stagger_delay)
                    try:
                        logger.info(f"Analyzing hooks for '{title}' (max_velocity={max_vel:.3f})...")
                        hook = self._run_hook_analysis(title, group)
                        if hook:
                            self._persist_hook_analysis(title, artist, hook)
                    except Exception as e:
                        logger.error(f"Hook analysis error for '{title}': {e}")
            else:
                logger.info("Browser scraper returned 0 items. No DB updates or hook analysis performed.")
            self._last_scrape_result = f"saved {saved_count} reels from {total_scraped} scraped items"
            self._last_scrape_stats = scrape_stats
            return saved_count
        except Exception as e:
            self._last_scrape_result = "scrape crashed"
            self._last_scrape_stats = scrape_stats if 'scrape_stats' in locals() else {}
            raise
        finally:
            await self._close_browser_async()

    def scrape_trending_reels(self) -> int:
        return asyncio.run(self.scrape_trending_reels_async())

    def scrape_official_audio_counts(self, limit: int = 30) -> None:
        return asyncio.run(self.scrape_official_audio_counts_async(limit=limit))

    async def scrape_official_audio_counts_async(self, limit: int = 30) -> None:
        try:
            logger.info("Starting scrape of official audio counts...")
            # Query all currently tracked audios
            tracked_res = self.supabase.table("tracked_audio").select("audio_id").execute()
            tracked_ids = [row["audio_id"] for row in (tracked_res.data or []) if row.get("audio_id")]
            
            if not tracked_ids:
                logger.info("No tracked audios found to check.")
                return

            # Query recent reels to find active non-original audio IDs
            three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
            res = self.supabase.table("reels") \
                .select("audio_id") \
                .eq("is_original_audio", False) \
                .not_.is_("audio_id", "null") \
                .gte("scraped_at", three_days_ago.isoformat()) \
                .execute()
            
            reels_data = res.data or []
            audio_counts = {}
            for r in reels_data:
                aid = r.get("audio_id")
                if aid:
                    audio_counts[aid] = audio_counts.get(aid, 0) + 1
            
            # Sort by frequency and filter to only tracked audios
            sorted_audios = sorted(audio_counts.items(), key=lambda x: x[1], reverse=True)
            active_audio_ids = [aid for aid, count in sorted_audios if aid in tracked_ids][:limit]
            
            if not active_audio_ids:
                logger.info("No active tracked audio IDs found to check in the last 3 days.")
                # We still want to log all tracked audios as skipped
                for aid in tracked_ids:
                    logger.info(f"[AUDIO_COUNT_STATUS] ID {aid}: SKIPPED (queue cap)")
                return

            logger.info(f"Selected {len(active_audio_ids)} active audio IDs to scrape.")
            results = await self._scrape_audio_counts_playwright_async(active_audio_ids)
            
            for aid in tracked_ids:
                if aid in active_audio_ids:
                    status = results.get(aid, "ATTEMPTED BUT FAILED (unknown error)")
                    if status == "SUCCESS":
                        logger.info(f"[AUDIO_COUNT_STATUS] ID {aid}: SUCCESS")
                    else:
                        logger.info(f"[AUDIO_COUNT_STATUS] ID {aid}: ATTEMPTED BUT FAILED ({status})")
                else:
                    logger.info(f"[AUDIO_COUNT_STATUS] ID {aid}: SKIPPED (queue cap)")
            
        except Exception as e:
            logger.error(f"Error in scrape_official_audio_counts: {e}", exc_info=True)

    async def _scrape_audio_counts_playwright_async(self, audio_ids: list[str]) -> dict[str, str]:
        """Scrape official reel counts for tracked audio IDs using Camoufox stealth browser."""
        if not _CAMOUFOX_AVAILABLE:
            logger.error("Camoufox not installed. Cannot run stealth audio count scraper.")
            return {aid: "Camoufox not installed" for aid in audio_ids}

        results = {}
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        if not os.path.exists(cookies_path):
            err_msg = "cookies.json not found"
            logger.error(f"{err_msg}, cannot run Camoufox audio scraper")
            return {aid: err_msg for aid in audio_ids}

        with open(cookies_path, "r") as f:
            cookies = json.load(f)

        formatted_cookies = [
            {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".instagram.com"),
                "path": c.get("path", "/"),
            }
            for c in cookies
        ]

        browser = None
        context = None
        page = None

        async def launch_new_session():
            nonlocal browser, context, page
            try:
                if context:
                    await context.close()
            except Exception:
                pass
            try:
                if browser:
                    # camoufox uses standard close, but if async it needs await
                    if hasattr(browser, "close"):
                        await browser.close()
            except Exception:
                pass

            logger.info("Launching Camoufox stealth browser for audio count scraping...")
            # We instantiate it manually via __aenter__ so we can handle crashes
            browser = await CamoufoxBrowser(headless=True, geoip=True).__aenter__()
            context = await browser.new_context(no_viewport=True)
            await context.add_cookies(formatted_cookies)
            page = await context.new_page()

            # Warm up session with home page before hitting audio pages
            try:
                await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception as warm_err:
                logger.warning(f"Warm-up navigation failed (non-fatal): {warm_err}")

        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3  # Abort if browser repeatedly fails to launch/load

        try:
            for aid in audio_ids:
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}). Aborting audio count scrape.")
                    for remaining_aid in audio_ids:
                        if remaining_aid not in results:
                            results[remaining_aid] = "Skipped: browser driver crashed repeatedly"
                    break

                url = f"https://www.instagram.com/reels/audio/{aid}/"
                logger.info(f"Checking official count for audio_id {aid} via {url}...")
                try:
                    # Lazily start/restart session if it was cleared due to a crash
                    if page is None or page.is_closed():
                        await launch_new_session()

                    # Use domcontentloaded (not networkidle) — networkidle hangs on Instagram's
                    # heavy SPA and eventually kills the Playwright driver process.
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(4000)  # let React render the count

                    current_url = page.url
                    if "/accounts/login/" in current_url or "/challenge/" in current_url:
                        logger.error(f"[INSTAGRAM_FRICTION] Redirected to login/challenge page: {current_url}")
                        results[aid] = f"Redirected to login/challenge page: {current_url}"
                        consecutive_failures = 0  # Login redirect is not a driver crash
                        continue

                    body_text = await page.inner_text("body", timeout=15000)

                    # Scan for rate limits, blocks, or captcha text
                    friction_keywords = [
                        "suspicious activity", "confirm it's you", "robot", "captcha",
                        "restrict", "block", "try again later", "please wait a few minutes"
                    ]
                    friction_detected = next(
                        (kw for kw in friction_keywords if kw in body_text.lower()), None
                    )
                    if friction_detected:
                        logger.error(f"[INSTAGRAM_FRICTION] Found friction keyword '{friction_detected}' in body of {url}")
                        results[aid] = f"Friction keyword found: '{friction_detected}'"
                        consecutive_failures = 0
                        continue

                    # Parse count
                    count, precision_bucket = self._parse_reels_count_text(body_text)
                    if count is not None:
                        logger.info(f"Successfully scraped count for {aid}: {count} (precision: {precision_bucket})")
                        self._save_official_count(aid, count, precision_bucket)
                        results[aid] = "SUCCESS"
                        consecutive_failures = 0
                    else:
                        logger.warning(f"Could not find Reels count text in page body for {aid}")
                        results[aid] = "Could not find Reels count text in page body"
                        consecutive_failures = 0

                except Exception as ex:
                    err_str = str(ex)
                    logger.error(f"Error scraping audio {aid}: {ex}")
                    results[aid] = err_str
                    # Driver-level errors (connection closed, socket errors) count as failures
                    if "connection closed" in err_str.lower() or "socket" in err_str.lower() or "playwright" in err_str.lower() or "undefined" in err_str.lower():
                        consecutive_failures += 1
                        logger.warning(f"Driver-level failure #{consecutive_failures} for {aid}. Session discarded.")
                        page = None  # Force re-initialization of browser on next loop
                    else:
                        consecutive_failures = 0

                # Multi-second delay between requests to avoid rate limits
                time.sleep(5)
        finally:
            # Always ensure clean teardown of whatever is currently active
            try:
                if context:
                    await context.close()
            except Exception:
                pass
            try:
                if browser:
                    if hasattr(browser, "close"):
                        await browser.close()
            except Exception:
                pass

        return results

    def _parse_reels_count_text(self, text: str) -> tuple[int, str] | tuple[None, None]:
        match = re.search(r'([\d,.]+)([KMB]?)\s*reels?', text, re.IGNORECASE)
        if not match:
            return None, None
        val_str, suffix = match.groups()
        val_str = val_str.replace(',', '')
        try:
            val = float(val_str)
            suffix_upper = suffix.upper()
            if suffix_upper == 'K':
                val *= 1000
                precision_bucket = 'K'
            elif suffix_upper == 'M':
                val *= 1_000_000
                precision_bucket = 'M'
            elif suffix_upper == 'B':
                val *= 1_000_000_000
                precision_bucket = 'B'
            else:
                precision_bucket = 'exact'
            return int(val), precision_bucket
        except ValueError:
            return None, None

    def _save_official_count(self, audio_id: str, count: int, precision_bucket: str) -> None:
        try:
            # 1. Fetch previous count to calculate velocity
            prev = self.supabase.table("audio_official_counts") \
                .select("official_use_count, checked_at, precision_bucket") \
                .eq("audio_id", audio_id) \
                .order("checked_at", desc=True) \
                .limit(1) \
                .execute()
                
            velocity = 0.0
            now = datetime.now(timezone.utc)
            velocity_is_null = False
            
            if prev.data:
                prev_row = prev.data[0]
                prev_count = prev_row.get("official_use_count")
                prev_time_str = prev_row.get("checked_at")
                prev_bucket = prev_row.get("precision_bucket") or "exact"
                
                if prev_count is not None and prev_time_str:
                    try:
                        prev_time = datetime.fromisoformat(prev_time_str.replace("Z", "+00:00"))
                        if prev_time.tzinfo is None:
                            prev_time = prev_time.replace(tzinfo=timezone.utc)
                        time_diff_hours = (now - prev_time).total_seconds() / 3600.0
                        if time_diff_hours > 0.05: # avoid division by zero / super small windows
                            count_diff = count - prev_count
                            if count_diff == 0 and precision_bucket == prev_bucket and precision_bucket != 'exact':
                                velocity_is_null = True
                            else:
                                velocity = count_diff / time_diff_hours
                    except Exception as ve:
                        logger.warning(f"Error parsing checked_at for velocity check: {ve}")
            
            # 2. Append new row to audio_official_counts
            insert_data = {
                "audio_id": audio_id,
                "official_use_count": count,
                "checked_at": now.isoformat(),
                "precision_bucket": precision_bucket
            }
            if velocity_is_null:
                insert_data["official_count_velocity"] = None
            else:
                insert_data["official_count_velocity"] = velocity

            self.supabase.table("audio_official_counts").insert(insert_data).execute()
            
            # 3. Update the latest audio_use_count in the reels table
            self.supabase.table("reels") \
                .update({"audio_use_count": count}) \
                .eq("audio_id", audio_id) \
                .execute()
                
            velocity_str = f"{velocity:.3f}" if not velocity_is_null else "NULL"
            logger.info(f"Saved official count {count} for audio_id {audio_id} (velocity={velocity_str} per hour, precision={precision_bucket})")
        except Exception as e:
            logger.error(f"Error saving official count: {e}", exc_info=True)

if __name__ == "__main__":
    scraper = InstagramScraper()
    asyncio.run(scraper.scrape_trending_reels_async())






