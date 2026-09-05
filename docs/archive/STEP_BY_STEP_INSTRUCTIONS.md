# Step-by-Step Instructions for Completing All Fixes

## 1. Getting Fresh Instagram Cookies for Scraper

### Why This Is Needed
The scraper needs valid Instagram cookies to authenticate and scrape trending reels. Old cookies may have expired, causing the scraper to return 0 reels.

### Step-by-Step Instructions

#### Option A: Using Browser Extension (Recommended)

1. **Install "EditThisCookie" Extension**
   - Open Chrome/Edge browser
   - Go to Chrome Web Store / Edge Add-ons
   - Search for "EditThisCookie"
   - Install the extension

2. **Login to Instagram**
   - Go to https://www.instagram.com
   - Login with your Instagram account (trendr0p0)
   - Complete any 2FA if required

3. **Export Cookies**
   - Click the EditThisCookie extension icon
   - Click "Export" → "Export as JSON"
   - Save the file as `instagram_cookies.json`

4. **Convert to Base64**
   - Open PowerShell in the directory where you saved the file
   - Run: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("instagram_cookies.json")) > cookies_base64.txt`
   - Open `cookies_base64.txt` and copy the base64 string

5. **Update GitHub Secrets**
   - Go to your GitHub repository: https://github.com/ch1n-may/trendrop
   - Click "Settings" → "Secrets and variables" → "Actions"
   - Click "New repository secret"
   - Name: `INSTAGRAM_COOKIES_B64`
   - Value: Paste the base64 string from step 4
   - Click "Add secret"

#### Option B: Using Developer Tools

1. **Login to Instagram**
   - Go to https://www.instagram.com
   - Login with your Instagram account

2. **Open Developer Tools**
   - Press F12 or right-click → "Inspect"
   - Go to "Application" tab

3. **Extract Cookies**
   - Expand "Cookies" → "https://www.instagram.com"
   - Click each cookie and copy the value
   - Format as JSON:
   ```json
   [
     {"name": "sessionid", "value": "...", "domain": ".instagram.com", "path": "/", "httpOnly": true, "secure": true},
     {"name": "csrftoken", "value": "...", "domain": ".instagram.com", "path": "/", "httpOnly": false, "secure": true}
   ]
   ```

4. **Convert to Base64 and Update GitHub Secrets**
   - Follow steps 4-5 from Option A

### Testing Instagram Cookies

After updating cookies, test the scraper:
```bash
cd backend
python test_scraper.py
```

Expected output: `[OK] Scraped X reels` (where X > 0)

---

## 2. Enabling GitHub Actions in Repository Settings

### Why This Is Needed
GitHub Actions may be disabled in repository settings, causing 404 errors when trying to access workflows.

### Step-by-Step Instructions

1. **Go to Repository Settings**
   - Go to https://github.com/ch1n-may/trendrop
   - Click "Settings" tab

2. **Check Actions Permissions**
   - Click "Actions" → "General" in left sidebar
   - Under "Actions permissions", select:
     - "Allow all actions and reusable workflows" OR
     - "Allow [your organization] and [your username]"

3. **Enable Workflow Permissions**
   - Under "Workflow permissions", select:
     - "Read and write permissions" if needed
     - Click "Save"

4. **Verify Actions is Enabled**
   - Click "Actions" tab at the top of the repository
   - You should see workflow runs (or "No workflows run yet")
   - If you see "Actions not enabled", click "Enable Actions"

5. **Manually Trigger Workflows**
   - Go to "Actions" tab
   - Click "CI Smoke Test" workflow
   - Click "Run workflow" button
   - Click "Run workflow" to trigger manually
   - Wait for it to complete

6. **Test Scraper Workflow**
   - Go to "Actions" tab
   - Click "Run Scraper & Trend Pipeline" workflow
   - Click "Run workflow" button
   - Click "Run workflow" to trigger manually
   - Wait for it to complete (may take 10-30 minutes)

### Expected Results
- Workflows should be visible in Actions tab
- Manual trigger should be available
- Workflows should run successfully (green checkmark)

---

## 3. Integrating Auth System in Frontend

### Why This Is Needed
The backend auth system is implemented, but the frontend still uses localStorage-only preferences. We need to add real login/signup pages and auth guards.

### Step-by-Step Instructions

#### Step 1: Create Login Page

1. **Create login page**
   - Create file: `frontend/src/routes/login.tsx`
   - Add login form with email and password
   - Call `/api/auth/login` endpoint
   - Store session token in localStorage on success
   - Redirect to home page on success

#### Step 2: Create Signup Page

1. **Create signup page**
   - Create file: `frontend/src/routes/signup.tsx`
   - Add signup form with email, password, niche, language
   - Call `/api/auth/signup` endpoint
   - Store session token in localStorage on success
   - Redirect to home page on success

#### Step 3: Create Auth Context

1. **Create auth context**
   - Create file: `frontend/src/contexts/AuthContext.tsx`
   - Manage user session state
   - Provide login/logout functions
   - Check session validity on load

#### Step 4: Add Auth Guard

1. **Create auth guard component**
   - Create file: `frontend/src/components/AuthGuard.tsx`
   - Check if user is authenticated
   - Redirect to login if not authenticated
   - Wrap protected routes with this guard

#### Step 5: Update Home Page

1. **Modify home page**
   - Update `frontend/src/routes/index.tsx`
   - Remove onboarding for authenticated users
   - Show auth guard for main content
   - Redirect to login if not authenticated

#### Step 6: Update API Client

1. **Modify API client**
   - Update `frontend/src/lib/api.ts`
   - Add session token to all API requests
   - Add auth functions (login, signup, logout, verify)
   - Handle 401 errors (redirect to login)

#### Step 7: Add Navigation

1. **Add login/signup links**
   - Update navigation header
   - Add "Login" and "Signup" buttons
   - Add "Logout" button for authenticated users

### Testing Auth Integration

1. **Test signup flow**
   - Go to `/signup`
   - Create new account
   - Verify redirect to home page
   - Verify session token stored

2. **Test login flow**
   - Go to `/login`
   - Login with existing account
   - Verify redirect to home page
   - Verify session token stored

3. **Test auth guard**
   - Clear localStorage
   - Go to home page
   - Verify redirect to login page

4. **Test logout**
   - Click logout button
   - Verify session token removed
   - Verify redirect to login page

---

## 4. Testing All Fixes Together

### Complete Testing Checklist

1. **Test Timestamps**
   ```bash
   cd backend
   python check_recent_trends.py
   ```
   - Verify trends have created_at field
   - Verify timestamps are reasonable

2. **Test Auth Backend**
   ```bash
   cd backend
   python auth_system.py
   ```
   - Verify user creation works
   - Verify login works
   - Verify session verification works

3. **Test Scraper**
   ```bash
   cd backend
   python test_scraper.py
   ```
   - Verify scraper runs without errors
   - Verify scraper returns > 0 reels

4. **Test GitHub Actions**
   - Go to GitHub Actions tab
   - Manually trigger CI workflow
   - Manually trigger scraper workflow
   - Verify both complete successfully

5. **Test Frontend Auth**
   - Start frontend: `cd frontend && npm run dev`
   - Start backend: `cd backend && python -m uvicorn api:app`
   - Test signup flow
   - Test login flow
   - Test auth guard
   - Test logout

---

## 5. Pushing Changes to GitHub

### Step-by-Step Instructions

1. **Push current changes**
   ```bash
   cd C:\Users\Chinmay\OneDrive\Desktop\trendrop
   git push
   ```

2. **Verify GitHub Actions run**
   - Go to https://github.com/ch1n-may/trendrop/actions
   - Verify CI workflow runs on push
   - Verify it completes successfully

---

## 6. Monitoring Scraper Going Forward

### Daily Scraper Check

1. **Check GitHub Actions**
   - Go to Actions tab daily
   - Check if scraper workflow ran successfully
   - Check for any errors in logs

2. **Check Database**
   ```bash
   cd backend
   python check_recent_trends.py
   ```
   - Verify new trends are being added
   - Verify timestamps are recent

3. **Check Frontend**
   - Go to your deployed app
   - Verify new trends are showing
   - Verify trends have dates

---

## Summary of Files to Create/Modify

### Files to Create
- `frontend/src/routes/login.tsx` - Login page
- `frontend/src/routes/signup.tsx` - Signup page
- `frontend/src/contexts/AuthContext.tsx` - Auth context
- `frontend/src/components/AuthGuard.tsx` - Auth guard component

### Files to Modify
- `frontend/src/lib/api.ts` - Add auth functions and session token handling
- `frontend/src/routes/index.tsx` - Add auth guard
- `frontend/src/components/Navigation.tsx` - Add login/signup/logout buttons

---

## Expected Timeline

1. **Instagram cookies:** 10-15 minutes
2. **GitHub Actions enable:** 5-10 minutes
3. **Frontend auth integration:** 2-3 hours
4. **Testing all fixes:** 30-60 minutes
5. **Total:** 3-4 hours

---

## Troubleshooting

### Scraper Still Returns 0 Reels
- Instagram cookies may be expired
- Instagram account may be blocked
- Try with a different Instagram account
- Check Instagram cookies format

### GitHub Actions Still 404
- Check organization permissions
- Check repository is not archived
- Check you have admin access
- Contact GitHub support if needed

### Frontend Auth Not Working
- Check backend is running
- Check API endpoints are accessible
- Check session token is being stored
- Check API requests include session token
- Check browser console for errors

---

## Need Help?

If you encounter any issues:
1. Check the error logs
2. Verify environment variables are set
3. Check GitHub Actions logs
4. Check browser console for frontend errors
5. Check backend logs for API errors