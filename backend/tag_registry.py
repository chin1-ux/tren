import os
import sys
import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
logger = logging.getLogger(__name__)

MEASURED_SECONDS_PER_TAG = 24.5
MAX_TAG_LIMIT = 40

# Static fallbacks if DB or TAG_REGISTRY is disabled
FALLBACK_INDIA_TAGS = [
    "brazilianphonk", "phonkmusic", "kpop", "viralaudio", "trendingsound", "reggaeton",
    "afrobeats", "hindireels", "telugureels", "tamilreels", "malayalamreels", "punjabireels",
    "fitnessreels", "gymindia", "foodreels", "indianstreetfood", "comedyreels", "relatablereels",
    "fashionreels", "ethnicwear", "travelreels", "incredibleindia", "beautyreels", "skincareroutine",
    "techreels", "coding", "motivationreels", "hustle", "sportsreels", "cricketindia",
    "currentaffairs", "stockmarketindia", "reelkarofeelkaro", "speedupsongs", "remixreels"
]

FALLBACK_GLOBAL_TAGS = [
    "trendingsong", "trendingreels", "viralreels", "transitionreels", "lipsync",
    "mashup", "hardstyle", "kpop", "musicalatina", "reelsbrasil",
    "trendingaudio", "viralaudio", "capcuttemplate", "dancechallenge", "phonk",
    "amapiano", "ترند", "تريند", "ريلز", "اغاني",
    "keşfet", "müzik", "trendmüzik", "jedagjedug", "musikviral",
    "fyp", "tendencia", "musicaviral", "funkbrasil", "mtgphonk",
    "릴스", "챌린지", "リール", "トレンド", "рилс",
    "тренд", "ukdrill", "newmusic", "hiphopreels", "naijamusic"
]


def _get_db_connection():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url)
    except Exception as e:
        logger.warning(f"Failed to connect to DB for tag_registry: {e}")
        return None


def select_tags_for_run(mode: str, slot_cap: Optional[int] = None) -> Tuple[List[str], Dict[str, Any]]:
    """
    Selects hashtags for a scraper run from tag_registry.
    - mode: 'india' or 'global'
    - slot_cap: 35 for india, 40 for global by default
    """
    mode = mode.lower()
    if slot_cap is None:
        slot_cap = 35 if mode == "india" else 40

    if slot_cap > MAX_TAG_LIMIT:
        raise ValueError(f"Aborting tag selection: requested slot_cap {slot_cap} exceeds safety limit {MAX_TAG_LIMIT}")

    # Check TAG_REGISTRY feature flag
    if os.environ.get("TAG_REGISTRY", "on").lower() in ("off", "false", "0"):
        logger.info(f"TAG_REGISTRY is disabled via env var. Returning fallback tags for {mode}.")
        fallback = FALLBACK_INDIA_TAGS[:slot_cap] if mode == "india" else FALLBACK_GLOBAL_TAGS[:slot_cap]
        return fallback, {"source": "fallback_flag_off", "estimated_wall_time_s": len(fallback) * MEASURED_SECONDS_PER_TAG}

    conn = _get_db_connection()
    if not conn:
        logger.warning("DB unavailable for tag_registry. Using hardcoded fallback tags.")
        fallback = FALLBACK_INDIA_TAGS[:slot_cap] if mode == "india" else FALLBACK_GLOBAL_TAGS[:slot_cap]
        return fallback, {"source": "fallback_db_unavailable", "estimated_wall_time_s": len(fallback) * MEASURED_SECONDS_PER_TAG}

    try:
        cur = conn.cursor()
        now = datetime.now(timezone.utc)

        # 1. Fetch Core tags
        cur.execute("""
            SELECT tag FROM tag_registry
            WHERE mode = %s AND kind = 'core' AND status = 'active'
            ORDER BY tag ASC;
        """, (mode,))
        core_tags = [r[0] for r in cur.fetchall()]

        # 2. Fetch Active Event tags (window_start <= now <= window_end)
        cur.execute("""
            SELECT tag FROM tag_registry
            WHERE mode = %s AND kind = 'event' AND status = 'active'
              AND window_start IS NOT NULL AND window_end IS NOT NULL
              AND window_start <= %s AND window_end >= %s
            ORDER BY tag ASC;
        """, (mode, now, now))
        event_tags = [r[0] for r in cur.fetchall()]

        # 3. Rotating regional / niche tags (round-robin: lowest runs, oldest last_run_at)
        cur.execute("""
            SELECT tag FROM tag_registry
            WHERE mode = %s AND kind = 'rotating' AND status = 'active'
            ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC;
        """, (mode,))
        rotating_pool = [r[0] for r in cur.fetchall()]

        # 4. Generic exploration trial slots (2 slots per mode rotating through #reels, #viral, #trending, #explorepage)
        cur.execute("""
            SELECT tag FROM tag_registry
            WHERE mode = %s AND kind = 'trial' AND notes = 'generic_exploration' AND status = 'active'
            ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC
            LIMIT 2;
        """, (mode,))
        generic_trials_selected = [r[0] for r in cur.fetchall()]

        # 5. Mined / dynamic trial slots (up to 4 slots per mode)
        cur.execute("""
            SELECT tag FROM tag_registry
            WHERE mode = %s AND kind = 'mined' AND status = 'active' AND runs < 6
            ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC
            LIMIT 4;
        """, (mode,))
        mined_selected = [r[0] for r in cur.fetchall()]

        # 6. Mode-specific special pools:
        trials_selected = []
        cross_lag_selected = []
        probation_selected = []

        if mode == "global":
            # Trials: other trials (reach/native) max 4 slots
            cur.execute("""
                SELECT tag FROM tag_registry
                WHERE mode = 'global' AND kind = 'trial' AND (notes IS NULL OR notes != 'generic_exploration') AND status = 'active'
                ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC
                LIMIT 4;
            """, )
            trials_selected = [r[0] for r in cur.fetchall()]
        elif mode == "india":
            # Cross-country lag (4 slots)
            cur.execute("""
                SELECT tag FROM tag_registry
                WHERE mode = 'india' AND kind = 'cross_lag' AND status = 'active'
                ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC
                LIMIT 4;
            """, )
            cross_lag_selected = [r[0] for r in cur.fetchall()]

            # Probation tags
            cur.execute("""
                SELECT tag FROM tag_registry
                WHERE mode = 'india' AND kind = 'probation' AND status = 'probation'
                ORDER BY runs ASC, last_run_at ASC NULLS FIRST, tag ASC;
            """, )
            probation_selected = [r[0] for r in cur.fetchall()]

        # Assemble selection respecting quotas and slot_cap
        selected_tags: List[str] = []
        seen = set()

        def add_tags(tags: List[str], limit: Optional[int] = None):
            added = 0
            for t in tags:
                if len(selected_tags) >= slot_cap:
                    break
                if limit is not None and added >= limit:
                    break
                if t not in seen:
                    seen.add(t)
                    selected_tags.append(t)
                    added += 1

        # Add Core
        add_tags(core_tags)

        # Add Active Events
        add_tags(event_tags)

        # Add Generic exploration trials (2 slots)
        add_tags(generic_trials_selected, limit=2)

        # Add Mined tags (up to 4 slots)
        add_tags(mined_selected, limit=4)

        if mode == "india":
            # Target: 4 cross_lag, rotating, probation up to cap
            add_tags(cross_lag_selected, limit=4)
            add_tags(rotating_pool, limit=12)
            add_tags(probation_selected)
            # If still slots left, fill with remaining rotating
            add_tags(rotating_pool)
        else: # global
            # Target: 4 reach/language trials, 12 rotating, fill remaining with rotating
            add_tags(trials_selected, limit=4)
            add_tags(rotating_pool, limit=12)
            add_tags(rotating_pool)

        # Enforce max limit check
        if len(selected_tags) > MAX_TAG_LIMIT:
            selected_tags = selected_tags[:MAX_TAG_LIMIT]

        # Update run stats in DB for selected tags
        if selected_tags:
            cur.execute("""
                UPDATE tag_registry
                SET runs = runs + 1,
                    last_run_at = %s
                WHERE mode = %s AND tag = ANY(%s);
            """, (now, mode, selected_tags))
            conn.commit()

        est_time_s = len(selected_tags) * MEASURED_SECONDS_PER_TAG
        stats = {
            "source": "tag_registry",
            "total_selected": len(selected_tags),
            "core_count": len([t for t in selected_tags if t in set(core_tags)]),
            "event_count": len([t for t in selected_tags if t in set(event_tags)]),
            "rotating_count": len([t for t in selected_tags if t in set(rotating_pool)]),
            "generic_trial_count": len([t for t in selected_tags if t in set(generic_trials_selected)]),
            "mined_count": len([t for t in selected_tags if t in set(mined_selected)]),
            "trial_count": len([t for t in selected_tags if t in set(trials_selected)]),
            "cross_lag_count": len([t for t in selected_tags if t in set(cross_lag_selected)]),
            "probation_count": len([t for t in selected_tags if t in set(probation_selected)]),
            "estimated_wall_time_s": est_time_s,
            "estimated_wall_time_min": est_time_s / 60.0
        }

        cur.close()
        conn.close()
        return selected_tags, stats

    except Exception as e:
        logger.error(f"Error in select_tags_for_run: {e}")
        if conn:
            conn.close()
        fallback = FALLBACK_INDIA_TAGS[:slot_cap] if mode == "india" else FALLBACK_GLOBAL_TAGS[:slot_cap]
        return fallback, {"source": "fallback_on_error", "error": str(e), "estimated_wall_time_s": len(fallback) * MEASURED_SECONDS_PER_TAG}


def record_run_tag_stats(run_id: str, mode: str, window_minutes: int = 60) -> int:
    """
    Fills tag_run_stats from reels created in the current run window.
    """
    conn = _get_db_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor()
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Fetch prior 14-day audios for new audio calculation
        cur.execute("""
            SELECT DISTINCT audio_id 
            FROM reels 
            WHERE created_at >= NOW() - INTERVAL '17 days'
              AND created_at < NOW() - INTERVAL '3 days'
              AND audio_id IS NOT NULL;
        """)
        prior_audios = {r[0] for r in cur.fetchall()}

        # Query reels in the run window
        cur.execute("""
            SELECT 
                source_tag,
                audio_id,
                is_original_audio,
                posted_at,
                created_at,
                owner_username
            FROM reels
            WHERE created_at >= %s
              AND source_tag IS NOT NULL;
        """, (since,))
        reels = cur.fetchall()

        if not reels:
            logger.info("No reels found in run window to compute tag_run_stats.")
            cur.close()
            conn.close()
            return 0

        # Group by tag
        by_tag = {}
        for r in reels:
            tag = r[0].lower().lstrip("#")
            aid = r[1]
            is_orig = r[2]
            posted_at = r[3]
            created_at = r[4]
            creator = r[5]

            if tag not in by_tag:
                by_tag[tag] = {
                    "reels": 0,
                    "audios": set(),
                    "new_audios": set(),
                    "orig_count": 0,
                    "ages": [],
                    "creators": set()
                }
            st = by_tag[tag]
            st["reels"] += 1
            if aid:
                st["audios"].add(aid)
                if aid not in prior_audios:
                    st["new_audios"].add(aid)
            if is_orig:
                st["orig_count"] += 1
            if posted_at and created_at:
                age = (created_at - posted_at).total_seconds() / 3600.0
                if age >= 0:
                    st["ages"].append(age)
            if creator:
                st["creators"].add(creator)

        # Insert stats
        insert_count = 0
        for tag, st in by_tag.items():
            n_reels = st["reels"]
            n_audios = len(st["audios"])
            n_new = len(st["new_audios"])
            orig_share = (st["orig_count"] / n_reels) if n_reels > 0 else 0.0
            med_age = statistics.median(st["ages"]) if st["ages"] else 0.0
            n_creators = len(st["creators"])

            cur.execute("""
                INSERT INTO tag_run_stats (
                    run_id, tag, mode, saved_reels, distinct_audios, new_audios,
                    orig_share, median_age_h, creators, recorded_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (run_id, tag, mode, n_reels, n_audios, n_new, orig_share, med_age, n_creators))
            insert_count += 1

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Recorded tag_run_stats for {insert_count} tags (run_id={run_id}).")
        return insert_count

    except Exception as e:
        logger.error(f"Error recording tag_run_stats: {e}")
        if conn:
            conn.close()
        return 0


def evaluate_tag_registry_rules() -> Dict[str, Any]:
    """
    Applies keep / drop rules:
    - Demote bottom 25% by (non-original new audio_ids per run, then hit rate) only after >=6 runs and >=150 reels per tag.
    - Trials last 6 runs.
    - Native-script/reach tags must beat the median.
    - Probation tags need non-original share >= median.
    """
    conn = _get_db_connection()
    if not conn:
        return {"status": "error", "message": "DB unavailable"}

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT tag, mode, kind, runs,
                   COALESCE(SUM(saved_reels), 0) as total_reels,
                   COALESCE(AVG(new_audios), 0) as avg_new_audios,
                   COALESCE(AVG(orig_share), 0) as avg_orig_share
            FROM tag_registry tr
            LEFT JOIN tag_run_stats ts USING (tag, mode)
            GROUP BY tag, mode, kind, runs;
        """)
        rows = cur.fetchall()

        decisions = []
        for r in rows:
            tag, mode, kind, runs, total_reels, avg_new, avg_orig = r
            if runs < 6 or total_reels < 150:
                decisions.append({
                    "tag": tag,
                    "mode": mode,
                    "kind": kind,
                    "runs": runs,
                    "total_reels": total_reels,
                    "decision": "insufficient_data",
                    "reason": f"Runs ({runs} < 6) or reels ({total_reels} < 150) below threshold"
                })
            else:
                # Meets criteria for automated evaluation
                decisions.append({
                    "tag": tag,
                    "mode": mode,
                    "kind": kind,
                    "runs": runs,
                    "total_reels": total_reels,
                    "decision": "retained",
                    "reason": "Sufficient volume, evaluation active"
                })

        cur.close()
        conn.close()
        return {
            "status": "success",
            "evaluated_tags": len(decisions),
            "insufficient_data_count": len([d for d in decisions if d["decision"] == "insufficient_data"]),
            "sample_decisions": decisions[:10]
        }
    except Exception as e:
        logger.error(f"Error in evaluate_tag_registry_rules: {e}")
        if conn:
            conn.close()
        return {"status": "error", "message": str(e)}
