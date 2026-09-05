# API Keys Setup Guide

## Spotify API Keys (Required for External Discovery)

### Where to Get Spotify API Keys

1. **Go to Spotify Developer Dashboard**
   - Visit: https://developer.spotify.com/dashboard
   - Log in with your Spotify account

2. **Create a New App**
   - Click "Create App" or "Create App"
   - Fill in the required information:
     - **App name**: "Trendrop External Discovery" (or your preferred name)
     - **App description**: "Global trend discovery for Indian creator crossover detection"
     - **Redirect URI**: `http://localhost:8888/callback` (for OAuth if needed)
     - **Website**: Your project URL (optional)

3. **Get Your Credentials**
   - After creating the app, you'll see:
     - **Client ID**: A long alphanumeric string
     - **Client Secret**: A long alphanumeric string (click "Show" to reveal)

4. **Add to Environment Variables**
   Add these to your `.env` file:
   ```
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```

5. **Add to GitHub Secrets**
   For GitHub Actions deployment:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add:
     - `SPOTIFY_CLIENT_ID`: Your Spotify Client ID
     - `SPOTIFY_CLIENT_SECRET`: Your Spotify Client Secret

### Spotify API Limits
- **Free Tier**: 
  - 10,000 requests/hour for commercial apps
  - Sufficient for daily discovery cycle
- **No credit card required** for development tier

### Spotify API Endpoints Used
- `GET /charts/{region}/viral/weekly` - Viral 50 charts
- Authentication: OAuth 2.0 (Client Credentials Flow)

---

## YouTube API Key (Already Present)

### YouTube API Key Status
✅ **Already configured** in your project (used in `scraper.yml` and other backend files)

### Verify YouTube API Key
Check if it's working:
```bash
cd backend
python -c "from youtube_data_fetcher import YouTubeDataFetcher; print('YouTube API configured' if os.getenv('YOUTUBE_API_KEY') else 'Not configured')"
```

### YouTube API Limits
- **Free Tier**: 10,000 units/day (default quota)
- Each API call uses ~1-100 units depending on complexity
- Sufficient for daily discovery cycle

### YouTube API Endpoints Used
- `GET /youtube/v3/videos` - Trending videos
- Authentication: API Key (no OAuth required)

---

## Environment Variables Summary

### Required for External Discovery
```env
# Spotify API (NEW - need to add)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# YouTube API (ALREADY PRESENT)
YOUTUBE_API_KEY=your_existing_youtube_api_key
```

### Additional Required Variables (Already Present)
```env
# Supabase (already configured)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_DB_URL=your_database_url

# Other API keys (already configured)
GEMINI_API_KEY=your_gemini_key
GEMINI_API_KEY_2=your_gemini_key_2
```

---

## Testing API Keys

### Test Spotify API Key
```bash
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Spotify Client ID:', '✅' if os.getenv('SPOTIFY_CLIENT_ID') else '❌ Missing')
print('Spotify Client Secret:', '✅' if os.getenv('SPOTIFY_CLIENT_SECRET') else '❌ Missing')
"
```

### Test YouTube API Key
```bash
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('YouTube API Key:', '✅' if os.getenv('YOUTUBE_API_KEY') else '❌ Missing')
"
```

### Test Complete Setup
```bash
cd backend
python quick_verification.py
```

---

## Troubleshooting

### Spotify API Issues
- **Invalid Client ID/Secret**: Double-check you copied the correct values from Spotify Dashboard
- **Rate Limiting**: Free tier should be sufficient for daily use
- **401 Unauthorized**: Check that Client Secret is correct and not expired

### YouTube API Issues
- **Quota Exceeded**: Check usage in Google Cloud Console
- **API Key Disabled**: Re-enable in Google Cloud Console
- **403 Forbidden**: Check API key restrictions (should allow YouTube Data API v3)

### General Issues
- **Environment Variables Not Loading**: Ensure `.env` file is in the correct directory
- **GitHub Actions Not Working**: Check that secrets are properly configured in repository settings

---

## Security Notes

- **Never commit** `.env` file to version control
- **Never share** API keys publicly
- **Rotate keys** if they're accidentally exposed
- **Use different keys** for development and production environments
- **Monitor usage** in Spotify Dashboard and Google Cloud Console

---

## Next Steps After Setup

1. Add Spotify credentials to `.env` file
2. Add Spotify credentials to GitHub Secrets
3. Test the setup with `python quick_verification.py`
4. Run the monitoring dashboard: `python external_discovery_monitoring.py`
5. The GitHub Actions workflow will run automatically at 00:00 UTC daily
