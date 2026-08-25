# Simulated Endpoints Checklist

This document tracks backend endpoints that return simulated/fallback data and need real implementation or removal.

## HIGH PRIORITY (User-Facing)

### `/api/video/predict-virality`
- **Status**: USER-FACING (called from VideoAnalysisPanel on dashboard)
- **Current Behavior**: Returns simulated virality scores when ViralityScorer not configured
- **Frontend Handling**: Shows amber warning banner when `is_simulated: true` ✅
- **Trust Issue**: Paying customers may see fake virality scores
- **Action Required**: 
  - Option 1: Wire real ViralityScorer (FFmpeg + OpenCV + ML model)
  - Option 2: Hide feature behind "Coming Soon" until real implementation
  - Option 3: Remove simulated fallback, return 503 with clear message
- **Deadline**: Before next paid customer acquisition

## BACKLOG (Not User-Facing)

### `/api/video/analyze-metadata`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated video metadata when FFmpeg not configured
- **Action Required**: Install FFmpeg on server or remove endpoint

### `/api/video/analyze-visual`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated visual analysis when OpenCV not configured
- **Action Required**: Install OpenCV/pytesseract on server or remove endpoint

### `/api/video/improvements`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated improvement suggestions when ViralityScorer not configured
- **Action Required**: Install ViralityScorer dependencies or remove endpoint

### `/api/instagram/user-profile`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated Instagram profile data when InstagramDataFetcher not configured
- **Action Required**: Configure INSTAGRAM_APP_ID/INSTAGRAM_APP_SECRET or remove endpoint

### `/api/instagram/user-insights`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated Instagram insights when InstagramDataFetcher not configured
- **Action Required**: Configure Instagram Graph API credentials or remove endpoint

### `/api/instagram/user-media`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated Instagram media data when InstagramDataFetcher not configured
- **Action Required**: Configure Instagram Graph API credentials or remove endpoint

### `/api/youtube/trending`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated YouTube trending data when YOUTUBE_API_KEY not configured
- **Action Required**: Configure YOUTUBE_API_KEY or remove endpoint

### `/api/youtube/trending-music`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated YouTube trending music when YOUTUBE_API_KEY not configured
- **Action Required**: Configure YOUTUBE_API_KEY or remove endpoint

### `/api/realtime/trends`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated real-time trends when RealTimeTrendDetector not configured
- **Action Required**: Configure YOUTUBE_API_KEY and RealTimeTrendDetector or remove endpoint

### `/api/realtime/cross-platform`
- **Status**: NOT USER-FACING (not called from frontend)
- **Current Behavior**: Returns simulated cross-platform trends when RealTimeTrendDetector not configured
- **Action Required**: Configure YOUTUBE_API_KEY and RealTimeTrendDetector or remove endpoint

## Verification

Last verified: 2026-08-14
Method: Grepped frontend source code for API calls to each endpoint
Result: Only `/api/video/predict-virality` is actually called from frontend (VideoAnalysisPanel)

## Prevention

To prevent accidental exposure of simulated endpoints:
1. All simulated endpoints now have TODO comments with explicit warnings
2. Frontend check performed before adding new simulated endpoints
3. Any new user-facing feature must have real implementation or clear "Coming Soon" labeling