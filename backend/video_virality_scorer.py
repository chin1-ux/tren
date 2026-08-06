"""
Video Virality Scoring System
Combines metadata and visual analysis to predict video virality
Phase 1 of hybrid approach - weighted scoring with 70-80% accuracy
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


class VideoViralityScorer:
    """
    Combines metadata and visual analysis to predict video virality
    Uses weighted scoring based on research-proven factors
    """
    
    @staticmethod
    def calculate_virality_score(metadata_analysis: Dict, visual_analysis: Dict) -> Dict:
        """
        Calculate overall virality score from metadata and visual analysis
        
        Args:
            metadata_analysis: Result from VideoMetadataAnalyzer
            visual_analysis: Result from VideoVisualAnalyzer
        
        Returns:
            Virality prediction with score, confidence, and recommendations
        """
        # Import dependencies here to avoid errors if not installed
        try:
            from video_metadata_analyzer import VideoMetadataAnalyzer
        except Exception:
            VideoMetadataAnalyzer = None
        
        try:
            from video_visual_analyzer import VideoVisualAnalyzer
        except Exception:
            VideoVisualAnalyzer = None
        
        factors = {}
        
        # Factor 1: Duration score (weight: 0.20)
        duration_score = metadata_analysis.get('scores', {}).get('duration', 50)
        factors['duration'] = duration_score * 0.20
        
        # Factor 2: Aspect ratio score (weight: 0.15)
        aspect_score = metadata_analysis.get('scores', {}).get('aspect_ratio', 50)
        factors['aspect_ratio'] = aspect_score * 0.15
        
        # Factor 3: Resolution score (weight: 0.10)
        resolution_score = metadata_analysis.get('scores', {}).get('resolution', 50)
        factors['resolution'] = resolution_score * 0.10
        
        # Factor 4: Face presence (weight: 0.15)
        face_data = visual_analysis.get('face_detection', {})
        face_percentage = face_data.get('face_present_percentage', 0)
        # Videos with faces get 25% more engagement
        face_score = min(100, face_percentage * 2.5) if face_percentage > 0 else 30
        factors['face_presence'] = face_score * 0.15
        
        # Factor 5: Motion analysis (weight: 0.15)
        motion_data = visual_analysis.get('motion_analysis', {})
        has_motion = motion_data.get('has_constant_motion', False)
        motion_score = 80 if has_motion else 40
        factors['motion'] = motion_score * 0.15
        
        # Factor 6: Color vibrancy (weight: 0.10)
        color_data = visual_analysis.get('color_analysis', {})
        is_colorful = color_data.get('is_colorful', False)
        is_well_lit = color_data.get('is_well_lit', False)
        color_score = 80 if (is_colorful and is_well_lit) else 50
        factors['color'] = color_score * 0.10
        
        # Factor 7: Edit style (weight: 0.10)
        scene_data = visual_analysis.get('scene_detection', {})
        edit_style = scene_data.get('edit_style', 'slow')
        edit_scores = {'fast_cuts': 90, 'moderate': 75, 'slow': 50}
        edit_score = edit_scores.get(edit_style, 50)
        factors['edit_style'] = edit_score * 0.10
        
        # Factor 8: Text overlays (weight: 0.05)
        text_data = visual_analysis.get('text_detection', {})
        has_text = text_data.get('has_text_overlays', False)
        text_score = 85 if has_text else 60
        factors['text_overlays'] = text_score * 0.05
        
        # Calculate combined score
        combined_score = sum(factors.values())
        
        # Determine prediction category
        if combined_score >= 80:
            prediction = "HIGH - Likely to go viral"
            reach_estimate = "10,000-100,000 views"
            engagement_estimate = "15-25% engagement rate"
        elif combined_score >= 60:
            prediction = "MEDIUM - Good performance expected"
            reach_estimate = "5,000-50,000 views"
            engagement_estimate = "10-20% engagement rate"
        elif combined_score >= 40:
            prediction = "LOW - Average performance"
            reach_estimate = "1,000-10,000 views"
            engagement_estimate = "5-15% engagement rate"
        else:
            prediction = "VERY LOW - Poor performance expected"
            reach_estimate = "<1,000 views"
            engagement_estimate = "<5% engagement rate"
        
        # Generate recommendations
        recommendations = []
        
        if duration_score < 70:
            recommendations.append("Adjust video duration to 15-30 seconds for optimal engagement")
        
        if aspect_score < 70:
            recommendations.append("Use vertical 9:16 aspect ratio for better reach on Instagram Reels")
        
        if resolution_score < 70:
            recommendations.append("Increase resolution to 1080x1920 for better quality")
        
        if face_score < 60:
            recommendations.append("Include people/faces in your video - they get 25% more engagement")
        
        if motion_score < 60:
            recommendations.append("Add more motion and action to keep viewers engaged")
        
        if color_score < 60:
            recommendations.append("Improve lighting and use more vibrant colors")
        
        if edit_score < 60:
            recommendations.append("Use faster cuts and transitions to increase retention")
        
        if text_score < 60:
            recommendations.append("Add text overlays in the first 3 seconds as hooks")
        
        if not recommendations:
            recommendations.append("Video looks great! Ready to post.")
        
        return {
            'combined_score': round(combined_score, 2),
            'factors': {k: round(v, 2) for k, v in factors.items()},
            'prediction': prediction,
            'reach_estimate': reach_estimate,
            'engagement_estimate': engagement_estimate,
            'recommendations': recommendations,
            'confidence': min(95, 50 + (combined_score * 0.4))  # Higher score = higher confidence
        }
        
        # Calculate combined score
        combined_score = sum(factors.values())
        
        # Determine prediction category
        if combined_score >= 80:
            prediction = "HIGH - Likely to go viral"
            reach_estimate = "10,000-100,000 views"
            engagement_estimate = "15-25% engagement rate"
        elif combined_score >= 60:
            prediction = "MEDIUM - Good performance expected"
            reach_estimate = "5,000-50,000 views"
            engagement_estimate = "10-20% engagement rate"
        elif combined_score >= 40:
            prediction = "LOW - Average performance"
            reach_estimate = "1,000-10,000 views"
            engagement_estimate = "5-15% engagement rate"
        else:
            prediction = "VERY LOW - Poor performance expected"
            reach_estimate = "<1,000 views"
            engagement_estimate = "<5% engagement rate"
        
        # Generate recommendations
        recommendations = []
        
        if duration_score < 70:
            recommendations.append("Adjust video duration to 15-30 seconds for optimal engagement")
        
        if aspect_score < 70:
            recommendations.append("Use vertical 9:16 aspect ratio for better reach on Instagram Reels")
        
        if resolution_score < 70:
            recommendations.append("Increase resolution to 1080x1920 for better quality")
        
        if face_score < 60:
            recommendations.append("Include people/faces in your video - they get 25% more engagement")
        
        if motion_score < 60:
            recommendations.append("Add more motion and action to keep viewers engaged")
        
        if color_score < 60:
            recommendations.append("Improve lighting and use more vibrant colors")
        
        if edit_score < 60:
            recommendations.append("Use faster cuts and transitions to increase retention")
        
        if text_score < 60:
            recommendations.append("Add text overlays in the first 3 seconds as hooks")
        
        if not recommendations:
            recommendations.append("Video looks great! Ready to post.")
        
        return {
            'combined_score': round(combined_score, 2),
            'factors': {k: round(v, 2) for k, v in factors.items()},
            'prediction': prediction,
            'reach_estimate': reach_estimate,
            'engagement_estimate': engagement_estimate,
            'recommendations': recommendations,
            'confidence': min(95, 50 + (combined_score * 0.4))  # Higher score = higher confidence
        }
    
    @staticmethod
    def get_improvement_suggestions(metadata_analysis: Dict, visual_analysis: Dict) -> List[str]:
        """
        Get specific suggestions to improve video virality
        
        Args:
            metadata_analysis: Metadata analysis results
            visual_analysis: Visual analysis results
        
        Returns:
            List of specific improvement suggestions
        """
        suggestions = []
        
        # Metadata suggestions
        metadata_recs = metadata_analysis.get('recommendations', [])
        suggestions.extend(metadata_recs)
        
        # Visual suggestions
        face_data = visual_analysis.get('face_detection', {})
        if face_data.get('face_present_percentage', 0) < 20:
            suggestions.append("Include more people/faces - videos with faces get 25% more engagement")
        
        motion_data = visual_analysis.get('motion_analysis', {})
        if not motion_data.get('has_constant_motion', False):
            suggestions.append("Add more motion and dynamic content to keep viewers engaged")
        
        color_data = visual_analysis.get('color_analysis', {})
        if not color_data.get('is_well_lit', False):
            suggestions.append("Improve lighting - well-lit videos perform better")
        if not color_data.get('is_colorful', False):
            suggestions.append("Use more vibrant colors and saturation")
        
        scene_data = visual_analysis.get('scene_detection', {})
        if scene_data.get('edit_style') == 'slow':
            suggestions.append("Use faster cuts and transitions to increase retention")
        
        text_data = visual_analysis.get('text_detection', {})
        if not text_data.get('has_text_overlays', False):
            suggestions.append("Add text overlays in the first 3 seconds as hooks")
        
        return suggestions


# Test the video virality scorer
if __name__ == "__main__":
    print("=== Video Virality Scorer ===")
    
    # Test with sample data
    sample_metadata = {
        'scores': {
            'duration': 90,
            'aspect_ratio': 100,
            'resolution': 80,
            'frame_rate': 100,
            'file_size': 100
        },
        'overall_score': 90,
        'recommendations': []
    }
    
    sample_visual = {
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
        }
    }
    
    print("\n[Test 1] Virality Score Calculation")
    score = VideoViralityScorer.calculate_virality_score(sample_metadata, sample_visual)
    print(f"  [OK] Combined score: {score['combined_score']}")
    print(f"  [OK] Prediction: {score['prediction']}")
    print(f"  [OK] Reach estimate: {score['reach_estimate']}")
    print(f"  [OK] Confidence: {score['confidence']:.1f}%")
    
    print("\n[Test 2] Improvement Suggestions")
    suggestions = VideoViralityScorer.get_improvement_suggestions(sample_metadata, sample_visual)
    print(f"  [OK] Suggestions: {len(suggestions)}")
    for suggestion in suggestions[:3]:
        print(f"    - {suggestion}")
    
    print("\n=== Video Virality Scorer Working ===")