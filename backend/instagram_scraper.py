import os
import re
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client
from llm import call_llm

try:
    logging.basicConfig(
        filename="instagram_scraper.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass


# ── Utility helpers ───────────────────────────────────────────────────────────

def calculate_saturation(audio_use_count: int, india_use_count: int) -> dict:
    """
    Returns global and India saturation percentages (0–100).
    Thresholds:
      < 5K   = early (0–15%)
      5K–20K = rising (15–45%)
      20K–100K = peak (45–80%)
      > 100K = saturated (80–100%)
    India is typically 8–15x behind global for the same trend.
    """
    global_pct = min(100.0, (audio_use_count / 100_000) * 100)
    india_pct = min(100.0, (india_use_count / 8_000) * 100)
    return {
        "global": round(global_pct, 1),
        "india": round(india_pct, 1),
    }


def calculate_window_hours(audio_use_count: int, velocity_pct: float) -> int:
    """
    Estimates hours remaining before audio trend window closes.
    velocity_pct is velocity_score * 100 (i.e. units already ×100 since raw scores are small).
    """
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
        if not os.getenv("APIFY_API_TOKEN"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.apify_token:
            raise ValueError("APIFY_API_TOKEN missing from .env")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")

        # Support multiple comma-separated tokens for rotation
        tokens = [t.strip() for t in self.apify_token.split(",") if t.strip()]
        self.apify_clients = [ApifyClient(t) for t in tokens]
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

    def _is_top_20_for_audio(self, audio_id: str, view_count: int) -> bool:
        """Check if reel would be in the top 20 reels by view_count for this audio_id."""
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
        """Downloads MP4 from video_url and uploads to reels-preview bucket."""
        if not video_url:
            return None
        try:
            import requests
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(video_url, headers=headers, timeout=20)
            if not response.ok:
                logging.error(f"Download failed for video {video_url} with status {response.status_code}")
                return None
            
            safe_audio_id = audio_id or "no_audio"
            path = f"reels/{safe_audio_id}/{reel_id}.mp4"
            
            self.supabase.storage.from_("reels-preview").upload(
                path=path,
                file=response.content,
                file_options={"content-type": "video/mp4", "x-upsert": "true"}
            )
            
            # Bulletproof public URL resolver
            try:
                public_url_obj = self.supabase.storage.from_("reels-preview").get_public_url(path)
                if public_url_obj:
                    url = str(public_url_obj)
                else:
                    url = f"{self.supabase_url}/storage/v1/object/public/reels-preview/{path}"
            except Exception:
                url = f"{self.supabase_url}/storage/v1/object/public/reels-preview/{path}"
                
            logging.info(f"Successfully stored reel video {reel_id} at {url}")
            return url
        except Exception as e:
            logging.error(f"Video store failed for reel {reel_id}: {e}")
            return None

    # ── Audio helpers ─────────────────────────────────────────────────────────

    def _extract_audio_id(self, music_info_dict: dict | None) -> str | None:
        """Extract Instagram audio cluster/asset ID from musicInfo dict."""
        if not music_info_dict:
            return None
        # Try music_info -> music_asset_info id
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
        # Fallback: original_sound_info
        orig = music_info_dict.get("original_sound_info") or {}
        audio_id = orig.get("audio_asset_id") or orig.get("id") or orig.get("audio_id")
        return str(audio_id) if audio_id else None

    def _extract_audio_use_count(self, music_info_dict: dict | None) -> int:
        """Extract how many reels are currently using this audio."""
        if not music_info_dict:
            return 0
            
        # Log raw musicInfo structure
        try:
            logging.info(f"[AudioScraper] Raw music_info_dict keys: {list(music_info_dict.keys())} | raw: {json.dumps(music_info_dict)}")
        except Exception as log_err:
            logging.warning(f"Could not log music_info_dict: {log_err}")

        # 1. Check music_info -> music_consumption_info -> use_count
        minfo = music_info_dict.get("music_info") or {}
        m_cons = minfo.get("music_consumption_info") or {}
        if "use_count" in m_cons and m_cons["use_count"] is not None:
            try:
                return int(m_cons["use_count"])
            except (TypeError, ValueError):
                pass
                
        # 2. Check music_info -> music_asset_info -> use_count / usage_count etc.
        asset = minfo.get("music_asset_info") or {}
        for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
            if asset.get(key) is not None:
                try:
                    return int(asset[key])
                except (TypeError, ValueError):
                    pass
                    
        # 3. Check original_sound_info -> consumption_info -> use_count
        orig = music_info_dict.get("original_sound_info") or {}
        o_cons = orig.get("consumption_info") or {}
        if "use_count" in o_cons and o_cons["use_count"] is not None:
            try:
                return int(o_cons["use_count"])
            except (TypeError, ValueError):
                pass
                
        # 4. Check original_sound_info direct fields
        for key in ["use_count", "usage_count", "reel_count", "usageCount"]:
            if orig.get(key) is not None:
                try:
                    return int(orig[key])
                except (TypeError, ValueError):
                    pass
                    
        # 5. Check clip_metadata
        clip = music_info_dict.get("clip_metadata") or {}
        for key in ["total_reel_usage_count", "reel_count", "use_count"]:
            if clip.get(key) is not None:
                try:
                    return int(clip[key])
                except (TypeError, ValueError):
                    pass
                    
        return 0

    # ── Groq hook analysis ────────────────────────────────────────────────────

    def _run_hook_analysis(self, audio_title: str, reels_batch: list[dict]) -> dict:
        """
        Runs a single Groq inference call for the top reels sharing the same audio.
        Returns hook_brief, format_patterns, niche_tag.
        """
        # Build compact data string for prompt
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
  "hook_brief_one_line": "string under 15 words telling creator exactly how to open their reel",
  "niche_tags": ["fitness", "food", "comedy", "fashion", "business", "travel", "beauty", "other"]
}}"""

        try:
            result = call_llm(
                system_prompt="You are a social media trend analyst. Return ONLY valid JSON.",
                user_prompt=hook_prompt,
                response_mime_type="application/json",
                timeout=20,
            )
            return result
        except Exception as e:
            logging.error(f"Hook analysis failed for '{audio_title}': {e}")
            return {}

    def _persist_hook_analysis(self, audio_title: str, audio_artist: str, hook_data: dict):
        """Stores hook_brief, format_patterns, niche_tag back onto all matching reels."""
        if not hook_data:
            return
        niche_tags = hook_data.get("niche_tags") or []
        niche_tag = niche_tags[0] if niche_tags else "general"
        hook_brief = [
            {
                "dominant_hook_type": hook_data.get("dominant_hook_type"),
                "hook_opening_patterns": hook_data.get("hook_opening_patterns", []),
                "hook_brief_one_line": hook_data.get("hook_brief_one_line", ""),
                "optimal_length_seconds": hook_data.get("optimal_length_seconds", 30),
            }
        ]
        format_patterns = [
            {
                "visual_format": hook_data.get("visual_format"),
                "dominant_hook_type": hook_data.get("dominant_hook_type"),
            }
        ]
        try:
            self.supabase.table("reels").update({
                "hook_brief": json.dumps(hook_brief),
                "format_patterns": json.dumps(format_patterns),
                "niche_tag": niche_tag,
                "avg_reel_length_seconds": hook_data.get("optimal_length_seconds", 0),
            }).eq("audio_title", audio_title).eq("audio_artist", audio_artist).execute()
            logging.info(f"Hook analysis persisted for '{audio_title}' → niche={niche_tag}")
        except Exception as e:
            logging.error(f"Failed to persist hook analysis for '{audio_title}': {e}")

    # ── Apify call ────────────────────────────────────────────────────────────

    def _call_apify_with_retry(self, hashtag: str, max_retries: int = 3, delay: int = 15):
        """Calls Apify Instagram Hashtag Scraper with retry logic and client rotation."""
        actor_id = "apify/instagram-hashtag-scraper"
        run_input = {
            "hashtags": [hashtag],
            "resultsLimit": 10,
            "addParentData": True
        }
        for attempt in range(1, max_retries + 1):
            client = self.apify_clients[(attempt - 1) % len(self.apify_clients)]
            try:
                logging.info(f"Apify call for #{hashtag} (attempt {attempt} using token index {(attempt - 1) % len(self.apify_clients)})")
                run = client.actor(actor_id).call(run_input=run_input)
                dataset_id = None
                if run:
                    if hasattr(run, "default_dataset_id"):
                        dataset_id = run.default_dataset_id
                    elif isinstance(run, dict):
                        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
                    else:
                        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)
                if not dataset_id:
                    raise ValueError("Could not retrieve defaultDatasetId from Apify run")
                items = client.dataset(dataset_id).list_items().items
                logging.info(f"Scraped {len(items)} items for #{hashtag}")
                return items
            except Exception as e:
                logging.error(f"Apify attempt {attempt} failed for #{hashtag}: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    logging.error(f"All {max_retries} attempts failed for #{hashtag}")
                    raise

    def detect_reel_metadata(self, reel: dict) -> dict:
        prompt = f"""
You are a metadata tagger for Instagram Reels. Analyse the following reel data
and return ONLY a valid JSON object, no markdown, no explanation.

Caption: "{reel.get('caption', '')}"
Audio name: "{reel.get('audio_title', '') or reel.get('audio_name', '')}"
Creator location hint: "unknown"

Return this exact JSON structure:
{{
  "caption_language": "english" | "hindi" | "other",
  "audio_language": "english" | "hindi" | "russian" | "portuguese" | "spanish" | "korean" | "other",
  "trend_origin": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",
  "creator_country": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",
  "is_cross_cultural": true | false,
  "confidence": 0.0 to 1.0
}}

Rules:
- is_cross_cultural = true if audio_language !== caption_language
- If caption is in Devanagari script → caption_language = "hindi"
- If caption is in Latin script and English → caption_language = "english"
- If audio name contains non-English/non-Hindi words → tag audio_language accordingly
- Only return the JSON, nothing else
"""
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

    def _update_trend_lifecycle(self, audio_title: str, creator_country: str, scraped_at: str):
        """Update trend lifecycle spread timeline and saturation counts."""
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

    # ── Main scrape ───────────────────────────────────────────────────────────

    def scrape_trending_reels(self):
        """
        Scrapes trending reels across Indian hashtag groups.
        Uses follower-normalized velocity scoring.
        Saves high-velocity reels to Supabase.
        After insertion, runs Groq hook analysis grouped by audio.
        """
        total_scraped = 0
        saved_count = 0
        high_velocity_reels = []

        # Flatten all hashtags with priority
        priority_pool = (
            self.hashtag_groups["INTERNATIONAL_REGIONAL"][:6] +
            self.hashtag_groups["GLOBAL_TRENDING"][:4] +
            self.hashtag_groups["WESTERN_AND_GLOBAL"][:2]
        )
        seen = set()
        selected_hashtags = []
        for h in priority_pool:
            if h not in seen:
                seen.add(h)
                selected_hashtags.append(h)

        logging.info(f"Scraping {len(selected_hashtags)} hashtags: {selected_hashtags}")

        # Group saved reels by audio for later hook analysis
        audio_groups: dict[tuple, list[dict]] = {}

        scraped_time_str = datetime.now(timezone.utc).isoformat()

        for hashtag in selected_hashtags:
            try:
                items = self._call_apify_with_retry(hashtag)
                total_scraped += len(items)

                for item in items:
                    try:
                        reel_id = item.get("shortCode")
                        if not reel_id:
                            continue

                        view_count = int(item.get("videoViewCount") or 0)
                        like_count = int(item.get("likesCount") or 0)
                        comment_count = int(item.get("commentsCount") or 0)
                        follower_count = int(item.get("ownerFollowersCount") or 0)

                        timestamp_str = item.get("timestamp")
                        if not timestamp_str:
                            continue
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1] + "+00:00"
                        posted_at = datetime.fromisoformat(timestamp_str)
                        hours_live = max((datetime.now(timezone.utc) - posted_at).total_seconds() / 3600.0, 0.5)

                        # 2026 algorithm-weighted velocity
                        proxy_saves = like_count * 0.1
                        proxy_replays = view_count * 0.05
                        engagement_2026 = (
                            view_count  * 1.0 +
                            proxy_saves * 10.0 +
                            comment_count * 4.0 +
                            like_count  * 1.0 +
                            proxy_replays * 5.0
                        )
                        subscribers = max(follower_count, 1000)
                        velocity_score = (engagement_2026 / hours_live / subscribers) * 10000

                        if view_count < 10000 and like_count < 200:
                            continue

                        passes_velocity = velocity_score > 0.3
                        passes_raw = view_count > 15000 and hours_live < 6
                        if not (passes_velocity or passes_raw):
                            continue

                        # Skip if already in DB
                        check = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                        if check.data:
                            continue

                        owner_username = item.get("ownerUsername")
                        caption = (item.get("caption") or "")[:500]
                        hashtags_list = re.findall(r"#(\w+)", caption)
                        video_url = item.get("videoUrl")

                        # Parse nested musicInfo
                        music_title = None
                        music_artist = None
                        music_info_dict = item.get("musicInfo")
                        if music_info_dict:
                            minfo = music_info_dict.get("music_info")
                            if minfo:
                                asset = minfo.get("music_asset_info") or {}
                                music_title = asset.get("title")
                                music_artist = asset.get("display_artist")
                            if not music_title or not music_title.strip():
                                orig = music_info_dict.get("original_sound_info")
                                if orig:
                                    music_title = orig.get("original_audio_title")
                                    ig_artist = orig.get("ig_artist") or {}
                                    music_artist = ig_artist.get("username") or ig_artist.get("full_name")

                        thumbnail_url = item.get("thumbnailUrl") or item.get("displayUrl")

                        # Extract audio ID and use count
                        audio_id = self._extract_audio_id(music_info_dict)
                        audio_use_count = self._extract_audio_use_count(music_info_dict)

                        reel_data = {
                            "platform": "instagram",
                            "reel_id": reel_id,
                            "view_count": view_count,
                            "like_count": like_count,
                            "comment_count": comment_count,
                            "posted_at": posted_at.isoformat(),
                            "owner_username": owner_username,
                            "owner_follower_count": follower_count,
                            "caption": caption,
                            "hashtags": hashtags_list,
                            "video_url": video_url,
                            "thumbnail_url": thumbnail_url,
                            "audio_title": music_title,
                            "audio_artist": music_artist,
                            "audio_id": audio_id,
                            "audio_use_count": audio_use_count,
                            "velocity_score": velocity_score,
                            "scraped_at": scraped_time_str,
                        }

                        # Groq metadata tagging
                        metadata = self.detect_reel_metadata(reel_data)
                        creator_country = metadata.get("creator_country", "unknown")
                        
                        # Count Indian reels in DB for this audio ID / title
                        india_use_count = 0
                        try:
                            if audio_id:
                                res_in = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_id", audio_id).eq("creator_country", "IN").execute()
                                india_use_count = res_in.count or 0
                            else:
                                res_in = self.supabase.table("reels").select("reel_id", count="exact").eq("audio_title", music_title).eq("creator_country", "IN").execute()
                                india_use_count = res_in.count or 0
                        except Exception as e:
                            logging.warning(f"Error querying India reels count: {e}")
                            
                        # If current reel is from India, add it to count
                        if creator_country == "IN":
                            india_use_count += 1
                            
                        sat = calculate_saturation(audio_use_count, india_use_count)
                        window_hours = calculate_window_hours(audio_use_count, velocity_score * 100)

                        reel_data.update({
                            "audio_language": metadata.get("audio_language", "unknown"),
                            "caption_language": metadata.get("caption_language", "unknown"),
                            "trend_origin": metadata.get("trend_origin", "unknown"),
                            "creator_country": creator_country,
                            "is_cross_cultural": metadata.get("is_cross_cultural", False),
                            "language_confidence": metadata.get("confidence", 0.0),
                            "global_saturation_pct": sat["global"],
                            "india_saturation_pct": sat["india"],
                            "window_hours_remaining": window_hours,
                        })

                        # Video storage check for trend-card eligibility
                        is_trend_card = (velocity_score > 0.5) or self._is_top_20_for_audio(audio_id, view_count)
                        if is_trend_card:
                            stored_url = self._store_reel_video(reel_id, video_url, audio_id)
                            if stored_url:
                                reel_data["preview_url"] = stored_url
                                reel_data["video_storage_status"] = "stored"
                                reel_data["video_stored_at"] = datetime.now(timezone.utc).isoformat()
                            else:
                                reel_data["preview_url"] = None
                                reel_data["video_storage_status"] = "failed"
                                reel_data["video_stored_at"] = None
                        else:
                            reel_data["video_storage_status"] = "pending"

                        self.supabase.table("reels").insert(reel_data).execute()
                        logging.info(f"Saved reel {reel_id} by @{owner_username} (velocity={velocity_score:.3f})")

                        # Update trend lifecycle
                        self._update_trend_lifecycle(
                            audio_title=music_title or "unknown_trend",
                            creator_country=metadata.get("creator_country", "unknown"),
                            scraped_at=scraped_time_str
                        )

                        high_velocity_reels.append(velocity_score)
                        saved_count += 1

                        # Group for hook analysis
                        if music_title:
                            key = (music_title.strip(), (music_artist or "").strip())
                            if key not in audio_groups:
                                audio_groups[key] = []
                            audio_groups[key].append(reel_data)

                    except Exception as e:
                        logging.error(f"Error processing reel: {e}", exc_info=True)

            except Exception as e:
                logging.error(f"Failed hashtag #{hashtag}: {e}", exc_info=True)

        high_velocity_reels.sort(reverse=True)
        top3 = [round(s, 4) for s in high_velocity_reels[:3]]
        print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")

        if saved_count == 0:
            logging.info("Apify scraping returned 0 items. Retaining last successfully fetched stable dataset from Supabase.")
        else:
            # ── Run Groq hook analysis for each audio group ───────────────────
            logging.info(f"Running Groq hook analysis for {len(audio_groups)} audio groups...")
            for (title, artist), group_reels in audio_groups.items():
                try:
                    hook_data = self._run_hook_analysis(title, group_reels)
                    if hook_data:
                        self._persist_hook_analysis(title, artist, hook_data)
                except Exception as e:
                    logging.error(f"Hook analysis error for '{title}': {e}")

        return saved_count




if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.scrape_trending_reels()
