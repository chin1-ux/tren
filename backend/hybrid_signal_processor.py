#!/usr/bin/env python3
"""
Hybrid Signal Processing Pipeline - Orchestrates early detection with hybrid processing
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client

# Import detection modules
from early_signal_detector import detector
from creator_baseline_tracker import baseline_tracker
from geographic_spread_analyzer import geo_analyzer
from dynamic_hashtag_discovery import hashtag_discovery
from tier_based_scraper import tier_scraper
from realtime_velocity_tracker import velocity_tracker

load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

logger = logging.getLogger(__name__)

# Processing schedules
HYBRID_PROCESSING_SCHEDULE = {
    "micro_pool": {
        "frequency_hours": 1,  # Hourly for micro pools
        "signal_threshold": 60,  # Lower threshold for early detection
        "confidence_min": 0.6
    },
    "main_pool": {
        "frequency_hours": 8,  # Every 8 hours for main pools
        "signal_threshold": 75,  # Higher threshold for validation
        "confidence_min": 0.75
    }
}

class HybridSignalProcessor:
    """
    Orchestrates early detection with hybrid processing approach
    """
    
    def __init__(self):
        self.supabase = sb
        self.last_processing_times = {}
        self.alert_queue = []
    
    def process_micro_pool_signals(self) -> Dict:
        """
        Process signals from micro-creator pools (hourly)
        """
        try:
            logger.info("Processing micro pool signals...")
            
            # Get reels from micro pools
            micro_pools = ["MICRO_DANCE", "MICRO_FOOD", "MICRO_FASHION", "MICRO_COMEDY"]
            all_reels = []
            
            for pool_name in micro_pools:
                pool_hashtags = hashtag_discovery.get_pool_hashtags(pool_name)
                for hashtag in pool_hashtags:
                    result = self.supabase.table('reels').select('*').contains('hashtags', [hashtag]).order('created_at', desc=True).limit(50).execute()
                    all_reels.extend(result.data)
            
            # Process each reel for early signals
            detected_signals = []
            
            for reel in all_reels:
                # Get creator baseline
                creator_baseline = baseline_tracker.get_creator_baseline(reel.get('owner_username'))
                if not creator_baseline:
                    # Create baseline if doesn't exist
                    baseline_tracker.update_creator_baseline(reel.get('owner_username'), reel)
                    creator_baseline = baseline_tracker.get_creator_baseline(reel.get('owner_username'))
                
                # Detect all signal types
                velocity_signal = detector.detect_velocity_spikes(reel, creator_baseline or {})
                audio_signal = detector.detect_audio_acceleration(reel.get('audio_id'))
                creator_signal = detector.detect_creator_cascade(reel.get('audio_id'))
                hashtag_signal = detector.detect_hashtag_virality(reel.get('hashtags', []))
                
                # Calculate composite score
                signals = [velocity_signal, audio_signal, creator_signal, hashtag_signal]
                signal_score = detector.calculate_early_signal_score(signals)
                
                # Check if meets threshold
                if signal_score >= HYBRID_PROCESSING_SCHEDULE["micro_pool"]["signal_threshold"]:
                    # Get geographic spread
                    geo_data = geo_analyzer.analyze_geographic_spread(reel.get('audio_id'))
                    
                    # Calculate detection tier
                    detection_tier = self._determine_detection_tier(signal_score, geo_data)
                    
                    # Store early signal
                    signal_data = {
                        "signal_type": "composite",
                        "reel_id": reel['id'],
                        "audio_id": reel.get('audio_id'),
                        "audio_title": reel.get('audio_title'),
                        "signal_strength": signal_score,
                        "detection_tier": detection_tier,
                        "creator_tier": creator_baseline.get('creator_tier') if creator_baseline else None,
                        "creator_baseline_data": creator_baseline,
                        "signal_data": {
                            "velocity": velocity_signal,
                            "audio": audio_signal,
                            "creator": creator_signal,
                            "hashtag": hashtag_signal
                        },
                        "geographic_spread": geo_data,
                        "predicted_viral_probability": detector.predict_viral_probability(signal_score, {}),
                        "confidence_score": signal_score / 100
                    }
                    
                    detector.store_early_signal(signal_data)
                    detected_signals.append(signal_data)
                    
                    # Queue alert if high confidence
                    if signal_score >= 80:
                        self.alert_queue.append({
                            "type": "early_detection",
                            "data": signal_data,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
            
            # Update processing time
            self.last_processing_times["micro_pool"] = datetime.now(timezone.utc)
            
            return {
                "success": True,
                "pool_type": "micro_pool",
                "reels_processed": len(all_reels),
                "signals_detected": len(detected_signals),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error processing micro pool signals: {e}")
            return {"success": False, "error": str(e)}
    
    def process_main_pool_signals(self) -> Dict:
        """
        Process signals from main pools (every 8 hours)
        """
        try:
            logger.info("Processing main pool signals...")
            
            # Get reels from main pools
            main_pools = ["INDIA_TRENDING", "INDIA_VERNACULAR", "GLOBAL_NICHES", "GLOBAL_DISCOVERY"]
            all_reels = []
            
            for pool_name in main_pools:
                pool_hashtags = hashtag_discovery.get_pool_hashtags(pool_name)
                for hashtag in pool_hashtags:
                    result = self.supabase.table('reels').select('*').contains('hashtags', [hashtag]).order('created_at', desc=True).limit(100).execute()
                    all_reels.extend(result.data)
            
            # Process reels (similar to micro pool but with higher threshold)
            detected_signals = []
            
            for reel in all_reels:
                creator_baseline = baseline_tracker.get_creator_baseline(reel.get('owner_username'))
                if not creator_baseline:
                    baseline_tracker.update_creator_baseline(reel.get('owner_username'), reel)
                    creator_baseline = baseline_tracker.get_creator_baseline(reel.get('owner_username'))
                
                velocity_signal = detector.detect_velocity_spikes(reel, creator_baseline or {})
                audio_signal = detector.detect_audio_acceleration(reel.get('audio_id'))
                creator_signal = detector.detect_creator_cascade(reel.get('audio_id'))
                hashtag_signal = detector.detect_hashtag_virality(reel.get('hashtags', []))
                
                signals = [velocity_signal, audio_signal, creator_signal, hashtag_signal]
                signal_score = detector.calculate_early_signal_score(signals)
                
                # Higher threshold for main pool
                if signal_score >= HYBRID_PROCESSING_SCHEDULE["main_pool"]["signal_threshold"]:
                    geo_data = geo_analyzer.analyze_geographic_spread(reel.get('audio_id'))
                    detection_tier = self._determine_detection_tier(signal_score, geo_data)
                    
                    signal_data = {
                        "signal_type": "composite",
                        "reel_id": reel['id'],
                        "audio_id": reel.get('audio_id'),
                        "audio_title": reel.get('audio_title'),
                        "signal_strength": signal_score,
                        "detection_tier": detection_tier,
                        "creator_tier": creator_baseline.get('creator_tier') if creator_baseline else None,
                        "creator_baseline_data": creator_baseline,
                        "signal_data": {
                            "velocity": velocity_signal,
                            "audio": audio_signal,
                            "creator": creator_signal,
                            "hashtag": hashtag_signal
                        },
                        "geographic_spread": geo_data,
                        "predicted_viral_probability": detector.predict_viral_probability(signal_score, {}),
                        "confidence_score": signal_score / 100
                    }
                    
                    detector.store_early_signal(signal_data)
                    detected_signals.append(signal_data)
            
            # Update processing time
            self.last_processing_times["main_pool"] = datetime.now(timezone.utc)
            
            return {
                "success": True,
                "pool_type": "main_pool",
                "reels_processed": len(all_reels),
                "signals_detected": len(detected_signals),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error processing main pool signals: {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_detection_tier(self, signal_score: float, geo_data: dict) -> str:
        """
        Determine detection tier based on signal score and geographic spread
        """
        if signal_score >= 85 and geo_data.get('diversity_score', 0) >= 70:
            return "crossover"
        elif signal_score >= 75 and geo_data.get('diversity_score', 0) >= 50:
            return "early_growth"
        elif signal_score >= 60:
            return "very_early"
        else:
            return "observation"
    
    def execute_hybrid_schedule(self) -> Dict:
        """
        Execute the hybrid processing schedule
        """
        now = datetime.now(timezone.utc)
        results = {
            "timestamp": now.isoformat(),
            "executed_tasks": [],
            "skipped_tasks": [],
            "alerts_generated": 0
        }
        
        # Check micro pool schedule
        last_micro = self.last_processing_times.get("micro_pool")
        if last_micro:
            hours_since = (now - last_micro).total_seconds() / 3600
            should_process = hours_since >= HYBRID_PROCESSING_SCHEDULE["micro_pool"]["frequency_hours"]
        else:
            should_process = True
        
        if should_process:
            micro_result = self.process_micro_pool_signals()
            results["executed_tasks"].append({
                "task": "micro_pool_processing",
                "result": micro_result
            })
        else:
            results["skipped_tasks"].append({
                "task": "micro_pool_processing",
                "reason": f"Last processed {hours_since:.1f} hours ago (frequency: {HYBRID_PROCESSING_SCHEDULE['micro_pool']['frequency_hours']}h)"
            })
        
        # Check main pool schedule
        last_main = self.last_processing_times.get("main_pool")
        if last_main:
            hours_since = (now - last_main).total_seconds() / 3600
            should_process = hours_since >= HYBRID_PROCESSING_SCHEDULE["main_pool"]["frequency_hours"]
        else:
            should_process = True
        
        if should_process:
            main_result = self.process_main_pool_signals()
            results["executed_tasks"].append({
                "task": "main_pool_processing",
                "result": main_result
            })
        else:
            results["skipped_tasks"].append({
                "task": "main_pool_processing",
                "reason": f"Last processed {hours_since:.1f} hours ago (frequency: {HYBRID_PROCESSING_SCHEDULE['main_pool']['frequency_hours']}h)"
            })
        
        # Process alerts
        results["alerts_generated"] = len(self.alert_queue)
        alerts = self.alert_queue.copy()
        self.alert_queue.clear()
        
        results["alerts"] = alerts
        
        return results
    
    def get_system_status(self) -> Dict:
        """
        Get current system status
        """
        now = datetime.now(timezone.utc)
        
        status = {
            "timestamp": now.isoformat(),
            "last_processing": {},
            "next_processing": {},
            "alert_queue_size": len(self.alert_queue),
            "pool_statistics": {}
        }
        
        # Last processing times
        for pool_type in ["micro_pool", "main_pool"]:
            last_time = self.last_processing_times.get(pool_type)
            if last_time:
                hours_since = (now - last_time).total_seconds() / 3600
                frequency = HYBRID_PROCESSING_SCHEDULE[pool_type]["frequency_hours"]
                hours_until = max(0, frequency - hours_since)
                
                status["last_processing"][pool_type] = last_time.isoformat()
                status["next_processing"][pool_type] = (now + timedelta(hours=hours_until)).isoformat()
            else:
                status["last_processing"][pool_type] = "Never"
                status["next_processing"][pool_type] = "Immediate"
        
        # Pool statistics
        pool_stats = hashtag_discovery.get_pool_performance_summary()
        if pool_stats.get('success'):
            status["pool_statistics"] = pool_stats['pool_summary']
        
        return status

# Global instance
hybrid_processor = HybridSignalProcessor()