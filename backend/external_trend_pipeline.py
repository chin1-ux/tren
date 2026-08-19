#!/usr/bin/env python3
"""
External Trend Pipeline - Daily validation job for global-to-India crossover detection

This script runs daily (separate from the 8h hashtag cycle) to:
1. Fetch trending songs from Spotify/YouTube
2. Validate them for Indian creator crossover potential
3. Feed validated candidates into the existing trend_engine
4. Track discovery source as "GLOBAL_TO_INDIA_CROSSOVER"
"""

import os
import sys
import logging
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from external_trend_discovery import ExternalTrendDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_supabase():
    """Initialize Supabase client with connection timeout handling"""
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise RuntimeError('Supabase credentials not set')
    
    # Create client with timeout settings
    try:
        client = create_client(url, key)
        # Test connection with timeout
        client.table('reels').select('id', count='exact').limit(1).execute()
        return client
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        raise


def create_candidate_trend_record(candidate: dict, supabase) -> bool:
    """
    Create a trend record for a validated external candidate.
    
    Args:
        candidate: Validated candidate from external discovery
        supabase: Supabase client
    
    Returns:
        True if successful, False otherwise
    """
    try:
        song = candidate['song']
        indian_signals = candidate.get('indian_signals', {})
        
        # Dedup guard: check if this trend already exists by title+artist.
        # Same never-downgrade logic as trend_engine.py Change A.
        # Status priority: rising(3) > emerging(2) > peaked(1) > expired(0).
        # Only status is updated — velocity/metrics owned by trend_refresher.py.
        STATUS_PRIORITY = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}
        existing = supabase.table("trends") \
            .select("id, status") \
            .eq("audio_title", song.title) \
            .eq("audio_artist", song.artist) \
            .execute()
        if existing.data:
            old_status = existing.data[0].get("status", "emerging")
            new_detected_status = "emerging"
            old_priority = STATUS_PRIORITY.get(old_status, 0)
            new_priority = STATUS_PRIORITY.get(new_detected_status, 0)
            final_status = old_status if old_priority >= new_priority else new_detected_status
            if final_status != old_status:
                supabase.table("trends") \
                    .update({"status": final_status}) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
                logger.info(
                    f"Updated existing trend '{song.title}' (id={existing.data[0]['id']}): "
                    f"status {old_status} -> {final_status}"
                )
            else:
                logger.info(f"Trend '{song.title}' by {song.artist} already exists (status={old_status}), skipping")
            return False
        
        # Create trend record with discovery source tracking
        trend_data = {
            'audio_title': song.title,
            'audio_artist': song.artist,
            'platform': 'instagram',  # Even though discovered externally, platform is Instagram
            'trend_type': 'music',
            'velocity_avg': 0.0,  # Will be calculated by trend_engine
            'reel_count': 0,  # Will be populated by trend_engine
            'status': 'emerging',  # Start as emerging since it's newly discovered
            'discovery_source': 'GLOBAL_TO_INDIA_CROSSOVER',
            'confidence': 0.7,  # Moderate confidence for external discovery
            'first_detected_at': datetime.now(timezone.utc).isoformat(),
            # Metadata for tracking
            'raw_llm_response': {
                'external_discovery': {
                    'platform': song.platform,
                    'chart_position': song.chart_position,
                    'chart_region': song.chart_region,
                    'chart_url': song.chart_url,
                    'discovered_at': song.discovered_at.isoformat(),
                    'indian_signals': indian_signals
                }
            }
        }
        
        result = supabase.table('trends').insert(trend_data).execute()
        
        if result.data:
            logger.info(f"Created trend record for {song.title} by {song.artist}")
            return True
        else:
            logger.error(f"Failed to create trend record for {song.title}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating trend record: {e}")
        return False


def trigger_trend_engine_for_candidates(candidates: list, supabase):
    """
    Trigger trend_engine to process the new external candidates.
    
    This ensures the newly added trends get proper velocity calculation,
    reel counting, and classification from the existing trend_engine logic.
    
    Args:
        candidates: List of validated candidates
        supabase: Supabase client
    """
    try:
        # Import trend_engine
        from trend_engine import TrendEngine
        
        logger.info("Triggering trend_engine for external candidates...")
        
        # Initialize trend engine
        engine = TrendEngine(supabase)
        
        # Run trend detection - this will pick up the newly added trends
        # and calculate proper metrics
        new_trend_ids = engine.detect_trends()
        
        logger.info(f"Trend engine processed {len(new_trend_ids)} trends")
        
        return new_trend_ids
        
    except ImportError:
        logger.warning("Trend engine not available, skipping processing")
        return []
    except Exception as e:
        logger.error(f"Error triggering trend engine: {e}")
        return []


def log_pipeline_results(results: dict, supabase):
    """
    Log pipeline results to database for tracking.
    
    Args:
        results: Pipeline execution results
        supabase: Supabase client
    """
    try:
        log_data = {
            'job_type': 'external_trend_discovery',
            'status': 'completed' if results.get('validated_candidates') else 'no_candidates',
            'input_data': f"Spotify: {len(results.get('spotify_songs', []))}, YouTube: {len(results.get('youtube_songs', []))}",
            'output_url': f"Validated: {len(results.get('validated_candidates', []))}, Skipped: {len(results.get('skipped', []))}",
            'error_message': results.get('error', ''),
            'progress': 100,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table('jobs').insert(log_data).execute()
        logger.info("Pipeline results logged to database")
        
    except Exception as e:
        logger.error(f"Error logging pipeline results: {e}")


def run_external_trend_pipeline():
    """
    Main pipeline execution function.
    
    Returns:
        dict with pipeline execution results
    """
    logger.info("=== Starting External Trend Discovery Pipeline ===")
    start_time = datetime.now(timezone.utc)
    
    results = {
        'start_time': start_time.isoformat(),
        'validated_candidates': [],
        'created_trends': [],
        'errors': []
    }
    
    try:
        # Initialize components with retry logic
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                supabase = get_supabase()
                discovery = ExternalTrendDiscovery()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Supabase connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise e
        
        # Run discovery cycle
        logger.info("Running external trend discovery cycle...")
        discovery_results = discovery.run_discovery_cycle()
        
        results.update(discovery_results)
        
        # Process validated candidates
        validated_candidates = discovery_results.get('validated_candidates', [])
        logger.info(f"Processing {len(validated_candidates)} validated candidates...")
        
        for candidate in validated_candidates:
            try:
                # Create trend record
                success = create_candidate_trend_record(candidate, supabase)
                if success:
                    results['created_trends'].append(candidate['song'].title)
                    
            except Exception as e:
                logger.error(f"Error processing candidate {candidate['song'].title}: {e}")
                results['errors'].append({
                    'candidate': candidate['song'].title,
                    'error': str(e)
                })
        
        # Trigger trend engine for proper processing
        if results['created_trends']:
            logger.info("Triggering trend engine for new trends...")
            trend_engine_results = trigger_trend_engine_for_candidates(validated_candidates, supabase)
            results['trend_engine_results'] = trend_engine_results
        
        # Log results
        log_pipeline_results(results, supabase)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration
        results['status'] = 'completed'
        
        logger.info(f"=== Pipeline completed in {duration:.2f} seconds ===")
        logger.info(f"Validated candidates: {len(results['validated_candidates'])}")
        logger.info(f"Created trends: {len(results['created_trends'])}")
        logger.info(f"Errors: {len(results['errors'])}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
        results['end_time'] = datetime.now(timezone.utc).isoformat()
    
    return results


def main():
    """Main entry point"""
    results = run_external_trend_pipeline()
    
    # Print summary
    print("\n=== EXTERNAL TREND DISCOVERY PIPELINE SUMMARY ===")
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
    print(f"Spotify songs fetched: {len(results.get('spotify_songs', []))}")
    print(f"YouTube songs fetched: {len(results.get('youtube_songs', []))}")
    print(f"Validated candidates: {len(results.get('validated_candidates', []))}")
    print(f"Created trends: {len(results.get('created_trends', []))}")
    print(f"Errors: {len(results.get('errors', []))}")
    
    if results.get('created_trends'):
        print("\n=== CREATED TRENDS ===")
        for title in results['created_trends']:
            print(f"- {title}")
    
    if results.get('errors'):
        print("\n=== ERRORS ===")
        for error in results['errors']:
            print(f"- {error}")
    
    # Exit with error code if pipeline failed
    if results.get('status') == 'failed':
        sys.exit(1)


if __name__ == '__main__':
    main()
