import os
import re
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Camoufox and browser-use imports (assumed installed)
try:
    from camoufox import launch as launch_camoufox
except ImportError:
    raise ImportError("camoufox is required for InstagramScraperBrowser but is not installed.")

try:
    from browser_use import BrowserUse
except ImportError:
    raise ImportError("browser-use is required for InstagramScraperBrowser but is not installed.")

# Supabase client
from supabase import create_client, Client

# LLM hook (reuse existing implementation)
from llm import call_llm

logging.basicConfig(
    filename="instagram_scraper_browser.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class InstagramScraperBrowser:
    """Browser-based Instagram scraper that matches the original ``InstagramScraper`` interface.

    It uses a stealth Firefox binary via ``camoufox`` and high-level actions via
    ``browser-use``. All public methods are compatible with the existing pipeline
    and can be selected with the ``SCRAPER_BACKEND=browser_use`` environment variable.
    """

    def __init__(self):
        load_dotenv()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        # Global & Western focused hashtag groups
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
        self.browser = None
        self._init_browser()

    def _init_browser(self):
        try:
            self.browser = launch_camoufox(headless=True)
            self.browser_use = BrowserUse(self.browser)
            logging.info("Camoufox launched and wrapped with BrowserUse.")
        except Exception as e:
            logging.error(f"Failed to launch camoufox: {e}")
            raise

    def _extract_audio_id(self, music_info_dict: dict | None) -> str | None:
        if not music_info_dict:
            return None
        minfo = music_info_dict.get("music_info") or {}
        asset = minfo.get("music_asset_info") or {}
        audio_id = (
            asset.get("id")
            or asset.get("audio_cluster_id")
            or asset.get("audioClusterId")
            or asset.get("music_id")
        )
        if audio_id:
            return str(audio_id)
        orig = music_info_dict.get("original_sound_info") or {}
        audio_id = orig.get("audio_asset_id") or orig.get("id") or orig.get("audio_id")
        return str(audio_id) if audio_id else None

    def _extract_audio_use_count(self, music_info_dict: dict | None) -> int:
        if not music_info_dict:
            return 0
        minfo = music_info_dict.get("music_info") or {}
        m_cons = minfo.get("music_consumption_info") or {}
        if "use_count" in m_cons and m_cons["use_count"] is not None:
            try:
                return int(m_cons["use_count"])
            except Exception:
                pass
        asset = minfo.get("music_asset_info") or {}
        for key in ["use_count","usage_count","reel_count","usageCount"]:
            if asset.get(key) is not None:
                try:
                    return int(asset[key])
                except Exception:
                    pass
        orig = music_info_dict.get("original_sound_info") or {}
        o_cons = orig.get("consumption_info") or {}
        if "use_count" in o_cons and o_cons["use_count"] is not None:
            try:
                return int(o_cons["use_count"])
            except Exception:
                pass
        for key in ["use_count","usage_count","reel_count","usageCount"]:
            if orig.get(key) is not None:
                try:
                    return int(orig[key])
                except Exception:
                    pass
        clip = music_info_dict.get("clip_metadata") or {}
        for key in ["total_reel_usage_count","reel_count","use_count"]:
            if clip.get(key) is not None:
                try:
                    return int(clip[key])
                except Exception:
                    pass
        return 0

    def _scrape_hashtag_page(self, hashtag: str) -> list[dict]:
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        try:
            page = self.browser_use.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
            script_content = page.evaluate(
                "() => {"
                "  const scripts = Array.from(document.querySelectorAll('script'));"
                "  const target = scripts.find(s => s.textContent.includes('window._sharedData'));"
                "  return target ? target.textContent : '';"
                "}"
            )
            if not script_content:
                logging.warning(f"No shared data script found for #{hashtag}")
                return []
            json_str = script_content.split('window._sharedData = ')[1].split(';</script>')[0].strip()
            data = json.loads(json_str)
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
                    "ownerFollowersCount": None,
                    "timestamp": datetime.fromtimestamp(node.get('taken_at_timestamp', 0), tz=timezone.utc).isoformat(),
                    "ownerUsername": node.get('owner', {}).get('username'),
                    "caption": (node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text') or ''),
                    "videoUrl": node.get('video_url'),
                    "musicInfo": node.get('music_info'),
                })
            logging.info(f"Scraped {len(items)} reels for #{hashtag} via browser")
            return items
        except Exception as e:
            logging.error(f"Browser scrape failed for #{hashtag}: {e}")
            return []
        finally:
            try:
                page.close()
            except Exception:
                pass

    def scrape_trending_reels(self) -> int:
        total_scraped = 0
        saved_count = 0
        high_velocity = []
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
        logging.info(f"Scraping {len(selected)} hashtags: {selected}")
        scraped_at = datetime.now(timezone.utc).isoformat()
        audio_groups: dict[tuple, list[dict]] = {}
        for tag in selected:
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
                    if view < 10000 and likes < 200:
                        continue
                    if not (velocity > 0.3 or (view > 15000 and hours_live < 6)):
                        continue
                    dup = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                    if dup.data:
                        continue
                    owner = item.get("ownerUsername")
                    caption = (item.get("caption") or "")[:500]
                    hashtags = re.findall(r"#(\w+)", caption)
                    video_url = item.get("videoUrl")
                    music = item.get("musicInfo")
                    audio_id = self._extract_audio_id(music)
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
                        "audio_id": audio_id,
                        "audio_use_count": audio_use,
                        "velocity_score": velocity,
                        "scraped_at": scraped_at,
                    }
                    meta = self.detect_reel_metadata(reel)
                    creator_country = meta.get("creator_country", "unknown")
                    india_use = 0
                    if audio_id:
                        res = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_id", audio_id).eq("creator_country", "IN").execute()
                        india_use = res.count or 0
                    if creator_country == "IN":
                        india_use += 1
                    sat = self.calculate_saturation(audio_use, india_use)
                    window = self.calculate_window_hours(audio_use, velocity * 100)
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
                    self.supabase.table("reels").insert(reel).execute()
                    logging.info(f"Saved reel {reel_id} by @{owner} (velocity={velocity:.3f})")
                    self._update_trend_lifecycle(
                        audio_title=meta.get("audio_title", "unknown_trend"),
                        creator_country=creator_country,
                        scraped_at=scraped_at,
                    )
                    saved_count += 1
                    high_velocity.append(velocity)
                    audio_title = meta.get("audio_title")
                    audio_artist = meta.get("audio_artist")
                    if audio_title:
                        key = (audio_title.strip(), (audio_artist or "").strip())
                        audio_groups.setdefault(key, []).append(reel)
                except Exception as e:
                    logging.error(f"Error processing reel: {e}", exc_info=True)
        high_velocity.sort(reverse=True)
        top3 = [round(v, 4) for v in high_velocity[:3]]
        print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")
        if saved_count:
            logging.info(f"Running Groq hook analysis for {len(audio_groups)} audio groups...")
            for (title, artist), group in audio_groups.items():
                try:
                    hook = self._run_hook_analysis(title, group)
                    if hook:
                        self._persist_hook_analysis(title, artist, hook)
                except Exception as e:
                    logging.error(f"Hook analysis error for '{title}': {e}")
        else:
            logging.info("Browser scraper returned 0 items. No DB updates performed.")
        return saved_count

    # Delegated helpers - use absolute imports (this is not a package)
    def calculate_saturation(self, audio_use_count: int, india_use_count: int) -> dict:
        from instagram_scraper import calculate_saturation
        return calculate_saturation(audio_use_count, india_use_count)

    def calculate_window_hours(self, audio_use_count: int, velocity_pct: float) -> int:
        from instagram_scraper import calculate_window_hours
        return calculate_window_hours(audio_use_count, velocity_pct)

    def _is_top_20_for_audio(self, audio_id: str, view_count: int) -> bool:
        """Check if reel would be in top 20 by view_count for this audio_id."""
        if not audio_id:
            return False
        try:
            res = self.supabase.table("reels").select("id", count="exact").eq("audio_id", audio_id).gt("view_count", view_count).execute()
            count = res.count if hasattr(res, 'count') else (len(res.data) if res.data else 0)
            return count < 20
        except Exception as e:
            logging.error(f"Error checking top 20 for audio {audio_id}: {e}")
            return True

    def _store_reel_video(self, reel_id: str, video_url: str, audio_id: str) -> str | None:
        """Download and upload video to Supabase storage."""
        if not video_url:
            return None
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(video_url, headers=headers, timeout=20)
            if not response.ok:
                logging.error(f"Download failed for video {video_url}: {response.status_code}")
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
            logging.info(f"Stored reel video {reel_id} at {url}")
            return url
        except Exception as e:
            logging.error(f"Video store failed for reel {reel_id}: {e}")
            return None

    def _run_hook_analysis(self, audio_title: str, reels_batch: list[dict]) -> dict:
        """Groq inference for hook patterns - same prompt as original scraper."""
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
            logging.error(f"Hook analysis failed for '{audio_title}': {e}")
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
        except Exception as e:
            logging.error(f"Failed to persist hook analysis for '{audio_title}': {e}")

    def _update_trend_lifecycle(self, audio_title: str, creator_country: str, scraped_at: str) -> None:
        """Update trend lifecycle spread timeline in Supabase."""
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
            logging.error(f"Error updating trend lifecycle: {e}", exc_info=True)

    def detect_reel_metadata(self, reel: dict) -> dict:
        """LLM metadata tagging - same prompt as original scraper."""
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
            '  "confidence": 0.0\n'
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
            logging.error(f"Error in detect_reel_metadata: {e}")
            return {
                "caption_language": "unknown",
                "audio_language": "unknown",
                "trend_origin": "unknown",
                "creator_country": "unknown",
                "is_cross_cultural": False,
                "confidence": 0.0
            }

