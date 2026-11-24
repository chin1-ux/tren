"""
Circuit Breaker & Health State Manager for Sources
Tracks consecutive failures per source and persists state to source_health table.
- 3 consecutive failures: status = 'degraded'
- 6 consecutive failures: status = 'blocked'
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("circuit_breaker")

class SourceCircuitBreaker:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        if not self.supabase:
            try:
                from utils.db import get_supabase_client
                self.supabase = get_supabase_client()
            except Exception:
                pass

    def get_source_health(self, source_name: str) -> dict[str, Any]:
        """Reads health status from Supabase or returns default OK if table/row missing."""
        if not self.supabase:
            return {"status": "ok", "fail_count": 0, "reason": "db_unavailable"}
        try:
            res = self.supabase.table("source_health").select("*").eq("source_name", source_name).limit(1).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                return {
                    "status": row.get("status", "ok"),
                    "fail_count": row.get("fail_count", 0),
                    "reason": row.get("last_failure_reason", "")
                }
        except Exception as e:
            logger.debug(f"[CIRCUIT_BREAKER] source_health query failed (table may not exist yet): {e}")
        return {"status": "ok", "fail_count": 0, "reason": "untracked"}

    def record_run(self, source_name: str, success: bool, reason: str = "") -> dict[str, Any]:
        """Updates consecutive failure/success count and transitions status."""
        current = self.get_source_health(source_name)
        fail_count = current.get("fail_count", 0)
        now_iso = datetime.now(timezone.utc).isoformat()

        if success:
            fail_count = 0
            new_status = "ok"
            update_data = {
                "source_name": source_name,
                "status": new_status,
                "fail_count": 0,
                "consecutive_success_count": 1,
                "last_success_at": now_iso,
                "updated_at": now_iso
            }
        else:
            fail_count += 1
            if fail_count >= 6:
                new_status = "blocked"
            elif fail_count >= 3:
                new_status = "degraded"
            else:
                new_status = "ok"

            update_data = {
                "source_name": source_name,
                "status": new_status,
                "fail_count": fail_count,
                "last_failure_at": now_iso,
                "last_failure_reason": reason[:255] if reason else "scrape_failed",
                "updated_at": now_iso
            }

        logger.info(f"[CIRCUIT_BREAKER] Source '{source_name}': status={new_status}, fail_count={fail_count}")

        if self.supabase:
            try:
                self.supabase.table("source_health").upsert(update_data).execute()
            except Exception as e:
                logger.debug(f"[CIRCUIT_BREAKER] Failed to upsert source_health: {e}")

        return {"status": new_status, "fail_count": fail_count, "reason": reason}
