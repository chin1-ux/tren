# WARNING: Deprecated/Unused in production API environment.
# This module is only intended for local worker run configurations.
import os
import logging
import numpy as np
import librosa


# Configure logging
try:
    logging.basicConfig(
        filename="beat_detector.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)

class AudioAnalysisError(Exception):
    """Custom exception raised when audio analysis fails due to corruption or loading issues."""
    pass

class BeatDetector:
    """Class to detect song beats and compute photo/video cut points using librosa."""

    @staticmethod
    def analyze_audio(audio_file_path: str) -> dict:
        """
        Loads the first 30 seconds of an audio file and analyzes it to detect
        tempo, beat times, onset times, mood, recommended transition, and duration.

        Args:
            audio_file_path (str): Path to the audio file to analyze.

        Returns:
            dict: Dictionary containing:
                - tempo (float): Detected tempo in BPM
                - beat_times (list): List of timestamps in seconds for detected beats
                - onset_times (list): List of timestamps in seconds for onset events
                - mood (str): Classified mood based on tempo
                - recommended_transition (str): Transition recommended for the mood
                - total_duration (float): Total duration of the analyzed audio clip in seconds

        Raises:
            AudioAnalysisError: If the audio file cannot be loaded or is corrupted.
        """
        logger.info(f"Starting audio analysis for file: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            error_msg = f"Audio file not found: {audio_file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            # 1. Load audio: Only load first 30 seconds — reels are max 30 seconds
            # sr=None preserves the native sampling rate
            y, sr = librosa.load(audio_file_path, duration=30, sr=None)
        except Exception as e:
            error_msg = f"Failed to load or decode audio file '{audio_file_path}'. File might be corrupted: {e}"
            logger.error(error_msg, exc_info=True)
            raise AudioAnalysisError(error_msg) from e

        try:
            # 2. Detect tempo and beats
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            beat_times = beat_times.tolist()

            # Handle tempo output formats (newer librosa returns array or float)
            if hasattr(tempo, "item"):
                tempo_float = float(tempo.item())
            elif isinstance(tempo, (list, np.ndarray)):
                tempo_float = float(tempo[0])
            else:
                tempo_float = float(tempo)

            # 3. Detect onset events (additional cut points)
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            onset_times = onset_times.tolist()

            # 4. Classify music mood and transitions by tempo
            if tempo_float < 70:
                mood = "slow_calm"
                transition = "slow_dissolve"
            elif tempo_float < 100:
                mood = "chill"
                transition = "smooth_transition"
            elif tempo_float < 130:
                mood = "upbeat"
                transition = "fast_cuts"
            elif tempo_float < 160:
                mood = "energetic"
                transition = "zoom_pulse"
            else:
                mood = "intense"
                transition = "color_flash"

            # Compute total duration of loaded audio
            total_duration = float(librosa.get_duration(y=y, sr=sr))

            result = {
                "tempo": tempo_float,
                "beat_times": beat_times,
                "onset_times": onset_times,
                "mood": mood,
                "recommended_transition": transition,
                "total_duration": total_duration
            }

            logger.info(f"Successfully analyzed '{audio_file_path}'. Tempo: {tempo_float:.2f} BPM, Beats: {len(beat_times)}, Onsets: {len(onset_times)}, Mood: {mood}")
            return result

        except Exception as e:
            error_msg = f"Error occurred during analysis of audio file '{audio_file_path}': {e}"
            logger.error(error_msg, exc_info=True)
            raise AudioAnalysisError(error_msg) from e

    @staticmethod
    def get_cut_points(beat_data, num_photos: int) -> list:
        """
        Given the beat_times list and number of photos, return exactly num_photos
        evenly distributed timestamps from beat_times to use as cut points.
        If fewer beats than photos, interpolate between beats.

        Args:
            beat_data (dict or list): The dictionary returned by analyze_audio or the list of beat_times directly.
            num_photos (int): The exact number of cut points to return.

        Returns:
            list: A list containing exactly `num_photos` float timestamps.
        """
        if isinstance(beat_data, dict):
            beat_times = beat_data.get("beat_times", [])
        else:
            beat_times = beat_data

        if num_photos <= 0:
            logger.warning(f"Requested {num_photos} cut points. Returning empty list.")
            return []

        if not beat_times:
            logger.warning("No beat times provided for cut points calculation. Returning empty list.")
            return []

        n_beats = len(beat_times)

        # Edge cases
        if num_photos == 1:
            return [beat_times[0]]

        if n_beats == 1:
            logger.warning("Only 1 beat available. Repeating it to match num_photos.")
            return [beat_times[0]] * num_photos

        # Use linear interpolation/spacing for even distribution.
        # x_old represents the original indices [0, 1, ..., n_beats - 1]
        # x_new represents the desired evenly spaced indices [0, ..., n_beats - 1] of length num_photos
        x_old = np.arange(n_beats)
        x_new = np.linspace(0, n_beats - 1, num_photos)
        
        # Interpolate the beat times at the new indices
        cut_points = np.interp(x_new, x_old, beat_times).tolist()
        
        logger.info(f"Generated {len(cut_points)} cut points from {n_beats} beats. Min: {cut_points[0]:.3f}s, Max: {cut_points[-1]:.3f}s")
        return cut_points
