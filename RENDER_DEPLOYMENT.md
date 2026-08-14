# Backend Deployment on Render

This guide explains how to deploy the Trendrop backend to Render (free tier: 750 hours/month) while keeping the frontend on Vercel.

## Why Render?

- **Free tier**: 750 hours/month of web service
- **Native Python support**: Works perfectly with FastAPI
- **Automatic SSL**: HTTPS by default
- **Easy deployment**: Direct from GitHub
- **No function invocation issues**: Unlike Vercel Python functions

## Deployment Steps

### 1. Create Render Account

1. Go to https://render.com
2. Sign up (GitHub integration recommended)
3. Verify your email

### 2. Deploy Backend

1. Go to Render Dashboard → "New +"
2. Select "Web Service"
3. Connect your GitHub repository (ch1n-may/trendrop)
4. Configure:
   - **Name**: trendrop-backend
   - **Region**: Oregon (or closest to you)
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.api:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

5. Add Environment Variables (copy from Vercel):
   - SUPABASE_URL
   - SUPABASE_KEY
   - SUPABASE_SERVICE_ROLE_KEY
   - JWT_SECRET_KEY
   - ADMIN_SECRET_KEY
   - GROQ_API_KEY
   - GEMINI_API_KEY
   - REDIS_URL
   - YOUTUBE_API_KEY
   - INSTAGRAM_USERNAME
   - INSTAGRAM_PASSWORD
   - INSTAGRAM_APP_ID
   - INSTAGRAM_REDIRECT_URI
   - APIFY_API_TOKEN
   - RESEND_API_KEY
   - RESEND_FROM_EMAIL
   - RAZORPAY_KEY_ID
   - RAZORPAY_KEY_SECRET
   - VITE_ADMIN_KEY

6. Click "Create Web Service"
7. Wait for deployment (2-3 minutes)

### 3. Update Frontend API URL

Once the backend is deployed, you'll get a URL like:
`https://trendrop-backend.onrender.com`

Update the frontend to use this backend URL:

1. In `frontend/src/lib/api.ts`, update the base URL
2. In Vercel project settings, add environment variable:
   - Key: `VITE_API_BASE_URL`
   - Value: `https://trendrop-backend.onrender.com`

### 4. Test Admin Login

1. Go to your frontend: https://trendrop-black.vercel.app
2. Navigate to admin login
3. Enter admin credentials
4. Should work correctly now!

## Architecture

```
Frontend (Vercel) → Backend (Render) → Supabase Database
     ↓                  ↓                  ↓
  React/TSX        FastAPI/Python     PostgreSQL
```

## Benefits

- ✅ Frontend stays on Vercel (working perfectly)
- ✅ Backend on Render with proper Python support
- ✅ Both use same Supabase database
- ✅ Free hosting (within limits)
- ✅ Automatic SSL and HTTPS
- ✅ Easy to scale if needed

## Troubleshooting

### Backend fails to start
- Check Render logs for errors
- Verify all environment variables are set
- Ensure requirements.txt has all dependencies

### Frontend can't connect to backend
- Verify VITE_API_BASE_URL is set correctly
- Check CORS settings in backend/api.py
- Ensure backend URL is accessible

### Admin login still fails
- Check Render logs for authentication errors
- Verify Supabase connection
- Check admin user exists in database

## Cost

- **Render Free Tier**: 750 hours/month (~1 full month of uptime)
- **Vercel Free Tier**: 100GB bandwidth/month (frontend only)
- **Total**: $0/month for development

## Scaling

If you need more resources:
- Render: Upgrade to Starter ($7/month) for more hours
- Vercel: Upgrade to Pro ($20/month) for more bandwidth
