import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False


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


def _send_webhook(message: str) -> bool:
    """
    Send the same alert to a direct webhook channel such as Slack or Discord.
    Supports standard incoming webhooks without adding a new dependency.
    
    Returns:
        True if webhook succeeded, False otherwise
    """
    webhook_url = os.getenv("CRON_HEARTBEAT_WEBHOOK_URL")
    if not webhook_url:
        print("CRON_HEARTBEAT_WEBHOOK_URL is not set, skipping webhook")
        return False

    is_discord = "discord.com/api/webhooks" in webhook_url or "discordapp.com/api/webhooks" in webhook_url
    if is_discord:
        payload = {"content": message}
    else:
        payload = {"text": message}

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    req.add_header("User-Agent", "TrendropHeartbeatBot/1.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            print(f"webhook_status={resp.status}")
            if body:
                print(f"webhook_body={body}")
            if resp.status not in (200, 204):
                print(f"Webhook delivery failed with status {resp.status}")
                return False
        return True
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace").strip()
        headers = dict(err.headers.items()) if err.headers else {}
        print(f"webhook_status={err.code}")
        print(f"webhook_headers={json.dumps(headers, sort_keys=True)}")
        if body:
            print(f"webhook_body={body}")
        print(f"Webhook delivery failed with status {err.code}")
        return False
    except Exception as e:
        print(f"Webhook delivery failed: {e}")
        return False


def _send_email(message: str) -> bool:
    """
    Send alert via email using Resend as fallback.
    
    Returns:
        True if email succeeded, False otherwise
    """
    if not RESEND_AVAILABLE:
        print("Resend not available, skipping email fallback")
        return False
    
    resend_key = os.getenv("RESEND_API_KEY")
    alert_email = os.getenv("CRON_HEARTBEAT_ALERT_EMAIL")
    from_email = os.getenv("RESEND_FROM_EMAIL", "alerts@trendrop.ai")
    
    if not resend_key or not alert_email:
        print("RESEND_API_KEY or CRON_HEARTBEAT_ALERT_EMAIL not set, skipping email fallback")
        return False
    
    try:
        resend.api_key = resend_key
        resend.Emails.send({
            "from": from_email,
            "to": alert_email,
            "subject": "Trendrop Heartbeat Alert",
            "html": f"<p>{message}</p>"
        })
        print(f"Email sent to {alert_email}")
        return True
    except Exception as e:
        print(f"Email delivery failed: {e}")
        return False


def check_cron_heartbeat(max_age_hours: int = 8, dry_run: bool = False) -> dict:
    """
    Look for the most recent successful cron run and email a human if the
    pipeline has gone stale longer than the allowed threshold.
    """
    sb = _get_supabase()
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
            webhook_success = _send_webhook("Trendrop cron heartbeat missed. No rows exist in cron_runs.")
            if not webhook_success:
                # Fallback to email if webhook fails
                email_success = _send_email("Trendrop cron heartbeat missed. No rows exist in cron_runs.")
                payload["alert_sent"] = email_success
            else:
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
        webhook_success = _send_webhook(message)
        if not webhook_success:
            # Fallback to email if webhook fails
            email_success = _send_email(message)
            alert_sent = email_success
        else:
            alert_sent = True
    else:
        alert_sent = False

    return {
        "status": "stale" if stale else "fresh",
        "age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
        "latest_completed_at": completed_dt.isoformat(),
        "alert_sent": alert_sent,
    }


if __name__ == "__main__":
    result = check_cron_heartbeat()
    print(result)
