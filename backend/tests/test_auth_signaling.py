import os
import sys
import unittest
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env.vercel"))

from fastapi.testclient import TestClient
from api import app
from supabase import create_client

class TestAuthSignaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        cls.supabase = create_client(supabase_url, supabase_key)

    def test_guest_request_no_header(self):
        resp = self.client.get("/api/trends")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.headers.get("X-Token-Status"))
        self.assertTrue(len(resp.json()) > 0)

    def test_expired_token_request_signaling(self):
        resp = self.client.get("/api/trends", headers={"Authorization": "Bearer sample_expired_jwt_token_123"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Token-Status"), "expired")
        self.assertTrue(len(resp.json()) > 0)

    def test_valid_pro_token_request(self):
        try:
            auth_res = self.supabase.auth.sign_in_with_password({"email": "test-agency@trendrop.internal", "password": "TestAgency2026!"})
            valid_token = auth_res.session.access_token if (auth_res and auth_res.session) else None
        except Exception:
            valid_token = None

        if valid_token:
            resp = self.client.get("/api/trends", headers={"Authorization": f"Bearer {valid_token}"})
            self.assertEqual(resp.status_code, 200)
            self.assertIsNone(resp.headers.get("X-Token-Status"))
            self.assertTrue(len(resp.json()) > 0)

if __name__ == "__main__":
    unittest.main()
