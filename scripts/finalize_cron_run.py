import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv("backend/.env")
load_dotenv(".env")

def finalize_run():
    github_run_id = os.getenv("GITHUB_RUN_ID")
    job_status = os.getenv("JOB_STATUS", "unknown")
    run_conclusion = os.getenv("STEP_CONCLUSION") or job_status
    
    logging.info(f"Finalizing cron run: github_run_id={github_run_id}, status={job_status}, conclusion={run_conclusion}")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logging.warning("Missing Supabase credentials; cannot write finalize row.")
        return 0
        
    try:
        from supabase import create_client
        sb = create_client(url, key)
        
        # Check if row with github_run_id already exists in cron_runs
        existing = None
        if github_run_id:
            try:
                res = sb.table("cron_runs").select("id, status").eq("github_run_id", github_run_id).limit(1).execute()
                if res.data:
                    existing = res.data[0]
            except Exception as _e:
                logging.debug(f"Could not query by github_run_id: {_e}")
                
        now_iso = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update conclusion and updated_at
            sb.table("cron_runs").update({
                "status": "success" if run_conclusion == "success" else "failure",
                "conclusion": run_conclusion,
                "updated_at": now_iso
            }, returning="minimal").eq("id", existing["id"]).execute()
            logging.info(f"Updated existing cron_runs row {existing['id']} with conclusion={run_conclusion}")
        else:
            # Insert a finalize row so timeouts/cancellations are never lost
            insert_payload = {
                "created_at": now_iso,
                "run_at": now_iso,
                "status": "success" if run_conclusion == "success" else "failure",
                "conclusion": run_conclusion,
                "github_run_id": str(github_run_id) if github_run_id else None,
                "notes": f"Recorded by finalize_cron_run (job_status={job_status})"
            }
            sb.table("cron_runs").insert(insert_payload, returning="minimal").execute()
            logging.info(f"Inserted new cron_runs row for github_run_id={github_run_id} with status={job_status}")
            
        return 0
    except Exception as err:
        logging.error(f"Failed to finalize cron_runs: {err}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(finalize_run())
