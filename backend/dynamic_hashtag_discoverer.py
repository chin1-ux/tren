import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Tuple, Optional


class DynamicHashtagDiscoverer:
    """
    Autonomous, high-precision hashtag discovery pipeline.
    Mines ingested reels for accelerating hashtags and applies a non-circular Quality Gate.
    """

    # Regex patterns matching exact meta-tags and substring spam variants anywhere in tag (e.g. #kpopfyp, #viralvideo, #explorepage)
    SPAM_PATTERNS = [
        r".*fyp.*", r".*viral.*", r".*trending.*", r".*explore.*", r".*foryou.*",
        r".*follow.*", r".*likeforlike.*", r".*like4like.*", r".*sub4sub.*",
        r"^reels$", r"^reelsinstagram$", r"^reelsvideo$"
    ]

    def __init__(
        self,
        max_queue_size: int = 10,
        default_ttl_hours: int = 72,
        min_views_single_creator: int = 50000,
        min_likes_single_creator: int = 5000,
        spam_patterns: Optional[List[str]] = None
    ):
        self.max_queue_size = max_queue_size
        self.default_ttl_hours = default_ttl_hours
        self.min_views_single_creator = min_views_single_creator
        self.min_likes_single_creator = min_likes_single_creator
        
        patterns = spam_patterns if spam_patterns is not None else self.SPAM_PATTERNS
        self.compiled_spam_regex = re.compile(r"|".join(patterns), re.IGNORECASE)

    def normalize_hashtag(self, tag: str) -> str:
        """Strip leading '#' and convert to lowercase."""
        if not tag:
            return ""
        return tag.strip().lower().lstrip('#')

    def check_meta_blacklist(self, hashtag: str) -> Tuple[bool, Optional[str]]:
        """
        Check if hashtag matches meta/spam regex patterns (e.g. #kpopfyp, #viralvideo).
        Returns (is_valid, rejection_reason).
        """
        norm_tag = self.normalize_hashtag(hashtag)
        if not norm_tag:
            return False, "EMPTY_HASHTAG"

        if self.compiled_spam_regex.search(norm_tag):
            return False, "META_SPAM_BLACKLIST"

        return True, None

    def calculate_velocity(self, recent_count: int, baseline_count: int) -> float:
        """
        Calculate acceleration velocity using Laplace smoothing:
        V = (recent_count + 1.0) / (baseline_count + 5.0)
        """
        return (recent_count + 1.0) / (baseline_count + 5.0)

    def evaluate_quality_gate(
        self,
        hashtag: str,
        reels: List[Dict],
        recent_count: int,
        baseline_count: int,
        verified_audio_ids: Optional[Set[str]] = None
    ) -> Tuple[bool, str, float]:
        """
        Evaluate candidate hashtag against Quality Gate rules.
        Returns (is_valid, reason, final_score).
        """
        # 1. Substring Regex-Based Meta/Spam Blacklist Check
        is_valid_tag, blacklist_reason = self.check_meta_blacklist(hashtag)
        if not is_valid_tag:
            return False, blacklist_reason, 0.0

        # Calculate base velocity
        velocity = self.calculate_velocity(recent_count, baseline_count)

        # 2. Creator Diversity & Single-Creator Override Check
        creators = set()
        max_play_count = 0
        max_like_count = 0
        has_anchor_cooccurrence = False

        verified_audios = verified_audio_ids if verified_audio_ids else set()

        for r in reels:
            creator = r.get('owner_username') or r.get('creator_username') or r.get('owner_id')
            if creator:
                creators.add(creator)

            plays = r.get('play_count') or r.get('video_view_count') or 0
            likes = r.get('like_count') or 0

            if plays > max_play_count:
                max_play_count = plays
            if likes > max_like_count:
                max_like_count = likes

            aid = r.get('audio_id')
            if aid and str(aid) in verified_audios:
                has_anchor_cooccurrence = True

        passed_diversity = False
        pass_reason = ""

        if len(creators) >= 2:
            passed_diversity = True
            pass_reason = "CREATOR_DIVERSITY_PASSED"
        elif len(creators) == 1:
            # Single-creator high-velocity override requires absolute engagement floor
            if max_play_count >= self.min_views_single_creator or max_like_count >= self.min_likes_single_creator:
                passed_diversity = True
                pass_reason = "SINGLE_CREATOR_HIGH_VELOCITY_OVERRIDE"
            else:
                return False, f"INSUFFICIENT_CREATOR_DIVERSITY (1 creator, max_views={max_play_count} < {self.min_views_single_creator})", 0.0
        else:
            return False, "NO_CREATOR_DATA", 0.0

        # 3. Score Calculation & Anchor Co-occurrence Confidence Booster
        final_score = velocity
        if has_anchor_cooccurrence:
            final_score *= 1.5  # 1.5x rank boost for verified anchor co-occurrence

        return True, pass_reason, round(final_score, 4)

    def build_queue(self, candidates: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Sort candidate tags by score, cap queue at max_queue_size,
        and assign TTL expiration timestamps.
        Returns (promoted_queue, audit_log).
        """
        now = datetime.now(timezone.utc)
        ttl_expires_at = (now + timedelta(hours=self.default_ttl_hours)).isoformat()

        valid_candidates = [c for c in candidates if c.get('score', 0) > 0]
        sorted_candidates = sorted(valid_candidates, key=lambda x: x['score'], reverse=True)

        promoted = []
        audited = []

        for idx, item in enumerate(sorted_candidates):
            item_copy = dict(item)
            item_copy['promoted_at'] = now.isoformat()
            item_copy['expires_at'] = ttl_expires_at

            if idx < self.max_queue_size:
                promoted.append(item_copy)
            else:
                item_copy['reason'] = f"QUEUE_CAP_EXCEEDED (Rank #{idx+1})"
                audited.append(item_copy)

        return promoted, audited
