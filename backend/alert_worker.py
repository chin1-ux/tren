import os
import sys
import logging
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("alert_worker")

# Load environment variables
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error("Supabase credentials missing from environment.")
    sys.exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

def deduct_credit(user_id: int, amount: int, reason: str) -> bool:
    """
    Atomically deducts credits via RPC function deduct_credit_atomic.
    Returns True if deduction succeeds, False otherwise.
    """
    try:
        result = supabase.rpc('deduct_credit_atomic', {
            'p_user_id': user_id,
            'p_amount': amount,
            'p_reason': reason
        }).execute()
        
        data = result.data
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
            
        if isinstance(data, dict):
            return data.get('success', False)
        elif isinstance(data, bool):
            return data
            
        logger.warning(f"Unexpected RPC return format: {data}")
        return False
    except Exception as e:
        logger.error(f"Error calling deduct_credit_atomic for user {user_id}: {e}", exc_info=True)
        return False

def send_whatsapp_alert(phone: str, niche: str, trend_id: int) -> bool:
    """
    Sends an alert via WhatsApp (Meta Cloud API) or email fallback.
    Currently defaults to mock mode; requires WhatsApp credentials for real delivery.
    TODO: Configure WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN for real WhatsApp delivery.
    """
    mock_mode = os.getenv('WHATSAPP_MOCK_MODE', 'true').lower() == 'true'
    if mock_mode:
        logger.info(f"[MOCK] Would send alert to {phone} for niche '{niche}', trend {trend_id}")
        return True

    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    token = os.getenv('WHATSAPP_ACCESS_TOKEN')

    if not phone_id or not token:
        logger.error("WhatsApp credentials (WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_ACCESS_TOKEN) missing in non-mock mode.")
        logger.info("Falling back to email delivery for alert")
        # TODO: Implement email fallback here using Resend
        return False

    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "trend_alert",  # must be pre-approved in Meta Business Manager
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": niche}]
            }]
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.info(f"WhatsApp Meta API response: {resp.status_code} - {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Error calling Meta WhatsApp Cloud API: {e}", exc_info=True)
        return False

def process_alert_queue():
    logger.info("Processing pending alert queue...")
    try:
        pending = supabase.table('alert_queue').select('*').eq('status', 'pending').limit(50).execute()
    except Exception as e:
        logger.error(f"Failed to fetch pending alerts: {e}", exc_info=True)
        return

    logger.info(f"Found {len(pending.data or [])} pending alerts.")

    for alert in (pending.data or []):
        alert_id = alert['id']
        user_id = alert['user_id']
        trend_id = alert['trend_id']
        niche = alert['niche_name'] or 'general'

        # Check + deduct credit atomically
        success = deduct_credit(user_id, amount=1, reason='alert_sent')

        if not success:
            logger.info(f"Skipping alert {alert_id} for user {user_id} due to insufficient credits.")
            try:
                supabase.table('alert_queue').update({
                    'status': 'skipped_no_credits',
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', alert_id).execute()
            except Exception as e:
                logger.error(f"Failed to update skipped_no_credits status for alert {alert_id}: {e}")
            continue

        # Fetch user phone
        try:
            user_res = supabase.table('users').select('phone_number').eq('id', user_id).single().execute()
            phone = user_res.data.get('phone_number') if user_res.data else None
        except Exception as e:
            logger.error(f"Failed to fetch phone number for user {user_id}: {e}")
            phone = None

        if not phone:
            logger.warning(f"No phone number found for user {user_id}. Marking alert {alert_id} as failed.")
            # Refund the credit since we didn't attempt sending due to missing phone
            deduct_credit(user_id, amount=-1, reason='alert_refund_no_phone')
            try:
                supabase.table('alert_queue').update({
                    'status': 'failed',
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', alert_id).execute()
            except Exception as e:
                logger.error(f"Failed to update failed status for alert {alert_id}: {e}")
            continue

        # Send alert
        sent = send_whatsapp_alert(phone=phone, niche=niche, trend_id=trend_id)

        # Update alert status
        status = 'sent' if sent else 'failed'
        if not sent:
            # Refund the credit since sending failed
            logger.warning(f"WhatsApp sending failed. Refunding credit to user {user_id}.")
            deduct_credit(user_id, amount=-1, reason='alert_refund_failed_send')

        try:
            supabase.table('alert_queue').update({
                'status': status,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', alert_id).execute()
            logger.info(f"Alert {alert_id} status updated to {status}.")
        except Exception as e:
            logger.error(f"Failed to update status {status} for alert {alert_id}: {e}")

if __name__ == "__main__":
    process_alert_queue()
