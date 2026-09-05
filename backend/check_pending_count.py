"""
Check pending trends count and determine if emergency classification is needed.
Outputs GitHub Actions compatible format for conditional execution.
"""

import os
import sys
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from datetime import datetime, timedelta
import httpx

# Configuration
PENDING_THRESHOLD = 20  # Trigger emergency classification if pending > 20
EMERGING_PENDING_THRESHOLD = 3  # Additional trigger for Emerging pending (lowered from 5)
HIGH_PENDING_THRESHOLD = 25  # Warning threshold (lowered from 50)

def get_pending_count():
    """Get current pending trends count."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Get total pending count
    response = httpx.get(
        f"{supabase_url}/rest/v1/trends?llm_classification_status=eq.pending&select=id",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Error fetching pending count: {response.status_code}")
        sys.exit(1)
    
    total_pending = len(response.json())
    
    # Get Emerging pending count
    response = httpx.get(
        f"{supabase_url}/rest/v1/trends?llm_classification_status=eq.pending&status=eq.emerging&select=id",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Error fetching Emerging pending count: {response.status_code}")
        sys.exit(1)
    
    emerging_pending = len(response.json())
    
    return total_pending, emerging_pending

def main():
    print("Checking pending trends count...")
    
    total_pending, emerging_pending = get_pending_count()
    
    print(f"Total pending: {total_pending}")
    print(f"Emerging pending: {emerging_pending}")
    
    # Determine if emergency classification is needed
    needs_classification = (
        total_pending >= PENDING_THRESHOLD or 
        emerging_pending >= EMERGING_PENDING_THRESHOLD
    )
    
    high_pending = total_pending >= HIGH_PENDING_THRESHOLD
    
    # Output for GitHub Actions
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as fh:
            if needs_classification:
                fh.write(f"needs_classification=true\n")
                fh.write(f"high_pending={str(high_pending).lower()}\n")
            else:
                fh.write(f"needs_classification=false\n")
                fh.write(f"high_pending={str(high_pending).lower()}\n")
    
    if needs_classification:
        print(f"EMERGENCY CLASSIFICATION TRIGGERED: {total_pending} pending, {emerging_pending} Emerging pending")
    else:
        print(f"No emergency classification needed: {total_pending} pending, {emerging_pending} Emerging pending")
    
    if high_pending:
        print(f"::warning::High pending count: {total_pending}")

if __name__ == "__main__":
    main()