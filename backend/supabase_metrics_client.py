"""
backend/supabase_metrics_client.py
-----------------------------------
Transparent metrics and caching proxy wrapper for Supabase client.
1. Intercepts queries to track requests count and estimated bytes per table.
2. Persists per-run telemetry into egress_log and cron_runs.
"""

import time
import json
import logging
from typing import Any, Dict, Optional, Set
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("supabase_metrics")

class MetricsRequestWrapper:
    def __init__(self, table_name: str, builder: Any, tracker: 'SupabaseMetricsTracker'):
        self.table_name = table_name
        self.builder = builder
        self.tracker = tracker
        self._is_audio_official_lookup = False
        self._target_audio_id = None

    def eq(self, column: str, value: Any):
        if self.table_name == "audio_official_counts" and column == "audio_id":
            self._is_audio_official_lookup = True
            self._target_audio_id = str(value)
        self.builder = self.builder.eq(column, value)
        return self

    def select(self, *args, **kwargs):
        self.builder = self.builder.select(*args, **kwargs)
        return self

    def in_(self, column: str, values: list):
        self.builder = self.builder.in_(column, values)
        return self

    def order(self, *args, **kwargs):
        self.builder = self.builder.order(*args, **kwargs)
        return self

    def limit(self, *args, **kwargs):
        self.builder = self.builder.limit(*args, **kwargs)
        return self

    def range(self, *args, **kwargs):
        self.builder = self.builder.range(*args, **kwargs)
        return self

    def gte(self, *args, **kwargs):
        self.builder = self.builder.gte(*args, **kwargs)
        return self

    def lt(self, *args, **kwargs):
        self.builder = self.builder.lt(*args, **kwargs)
        return self

    def lte(self, *args, **kwargs):
        self.builder = self.builder.lte(*args, **kwargs)
        return self

    def insert(self, *args, **kwargs):
        self.builder = self.builder.insert(*args, **kwargs)
        return self

    def update(self, *args, **kwargs):
        self.builder = self.builder.update(*args, **kwargs)
        return self

    def upsert(self, *args, **kwargs):
        self.builder = self.builder.upsert(*args, **kwargs)
        return self

    def delete(self, *args, **kwargs):
        self.builder = self.builder.delete(*args, **kwargs)
        return self

    def execute(self):
        # 1. Check in-memory cache for audio_official_counts
        if self._is_audio_official_lookup and self._target_audio_id:
            cached_val = self.tracker.get_cached_audio_official(self._target_audio_id)
            if cached_val is not None:
                self.tracker.record_cache_hit(self.table_name)
                class CachedResponse:
                    def __init__(self, data):
                        self.data = data
                        self.count = len(data) if isinstance(data, list) else 1
                return CachedResponse(cached_val)

        # 2. Execute real request
        t0 = time.monotonic()
        res = self.builder.execute()
        duration_ms = (time.monotonic() - t0) * 1000

        # Estimate bytes transferred
        data = getattr(res, "data", None) or []
        try:
            byte_count = len(json.dumps(data))
        except Exception:
            byte_count = len(data) * 200

        self.tracker.record_request(self.table_name, byte_count, duration_ms)

        # Populate cache if audio_official_counts
        if self._is_audio_official_lookup and self._target_audio_id:
            self.tracker.cache_audio_official(self._target_audio_id, data)

        return res

    def __getattr__(self, name):
        attr = getattr(self.builder, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                res = attr(*args, **kwargs)
                self.builder = res
                return self
            return wrapper
        return attr


class SupabaseMetricsTracker:
    def __init__(self):
        self.requests_by_table = defaultdict(int)
        self.bytes_by_table = defaultdict(int)
        self.cache_hits_by_table = defaultdict(int)
        self.total_requests = 0
        self.total_bytes = 0
        self.audio_official_cache = {}

    def record_request(self, table: str, bytes_count: int, duration_ms: float):
        self.requests_by_table[table] += 1
        self.bytes_by_table[table] += bytes_count
        self.total_requests += 1
        self.total_bytes += bytes_count

    def record_cache_hit(self, table: str):
        self.cache_hits_by_table[table] += 1

    def get_cached_audio_official(self, audio_id: str):
        return self.audio_official_cache.get(audio_id)

    def cache_audio_official(self, audio_id: str, data: list):
        self.audio_official_cache[audio_id] = data

    def preload_audio_official_counts(self, sb_client, audio_ids: list):
        """Preload in chunks of 200 to eliminate N+1 queries"""
        if not audio_ids:
            return
        unique_ids = list(set(audio_ids))
        for i in range(0, len(unique_ids), 200):
            chunk = unique_ids[i:i+200]
            try:
                res = sb_client.table("audio_official_counts") \
                    .select("audio_id, official_count_velocity, checked_at") \
                    .in_("audio_id", chunk) \
                    .order("checked_at", desc=True) \
                    .execute()
                for row in (res.data or []):
                    aid = str(row.get("audio_id"))
                    if aid not in self.audio_official_cache:
                        self.audio_official_cache[aid] = [row]
            except Exception as e:
                logger.warning(f"Error preloading audio_official_counts chunk: {e}")

    def get_summary(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_estimated_bytes": self.total_bytes,
            "total_mb": round(self.total_bytes / (1024 * 1024), 3),
            "requests_by_table": dict(self.requests_by_table),
            "bytes_by_table": dict(self.bytes_by_table),
            "cache_hits_by_table": dict(self.cache_hits_by_table)
        }

    def persist(self, workflow: str = "scraper", github_run_id: Optional[Any] = None, sb_client: Optional[Any] = None):
        """
        Persists per-table accounting to egress_log and aggregates to cron_runs.
        Safe, non-fatal, logs errors cleanly.
        """
        if not sb_client:
            logger.debug("No sb_client provided; skipping persist.")
            return

        run_id_int = int(github_run_id) if (github_run_id and str(github_run_id).isdigit()) else None

        # 1. Insert per-table rows into egress_log
        now_iso = datetime.now(timezone.utc).isoformat()
        log_rows = []
        for table, reqs in self.requests_by_table.items():
            b = self.bytes_by_table.get(table, 0)
            log_rows.append({
                "created_at": now_iso,
                "workflow": workflow,
                "github_run_id": run_id_int,
                "table_name": table,
                "requests_count": reqs,
                "estimated_bytes": b
            })

        if log_rows:
            try:
                sb_client.table("egress_log").insert(log_rows, returning="minimal").execute()
                logger.info(f"Persisted {len(log_rows)} rows to egress_log (total_bytes={self.total_bytes}, requests={self.total_requests})")
            except Exception as e:
                logger.warning(f"Could not persist to egress_log: {e}")

        # 2. Update cron_runs row if github_run_id is known
        if run_id_int:
            try:
                sb_client.table("cron_runs").update({
                    "egress_requests": self.total_requests,
                    "egress_bytes": self.total_bytes
                }, returning="minimal").eq("github_run_id", run_id_int).execute()
                logger.info(f"Updated cron_runs for github_run_id={run_id_int} with egress={self.total_bytes}b")
            except Exception as e:
                logger.warning(f"Could not update cron_runs telemetry: {e}")


class MonitoredSupabaseClient:
    def __init__(self, raw_client: Any, tracker: Optional[SupabaseMetricsTracker] = None):
        self.raw_client = raw_client
        self.tracker = tracker or SupabaseMetricsTracker()

    def table(self, table_name: str):
        raw_builder = self.raw_client.table(table_name)
        return MetricsRequestWrapper(table_name, raw_builder, self.tracker)

    def from_(self, table_name: str):
        return self.table(table_name)

    def rpc(self, *args, **kwargs):
        self.tracker.record_request("rpc", 100, 10.0)
        return self.raw_client.rpc(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.raw_client, name)
