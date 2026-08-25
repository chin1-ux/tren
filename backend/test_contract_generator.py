import sys
sys.path.insert(0, '.')

print("=" * 80)
print("TEST: contract_generator import from backend directory")
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
        import traceback
        traceback.print_exc()
except ImportError as e:
    print(f"❌ contract_generator import failed: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ contract_generator error: {e}")
    import traceback
    traceback.print_exc()
