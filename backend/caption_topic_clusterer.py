import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import math


class CaptionTopicClusterer:
    """
    Autonomous Caption & Topic Clustering Engine for format & transition trends.
    Discovers non-audio template trends via TF-IDF Cosine Similarity, synopsis detection, CTA filtering, foreign language filtering, and stopword-filtered n-gram extraction.
    """

    KNOWN_PATTERN_HOOKS = [
        r"\bpov\b", r"\bwait till\b", r"\bwait for\b", r"\btransformation\b", r"\bglow up\b",
        r"\bbefore vs after\b", r"\bday \d+ of\b", r"\bwatch till\b", r"\boutfit reveal\b",
        r"\btransition\b", r"\bwait for the end\b", r"\bhow to\b", r"\bstyle check\b",
        r"\bgrwm\b", r"\bget ready\b", r"\brecipereel\b", r"\bdiy\b"
    ]

    # Structural Movie/Show Synopsis, Bio & Narrative Credit Regex Filter
    SYNOPSIS_REGEX_FILTER = re.compile(
        r"\b(story|revolves|revolves around|was born|starring|cast|synopsis|plot|directed|directed by|produced|produced by|written|written and|lead role|lead roles|film|movie|actor|actress|cinema|rights|reserved|copyright|subscribe|follow|credit|credits|one of the|one of the most|one of the best)\b",
        re.IGNORECASE
    )

    # Token-combination structural CTA & social courtesy marketing spam words
    CTA_VERBS = {'dm', 'inbox', 'message', 'collab', 'order', 'price', 'buy', 'shop', 'contact', 'whatsapp', 'email', 'thank', 'thanks', 'comment', 'follow'}
    CTA_DESTINATIONS = {'link', 'bio', 'details', 'number', 'promo', 'watching', 'following', 'support', 'help', 'orders', 'purchases', 'below'}

    # Foreign Non-Target Language Tokens (Portuguese, Spanish) to prevent non-Indian scope creep
    FOREIGN_LANGUAGE_TOKENS = {
        'escala', '6x1', 'brasil', 'deputado', 'federal', 'cassinos', 'viver', 'trabalho', 'trabalhar',
        'milhões', 'milhoes', 'aquela', 'sica', 'arcángel', 'arcangel', 'américa', 'americas',
        'chuva', 'difícil', 'dificil', 'música', 'musica', 'família', 'familia', 'semana', 'saúde', 'saude',
        'cofres', 'discussão', 'discussao', 'alguém', 'alguem', 'seguidores', 'tempo', 'vida', 'tudo'
    }

    # Social engagement hashtag-spam tokens to strip completely prior to n-gram extraction
    GENERIC_ENGAGEMENT_TOKENS = {
        'fyp', 'viral', 'explore', 'trending', 'foryou', 'reels', 'feed', 'algorithm',
        'explorepage', 'viralreels', 'instagood', 'instagram', 'like', 'share', 'follow', 'thank'
    }

    # Stopwords across English, Hindi, and Portuguese function words
    STOPWORDS = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t', 'as', 'at',
        'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'cant', 'cannot',
        'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t', 'down', 'during', 'each',
        'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have', 'haven\'t', 'having', 'he', 'he\'d',
        'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i',
        'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if', 'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s',
        'me', 'more', 'most', 'mustn\'t', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or',
        'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll',
        'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs',
        'them', 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve',
        'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll',
        'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which',
        'while', 'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d',
        'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves',
        'de', 'do', 'da', 'dos', 'das', 'em', 'um', 'uma', 'na', 'no', 'que', 'com', 'por', 'para', 'se', 'el', 'la', 'los', 'las'
    }

    def __init__(
        self,
        similarity_threshold: float = 0.60,
        min_creators_floor: int = 2,
        min_views_single_creator: int = 50000,
        pattern_boost_multiplier: float = 1.5
    ):
        self.similarity_threshold = similarity_threshold
        self.min_creators_floor = min_creators_floor
        self.min_views_single_creator = min_views_single_creator
        self.pattern_boost_multiplier = pattern_boost_multiplier
        self.compiled_hooks = re.compile(r"|".join(self.KNOWN_PATTERN_HOOKS), re.IGNORECASE)

    def is_proper_name_or_celebrity(self, raw_caption: str, ng: str) -> bool:
        """
        Named Entity Detector: Checks if the n-gram matched a Title Case proper name / celebrity in the original raw caption.
        """
        if not raw_caption or not ng:
            return False

        words = ng.split()
        if len(words) >= 2:
            pattern = r"\b" + r"\s+".join([rf"{re.escape(w.title())}" for w in words]) + r"\b"
            if re.search(pattern, raw_caption):
                if not self.compiled_hooks.search(ng):
                    return True

        return False

    def is_synopsis_or_spam(self, ng: str, creator_names: Set[str], raw_caption: str = "") -> bool:
        """
        Structural detector for plot synopses, CTA/marketing spam, foreign language tokens, hashtag-spam tokens, celebrity names, and creator handles.
        """
        # 1. Structural plot synopsis / credit pattern detector
        if self.SYNOPSIS_REGEX_FILTER.search(ng):
            return True

        words = set(ng.lower().split())

        # 2. Foreign Non-Target Language Token Detector (Portuguese, Spanish)
        if any(fw in words for fw in self.FOREIGN_LANGUAGE_TOKENS):
            return True

        # 3. Token-combination structural CTA & social courtesy detector (verb or destination tokens)
        if any(w in self.CTA_VERBS or w in self.CTA_DESTINATIONS for w in words):
            return True

        # 4. Generic engagement token check (fyp, viral, explore)
        if all(w in self.GENERIC_ENGAGEMENT_TOKENS or w in self.STOPWORDS for w in words):
            return True

        # 5. Pure digits / year number leakage check (e.g. 1999, 2024, 2026)
        if any(w.isdigit() for w in words):
            return True

        # 6. Proper Name / Celebrity Named Entity detector
        if self.is_proper_name_or_celebrity(raw_caption, ng):
            return True

        # 7. Personal creator name/handle detector
        for w in words:
            if len(w) >= 4 and any(w in c.lower() for c in creator_names if c):
                return True

        return False

    def extract_ngrams(self, caption: str) -> List[str]:
        """
        Extract meaningful 2-grams and 3-grams from caption text.
        Strips hashtags, mentions, URLs, foreign language tokens, CTA spam, generic engagement tokens, and stopwords.
        """
        if not caption:
            return []

        text = re.sub(r'http\S+|www\S+|@\w+|#\w+', '', caption)
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text).lower()
        
        words = [w for w in text.split() if len(w) >= 2 and w not in self.GENERIC_ENGAGEMENT_TOKENS and w not in self.FOREIGN_LANGUAGE_TOKENS and not w.isdigit()]

        ngrams = []
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i+1]
            pair = f"{w1} {w2}"
            if (w1 not in self.STOPWORDS or w2 not in self.STOPWORDS) and not self.SYNOPSIS_REGEX_FILTER.search(pair):
                ngrams.append(pair)

        for i in range(len(words) - 2):
            w1, w2, w3 = words[i], words[i+1], words[i+2]
            non_stop_count = sum(1 for w in [w1, w2, w3] if w not in self.STOPWORDS)
            triplet = f"{w1} {w2} {w3}"
            if non_stop_count >= 2 and not self.SYNOPSIS_REGEX_FILTER.search(triplet):
                ngrams.append(triplet)

        return ngrams

    def generate_cluster_key(self, ngrams: List[str]) -> str:
        """
        Generates a collision-resistant cluster key using the top 2 discriminating n-grams.
        """
        if not ngrams:
            return f"format_generic_{int(datetime.now(timezone.utc).timestamp())}"

        filtered = [ng for ng in ngrams if not all(w in self.STOPWORDS or w in self.GENERIC_ENGAGEMENT_TOKENS for w in ng.split())]
        counts = Counter(filtered if filtered else ngrams)
        most_common = [item[0] for item in counts.most_common(2)]

        slugified = []
        for phrase in most_common:
            slug = re.sub(r'[^a-zA-Z0-9]', '_', phrase).strip('_')
            if slug:
                slugified.append(slug)

        key_body = "_".join(slugified) if slugified else "unknown"
        return f"format_{key_body}"

    def evaluate_format_gate(self, reels: List[Dict]) -> Tuple[bool, str, float]:
        """
        Evaluates format candidate cluster against creator diversity floor and engagement override.
        """
        if not reels:
            return False, "NO_REELS", 0.0

        creators = set()
        max_views = 0
        max_likes = 0
        has_hook_pattern = False

        for r in reels:
            creator = r.get('owner_username') or r.get('creator_username') or r.get('owner_id')
            if creator:
                creators.add(creator)

            plays = r.get('view_count') or r.get('play_count') or 0
            likes = r.get('like_count') or 0

            if plays > max_views:
                max_views = plays
            if likes > max_likes:
                max_likes = likes

            cap = r.get('caption') or ''
            if self.compiled_hooks.search(cap):
                has_hook_pattern = True

        passed_gate = False
        pass_reason = ""

        if len(creators) >= self.min_creators_floor:
            passed_gate = True
            pass_reason = "CREATOR_DIVERSITY_PASSED"
        elif len(creators) == 1:
            if max_views >= self.min_views_single_creator:
                passed_gate = True
                pass_reason = "SINGLE_CREATOR_HIGH_VELOCITY_OVERRIDE"
            else:
                return False, f"INSUFFICIENT_CREATOR_DIVERSITY (1 creator, max_views={max_views} < {self.min_views_single_creator})", 0.0
        else:
            return False, "NO_CREATOR_DATA", 0.0

        base_velocity = (len(reels) + 1.0) / 5.0
        if has_hook_pattern:
            base_velocity *= self.pattern_boost_multiplier

        return True, pass_reason, round(base_velocity, 4)

    def determine_lifecycle_status(self, creator_count: int, velocity: float, peak_velocity: float) -> str:
        """
        Lifecycle state machine for format trends: emerging -> rising -> peaked -> expired.
        """
        if peak_velocity > 0 and velocity < (0.60 * peak_velocity):
            return "peaked"
        if creator_count >= 5 or velocity >= 1.5:
            return "rising"
        if creator_count >= 2 or velocity >= 0.4:
            return "emerging"
        return "emerging"

    def calculate_tfidf_score(self, ng: str, doc_count: int, total_docs: int) -> float:
        """
        Calculate TF-IDF relevance score for n-gram candidate ranking.
        """
        idf = math.log((total_docs + 1.0) / (doc_count + 1.0)) + 1.0
        words = ng.split()
        non_stop_ratio = sum(1 for w in words if w not in self.STOPWORDS and w not in self.GENERIC_ENGAGEMENT_TOKENS) / max(1, len(words))
        return idf * non_stop_ratio

    def cluster_reels(self, reels: List[Dict]) -> List[Dict]:
        """
        Unsupervised TF-IDF n-gram phrase clustering across reel captions.
        Filters out movie synopses, credit blocks, CTA/marketing spam, foreign language tokens, digit leaks, celebrity names, and creator handles.
        """
        total_docs = len(reels)
        all_creator_names = set(r.get('owner_username') or r.get('owner_id') for r in reels if (r.get('owner_username') or r.get('owner_id')))

        ngram_map = {}
        for r in reels:
            cap = r.get('caption') or ''
            ngrams = self.extract_ngrams(cap)
            for ng in set(ngrams):
                if not self.is_synopsis_or_spam(ng, all_creator_names, raw_caption=cap):
                    if ng not in ngram_map:
                        ngram_map[ng] = []
                    ngram_map[ng].append(r)

        clusters = []
        processed_reels = set()

        ranked_ngrams = []
        for ng, cluster_reels in ngram_map.items():
            creators = set(r.get('owner_username') or r.get('owner_id') for r in cluster_reels)
            if len(creators) < self.min_creators_floor:
                continue

            tfidf = self.calculate_tfidf_score(ng, len(cluster_reels), total_docs)
            hook_boost = 1.5 if self.compiled_hooks.search(ng) else 1.0
            rank_score = tfidf * len(creators) * hook_boost
            ranked_ngrams.append((rank_score, ng, cluster_reels))

        ranked_ngrams.sort(key=lambda x: x[0], reverse=True)

        for rank_score, ng, cluster_reels in ranked_ngrams:
            unassigned_reels = [r for r in cluster_reels if r.get('id') not in processed_reels]
            if len(unassigned_reels) < self.min_creators_floor:
                continue

            is_valid, reason, velocity = self.evaluate_format_gate(unassigned_reels)
            if is_valid:
                all_ngrams = []
                for r in unassigned_reels:
                    all_ngrams.extend(self.extract_ngrams(r.get('caption') or ''))

                cluster_key = self.generate_cluster_key(all_ngrams)
                creators = list(set(r.get('owner_username') or r.get('owner_id') for r in unassigned_reels if (r.get('owner_username') or r.get('owner_id'))))
                status = self.determine_lifecycle_status(len(creators), velocity, velocity)

                clusters.append({
                    'cluster_key': cluster_key,
                    'format_name': ng.title(),
                    'primary_ngrams': [ng],
                    'creator_count': len(creators),
                    'reel_count': len(unassigned_reels),
                    'velocity_score': velocity,
                    'peak_velocity': velocity,
                    'status': status,
                    'sample_reel_ids': [str(r.get('id')) for r in unassigned_reels[:5]]
                })

                for r in unassigned_reels:
                    processed_reels.add(r.get('id'))

        return clusters
