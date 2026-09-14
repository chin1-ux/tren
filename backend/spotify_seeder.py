import logging
from datetime import datetime, timezone
from audio_utils import _normalize_audio_title_and_artist, _extract_remix_indicators

logger = logging.getLogger(__name__)

# Named constants for match threshold calibration
MIN_TITLE_LEN_FOR_ARTIST_BYPASS = 15
MIN_ARTIST_LEN_FOR_SUBSTRING = 5


def extract_artist_fallback(trend_name: str, artist: str) -> str:
    """
    Extracts artist from explicit DB column, falling back to parsing 'trend_name'
    formatted as 'Title - Artist' for legacy candidate rows.
    """
    if artist and artist.strip() and artist.lower() != "none":
        return artist.strip()
    if trend_name and " - " in trend_name:
        parts = trend_name.rsplit(" - ", 1)
        if len(parts) == 2 and parts[1].strip():
            return parts[1].strip()
    return ""


def _are_artists_matching(s_artist_norm: str, r_artist_norm: str, norm_title_len: int) -> bool:
    """
    Evaluates artist matching with title-length gated fallback & MIN_ARTIST_LEN_FOR_SUBSTRING floor.
    """
    # 1. If artist is missing on either side after fallback extraction:
    if not s_artist_norm or not r_artist_norm:
        # Require long/distinctive title (>= 15 chars) to allow artist-missing match.
        # Short/generic titles (< 15 chars) REQUIRE artist verification — no bypass allowed.
        return norm_title_len >= MIN_TITLE_LEN_FOR_ARTIST_BYPASS

    # 2. Exact normalized artist match
    if s_artist_norm == r_artist_norm:
        return True

    # 3. Substring containment requires >= MIN_ARTIST_LEN_FOR_SUBSTRING (prevents short stage name collisions like "SZA")
    if len(s_artist_norm) >= MIN_ARTIST_LEN_FOR_SUBSTRING and s_artist_norm in r_artist_norm:
        return True

    if len(r_artist_norm) >= MIN_ARTIST_LEN_FOR_SUBSTRING and r_artist_norm in s_artist_norm:
        return True

    return False


def is_passive_match(s_title: str, s_artist: str, s_trend_name: str, r_title: str, r_artist: str) -> bool:
    """
    Strict multi-stage passive matching rule.
    """
    effective_s_artist = extract_artist_fallback(s_trend_name, s_artist)

    s_norm_t, s_norm_a = _normalize_audio_title_and_artist(s_title, effective_s_artist)
    r_norm_t, r_norm_a = _normalize_audio_title_and_artist(r_title, r_artist)

    # 1. Minimum normalized title length guard (stops non-ASCII stripped titles)
    if not s_norm_t or not r_norm_t:
        return False

    # 2. Strict normalized title equality
    if s_norm_t != r_norm_t:
        return False

    # 3. Strict symmetric remix-tag set equality
    s_remix: set[str] = _extract_remix_indicators(s_title)
    r_remix: set[str] = _extract_remix_indicators(r_title)
    if s_remix != r_remix:
        return False

    # 4. Artist verification (title-length gated fallback + >= 5-char substring floor)
    return _are_artists_matching(s_norm_a, r_norm_a, len(s_norm_t))


def bind_spotify_candidates_to_scraped_audio(sb) -> list[dict]:
    """
    Passively cross-references unlinked Spotify candidate rows in content_trends (where audio_id IS NULL)
    against scraped reels and trends to auto-bind IG audio_ids and enroll them in tracked_audio.
    """
    if not sb:
        logger.warning("Supabase client is null. Skipping Spotify passive auto-binding.")
        return []

    logger.info("Starting Spotify candidate passive auto-binding...")

    # 1. Fetch unbound Spotify candidate rows
    try:
        sp_res = sb.table("content_trends") \
            .select("id, trend_name, artist, template_pattern, status, niche_relevance, release_year") \
            .eq("trend_type", "audio") \
            .eq("status", "candidate") \
            .is_("audio_id", "null") \
            .execute()
        candidates = sp_res.data or []
    except Exception as e:
        logger.error(f"Failed to fetch unbound Spotify candidates: {e}")
        return []

    if not candidates:
        logger.info("No unbound Spotify candidate rows found.")
        return []

    # 2. Fetch unique scraped audio sources from reels and trends
    scraped_audio_sources = []
    seen_audio_ids = set()

    try:
        reels_res = sb.table("reels") \
            .select("audio_id, audio_title, audio_artist") \
            .not_.is_("audio_id", "null") \
            .execute()
        for r in (reels_res.data or []):
            aid = str(r.get("audio_id") or "")
            if aid and aid not in seen_audio_ids and r.get("audio_title"):
                seen_audio_ids.add(aid)
                scraped_audio_sources.append({
                    "audio_id": aid,
                    "title": r.get("audio_title"),
                    "artist": r.get("audio_artist") or ""
                })
    except Exception as e:
        logger.warning(f"Error fetching reels audio for auto-binding: {e}")

    try:
        trends_res = sb.table("trends") \
            .select("audio_id, audio_title, audio_artist") \
            .not_.is_("audio_id", "null") \
            .execute()
        for t in (trends_res.data or []):
            aid = str(t.get("audio_id") or "")
            if aid and aid not in seen_audio_ids and t.get("audio_title"):
                seen_audio_ids.add(aid)
                scraped_audio_sources.append({
                    "audio_id": aid,
                    "title": t.get("audio_title"),
                    "artist": t.get("audio_artist") or ""
                })
    except Exception as e:
        logger.warning(f"Error fetching trends audio for auto-binding: {e}")

    if not scraped_audio_sources:
        logger.info("No scraped IG audio available to bind candidates against.")
        return []

    # 3. Match candidates against scraped audio sources
    bound_results = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for cand in candidates:
        niche_rel = cand.get("niche_relevance") or {}
        if niche_rel.get("vintage_catalog"):
            logger.debug(f"Skipping vintage catalog candidate '{cand.get('trend_name')}' from auto-binding.")
            continue

        tn = cand.get("trend_name") or ""
        art = cand.get("artist") or ""
        # Extract title portion if formatted as "Title - Artist"
        if " - " in tn and art and tn.endswith(art):
            title = tn[:-len(art)-3].strip()
        elif " - " in tn:
            title = tn.split(" - ")[0].strip()
        else:
            title = tn.strip()

        for source in scraped_audio_sources:
            r_title = source["title"]
            r_artist = source["artist"]
            r_aid = source["audio_id"]

            if is_passive_match(title, art, tn, r_title, r_artist):
                logger.info(f"[SPOTIFY_AUTO_BIND] Bound Spotify candidate '{tn}' to IG audio_id {r_aid} ('{r_title}')")
                
                # Update content_trends.audio_id
                try:
                    sb.table("content_trends") \
                        .update({"audio_id": r_aid}) \
                        .eq("id", cand["id"]) \
                        .execute()
                except Exception as update_err:
                    logger.error(f"Failed to update content_trends.audio_id for {cand['id']}: {update_err}")
                    continue

                # Ensure tracked_audio enrollment to satisfy FK constraint for audio_official_counts
                try:
                    sb.table("tracked_audio").upsert({
                        "audio_id": r_aid,
                        "audio_title": r_title,
                        "audio_artist": r_artist,
                        "first_seen_at": now_iso
                    }, on_conflict="audio_id").execute()
                except Exception as ta_err:
                    logger.warning(f"Failed to upsert tracked_audio for {r_aid}: {ta_err}")

                bound_results.append({
                    "candidate_id": cand["id"],
                    "trend_name": tn,
                    "audio_id": r_aid,
                    "matched_title": r_title
                })
                break  # Stop searching for this candidate once bound

    logger.info(f"Spotify passive auto-binding complete. Bound {len(bound_results)} candidates.")
    return bound_results
