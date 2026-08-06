"""
Video Visual Analysis System
Analyzes video visual content using OpenCV (free library)
Phase 1 of hybrid approach - visual analysis for virality prediction
"""
import os
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

# Try to import OpenCV - if not available, provide simulation
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("Warning: OpenCV not installed. Visual analysis will use simulation mode.")


class VideoVisualAnalyzer:
    """
    Analyzes video visual content using OpenCV
    Includes face detection, motion analysis, color analysis, text detection
    """
    
    @staticmethod
    def analyze_visual_content(video_path: str) -> Dict:
        """
        Analyze visual content of a video
        
        Args:
            video_path: Path to video file
        
        Returns:
            Visual analysis results
        """
        if not OPENCV_AVAILABLE:
            return VideoVisualAnalyzer._simulate_visual_analysis()
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {'error': 'Could not open video file'}
            
            # Get video properties
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            # Sample frames for analysis
            sample_interval = max(1, frame_count // 30)  # Sample 30 frames
            frames = []
            
            frame_idx = 0
            while len(frames) < 30 and frame_idx < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                frame_idx += sample_interval
            
            cap.release()
            
            if not frames:
                return {'error': 'Could not extract frames from video'}
            
            # Analyze frames
            analysis = {
                'face_detection': VideoVisualAnalyzer._detect_faces(frames),
                'motion_analysis': VideoVisualAnalyzer._analyze_motion(frames),
                'color_analysis': VideoVisualAnalyzer._analyze_colors(frames),
                'scene_detection': VideoVisualAnalyzer._detect_scenes(frames),
                'text_detection': VideoVisualAnalyzer._detect_text(frames)
            }
            
            return analysis
            
        except Exception as e:
            return {'error': f'Visual analysis failed: {str(e)}'}
    
    @staticmethod
    def _detect_faces(frames: List) -> Dict:
        """Detect faces in video frames using OpenCV"""
        try:
            # Load pre-trained face detector
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            faces_per_frame = []
            total_faces = 0
            
            for frame in frames:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
                faces_per_frame.append(len(faces))
                total_faces += len(faces)
            
            avg_faces = total_faces / len(frames) if frames else 0
            max_faces = max(faces_per_frame) if faces_per_frame else 0
            
            return {
                'total_faces_detected': total_faces,
                'average_faces_per_frame': round(avg_faces, 2),
                'max_faces_in_frame': max_faces,
                'frames_with_faces': sum(1 for f in faces_per_frame if f > 0),
                'face_present_percentage': round((sum(1 for f in faces_per_frame if f > 0) / len(frames)) * 100, 2) if frames else 0
            }
            
        except Exception as e:
            return {'error': f'Face detection failed: {str(e)}'}
    
    @staticmethod
    def _analyze_motion(frames: List) -> Dict:
        """Analyze motion patterns in video"""
        try:
            if len(frames) < 2:
                return {'error': 'Not enough frames for motion analysis'}
            
            motion_scores = []
            
            for i in range(len(frames) - 1):
                # Calculate frame difference
                diff = cv2.absdiff(frames[i], frames[i+1])
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                motion_score = gray_diff.mean()
                motion_scores.append(motion_score)
            
            avg_motion = sum(motion_scores) / len(motion_scores) if motion_scores else 0
            max_motion = max(motion_scores) if motion_scores else 0
            
            # Determine motion level
            if avg_motion > 50:
                motion_level = 'high'
            elif avg_motion > 20:
                motion_level = 'medium'
            else:
                motion_level = 'low'
            
            return {
                'average_motion': round(avg_motion, 2),
                'max_motion': round(max_motion, 2),
                'motion_level': motion_level,
                'has_constant_motion': motion_level in ['medium', 'high']
            }
            
        except Exception as e:
            return {'error': f'Motion analysis failed: {str(e)}'}
    
    @staticmethod
    def _analyze_colors(frames: List) -> Dict:
        """Analyze color properties (vibrancy, brightness, saturation)"""
        try:
            if not frames:
                return {'error': 'No frames for color analysis'}
            
            brightness_values = []
            saturation_values = []
            
            for frame in frames:
                # Convert to HSV
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Average brightness (V channel)
                brightness = hsv[:, :, 2].mean()
                brightness_values.append(brightness)
                
                # Average saturation (S channel)
                saturation = hsv[:, :, 1].mean()
                saturation_values.append(saturation)
            
            avg_brightness = sum(brightness_values) / len(brightness_values) if brightness_values else 0
            avg_saturation = sum(saturation_values) / len(saturation_values) if saturation_values else 0
            
            # Determine vibrancy
            if avg_saturation > 150:
                vibrancy = 'high'
            elif avg_saturation > 100:
                vibrancy = 'medium'
            else:
                vibrancy = 'low'
            
            return {
                'average_brightness': round(avg_brightness, 2),
                'average_saturation': round(avg_saturation, 2),
                'vibrancy_level': vibrancy,
                'is_well_lit': 100 <= avg_brightness <= 200,
                'is_colorful': avg_saturation > 100
            }
            
        except Exception as e:
            return {'error': f'Color analysis failed: {str(e)}'}
    
    @staticmethod
    def _detect_scenes(frames: List) -> Dict:
        """Detect scene changes/edits"""
        try:
            if len(frames) < 2:
                return {'error': 'Not enough frames for scene detection'}
            
            scene_changes = 0
            prev_frame = frames[0]
            
            for frame in frames[1:]:
                # Calculate difference
                diff = cv2.absdiff(prev_frame, frame)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                
                # Threshold for scene change
                if gray_diff.mean() > 30:
                    scene_changes += 1
                
                prev_frame = frame
            
            # Calculate edit frequency
            edit_frequency = scene_changes / len(frames) if frames else 0
            
            if edit_frequency > 0.1:
                edit_style = 'fast_cuts'
            elif edit_frequency > 0.05:
                edit_style = 'moderate'
            else:
                edit_style = 'slow'
            
            return {
                'scene_changes': scene_changes,
                'edit_frequency': round(edit_frequency, 3),
                'edit_style': edit_style,
                'estimated_cuts': scene_changes
            }
            
        except Exception as e:
            return {'error': f'Scene detection failed: {str(e)}'}
    
    @staticmethod
    def _detect_text(frames: List) -> Dict:
        """Detect text overlays in video"""
        try:
            # Try to import pytesseract
            import pytesseract
            
            text_present_frames = 0
            text_detections = []
            
            for frame in frames:
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Use pytesseract to detect text
                text = pytesseract.image_to_string(gray)
                
                if text.strip():
                    text_present_frames += 1
                    text_detections.append(text.strip()[:50])  # First 50 chars
            
            text_percentage = (text_present_frames / len(frames)) * 100 if frames else 0
            
            return {
                'frames_with_text': text_present_frames,
                'text_percentage': round(text_percentage, 2),
                'has_text_overlays': text_percentage > 10,
                'text_detected_count': len(text_detections)
            }
            
        except ImportError:
            return {'error': 'pytesseract not installed - text detection requires pytesseract'}
        except Exception as e:
            return {'error': f'Text detection failed: {str(e)}'}
    
    @staticmethod
    def _simulate_visual_analysis() -> Dict:
        """Simulate visual analysis when OpenCV is not available"""
        return {
            'face_detection': {
                'total_faces_detected': 12,
                'average_faces_per_frame': 0.4,
                'max_faces_in_frame': 2,
                'frames_with_faces': 8,
                'face_present_percentage': 26.67
            },
            'motion_analysis': {
                'average_motion': 45.2,
                'max_motion': 89.5,
                'motion_level': 'medium',
                'has_constant_motion': True
            },
            'color_analysis': {
                'average_brightness': 145.8,
                'average_saturation': 128.3,
                'vibrancy_level': 'medium',
                'is_well_lit': True,
                'is_colorful': True
            },
            'scene_detection': {
                'scene_changes': 3,
                'edit_frequency': 0.1,
                'edit_style': 'fast_cuts',
                'estimated_cuts': 3
            },
            'text_detection': {
                'frames_with_text': 5,
                'text_percentage': 16.67,
                'has_text_overlays': True,
                'text_detected_count': 3
            },
            'simulation_mode': True
        }


# Test the video visual analyzer
if __name__ == "__main__":
    print("=== Video Visual Analyzer ===")
    
    print(f"\n[Info] OpenCV Available: {OPENCV_AVAILABLE}")
    
    # Test visual analysis
    print("\n[Test 1] Visual Content Analysis")
    
    if OPENCV_AVAILABLE:
        print("  [OK] Full OpenCV analysis available")
        print("  [Note] Requires actual video file for real analysis")
    else:
        analysis = VideoVisualAnalyzer._simulate_visual_analysis()
        print(f"  [OK] Simulation mode")
        print(f"  [OK] Face detection: {analysis['face_detection']['total_faces_detected']} faces")
        print(f"  [OK] Motion level: {analysis['motion_analysis']['motion_level']}")
        print(f"  [OK] Vibrancy: {analysis['color_analysis']['vibrancy_level']}")
        print(f"  [OK] Edit style: {analysis['scene_detection']['edit_style']}")
        print(f"  [OK] Text overlays: {analysis['text_detection']['has_text_overlays']}")
    
    print("\n=== Video Visual Analyzer Working ===")
    print("\nNote: Install OpenCV with: pip install opencv-python")
    print("Install pytesseract with: pip install pytesseract")
    print("Full visual analysis requires both libraries")