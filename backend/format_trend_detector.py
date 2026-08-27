"""
Format & Caption Pattern Trend Detector
=========================================
Detects visual format trends and meme/challenge patterns beyond pure audio tracking.

Three detection methods:
  1. Caption Template Detection  — recurring structural patterns across multiple reels
     (e.g., "POV: [scenario]", "Wait for it…", "Day [N] of [challenge]")
  2. Format Keyword Detection    — visual format signals in captions ("greenscreen", "duet", etc.)
  3. Challenge Hashtag Detection — sudden velocity spike of a new challenge hashtag

This module is additive — it runs AFTER the main audio trend engine and writes to
the `content_trends` table (to be created via migration).
"""

import re
import os
import sys
import logging
from collections import defaultdict, Counter
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("format_trend_detector")

load_dotenv()

# ─── Constants ────────────────────────────────────────────────────────────────

# Caption template patterns — ordered by specificity (more specific first)
CAPTION_TEMPLATES: list[tuple[str, str, str]] = [
    # (pattern_name, regex_pattern, trend_name_template)
    ("pov_format",         r"(?i)^pov\s*:",                               "POV Format"),
    ("wait_for_it",        r"(?i)\bwait\s+for\s+it\b",                    "Wait For It Format"),
    ("day_of_challenge",   r"(?i)\bday\s+\d+\s+of\b",                    "Day N of Challenge"),
    ("before_after",       r"(?i)\bbefore\s*(vs|versus|or|&)\s*after\b", "Before vs After"),
    ("plot_twist",         r"(?i)\b(plot\s*twist|not\s*what\s*you\s*think)\b", "Plot Twist Format"),
    ("grwm_format",        r"(?i)\bgrwm\b",                               "GRWM Format"),
    ("rate_this",          r"(?i)\brate\s+(this|my|our)\b",               "Rate This Format"),
    ("tell_me_without",    r"(?i)tell\s+me\s+.{0,30}without\s+telling\s+me", "Tell Me Without Format"),
    ("expectation_vs_reality", r"(?i)\b(expectation|expected)\s*(vs|versus|or)\s*(reality|real)\b", "Expectation vs Reality"),
    ("things_nobody_told", r"(?i)\bthings\s+(nobody|no\s+one)\s+(told|tells)\b", "Things Nobody Told Format"),
    ("reasons_i",          r"(?i)\breasons?\s+(why\s+)?i\b",              "Reasons I Format"),
    ("when_you",           r"(?i)^when\s+you\b",                          "When You Format"),
    ("honest_review",      r"(?i)\bhonest\s+review\b",                    "Honest Review Format"),
    ("types_of",           r"(?i)\btypes\s+of\s+\w+",                    "Types Of Format"),
    ("if_you",             r"(?i)^if\s+you\b",                            "If You Format"),
]

# Visual format keywords in captions — map signal → format category
VISUAL_FORMAT_SIGNALS: dict[str, list[str]] = {
    "greenscreen":  ["greenscreen", "green screen", "greenscrn", "chroma key"],
    "duet":         ["duet", "@duet"],
    "stitch":       ["stitch", "#stitch"],
    "transition":   ["transition", "smooth transition", "outfit change", "outfit reveal", "transformation"],
    "talking_head": ["storytime", "story time", "speaking directly", "sit down chat", "vlog style"],
    "text_overlay": ["text overlay", "caption style", "text on screen", "words on screen"],
    "split_screen": ["split screen", "side by side", "comparison"],
    "timelapse":    ["timelapse", "time lapse", "time-lapse", "sped up", "speed up"],
    "asmr":         ["asmr", "#asmr", "satisfying", "#satisfying"],
}

# Minimum reels to be considered a pattern
MIN_REELS_FOR_PATTERN = 5
# Minimum distinct creators for a pattern to be trending (not just one person's style)
MIN_CREATORS_FOR_PATTERN = 3
# Hours lookback window for pattern analysis
PATTERN_LOOKBACK_HOURS = 24


# ─── Core Pattern Extraction ──────────────────────────────────────────────────

def normalize_caption(caption: str) -> str:
    """Normalize a caption for pattern matching."""
    if not caption:
        return ""
    # Strip excess whitespace and collapse multiple newlines
    return re.sub(r"\s+", " ", caption.strip()).lower()


def extract_caption_template(caption: str) -> dict | None:
    """
    Try to match a caption against known templates.
    Returns dict with pattern info or None if no match.
    """
    if not caption:
        return None
    normalized = normalize_caption(caption)
    for pattern_name, regex, trend_name in CAPTION_TEMPLATES:
        if re.search(regex, normalized):
            return {
                "pattern_name": pattern_name,
                "trend_name": trend_name,
                "matched_text": re.search(regex, normalized).group(0),
            }
    return None


def extract_visual_format(caption: str) -> str | None:
    """
    Check if a caption contains signals for a known visual format.
    Returns the format category or None.
    """
    if not caption:
        return None
    normalized = caption.lower()
    for format_name, signals in VISUAL_FORMAT_SIGNALS.items():
        if any(sig in normalized for sig in signals):
            return format_name
    return None


def extract_challenge_hashtags(hashtags: list[str]) -> list[str]:
    """
    Extract hashtags that look like they could be challenge hashtags.
    Pattern: contains "challenge", "trend", "check", or "day" in the tag.
    """
    challenge_tags = []
    for tag in (hashtags or []):
        tag_clean = tag.lower().lstrip("#")
        if any(kw in tag_clean for kw in ["challenge", "trend", "check", "day"]):
            challenge_tags.append(tag_clean)
    return challenge_tags


# ─── Trend Pattern Aggregator ─────────────────────────────────────────────────

class FormatTrendDetector:
    """
    Reads recent reels from the database, extracts format/caption patterns,
    and writes detected format trends to the `content_trends` table.
    """

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Supabase credentials not set in environment.")
        self.supabase = create_client(url, key)

    def load_recent_reels(self, hours: int = PATTERN_LOOKBACK_HOURS) -> list[dict]:
        """Load recent reels from the database for analysis."""
        from datetime import timedelta
        threshold = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            res = self.supabase.table("reels") \
                .select("reel_id,caption,hashtags,owner_username,velocity_score,view_count,like_count,scraped_at,source_hashtag_pool") \
                .gte("scraped_at", threshold) \
                .gt("velocity_score", 0) \
                .order("scraped_at", desc=True) \
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to load recent reels: {e}")
            return []

    def detect_caption_patterns(self, reels: list[dict]) -> list[dict]:
        """
        Group reels by caption template pattern and return a list of detected format trends.
        Only returns patterns with >= MIN_REELS_FOR_PATTERN reels from >= MIN_CREATORS_FOR_PATTERN distinct creators.
        """
        # pattern_name -> list of reels
        pattern_buckets: dict[str, list[dict]] = defaultdict(list)
        
        for reel in reels:
            caption = reel.get("caption") or ""
            match = extract_caption_template(caption)
            if match:
                pattern_name = match["pattern_name"]
                pattern_buckets[pattern_name].append({**reel, "_pattern_match": match})
        
        detected = []
        for pattern_name, bucket in pattern_buckets.items():
            creators = {r.get("owner_username") for r in bucket if r.get("owner_username")}
            if len(bucket) >= MIN_REELS_FOR_PATTERN and len(creators) >= MIN_CREATORS_FOR_PATTERN:
                trend_name = bucket[0]["_pattern_match"]["trend_name"]
                avg_velocity = sum(r.get("velocity_score", 0) for r in bucket) / len(bucket)
                total_views = sum(r.get("view_count", 0) for r in bucket)
                sample_captions = [(r.get("caption") or "")[:150] for r in bucket[:5]]
                
                detected.append({
                    "trend_type": "format",
                    "trend_name": trend_name,
                    "template_pattern": pattern_name,
                    "topic_keywords": [pattern_name.replace("_", " ")],
                    "reel_count": len(bucket),
                    "creator_count": len(creators),
                    "velocity_avg": round(avg_velocity, 3),
                    "total_views": total_views,
                    "confidence": min(0.95, round(len(bucket) / 20 + len(creators) / 10, 2)),
                    "status": "emerging",
                    "sample_captions": sample_captions,
                    "window_hours_remaining": 24.0,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Detected format trend: '{trend_name}' — {len(bucket)} reels, {len(creators)} creators")
        
        return detected

    def detect_visual_formats(self, reels: list[dict]) -> list[dict]:
        """
        Detect visual format trends (greenscreen, duet, transition, etc.)
        """
        format_buckets: dict[str, list[dict]] = defaultdict(list)
        
        for reel in reels:
            caption = reel.get("caption") or ""
            fmt = extract_visual_format(caption)
            if fmt:
                format_buckets[fmt].append(reel)
        
        detected = []
        for format_name, bucket in format_buckets.items():
            creators = {r.get("owner_username") for r in bucket if r.get("owner_username")}
            if len(bucket) >= MIN_REELS_FOR_PATTERN and len(creators) >= MIN_CREATORS_FOR_PATTERN:
                avg_velocity = sum(r.get("velocity_score", 0) for r in bucket) / len(bucket)
                trend_name = format_name.replace("_", " ").title() + " Format"
                
                detected.append({
                    "trend_type": "format",
                    "trend_name": trend_name,
                    "template_pattern": format_name,
                    "topic_keywords": VISUAL_FORMAT_SIGNALS.get(format_name, []),
                    "reel_count": len(bucket),
                    "creator_count": len(creators),
                    "velocity_avg": round(avg_velocity, 3),
                    "total_views": sum(r.get("view_count", 0) for r in bucket),
                    "confidence": min(0.95, round(len(bucket) / 20, 2)),
                    "status": "emerging",
                    "sample_captions": [(r.get("caption") or "")[:150] for r in bucket[:3]],
                    "window_hours_remaining": 24.0,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Detected visual format trend: '{trend_name}' — {len(bucket)} reels, {len(creators)} creators")
        
        return detected

    def detect_challenge_hashtags(self, reels: list[dict]) -> list[dict]:
        """
        Detect trending challenge hashtags.
        """
        tag_buckets: dict[str, list[dict]] = defaultdict(list)
        
        for reel in reels:
            hashtags = reel.get("hashtags") or []
            if isinstance(hashtags, str):
                # Sometimes stored as JSON string
                try:
                    import json
                    hashtags = json.loads(hashtags)
                except Exception:
                    hashtags = []
            challenge_tags = extract_challenge_hashtags(hashtags)
            for tag in challenge_tags:
                tag_buckets[tag].append(reel)
        
        detected = []
        for tag, bucket in tag_buckets.items():
            creators = {r.get("owner_username") for r in bucket if r.get("owner_username")}
            if len(bucket) >= MIN_REELS_FOR_PATTERN and len(creators) >= MIN_CREATORS_FOR_PATTERN:
                avg_velocity = sum(r.get("velocity_score", 0) for r in bucket) / len(bucket)
                trend_name = f"#{tag} Challenge"
                
                detected.append({
                    "trend_type": "challenge",
                    "trend_name": trend_name,
                    "template_pattern": f"hashtag::{tag}",
                    "topic_keywords": [tag],
                    "reel_count": len(bucket),
                    "creator_count": len(creators),
                    "velocity_avg": round(avg_velocity, 3),
                    "total_views": sum(r.get("view_count", 0) for r in bucket),
                    "confidence": min(0.95, round(len(bucket) / 15, 2)),
                    "status": "emerging",
                    "sample_captions": [(r.get("caption") or "")[:150] for r in bucket[:3]],
                    "window_hours_remaining": 18.0,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"Detected challenge trend: '{trend_name}' — {len(bucket)} reels, {len(creators)} creators")
        
        return detected

    def save_content_trends(self, trends: list[dict]) -> int:
        """
        Save detected format/challenge trends to content_trends table.
        Uses upsert on (trend_type, template_pattern) to avoid duplicates.
        Returns count of saved rows.
        """
        if not trends:
            return 0
        
        saved = 0
        for t in trends:
            row = {
                "trend_type": t["trend_type"],
                "trend_name": t["trend_name"],
                "template_pattern": t.get("template_pattern"),
                "topic_keywords": t.get("topic_keywords", []),
                "reel_count": t["reel_count"],
                "velocity_avg": t["velocity_avg"],
                "confidence": t["confidence"],
                "status": t["status"],
                "window_hours_remaining": t.get("window_hours_remaining", 24.0),
                "first_seen_at": t["first_seen_at"],
            }
            try:
                self.supabase.table("content_trends") \
                    .upsert(row, on_conflict="trend_type,template_pattern") \
                    .execute()
                saved += 1
            except Exception as e:
                logger.warning(f"Failed to save content trend '{t['trend_name']}': {e}")
        
        return saved

    def run(self) -> dict:
        """Run the full format trend detection pipeline."""
        logger.info("Starting Format & Caption Pattern Trend Detection...")
        
        reels = self.load_recent_reels()
        logger.info(f"Loaded {len(reels)} recent reels for analysis.")
        
        if not reels:
            return {"status": "no_data", "detected": 0}
        
        # Run all detection methods
        caption_trends = self.detect_caption_patterns(reels)
        visual_trends = self.detect_visual_formats(reels)
        challenge_trends = self.detect_challenge_hashtags(reels)
        
        all_trends = caption_trends + visual_trends + challenge_trends
        
        logger.info(
            f"Format trend detection complete. "
            f"Caption patterns: {len(caption_trends)}, "
            f"Visual formats: {len(visual_trends)}, "
            f"Challenge tags: {len(challenge_trends)}"
        )
        
        return {
            "status": "ok",
            "detected": len(all_trends),
            "caption_patterns": len(caption_trends),
            "visual_formats": len(visual_trends),
            "challenge_trends": len(challenge_trends),
            "trends": all_trends,
        }


def detect_format_trends_from_reels(reels: list[dict]) -> list[dict]:
    """
    Public helper: given a batch of reel dicts (from scraper), return detected format trends.
    Does NOT write to DB — caller is responsible for saving.
    """
    detector = FormatTrendDetector.__new__(FormatTrendDetector)
    detector.supabase = None  # Not needed for in-memory detection
    
    caption_trends = detector.detect_caption_patterns(reels)
    visual_trends = detector.detect_visual_formats(reels)
    challenge_trends = detector.detect_challenge_hashtags(reels)
    
    return caption_trends + visual_trends + challenge_trends


if __name__ == "__main__":
    import asyncio
    detector = FormatTrendDetector()
    result = detector.run()
    print(f"\nDetected {result['detected']} format/challenge trends:")
    for t in result.get("trends", []):
        print(f"  [{t['trend_type'].upper()}] {t['trend_name']} — {t['reel_count']} reels, "
              f"confidence={t['confidence']:.2f}, avg_vel={t['velocity_avg']:.1f}")
