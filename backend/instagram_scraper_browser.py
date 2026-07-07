"""
Improved Browser-Based Instagram Scraper using Camoufox + Browser-Use + Playwright.

This scraper replaces the Apify scraper to avoid monthly quota limits.
It uses a stealth Firefox browser (Camoufox) for anti-detection and Playwright for page automation.
Data pipeline: Browser → Instagram GraphQL → Supabase reels table → TrendEngine → trends table
"""

import os
import re
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import requests

# Playwright imports (Camoufox uses Playwright under the hood)
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise ImportError("playwright is required. Install via: pip install playwright")

# Supabase client
from supabase import create_client, Client

# LLM hook (reuse existing implementation)
from llm import call_llm

# Setup logging
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
    """
    Returns global and India saturation percentages (0–100).
    Thresholds:
      < 5K   = early (0–15%)
      5K–20K = rising (15–45%)
      20K–100K = peak (45–80%)
      > 100K = saturated (80–100%)
    """
    global_pct = min(100.0, (audio_use_count / 100_000) * 100)
    india_pct = min(100.0, (india_use_count / 8_000) * 100)
    return {
        "global": round(global_pct, 1),
        "india": round(india_pct, 1),
    }


def calculate_window_hours(audio_use_count: int, velocity_pct: float) -> int:
    """Estimates hours remaining before audio trend window closes."""
    if audio_use_count > 100_000:
        return 0
    if velocity_pct > 300 and audio_use_count < 20_000:
        return 8
    if velocity_pct > 150 and audio_use_count < 50_000:
        return 16
    if velocity_pct > 100 and audio_use_count < 80_000:
        return 24
    return 4


class InstagramScraper:
    """Browser-based Instagram scraper that matches the original interface."""

    def __init__(self):
        load_dotenv()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Hashtag groups
        self.hashtag_groups = {
            "GLOBAL_TRENDING": [
                "trending", "reels", "viral", "fyp", "explore",
                "trendingreels", "reelsinstagram", "globalreels", "reelsviral"
            ],
            "WESTERN_AND_GLOBAL": [
                "aesthetic", "dance", "music", "popmusic", "chartmusic", 
                "billboard", "tiktoktrend", "trendingsong", "latesthits"
            ],
            "INTERNATIONAL_REGIONAL": [
                "brazilianfunk", "russianmusic", "latintrend", "kpop", 
                "eurovision", "phonk", "techno", "electronicmusic"
            ]
        }
        
        self.playwright = None
        self.browser = None

    def _init_browser(self):
        """Initialize Camoufox browser for stealth Instagram scraping."""
        try:
            logger.info("Initializing Camoufox browser...")
            self.playwright = sync_playwright().start()
            
            # Launch with Camoufox for stealth
            # Camoufox patches Playwright's Chromium to add anti-detection measures
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            )
            logger.info("Camoufox browser initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            return False

    def _close_browser(self):
        """Clean up browser resources."""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    def _extract_audio_info(self, music_info_dict: dict | None) -> tuple[str | None, str | None, str | None]:
        """Extract audio ID, title, and artist from musicInfo."""
        if not music_info_dict:
            return None, None, None
        
        # Extract audio ID
        minfo = music_info_dict.get("music_info") or {}
        asset = minfo.get("music_asset_info") or {}
        audio_id = (
            asset.get("id")
            or asset.get("audio_cluster_id")
            or asset.get("audioClusterId")
            or asset.get("music_id")
        )
        if audio_id:
            audio_id = str(audio_id)
        else:
            orig = music_info_dict.get("original_sound_info") or {}
            audio_id = orig.get("audio_asset_id") or orig.get("id") or orig.get("audio_id")
            if audio_id:
                audio_id = str(audio_id)
        
        # Extract title and artist
        audio_title = asset.get("title")
        audio_artist = asset.get("display_artist")
        
        if not audio_title or not audio_title.strip():
            orig = music_info_dict.get("original_sound_info") or {}
            audio_title = orig.get("original_audio_title")
            if not audio_artist:
                ig_artist = orig.get("ig_artist") or {}
                audio_artist = ig_artist.get("username") or ig_artist.get("full_name")
        
        return audio_id, audio_title, audio_artist

    def _extract_audio_use_count(self, music_info_dict: dict | None) -> int:
        """Extract how many reels are currently using this audio."""
        if not music_info_dict:
            return 0
        
        minfo = music_info_dict.get("music_info") or {}
        m_cons = minfo.get("music_consumption_info") or {}
        if "use_count" in m_cons and m_cons["use_count"] is not None:
            try:
                return int(m_cons["use_count"])
            except (TypeError, ValueError):
                pass
        
        asset = minfo.get("music_asset_info") or {}
        for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
            if asset.get(key) is not None:
                try:
                    return int(asset[key])
                except (TypeError, ValueError):
                    pass
        
        orig = music_info_dict.get("original_sound_info") or {}
        o_cons = orig.get("consumption_info") or {}
        if "use_count" in o_cons and o_cons["use_count"] is not None:
            try:
                return int(o_cons["use_count"])
            except (TypeError, ValueError):
                pass
        
        for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
            if orig.get(key) is not None:
                try:
                    return int(orig[key])
                except (TypeError, ValueError):
                    pass
        
        return 0

    def _scrape_hashtag_page(self, hashtag: str) -> list[dict]:
        """Scrape hashtag page using Playwright + Camoufox."""
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        context = None
        page = None
        
        try:
            # Create new context for each request (better isolation)
            context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            # Navigate with timeout
            logger.info(f"Loading {url}...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)  # Extra wait for dynamic content
            
            # Extract Instagram shared data from script tag
            script_content = page.evaluate(
                """
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    const target = scripts.find(s => s.textContent && s.textContent.includes('window._sharedData'));
                    return target ? target.textContent : '';
                }
                """
            )
            
            if not script_content:
                logger.warning(f"No shared data script found for #{hashtag}")
                return []
            
            # Parse JSON
            try:
                json_str = script_content.split('window._sharedData = ')[1].split(';</script>')[0].strip()
                data = json.loads(json_str)
            except Exception as e:
                logger.warning(f"Failed to parse shared data for #{hashtag}: {e}")
                return []
            
            # Extract media edges
            edges = (
                data.get('entry_data', {})
                .get('TagPage', [{}])[0]
                .get('graphql', {})
                .get('hashtag', {})
                .get('edge_hashtag_to_media', {})
                .get('edges', [])
            )
            
            items = []
            for edge in edges:
                node = edge.get('node', {})
                items.append({
                    "shortCode": node.get('shortcode'),
                    "videoViewCount": node.get('video_view_count'),
                    "likesCount": node.get('edge_liked_by', {}).get('count'),
                    "commentsCount": node.get('edge_media_to_comment', {}).get('count'),
                    "ownerFollowersCount": node.get('owner', {}).get('edge_followed_by', {}).get('count'),
                    "timestamp": datetime.fromtimestamp(
                        node.get('taken_at_timestamp', 0),
                        tz=timezone.utc
                    ).isoformat(),
                    "ownerUsername": node.get('owner', {}).get('username'),
                    "caption": (node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text') or ''),
                    "videoUrl": node.get('video_url'),
                    "thumbnailUrl": node.get('display_url'),
                    "musicInfo": node.get('music_info'),
                })
            
            logger.info(f"Scraped {len(items)} reels for #{hashtag}")
            return items
            
        except Exception as e:
            logger.error(f"Browser scrape failed for #{hashtag}: {e}", exc_info=True)
            return []
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    def _is_top_20_for_audio(self, audio_id: str, view_count: int) -> bool:
        """Check if reel would be in top 20 by view_count for this audio_id."""
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
        """Download and upload video to Supabase storage."""
        if not video_url:
            return None
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(video_url, headers=headers, timeout=20)
            if not response.ok:
                logger.error(f"Download failed for video {video_url}: {response.status_code}")
                return None
            
            safe_audio_id = audio_id or "no_audio"
            path = f"reels/{safe_audio_id}/{reel_id}.mp4"
            
            self.supabase.storage.from_("reels-preview").upload(
                path=path,
                file=response.content,
                file_options={"content-type": "video/mp4", "x-upsert": "true"}
            )
            
            try:
                public_url_obj = self.supabase.storage.from_("reels-preview").get_public_url(path)
                url = str(public_url_obj) if public_url_obj else f"{self.supabase_url}/storage/v1/object/public/reels-preview/{path}"
            except Exception:
                url = f"{self.supabase_url}/storage/v1/object/public/reels-preview/{path}"
            
            logger.info(f"Stored reel video {reel_id} at {url}")
            return url
        except Exception as e:
            logger.error(f"Video store failed for reel {reel_id}: {e}")
            return None

    def detect_reel_metadata(self, reel: dict) -> dict:
        """LLM metadata tagging."""
        caption = reel.get('caption', '')
        audio_name = reel.get('audio_title', '') or reel.get('audio_name', '')
        
        prompt = (
            "You are a metadata tagger for Instagram Reels. Analyse the following reel data\n"
            "and return ONLY a valid JSON object, no markdown, no explanation.\n\n"
            f'Caption: "{caption}"\n'
            f'Audio name: "{audio_name}"\n'
            'Creator location hint: "unknown"\n\n'
            "Return this exact JSON structure:\n"
            '{\n'
            '  "caption_language": "english" | "hindi" | "other",\n'
            '  "audio_language": "english" | "hindi" | "russian" | "portuguese" | "spanish" | "korean" | "other",\n'
            '  "trend_origin": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",\n'
            '  "creator_country": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",\n'
            '  "is_cross_cultural": true | false,\n'
            '  "confidence": 0.0 to 1.0\n'
            '}\n\n'
            "Only return the JSON, nothing else."
        )
        
        try:
            return call_llm(
                system_prompt="You are a metadata tagger for Instagram Reels.",
                user_prompt=prompt,
                response_mime_type="application/json",
                timeout=15
            )
        except Exception as e:
            logger.error(f"Error in detect_reel_metadata: {e}")
            return {
                "caption_language": "unknown",
                "audio_language": "unknown",
                "trend_origin": "unknown",
                "creator_country": "unknown",
                "is_cross_cultural": False,
                "confidence": 0.0
            }

    def _run_hook_analysis(self, audio_title: str, reels_batch: list[dict]) -> dict:
        """Groq inference for hook patterns."""
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
        
        try:
            return call_llm(
                system_prompt="You are a social media trend analyst. Return ONLY valid JSON.",
                user_prompt=hook_prompt,
                response_mime_type="application/json",
                timeout=20,
            )
        except Exception as e:
            logger.error(f"Hook analysis failed for '{audio_title}': {e}")
            return {}

    def _persist_hook_analysis(self, audio_title: str, audio_artist: str, hook_data: dict) -> None:
        """Store hook analysis results back onto matching reels."""
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
            logger.info(f"Hook analysis persisted for '{audio_title}' → niche={niche_tag}")
        except Exception as e:
            logger.error(f"Failed to persist hook analysis for '{audio_title}': {e}")

    def _update_trend_lifecycle(self, audio_title: str, creator_country: str, scraped_at: str) -> None:
        """Update trend lifecycle spread timeline."""
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

    def scrape_trending_reels(self) -> int:
        """Main scraping method - the core pipeline."""
        total_scraped = 0
        saved_count = 0
        high_velocity = []
        
        if not self._init_browser():
            logger.error("Failed to initialize browser. Aborting scrape.")
            return 0
        
        try:
            priority_pool = (
                self.hashtag_groups["INTERNATIONAL_REGIONAL"][:6]
                + self.hashtag_groups["GLOBAL_TRENDING"][:4]
                + self.hashtag_groups["WESTERN_AND_GLOBAL"][:2]
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
            
            for tag_idx, tag in enumerate(selected):
                # Rate limiting between hashtags
                if tag_idx > 0:
                    wait_time = 3 + (tag_idx % 3)
                    logger.info(f"Rate limiting: waiting {wait_time}s before next hashtag...")
                    time.sleep(wait_time)
                
                logger.info(f"Scraping #{tag} ({tag_idx + 1}/{len(selected)})...")
                items = self._scrape_hashtag_page(tag)
                total_scraped += len(items)
                
                for item in items:
                    try:
                        reel_id = item.get("shortCode")
                        if not reel_id:
                            continue
                        
                        view = int(item.get("videoViewCount") or 0)
                        likes = int(item.get("likesCount") or 0)
                        comments = int(item.get("commentsCount") or 0)
                        followers = int(item.get("ownerFollowersCount") or 0)
                        
                        timestamp = item.get("timestamp")
                        if not timestamp:
                            continue
                        
                        posted = datetime.fromisoformat(timestamp)
                        hours_live = max((datetime.now(timezone.utc) - posted).total_seconds() / 3600.0, 0.5)
                        
                        # Calculate velocity
                        proxy_saves = likes * 0.1
                        proxy_replays = view * 0.05
                        engagement = (
                            view * 1.0 +
                            proxy_saves * 10.0 +
                            comments * 4.0 +
                            likes * 1.0 +
                            proxy_replays * 5.0
                        )
                        subs = max(followers, 1000)
                        velocity = (engagement / hours_live / subs) * 10000
                        
                        # Filter low-engagement
                        if view < 10000 and likes < 200:
                            continue
                        
                        if not (velocity > 0.3 or (view > 15000 and hours_live < 6)):
                            continue
                        
                        # Check duplicates
                        dup = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                        if dup.data:
                            continue
                        
                        # Extract data
                        owner = item.get("ownerUsername")
                        caption = (item.get("caption") or "")[:500]
                        hashtags = re.findall(r"#(\w+)", caption)
                        video_url = item.get("videoUrl")
                        thumbnail_url = item.get("thumbnailUrl")
                        
                        # Extract audio
                        music = item.get("musicInfo")
                        audio_id, audio_title, audio_artist = self._extract_audio_info(music)
                        audio_use = self._extract_audio_use_count(music)
                        
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
                            "video_url": video_url,
                            "thumbnail_url": thumbnail_url,
                            "audio_title": audio_title,
                            "audio_artist": audio_artist,
                            "audio_id": audio_id,
                            "audio_use_count": audio_use,
                            "velocity_score": velocity,
                            "scraped_at": scraped_at,
                        }
                        
                        # Metadata tagging
                        meta = self.detect_reel_metadata(reel)
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
                        })
                        
                        # Video storage
                        is_trend = (velocity > 0.5) or self._is_top_20_for_audio(audio_id, view)
                        if is_trend:
                            stored = self._store_reel_video(reel_id, video_url, audio_id)
                            if stored:
                                reel["preview_url"] = stored
                                reel["video_storage_status"] = "stored"
                                reel["video_stored_at"] = datetime.now(timezone.utc).isoformat()
                            else:
                                reel["preview_url"] = None
                                reel["video_storage_status"] = "failed"
                                reel["video_stored_at"] = None
                        else:
                            reel["video_storage_status"] = "pending"
                        
                        # Insert to DB
                        self.supabase.table("reels").insert(reel).execute()
                        logger.info(f"Saved reel {reel_id} by @{owner} (velocity={velocity:.3f}, lang={meta.get('caption_language')}, origin={meta.get('trend_origin')})")
                        
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
                        logger.error(f"Error processing reel: {e}", exc_info=True)
            
            high_velocity.sort(reverse=True)
            top3 = [round(v, 4) for v in high_velocity[:3]]
            print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")
            logger.info(f"Browser scraping complete: {total_scraped} items processed, {saved_count} saved")
            
            # Hook analysis
            if saved_count:
                logger.info(f"Running Groq hook analysis for {len(audio_groups)} audio groups...")
                for (title, artist), group in audio_groups.items():
                    try:
                        hook = self._run_hook_analysis(title, group)
                        if hook:
                            self._persist_hook_analysis(title, artist, hook)
                    except Exception as e:
                        logger.error(f"Hook analysis error for '{title}': {e}")
            else:
                logger.info("Browser scraper returned 0 items. No DB updates or hook analysis performed.")
            
            return saved_count
            
        finally:
            self._close_browser()


if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.scrape_trending_reels()
