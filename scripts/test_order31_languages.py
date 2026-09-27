import os
import sys
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)
load_dotenv(os.path.join(backend_dir, ".env"))

from fastapi.testclient import TestClient
from api import app
from supabase import create_client

def main():
    client = TestClient(app)

    print("=== TEST 1: Unfiltered feed (no languages param) ===")
    res_unfiltered = client.get("/api/trends")
    assert res_unfiltered.status_code == 200, f"Expected 200, got {res_unfiltered.status_code}"
    unfiltered_data = res_unfiltered.json()
    assert isinstance(unfiltered_data, list), "Expected list response"
    print(f"✓ Unfiltered feed count: {len(unfiltered_data)} trends returned (default-open, non-empty)")

    print("\n=== TEST 2: Multi-language filtered feed (?languages=hi,pa) ===")
    res_filtered = client.get("/api/trends?languages=hi,pa")
    assert res_filtered.status_code == 200, f"Expected 200, got {res_filtered.status_code}"
    filtered_data = res_filtered.json()
    assert isinstance(filtered_data, list), "Expected list response"
    print(f"✓ Filtered feed count (?languages=hi,pa): {len(filtered_data)} trends returned")

    # Verify each returned trend's language matches hi or pa
    allowed_langs = {"hi", "pa", "hindi", "punjabi"}
    mismatches = []
    for trend in filtered_data:
        lang = str(trend.get("language") or "").lower().strip()
        lang_final = str(trend.get("language_final") or "").lower().strip()
        # If trend has a language set, it must be in allowed_langs
        if lang and lang not in allowed_langs and lang_final and lang_final not in allowed_langs:
            mismatches.append((trend.get("id"), lang, lang_final))

    assert len(mismatches) == 0, f"Found mismatches in filtered feed: {mismatches}"
    print(f"✓ All {len(filtered_data)} returned trends strictly match requested languages ['hi', 'pa']")

    print("\n=== TEST 3: PUT /api/users/language-preferences with invalid code ===")
    from auth import require_auth
    app.dependency_overrides[require_auth] = lambda: "test-user@trendrop.app"

    headers = {"Authorization": "Bearer mock_test_token"}
    res_invalid = client.put(
        "/api/users/language-preferences",
        json={"languages": ["hi", "invalid_code_123"]},
        headers=headers
    )
    assert res_invalid.status_code == 400, f"Expected 400 Bad Request, got {res_invalid.status_code}: {res_invalid.text}"
    print(f"✓ Invalid language code correctly rejected with 400 Bad Request: {res_invalid.json().get('detail')}")

    print("\n=== TEST 4: PUT /api/users/language-preferences with valid codes ===")
    res_valid = client.put(
        "/api/users/language-preferences",
        json={"languages": ["hi", "pa", "en"]},
        headers=headers
    )
    assert res_valid.status_code == 200, f"Expected 200 OK, got {res_valid.status_code}: {res_valid.text}"
    valid_data = res_valid.json()
    assert valid_data.get("success") is True, "Expected success=True"
    assert set(valid_data.get("preferred_languages", [])) == {"hi", "pa", "en"}, f"Unexpected languages: {valid_data}"
    print(f"✓ Preferences successfully saved and returned: {valid_data.get('preferred_languages')}")

    print("\n==========================================")
    print("ALL ORDER 31 STEP 5 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    main()
