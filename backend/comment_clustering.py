import re
import os
import logging
from collections import defaultdict
from rapidfuzz import fuzz, process
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger("comment_clustering")

load_dotenv("backend/.env")

# Generic noise patterns to drop before clustering
NOISE_PATTERNS = re.compile(
    r'^(nice|first|lol+|wow|fire|omg|😂+|🔥+|❤️+|👍+)$', re.IGNORECASE
)

# A simple regex-based noun-phrase and key term extractor
# Extracts capitalized words (potential named entities) and common noun phrases
NOUN_PHRASE_PATTERN = re.compile(
    r'\b(?:[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*|\w{3,15}\s+(?:decision|referee|win|loss|match|player|umpire|game|song|track|trend|reels?|video))\b'
)

# Regex to strip hashtags from text
HASHTAG_PATTERN = re.compile(r'#\w+')

def clean_comments(comments: list[str]) -> list[str]:
    """Strip hashtags and noise comments before entity extraction."""
    cleaned = []
    for c in comments:
        text = c.strip()
        # Remove all hashtags from the text
        text = HASHTAG_PATTERN.sub('', text).strip()
        if len(text) < 3 or NOISE_PATTERNS.match(text):
            continue
        cleaned.append(text)
    return cleaned


# Stopwords to exclude from phrase extraction
STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for",
    "with", "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don",
    "should", "now", "like", "share", "follow", "reels", "reel", "video", "post", "instagram",
    "for", "you", "please", "page", "explore", "trending", "viral",
    "always", "really", "literally", "totally", "actually", "probably", "maybe", "never",
    "sometimes", "often", "back", "again", "going", "come", "get", "make", "think", "know"
}

def extract_phrases_regex(text: str) -> list[str]:
    """
    Extract entity candidates and key noun phrases using simple regex-based heuristics,
    applying a strict stopword filter.
    """
    matches = NOUN_PHRASE_PATTERN.findall(text)
    extracted = []
    for m in matches:
        phrase = m.lower().strip()
        # Drop stopwords and single short characters
        if phrase in STOPWORDS or len(phrase) < 3:
            continue
        # If it matches a single word, ensure it's not a common stopword
        if " " not in phrase and phrase in STOPWORDS:
            continue
        extracted.append(phrase)
    return extracted


class CommentClusteringEngine:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.error(f"Failed to create Supabase client in CommentClusteringEngine: {e}")
                self.supabase = None
        else:
            self.supabase = None
            
        self.alias_table = {}
        self.load_alias_table()

    def load_alias_table(self):
        """Load aliases from Supabase."""
        if not self.supabase:
            return
        try:
            res = self.supabase.table("comment_aliases").select("*").execute()
            if res.data:
                for row in res.data:
                    self.alias_table[row["alias"].lower()] = row["canonical_key"].lower()
        except Exception as e:
            logger.error(f"Error loading comment_aliases: {e}")

    def save_new_aliases(self, canonical_key: str, sample_phrases: list[str]):
        """Upsert newly discovered variations into comment_aliases table."""
        if not self.supabase:
            return
        try:
            # Clean and filter new candidate phrases
            to_upsert = []
            for phrase in set(sample_phrases):
                phrase_clean = phrase.lower().strip()
                if not phrase_clean or len(phrase_clean) < 3:
                    continue
                if phrase_clean not in self.alias_table:
                    to_upsert.append({
                        "alias": phrase_clean,
                        "canonical_key": canonical_key.lower().strip()
                    })
                    # Update local state immediately
                    self.alias_table[phrase_clean] = canonical_key.lower().strip()
            
            if to_upsert:
                self.supabase.table("comment_aliases").upsert(to_upsert).execute()
                logger.info(f"Successfully upserted {len(to_upsert)} new aliases for '{canonical_key}'")
        except Exception as e:
            logger.error(f"Failed to upsert new aliases for '{canonical_key}': {e}")

    def canonicalize_phrase(self, phrase: str, threshold: int = 85) -> str:
        """
        Match an extracted phrase against known canonical aliases using fuzzy matching.
        """
        phrase_norm = phrase.lower().strip()

        if phrase_norm in self.alias_table:
            return self.alias_table[phrase_norm]

        if self.alias_table:
            # Fuzzy match against existing alias keys
            match = process.extractOne(
                phrase_norm, self.alias_table.keys(), scorer=fuzz.token_sort_ratio
            )
            if match and match[1] >= threshold:
                return self.alias_table[match[0]]

        return phrase_norm

    def build_clusters(self, comments_with_meta: list[dict]) -> dict:
        """
        comments_with_meta: [{"text": str, "post_id": str, "creator_id": str, "extracted_phrases": [str]}]
        Returns: {canonical_key: {"unique_posts": set, "unique_creators": set, "total_comments": int, "sample_phrases": [str]}}
        """
        clusters = defaultdict(lambda: {
            "unique_posts": set(),
            "unique_creators": set(),
            "total_comments": 0,
            "sample_phrases": []
        })

        for item in comments_with_meta:
            for phrase in item.get("extracted_phrases", []):
                key = self.canonicalize_phrase(phrase)
                clusters[key]["unique_posts"].add(item["post_id"])
                clusters[key]["unique_creators"].add(item["creator_id"])
                clusters[key]["total_comments"] += 1
                if item["text"] not in clusters[key]["sample_phrases"]:
                    if len(clusters[key]["sample_phrases"]) < 10:
                        clusters[key]["sample_phrases"].append(item["text"])

        return clusters

    def calculate_cpdi_and_flag(self, clusters: dict, min_unique_posts: int = 5, cpdi_threshold: float = 0.15) -> list[dict]:
        """
        CPDI = unique_creators / total_comments
        Flags clusters with sufficient cross-post spread.
        """
        flagged = []
        for key, data in clusters.items():
            unique_posts = len(data["unique_posts"])
            unique_creators = len(data["unique_creators"])
            total = data["total_comments"]

            if unique_posts < min_unique_posts:
                continue

            cpdi = unique_creators / total if total else 0
            if cpdi >= cpdi_threshold:
                # Basic Heat Score formulation: DHS = unique_posts * (1 + log(total_comments))
                # For simplified offline testing (without prior history), velocity V is assumed to be 1.0
                import math
                heat_score = unique_posts * (1 + math.log(total))
                flagged.append({
                    "canonical_key": key,
                    "unique_posts_count": unique_posts,
                    "unique_creators_count": unique_creators,
                    "total_comments_count": total,
                    "cpdi": round(cpdi, 3),
                    "heat_score": round(heat_score, 2),
                    "sample_phrases": data["sample_phrases"]
                })

        flagged.sort(key=lambda x: x["unique_posts_count"], reverse=True)
        return flagged[:5]

def build_batch_naming_prompt(flagged_clusters: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(flagged_clusters):
        sample_text = "\n".join(f"- {p}" for p in c["sample_phrases"][:8])
        blocks.append(f"Cluster {i+1} (canonical_key: {c['canonical_key']}):\n{sample_text}")

    prompt = f"""You will be given {len(flagged_clusters)} clusters of comments from different Instagram posts, each cluster representing a possible trending topic.

For EACH cluster, return a 3-word title and a 1-sentence summary of what's being discussed.

Respond ONLY in JSON, no preamble, in this exact format:
{{
  "clusters": [
    {{"canonical_key": "...", "title": "...", "summary": "..."}},
    ...
  ]
}}

{chr(10).join(blocks)}
"""
    return prompt
