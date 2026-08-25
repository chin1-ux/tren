import os
import sys
import logging
import threading
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import unittest
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_alerts_pipeline")

load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error("Supabase credentials missing.")
    sys.exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

class TestAlertsPipeline(unittest.TestCase):
    def setUp(self):
        # Create a unique test user
        self.email = f"test_alert_user_{int(time.time())}@example.com"
        self.phone = f"+1555{int(time.time()) % 1000000:06d}"
        
        # We need a trend ID. Find an existing one or create a dummy.
        trend_res = supabase.table('trends').select('id').limit(1).execute()
        if trend_res.data:
            self.trend_id = trend_res.data[0]['id']
        else:
            dummy_trend = supabase.table('trends').insert({
                'audio_title': 'Test Audio Title',
                'audio_artist': 'Test Audio Artist',
                'platform': 'instagram',
                'trend_type': 'test_dance',
                'content_type': 'dance',
                'language': 'English'
            }).execute()
            self.trend_id = dummy_trend.data[0]['id']
            self.created_trend = True
            logger.info(f"Created dummy trend: {self.trend_id}")

        # Insert user
        user_res = supabase.table('users').insert({
            'email': self.email,
            'phone_number': self.phone,
            'niche': 'all',
            'plan': 'pro'
        }).execute()
        self.user_id = user_res.data[0]['id']
        logger.info(f"Created test user: {self.user_id} with email: {self.email}")

        # Set initial credit balance to 1
        supabase.table('credit_balances').upsert({
            'user_id': self.user_id,
            'balance': 1
        }).execute()
        logger.info(f"Set credit balance of user {self.user_id} to 1")

    def tearDown(self):
        # Clean up
        logger.info("Cleaning up test user data...")
        try:
            supabase.table('credit_transactions').delete().eq('user_id', self.user_id).execute()
            supabase.table('credit_balances').delete().eq('user_id', self.user_id).execute()
            supabase.table('alert_queue').delete().eq('user_id', self.user_id).execute()
            supabase.table('users').delete().eq('id', self.user_id).execute()
            if hasattr(self, 'created_trend'):
                supabase.table('trends').delete().eq('id', self.trend_id).execute()
            logger.info("Cleanup completed.")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def test_concurrent_credit_deduction(self):
        """
        Genuinely concurrent test: spawns two threads executing deduct_credit_atomic
        at the same time. One must succeed and return true; one must fail and return false.
        """
        logger.info("=== Starting Concurrent Race Condition Test ===")
        results = []
        threads = []

        def call_rpc():
            # Separate client per thread for separate session/connection
            thread_supabase = create_client(supabase_url, supabase_key)
            try:
                res = thread_supabase.rpc('deduct_credit_atomic', {
                    'p_user_id': self.user_id,
                    'p_amount': 1,
                    'p_reason': 'test_concurrent'
                }).execute()
                
                data = res.data
                if isinstance(data, list) and len(data) > 0:
                    data = data[0]
                results.append(data)
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        # Start 2 threads concurrently
        t1 = threading.Thread(target=call_rpc)
        t2 = threading.Thread(target=call_rpc)
        
        threads.append(t1)
        threads.append(t2)

        # Trigger concurrently
        t1.start()
        t2.start()

        for t in threads:
            t.join()

        logger.info(f"Concurrent thread results: {results}")

        # Assert exactly one succeeded and one failed
        successes = [r for r in results if isinstance(r, dict) and r.get('success') is True]
        failures = [r for r in results if isinstance(r, dict) and r.get('success') is False]

        print("\n--- CONCURRENT RUN DETAIL ---")
        for i, res in enumerate(results):
            print(f"Thread {i+1} response: {res}")
        print("-----------------------------\n")

        self.assertEqual(len(successes), 1, "Exactly one thread should successfully deduct credit")
        self.assertEqual(len(failures), 1, "Exactly one thread should fail to deduct credit")

        # Verify balance in database is now 0
        bal_res = supabase.table('credit_balances').select('balance').eq('user_id', self.user_id).single().execute()
        self.assertEqual(bal_res.data['balance'], 0)

        # Verify transaction ledger has exactly one row
        tx_res = supabase.table('credit_transactions').select('*').eq('user_id', self.user_id).execute()
        self.assertEqual(len(tx_res.data), 1)
        self.assertEqual(tx_res.data[0]['amount'], -1)

    @patch('resend.Emails.send')
    def test_alert_system_email_and_queue(self, mock_resend_send):
        """
        Verify that send_trend_alerts in alert_system.py still triggers the email send
        (mocked to verify it's called) AND enqueues into alert_queue.
        """
        logger.info("=== Starting Alert System Email and Queue Test ===")
        mock_resend_send.return_value = {"id": "mock-email-id"}

        from alert_system import AlertSystem
        alert_system = AlertSystem()
        
        # Overwrite user list returned by AlertSystem to contain our test user only
        # properties matched in AlertSystem: niche = 'dance' or 'all', language_preference = 'English'
        # content_type = 'dance'
        original_send = alert_system.send_trend_alerts
        
        # Trigger alerts for our trend ID
        alert_system.send_trend_alerts([self.trend_id])

        # Verify email send was called
        self.assertGreaterEqual(mock_resend_send.call_count, 1)
        logger.info("Verified: Email send function was called successfully (mocked).")

        # Verify the alert was written to the alert_queue
        queue_res = supabase.table('alert_queue').select('*').eq('user_id', self.user_id).eq('trend_id', self.trend_id).execute()
        self.assertEqual(len(queue_res.data), 1)
        self.assertEqual(queue_res.data[0]['status'], 'pending')
        logger.info("Verified: Alert queue entry was written successfully.")

    def test_alert_worker_flow(self):
        """
        Verify that alert_worker.py processes pending queue entries,
        deducts credits, mock sends WhatsApp message, and updates status.
        """
        logger.info("=== Starting Alert Worker Flow Test ===")
        
        # Enqueue a pending alert for our test user
        supabase.table('alert_queue').insert({
            'user_id': self.user_id,
            'trend_id': self.trend_id,
            'niche_name': 'dance',
            'status': 'pending'
        }).execute()

        # Run worker processing logic
        from alert_worker import process_alert_queue
        
        # Ensure we are in mock mode for test stability
        with patch.dict(os.environ, {"WHATSAPP_MOCK_MODE": "true"}):
            process_alert_queue()

        # Confirm queue status updated to 'sent'
        queue_res = supabase.table('alert_queue').select('*').eq('user_id', self.user_id).eq('trend_id', self.trend_id).execute()
        self.assertEqual(queue_res.data[0]['status'], 'sent')
        
        # Confirm credit balance decremented to 0
        bal_res = supabase.table('credit_balances').select('balance').eq('user_id', self.user_id).single().execute()
        self.assertEqual(bal_res.data['balance'], 0)
        logger.info("Verified: Worker successfully processed, deducted credit, and updated status to sent.")

    @patch('alert_worker.send_whatsapp_alert')
    def test_alert_worker_refund_flow(self, mock_send_alert):
        """
        Verify that alert_worker.py refunds the credit if WhatsApp send fails.
        """
        logger.info("=== Starting Alert Worker Refund Flow Test ===")
        mock_send_alert.return_value = False # Force WhatsApp send failure

        # Set user balance to 1
        supabase.table('credit_balances').upsert({
            'user_id': self.user_id,
            'balance': 1
        }).execute()

        # Enqueue a pending alert for our test user
        supabase.table('alert_queue').insert({
            'user_id': self.user_id,
            'trend_id': self.trend_id,
            'niche_name': 'dance',
            'status': 'pending'
        }).execute()

        from alert_worker import process_alert_queue
        process_alert_queue()

        # Confirm queue status updated to 'failed'
        queue_res = supabase.table('alert_queue').select('*').eq('user_id', self.user_id).eq('trend_id', self.trend_id).execute()
        self.assertEqual(queue_res.data[0]['status'], 'failed')

        # Confirm credit balance is still 1 (refunded)
        bal_res = supabase.table('credit_balances').select('balance').eq('user_id', self.user_id).single().execute()
        self.assertEqual(bal_res.data['balance'], 1)

        # Confirm refund transaction is recorded in the ledger
        tx_res = supabase.table('credit_transactions').select('*').eq('user_id', self.user_id).eq('reason', 'alert_refund_failed_send').execute()
        self.assertEqual(len(tx_res.data), 1)
        self.assertEqual(tx_res.data[0]['amount'], 1) # positive amount for refund
        logger.info("Verified: Worker successfully refunded credit and logged to ledger upon message send failure.")


if __name__ == '__main__':
    unittest.main()
