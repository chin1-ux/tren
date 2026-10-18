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
        logging.warning("Missing Supabase credentials; skipping finalize write cleanly.")
        return 0
        
    try:
        from supabase import create_client
        sb = create_client(url, key)
        
        existing = None
        if github_run_id:
            try:
                res = sb.table("cron_runs").select("id, status").eq("github_run_id", github_run_id).limit(1).execute()
                if res.data:
                    existing = res.data[0]
            except Exception as _e:
                logging.debug(f"Could not query by github_run_id (column may not exist yet): {_e}")
                
        now_iso = datetime.now(timezone.utc).isoformat()
        
        update_payload = {
            "status": "success" if run_conclusion == "success" else "failure",
            "conclusion": run_conclusion,
            "updated_at": now_iso
        }
        
        insert_payload = {
            "created_at": now_iso,
            "run_at": now_iso,
            "status": "success" if run_conclusion == "success" else "failure",
            "conclusion": run_conclusion,
            "github_run_id": int(github_run_id) if (github_run_id and str(github_run_id).isdigit()) else None,
            "cutoff_reason": f"Recorded by finalize_cron_run (job_status={job_status}, conclusion={run_conclusion})"
        }
        
        try:
            if existing:
                sb.table("cron_runs").update(update_payload, returning="minimal").eq("id", existing["id"]).execute()
                logging.info(f"Updated existing cron_runs row {existing['id']} with conclusion={run_conclusion}")
            else:
                sb.table("cron_runs").insert(insert_payload, returning="minimal").execute()
                logging.info(f"Inserted new cron_runs row for github_run_id={github_run_id}")
        except Exception as write_err:
            logging.warning(f"Initial finalize write failed (attempting safe fallback without newer schema columns): {write_err}")
            # Safe fallback: omit columns that might not exist in production yet
            safe_payload = {
                "created_at": now_iso,
                "run_at": now_iso,
                "status": "success" if run_conclusion == "success" else "failure",
                "cutoff_reason": f"finalize_cron_run (job_status={job_status}, conclusion={run_conclusion})"
            }
            try:
                sb.table("cron_runs").insert(safe_payload, returning="minimal").execute()
                logging.info("Successfully recorded fallback finalize row in cron_runs.")
            except Exception as safe_err:
                logging.warning(f"Safe fallback finalize insert failed non-fatally: {safe_err}")
                
        return 0
    except Exception as err:
        logging.warning(f"finalize_cron_run non-fatal outer error: {err}")
        return 0

if __name__ == "__main__":
    # Always exit 0 so finalize telemetry NEVER fails the GitHub Actions pipeline
    sys.exit(finalize_run())
