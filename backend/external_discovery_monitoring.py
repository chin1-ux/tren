#!/usr/bin/env python3
"""
Monitoring dashboard for external trend discovery system
"""

import os
import sys
import io
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
print(f"Loading .env from: {env_path}")
print(f".env exists: {os.path.exists(env_path)}")
load_dotenv(env_path)

# Fallback: try loading from current directory if above fails
if not os.getenv('SUPABASE_URL'):
    print("Trying fallback .env loading...")
    load_dotenv()

def external_discovery_monitoring():
    """Generate monitoring report for external trend discovery"""
    
    print("=== EXTERNAL TREND DISCOVERY MONITORING DASHBOARD ===")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # 1. Pipeline Health
    print("📊 PIPELINE HEALTH")
    print("-" * 50)
    
    time_threshold_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_jobs = sb.table('jobs').select('*').eq('job_type', 'external_trend_discovery').gte('created_at', time_threshold_24h).order('created_at', desc=True).limit(1).execute()
    
    if recent_jobs.data:
        latest_job = recent_jobs.data[0]
        status = latest_job.get('status', 'unknown')
        created_at = latest_job.get('created_at', 'unknown')
        
        if status == 'completed':
            print(f"✅ Status: HEALTHY")
        elif status == 'no_candidates':
            print(f"✅ Status: HEALTHY (no candidates found)")
        else:
            print(f"⚠️  Status: {status.upper()}")
        
        print(f"📅 Last run: {created_at}")
        
        if latest_job.get('error_message'):
            print(f"❌ Error: {latest_job.get('error_message')}")
    else:
        print("⚠️  Status: NO RECENT RUNS")
        print("📅 Last run: Never (or >24h ago)")
    
    # 2. Discovery Metrics
    print("\n📈 DISCOVERY METRICS")
    print("-" * 50)
    
    # Total external discovery trends
    all_external = sb.table('trends').select('*', count='exact').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').execute()
    total_external = all_external.count if hasattr(all_external, 'count') else len(all_external.data)
    print(f"🎵 Total external discoveries: {total_external}")
    
    # Recent discoveries (7 days)
    time_threshold_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_external = sb.table('trends').select('*', count='exact').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').gte('first_detected_at', time_threshold_7d).execute()
    recent_count = recent_external.count if hasattr(recent_external, 'count') else len(recent_external.data)
    print(f"🆕 Discoveries (7 days): {recent_count}")
    
    # Discovery by status
    emerging_external = sb.table('trends').select('*', count='exact').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').eq('status', 'emerging').execute()
    emerging_count = emerging_external.count if hasattr(emerging_external, 'count') else len(emerging_external.data)
    
    rising_external = sb.table('trends').select('*', count='exact').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').eq('status', 'rising').execute()
    rising_count = rising_external.count if hasattr(rising_external, 'count') else len(rising_external.data)
    
    print(f"📊 Status breakdown:")
    print(f"   - Emerging: {emerging_count}")
    print(f"   - Rising: {rising_count}")
    
    # 3. Source Distribution
    print("\n🌍 SOURCE DISTRIBUTION")
    print("-" * 50)
    
    all_trends = sb.table('trends').select('discovery_source', count='exact').execute()
    total_trends = all_trends.count if hasattr(all_trends, 'count') else len(all_trends.data)
    
    external_percentage = (total_external / total_trends * 100) if total_trends > 0 else 0
    print(f"📊 Total trends: {total_trends}")
    print(f"🎯 External discovery: {total_external} ({external_percentage:.1f}%)")
    print(f"🏷️  Hashtag discovery: {total_trends - total_external} ({100 - external_percentage:.1f}%)")
    
    # 4. Recent Discoveries
    print("\n🔍 RECENT DISCOVERIES")
    print("-" * 50)
    
    if recent_external.data:
        for trend in recent_external.data[:5]:  # Show last 5
            title = trend.get('audio_title', 'Unknown')
            artist = trend.get('audio_artist', 'Unknown')
            status = trend.get('status', 'unknown')
            detected = trend.get('first_detected_at', 'unknown')
            
            print(f"🎵 {title} by {artist}")
            print(f"   Status: {status} | Detected: {detected}")
            
            # Show external metadata if available
            raw_response = trend.get('raw_llm_response', {})
            if isinstance(raw_response, dict) and 'external_discovery' in raw_response:
                ext_data = raw_response['external_discovery']
                platform = ext_data.get('platform', 'unknown')
                region = ext_data.get('chart_region', 'unknown')
                print(f"   Source: {platform} {region}")
    else:
        print("No recent discoveries to display")
    
    # 5. System Configuration
    print("\n⚙️  SYSTEM CONFIGURATION")
    print("-" * 50)
    
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
    
    print(f"🔑 YouTube API Key: {'✅ Configured' if youtube_key else '❌ Missing'}")
    print(f"🔑 Spotify Client ID: {'✅ Configured' if spotify_client_id else '❌ Missing'}")
    print(f"🔑 Spotify Client Secret: {'✅ Configured' if os.getenv('SPOTIFY_CLIENT_SECRET') else '❌ Missing'}")
    
    # 6. Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 50)
    
    if not youtube_key:
        print("⚠️  Add YOUTUBE_API_KEY to environment variables")
    
    if not spotify_client_id:
        print("⚠️  Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to environment variables")
    
    if not recent_jobs.data:
        print("⚠️  Check if GitHub Actions workflow is properly scheduled")
    
    if total_external == 0:
        print("ℹ️  No external discoveries yet - system may need time to find crossover candidates")
    
    if recent_count == 0 and total_external > 0:
        print("ℹ️  No recent discoveries - this is normal if no global songs showed Indian signals")
    
    print("\n" + "=" * 50)
    print("Monitoring dashboard complete")
    
    return True

if __name__ == '__main__':
    success = external_discovery_monitoring()
    sys.exit(0 if success else 1)
