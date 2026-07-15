import os
import json
import logging
import re
import time
import math
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from llm import call_llm
import requests

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

class InstagramScraper:
    def __init__(self):
        load_dotenv()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.session = None
        
        self.hashtag_groups = {
            "GLOBAL_TRENDING": [
                "trending", "reels", "viral", "fyp", "explore",
                "trendingreels", "reelsinstagram", "globalreels", "reelsviral", "foryou"
            ],
            "GLOBAL_NICHES": [
                "aesthetic", "dance", "music", "popmusic", "chartmusic",
                "billboard", "tiktoktrend", "trendingsong", "latesthits", "cinematic"
            ],
            "INDIA_SUPPORTING": [
                "trendingindia", "reelsindia"
            ]
        }

    def _init_browser(self):
        try:
            logger.info("Initializing Instagram API session with cookies...")
            self.session = requests.Session()
            
            cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
            if not os.path.exists(cookies_path):
                logger.error("cookies.json not found! Run the cookie capturing setup first.")
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
            
            for cookie in cookies:
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ".instagram.com"),
                    path=cookie.get("path", "/")
                )
            
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.instagram.com/",
                "Origin": "https://www.instagram.com",
            })
            
            logger.info("Instagram API session successfully initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}", exc_info=True)
            return False

    def _close_browser(self):
        if self.session:
            self.session.close()
            self.session = None

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
                return str(audio_id), audio_title, audio_artist, True
        except Exception as e:
            logger.warning(f"Error extracting audio info: {e}")
        return None, None, None, False

    def _extract_audio_use_count(self, media: dict) -> int:
        try:
            clips_metadata = media.get("clips_metadata", {}) or {}
            music_info = clips_metadata.get("music_info") or media.get("music_info") or {}
            minfo = music_info.get("music_info") or {}
            m_cons = minfo.get("music_consumption_info") or {}
            if "use_count" in m_cons and m_cons["use_count"] is not None:
                return int(m_cons["use_count"])
            
            orig = clips_metadata.get("original_sound_info") or media.get("original_sound_info") or {}
            o_cons = orig.get("consumption_info") or {}
            if "use_count" in o_cons and o_cons["use_count"] is not None:
                return int(o_cons["use_count"])
        except Exception:
            pass
        return 0

    def _scrape_hashtag_page(self, hashtag: str) -> list[dict]:
        url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={hashtag}"
        try:
            logger.info(f"Fetching #{hashtag} via web_info API...")
            resp = self.session.get(
                url,
                headers={
                    "Referer": f"https://www.instagram.com/explore/tags/{hashtag}/",
                },
                timeout=20
            )
            
            if resp.status_code != 200:
                logger.warning(f"API returned status {resp.status_code} for #{hashtag}")
                return []
                
            data = resp.json()
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
                    "media_dict": media
                })
                
            logger.info(f"Extracted {len(items)} eligible video/reel posts for #{hashtag}")
            return items
            
        except Exception as e:
            logger.error(f"API request failed for #{hashtag}: {e}", exc_info=True)
            return []

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
        total_scraped = 0
        saved_count = 0
        high_velocity = []
        
        if not self._init_browser():
            logger.error("Failed to initialize session. Aborting scrape.")
            return 0
        
        try:
            priority_pool = (
                self.hashtag_groups["INDIA_SUPPORTING"][:2]
                + self.hashtag_groups["GLOBAL_TRENDING"][:3]
                + self.hashtag_groups["GLOBAL_NICHES"][:2]
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
                        engagement = (view * 1.0) + (likes * 3.0) + (comments * 5.0)
                        normalized_followers = math.log(followers + 10)
                        velocity = (engagement / hours_live / normalized_followers) * 100
                        
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
                        
                        # Extract audio using the raw media dictionary
                        media_dict = item.get("media_dict")
                        audio_id, audio_title, audio_artist, is_original_audio = self._extract_audio_info(media_dict)
                        audio_use = self._extract_audio_use_count(media_dict)
                        
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
                            "is_original_audio": is_original_audio,
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

                        # Track audio if it is a real (non-original) audio
                        is_orig = is_original_audio or (audio_title and "original audio" in audio_title.lower())
                        if audio_id and not is_orig:
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
                        logger.error(f"Error processing reel: {e}", exc_info=True)
            
            high_velocity.sort(reverse=True)
            top3 = [round(v, 4) for v in high_velocity[:3]]
            print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")
            logger.info(f"Browser scraping complete: {total_scraped} items processed, {saved_count} saved")
            
            # Hook analysis
            if saved_count:
                logger.info(f"Running Groq hook analysis for {len(audio_groups)} audio groups...")
                for idx, ((title, artist), group) in enumerate(audio_groups.items()):
                    if idx > 0:
                        stagger_delay = 1.5
                        logger.info(f"Rate limiting: sleeping {stagger_delay}s before next Groq hook analysis...")
                        time.sleep(stagger_delay)
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

    def scrape_official_audio_counts(self, limit: int = 30) -> None:
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
            results = self._scrape_audio_counts_playwright(active_audio_ids)
            
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

    def _scrape_audio_counts_playwright(self, audio_ids: list[str]) -> dict[str, str]:
        from playwright.sync_api import sync_playwright
        
        results = {}
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        if not os.path.exists(cookies_path):
            err_msg = "cookies.json not found"
            logger.error(f"{err_msg}, cannot run Playwright audio scraper")
            return {aid: err_msg for aid in audio_ids}
            
        with open(cookies_path, "r") as f:
            cookies = json.load(f)
            
        logger.info("Launching Playwright browser context...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Add cookies
            formatted_cookies = []
            for c in cookies:
                formatted_cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                })
            context.add_cookies(formatted_cookies)
            
            page = context.new_page()
            
            for aid in audio_ids:
                url = f"https://www.instagram.com/reels/audio/{aid}/"
                logger.info(f"Checking official count for audio_id {aid} via {url}...")
                try:
                    page.goto(url, wait_until="networkidle", timeout=20000)
                    time.sleep(3)  # wait for client-side JS rendering
                    
                    current_url = page.url
                    if "/accounts/login/" in current_url or "/challenge/" in current_url:
                        logger.error(f"[INSTAGRAM_FRICTION] Redirected to login/challenge page: {current_url}")
                        results[aid] = f"Redirected to login/challenge page: {current_url}"
                        continue
                        
                    body_text = page.inner_text("body")
                    
                    # Scan for rate limits, block or captcha text
                    friction_keywords = [
                        "suspicious activity", "confirm it's you", "robot", "captcha",
                        "restrict", "block", "try again later", "please wait a few minutes"
                    ]
                    friction_detected = None
                    for kw in friction_keywords:
                        if kw in body_text.lower():
                            logger.error(f"[INSTAGRAM_FRICTION] Found friction keyword '{kw}' in body text of {url}")
                            friction_detected = kw
                            
                    if friction_detected:
                        results[aid] = f"Friction keyword found: '{friction_detected}'"
                        continue
                    
                    # Parse count
                    count, precision_bucket = self._parse_reels_count_text(body_text)
                    if count is not None:
                        logger.info(f"Successfully scraped count for {aid}: {count} (precision: {precision_bucket})")
                        self._save_official_count(aid, count, precision_bucket)
                        results[aid] = "SUCCESS"
                    else:
                        logger.warning(f"Could not find Reels count text in page body for {aid}")
                        results[aid] = "Could not find Reels count text in page body"
                        
                except Exception as ex:
                    logger.error(f"Error scraping audio {aid}: {ex}")
                    results[aid] = str(ex)
                
                # Multi-second delay between requests to avoid rate limits
                time.sleep(5)
                
            browser.close()
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
    scraper.scrape_trending_reels()
