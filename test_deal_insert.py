import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")

print("=" * 80)
print("TEST: Direct insert into brand_deals table (service role)")
print("=" * 80)

sb = create_client(url, key)

# Test data matching what create_creator_deal sends
deal_data = {
    "creator_id": "test@example.com",
    "brand_name": "Test Brand",
    "deliverables": "1x Instagram Reel",
    "rate_amount": 50000,
    "currency": "INR",
    "usage_rights": "3 Months on Creator Socials",
    "exclusivity_clause": "30 Days after post",
    "timeline_start": "2026-08-13T00:00:00Z",
    "timeline_end": "2026-09-13T00:00:00Z",
    "cover_note_type": "english",
    "status": "active"
}

try:
    res = sb.table("brand_deals").insert(deal_data).execute()
    print("✓ INSERT SUCCESSFUL with service role")
    print(f"Inserted deal ID: {res.data[0]['id']}")
    
    # Clean up
    sb.table("brand_deals").delete().eq("creator_id", "test@example.com").execute()
    print("✓ Cleaned up test data")
except Exception as e:
    print(f"❌ INSERT FAILED: {e}")
    print(f"Error type: {type(e).__name__}")

print("\n" + "=" * 80)
print("TEST: Check if fpdf is installed")
print("=" * 80)

try:
    from fpdf import FPDF
    print("✓ fpdf is installed")
except ImportError as e:
    print(f"❌ fpdf NOT installed: {e}")

print("\n" + "=" * 80)
print("TEST: Check if contract_generator can be imported")
print("=" * 80)

try:
    from contract_generator import generate_contract_pdf
    print("✓ contract_generator imported successfully")
    
    # Test basic PDF generation
    try:
        b64 = generate_contract_pdf(
            creator_email="test@example.com",
            brand_name="Test Brand",
            deliverables="1x Reel",
            rate_amount=50000,
            currency="INR"
        )
        print(f"✓ PDF generation successful (length: {len(b64)} chars)")
    except Exception as pdf_err:
        print(f"❌ PDF generation failed: {pdf_err}")
except ImportError as e:
    print(f"❌ contract_generator import failed: {e}")
except Exception as e:
    print(f"❌ contract_generator error: {e}")
