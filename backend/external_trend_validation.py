from __future__ import annotations

# Disabled on 2026-08-01 because the Google Trends probe was rate-limited and is a weak fit for Reels-specific trend validation.
import json
import os
import random
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client


def _public_google_trends_probe(query: str) -> dict:
    """
    Lightweight external signal check.

    This is intentionally non-blocking and meant for a daily sanity job, not a gate.
    It uses a public trends endpoint as a coarse outside-world signal.
    """
    if not query.strip():
        return {"signal": False, "reason": "empty_query"}
    params = {
        "hl": "en-US",
        "tz": "330",
        "req": json.dumps({
            "comparisonItem": [{"keyword": query, "geo": "IN", "time": "now 7-d"}],
            "category": 0,
            "property": "",
        }),
    }
    resp = requests.get("https://trends.google.com/trends/api/explore", params=params, timeout=15)
    return {"signal": bool(resp.ok), "status_code": resp.status_code}


def run_external_trend_validation(sample_size: int = 5) -> dict:
    """
    Sample currently displayed trends and compare them to an external sanity signal.
    """
    load_dotenv("backend/.env")
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    now = datetime.now(timezone.utc).isoformat()
    rows = sb.table("trends").select("id,audio_title,audio_artist,status,velocity_avg,opportunity_score,trend_origin,is_cross_cultural").in_("status", ["emerging", "rising"]).execute().data or []
    sample = random.sample(rows, k=min(sample_size, len(rows)))
    results = []
    for row in sample:
        query = " ".join([row.get("audio_title") or "", row.get("audio_artist") or ""]).strip()
        external = _public_google_trends_probe(query)
        results.append({
            "trend_id": row["id"],
            "audio_title": row.get("audio_title"),
            "internal_velocity_avg": row.get("velocity_avg"),
            "internal_opportunity_score": row.get("opportunity_score"),
            "external_signal": external,
        })
    return {"ts": now, "sample_size": len(sample), "results": results}
