import os
import sys
import logging
import json
import io
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("video_visual_analyzer")

# Check Gemini API availability
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.warning("google-generativeai module not installed. Vision analysis will use text fallback heuristics.")

# Check OpenCV / Pillow availability for frame extraction
try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class VideoVisualAnalyzer:
    """
    Multi-Modal Vision Analysis Engine (Zero-Cost Storage Architecture).
    Extracts 3 in-memory keyframes (0.5s, 3.0s, end) from public reel previews,
    runs Gemini 1.5 Flash Vision classification for action tagging (OOTD, Gym, Dance, Talking Head)
    and OCR text overlays, keeping Supabase storage at EXACTLY 0 MB.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_2")
        self.model = None
        if _GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("Initialized Gemini 1.5 Flash Vision model for keyframe analysis.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini Vision model: {e}")

    def analyze_reel_keyframes_in_memory(
        self,
        image_bytes_list: List[bytes],
        caption: str = "",
        hashtags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze 1–3 keyframe image byte payloads using Gemini 1.5 Flash.
        Returns structured visual action tags, OCR text, and vibe categories.
        """
        if not self.model or not image_bytes_list:
            logger.info("Vision analysis running in text-fallback mode (no Gemini key or images).")
            return self._fallback_text_analysis(caption, hashtags)

        try:
            pil_images = []
            for img_bytes in image_bytes_list[:3]:
                if img_bytes and len(img_bytes) > 100:
                    try:
                        img = Image.open(io.BytesIO(img_bytes))
                        pil_images.append(img)
                    except Exception as img_err:
                        logger.warning(f"Could not parse image byte stream: {img_err}")

            if not pil_images:
                return self._fallback_text_analysis(caption, hashtags)

            prompt = (
                "You are an expert Instagram Reels visual analyst. Analyze these keyframes from a video reel.\n"
                "Extract structured JSON with the following exact keys:\n"
                "- 'visual_action': Primary action shown (e.g., 'OOTD Showcase', 'Gym Workout', 'Talking Head', 'Dance Choreo', 'Food Recipe', 'Car Edit', 'Product Unboxing', 'POV Meme')\n"
                "- 'vibe_category': Aesthetic / vibe ('transition', 'aesthetic', 'comedy', 'fitness', 'fashion', 'motivational')\n"
                "- 'detected_text_overlays': List of any visible on-screen text/POV captions\n"
                "- 'camera_motion': Type of camera movement ('static', 'slow pan', 'whip transition', 'handheld')\n"
                "- 'confidence': Float between 0.0 and 1.0\n\n"
                "Return ONLY valid JSON."
            )

            contents = [prompt] + pil_images
            response = self.model.generate_content(contents)
            
            raw_text = (response.text or "").strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            logger.info(f"Gemini Vision classification SUCCESS: visual_action='{parsed.get('visual_action')}', vibe='{parsed.get('vibe_category')}'")
            return {
                "status": "success",
                "visual_action": parsed.get("visual_action", "General Reel"),
                "vibe_category": parsed.get("vibe_category", "general"),
                "detected_text_overlays": parsed.get("detected_text_overlays", []),
                "camera_motion": parsed.get("camera_motion", "unknown"),
                "confidence": float(parsed.get("confidence", 0.85)),
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Gemini Vision analysis error: {e}", exc_info=True)
            return self._fallback_text_analysis(caption, hashtags)

    def _fallback_text_analysis(self, caption: str = "", hashtags: List[str] = None) -> Dict[str, Any]:
        """
        Rule-based text fallback when Gemini API or images are unavailable.
        """
        text = (caption or "").lower()
        tags = [t.lower() for t in (hashtags or [])]
        combined = text + " " + " ".join(tags)

        visual_action = "General Reel"
        vibe_category = "general"

        if any(w in combined for w in ["gym", "workout", "gains", "chest", "legday", "fitness"]):
            visual_action = "Gym Workout"
            vibe_category = "fitness"
        elif any(w in combined for w in ["ootd", "grwm", "fashion", "outfit", "style"]):
            visual_action = "OOTD Showcase"
            vibe_category = "fashion"
        elif any(w in combined for w in ["dance", "choreo", "steps", "indiandance"]):
            visual_action = "Dance Choreo"
            vibe_category = "transition"
        elif any(w in combined for w in ["pov", "relatable", "funny", "lol", "meme", "comedy"]):
            visual_action = "POV Meme"
            vibe_category = "comedy"
        elif any(w in combined for w in ["recipe", "food", "cooking", "delicious", "eat"]):
            visual_action = "Food Recipe"
            vibe_category = "aesthetic"

        return {
            "status": "fallback_heuristics",
            "visual_action": visual_action,
            "vibe_category": vibe_category,
            "detected_text_overlays": [],
            "camera_motion": "unknown",
            "confidence": 0.65,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }


# Quick test wrapper
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyzer = VideoVisualAnalyzer()
    res = analyzer.analyze_reel_keyframes_in_memory([], caption="POV: GRWM for college outfit check #ootd #fashion")
    print("Test Fallback Analysis Output:", res)