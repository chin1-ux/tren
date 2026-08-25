# WARNING: Deprecated/Unused in production API environment.
# This module is only intended for local worker run configurations.
import os
import time
import logging

try:
    logging.basicConfig(
        filename="reel_generator.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass
logger = logging.getLogger(__name__)


class ReelGenerator:
    """Create a simple vertical reel from user images and optional audio."""

    def __init__(self):
        pass

    def generate_reel(self, image_paths: list, audio_path: str, output_path: str, progress_callback=None):
        logger.info(f"Generating reel from {len(image_paths)} images and audio {audio_path} to {output_path}")

        if not image_paths:
            raise ValueError("At least one image is required to generate a reel")

        try:
            from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
        except Exception as exc:
            logger.exception("moviepy is required for reel generation")
            raise RuntimeError("Video generation dependencies are missing") from exc

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        clips = []
        total = len(image_paths)
        clip_duration = 1.8

        for index, image_path in enumerate(image_paths, start=1):
            if not os.path.exists(image_path):
                logger.warning(f"Skipping missing image: {image_path}")
                continue
            clip = ImageClip(image_path).with_duration(clip_duration)
            clip = clip.resized(height=1920)
            clip = clip.cropped(width=1080, height=1920, x_center=clip.w / 2, y_center=clip.h / 2)
            clips.append(clip)
            if progress_callback:
                try:
                    progress = int((index / total) * 70)
                    progress_callback(progress)
                except Exception:
                    logger.warning("Progress callback failed during image prep")

        if not clips:
            raise ValueError("No valid images found for reel generation")

        video = concatenate_videoclips(clips, method="compose")

        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                video = video.with_audio(audio)
            except Exception as exc:
                logger.warning(f"Could not attach audio: {exc}")

        if progress_callback:
            try:
                progress_callback(85)
            except Exception:
                pass

        video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac" if audio_path and os.path.exists(audio_path) else None,
            preset="medium",
            threads=2,
            logger=None,
        )

        if progress_callback:
            try:
                progress_callback(100)
            except Exception:
                pass

        logger.info(f"Reel generation complete. Saved output to {output_path}")
