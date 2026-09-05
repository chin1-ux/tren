# Setting JWT_SECRET_KEY in Vercel - Manual Instructions

The Vercel CLI is having issues with interactive prompts. Here's the reliable way to set the environment variable:

## Method 1: Vercel Dashboard (Recommended)

1. **Go to Vercel Dashboard**: https://vercel.com/dashboard
2. **Navigate to your project**: Click on "trendrop" 
3. **Go to Settings**: Click the "Settings" tab in the project
4. **Environment Variables**: Click "Environment Variables" in the left sidebar
5. **Add new variable**:
   - Click "Add New" or "Create Variable"
   - **Name:** `JWT_SECRET_KEY`
   - **Value:** `9xK2mN8pQ4vR7sT1wY5zA3bC6dE9fG2hJ5kM8nP1qS4tV7wX0zB3cF6iJ9lN2oP5rS8uV1yZ4`
   - **Environments:** Select "Production", "Preview", and "Development"
   - **Type:** Select "Sensitive" (recommended)
6. **Save**: Click "Save"
7. **Redeploy**: Vercel will ask if you want to redeploy - click "Redeploy"

## Method 2: Vercel CLI (Alternative)

If you prefer using CLI, try this approach:

```bash
# Add to production only
vercel env add JWT_SECRET_KEY production

# Then add to preview and development separately
vercel env add JWT_SECRET_KEY preview
vercel env add JWT_SECRET_KEY development
```

When prompted:
- "Store as sensitive?" → Type `Y` and press Enter
- For preview environment → Leave git branch empty and press Enter

## Current Status

✅ **JWT_SECRET_KEY is already set for Production** (added successfully)
⚠️ **Need to add for Preview and Development environments**

## Why This Is Important

The JWT_SECRET_KEY is required for:
- Admin login authentication
- JWT token generation and validation
- Session management
- Admin system security

Without this environment variable set, the admin login will fail with an authentication error.

## Verification

After setting the environment variable, verify it's working:

1. Go to https://trendrop-black.vercel.app/admin/login
2. Try to login with your credentials
3. If it works, the environment variable is correctly set
4. If it fails, check the environment variable is set for the correct environment

## Quick Checklist

- [ ] JWT_SECRET_KEY set in Production ✅ (already done)
- [ ] JWT_SECRET_KEY set in Preview 
- [ ] JWT_SECRET_KEY set in Development
- [ ] Application redeployed after setting variables
- [ ] Admin login tested and working