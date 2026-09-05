# Instagram Cookie Setup Instructions

## Problem Solved

The scraper was failing because Instagram cookies were provided in TSV (tab-separated) format from a raw browser export, but the scraper expects JSON format. We've created a conversion system to handle this.

## What Was Done

1. **Created conversion scripts:**
   - `convert_cookies_tsv_to_json.py` - Converts TSV to JSON
   - `encode_cookies_to_base64.py` - Encodes JSON to base64
   - `validate_cookies_format.py` - Validates cookie format

2. **Updated GitHub Actions workflow:**
   - Added cookie validation step
   - Improved error handling

3. **Converted your cookies:**
   - Your TSV cookies have been converted to JSON
   - JSON has been encoded to base64
   - Validation passed successfully

## Next Steps

### Step 1: Get the Base64 String

The base64 string has been saved to: `backend/cookies_base64.txt`

**To view it:**
```bash
cd backend
cat cookies_base64.txt
```

**Or regenerate it:**
```bash
cd backend
python encode_cookies_to_base64.py
```

### Step 2: Add to GitHub Secrets

1. **Go to GitHub Secrets:**
   - Visit: https://github.com/ch1n-may/trendrop/settings/secrets/actions

2. **Click "New repository secret"**

3. **Enter secret details:**
   - **Name:** `INSTAGRAM_COOKIES_B64`
   - **Value:** Paste the base64 string from `cookies_base64.txt`

4. **Click "Add secret"**

### Step 3: Test GitHub Actions

1. **Go to GitHub Actions:**
   - Visit: https://github.com/ch1n-may/trendrop/actions

2. **Select "Run Scraper & Trend Pipeline" workflow**

3. **Click "Run workflow"** (top right)

4. **Select branch:** `main`

5. **Click "Run workflow"**

6. **Wait for completion** (15-30 minutes)

### Step 4: Monitor Results

**Expected logs:**
```
[OK] Cookies file created successfully
[OK] cookies.json exists
[OK] Valid JSON format
[OK] Found 12 cookies
[OK] All cookies have required fields
[OK] sessionid cookie is present
[SUCCESS] Cookies are valid and ready for use
```

**Then:**
```
Step 1/5: Instagram scraping complete. X new reels saved
```

**Where X should be > 0**

## Cookie Validation Results

Your converted cookies passed all validation checks:

✅ Valid JSON format
✅ 12 cookies present
✅ All required fields present
✅ sessionid cookie present (critical for authentication)
✅ csrftoken cookie present
✅ mid cookie present
✅ datr cookie present
✅ ig_did cookie present

## If GitHub Actions Still Fails

If the workflow still fails after adding the base64 cookies:

1. **Check the logs** for specific error messages
2. **Verify the secret** was set correctly (should be 2944 characters)
3. **Check cookie expiration** - your cookies may be expired
4. **Try fresh cookies** - export new cookies from your browser

## Local Testing

To test locally with the converted cookies:

```bash
cd backend
python validate_cookies_format.py
python test_scraper.py
```

**Note:** Local testing may still return 0 reels due to IP blocking, but GitHub Actions should work with the proper cookies.

## Future Cookie Updates

When you need to update Instagram cookies in the future:

1. Export new cookies from your browser
2. Save as TSV format (same format as before)
3. Run: `python convert_cookies_tsv_to_json.py`
4. Run: `python encode_cookies_to_base64.py`
5. Update the base64 string in GitHub Secrets

## Summary

- ✅ Cookie conversion system created
- ✅ Your cookies converted and validated
- ✅ Base64 string ready for GitHub Secrets
- ⏳ Waiting for you to add to GitHub Secrets
- ⏳ Waiting for GitHub Actions test

The main issue was the cookie format mismatch. With the proper JSON format and base64 encoding, the scraper should work correctly in GitHub Actions.