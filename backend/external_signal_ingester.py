import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Tuple, Optional

from dynamic_hashtag_discoverer import DynamicHashtagDiscoverer


class ExternalSignalIngester:
    """
    Ingests external viral audio signals (Spotify Viral 50 India)
    and converts track/artist pairs into clean standalone candidate hashtags.
    """

    def __init__(self, max_existing_reels_floor: int = 5):
        self.max_existing_reels_floor = max_existing_reels_floor
        self.discoverer = DynamicHashtagDiscoverer()

    def derive_standalone_hashtags(self, title: str, artist: str) -> List[str]:
        """
        Derive standalone normalized title and artist hashtags.
        Discards concatenated strings (#titleartist) which empirical tests proved creators do not use.
        """
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', title or '').lower()
        clean_artist = re.sub(r'[^a-zA-Z0-9]', '', artist or '').lower()

        candidates = []
        if clean_title and len(clean_title) >= 3:
            is_valid, _ = self.discoverer.check_meta_blacklist(clean_title)
            if is_valid:
                candidates.append(clean_title)

        if clean_artist and len(clean_artist) >= 3:
            is_valid, _ = self.discoverer.check_meta_blacklist(clean_artist)
            if is_valid and clean_artist not in candidates:
                candidates.append(clean_artist)

        return candidates

    def is_covered_in_db(self, existing_reel_count: int) -> bool:
        """
        Returns True if candidate derived tag already has >= max_existing_reels_floor reels in DB.
        """
        return existing_reel_count >= self.max_existing_reels_floor

    def process_external_tracks(
        self,
        tracks: List[Dict],
        db_reel_counts_map: Dict[str, int]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Processes Spotify Viral 50 tracks into candidate external seed hashtags.
        Returns (promoted_seeds, audit_log).
        """
        now = datetime.now(timezone.utc)
        promoted_seeds = []
        audit_log = []

        for track in tracks:
            title = track.get('title') or track.get('name') or ''
            artist = track.get('artist') or track.get('artists') or ''

            derived_tags = self.derive_standalone_hashtags(title, artist)

            for tag in derived_tags:
                count = db_reel_counts_map.get(tag, 0)
                if self.is_covered_in_db(count):
                    audit_log.append({
                        'hashtag': f"#{tag}",
                        'track_title': title,
                        'artist': artist,
                        'db_reels_count': count,
                        'status': f"SKIPPED_ALREADY_COVERED (>= {self.max_existing_reels_floor} reels)"
                    })
                else:
                    promoted_seeds.append({
                        'hashtag': f"#{tag}",
                        'score': 1.0,  # External Spotify Viral seed priority
                        'recent_count': 0,
                        'baseline_count': 0,
                        'relevance_reason': f"EXTERNAL_SPOTIFY_VIRAL_SEED ('{title}' by {artist})",
                        'unique_creators': 0,
                        'promoted_at': now.isoformat(),
                        'expires_at': (now + timedelta(hours=72)).isoformat()
                    })

        return promoted_seeds, audit_log
