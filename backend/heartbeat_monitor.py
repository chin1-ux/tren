import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client


def _load_env() -> None:
    load_dotenv()
    if not os.getenv("SUPABASE_URL"):
        backend_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(backend_env):
            load_dotenv(backend_env)


def _get_supabase():
    _load_env()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are not set")
    return create_client(url, key)


def _send_webhook(message: str) -> None:
    """
    Send the same alert to a direct webhook channel such as Slack or Discord.
    Supports standard incoming webhooks without adding a new dependency.
    """
    webhook_url = os.getenv("CRON_HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("CRON_HEARTBEAT_WEBHOOK_URL is not set")

    if "discord.com/api/webhooks" in webhook_url:
        payload = {"content": message}
    else:
        payload = {"text": message}

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8", errors="replace").strip()
        print(f"webhook_status={resp.status}")
        if body:
            print(f"webhook_body={body}")
        if resp.status not in (200, 204):
            raise RuntimeError(f"Webhook delivery failed with status {resp.status}")


def check_cron_heartbeat(max_age_hours: int = 8, dry_run: bool = False) -> dict:
    """
    Look for the most recent successful cron run and email a human if the
    pipeline has gone stale longer than the allowed threshold.
    """
    force_stale_test = os.getenv("FORCE_STALE_TEST", "").strip().lower() in {"1", "true", "yes", "on"}
    sb = _get_supabase()
    if force_stale_test:
        now = datetime.now(timezone.utc)
        completed_dt = now - timedelta(hours=max_age_hours + 1)
        latest = {
            "run_at": completed_dt.isoformat(),
            "completed_at": completed_dt.isoformat(),
            "status": "success",
            "stage": "forced_test",
            "cutoff_reason": "forced stale test override",
        }
    else:
        res = (
            sb.table("cron_runs")
            .select("run_at, completed_at, status, stage, cutoff_reason")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
        latest = (res.data or [None])[0]
    now = datetime.now(timezone.utc)

    if not latest:
        payload = {
            "status": "stale",
            "reason": "no cron_runs rows found",
            "alert_sent": False,
        }
        if not dry_run:
            _send_webhook("Trendrop cron heartbeat missed. No rows exist in cron_runs.")
            payload["alert_sent"] = True
        return payload

    completed_at = latest.get("completed_at") or latest.get("run_at")
    if not completed_at:
        raise RuntimeError("Latest cron run is missing completed_at and run_at")

    completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    age_hours = (now - completed_dt).total_seconds() / 3600.0
    stale = age_hours > max_age_hours

    if stale and not dry_run:
        message = (
            f"Trendrop cron heartbeat missed. "
            f"Latest run: {completed_dt.isoformat()} | "
            f"Age: {age_hours:.1f}h | "
            f"Status: {latest.get('status')} | "
            f"Stage: {latest.get('stage')} | "
            f"Cutoff: {latest.get('cutoff_reason') or 'none'}"
        )
        _send_webhook(message)

    return {
        "status": "stale" if stale else "fresh",
        "age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
        "latest_completed_at": completed_dt.isoformat(),
        "alert_sent": bool(stale and not dry_run),
    }


if __name__ == "__main__":
    print(f"FORCE_STALE_TEST={os.getenv('FORCE_STALE_TEST', '')}")
    result = check_cron_heartbeat()
    print(result)
