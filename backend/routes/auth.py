from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from api_globals import _enforce_rate_limit, _get_client_ip
from schemas import *
import jwt

_jwks_client = None

def _get_supabase_jwks_client():
    global _jwks_client
    if _jwks_client is None and SUPABASE_URL:
        from jwt import PyJWKClient
        _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True)
    return _jwks_client

def _email_from_supabase_jwt(token: str) -> Optional[str]:
    """Return the email claim of a valid Supabase access token, else None."""
    try:
        client = _get_supabase_jwks_client()
        if client is None:
            return None
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1",
        )
        return claims.get("email")
    except Exception as e:
        logger.warning(f"Supabase JWT validation failed: {e}")
        return None

router = APIRouter()

@router.post("/api/auth/reset-password")
@limiter.limit("5/hour")
def reset_password(request: Request, req: ResetPasswordRequest):
    _enforce_rate_limit(request, "reset_password", 3, 3600, [req.email])
    try:
        frontend_url = os.getenv("FRONTEND_URL", "https://trendrop-black.vercel.app")
        supabase.auth.reset_password_email(req.email, options={"redirect_to": f"{frontend_url}/update-password"})
        return {"success": True, "message": "Password reset email sent if account exists"}
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return {"success": True, "message": "Password reset email sent if account exists"}


@router.post("/api/auth/signup")
@limiter.limit("5/hour")
def signup(request: Request, req: SignupRequest):
    """
    Initiate signup process with phone verification.
    Creates user in Supabase Auth but requires phone verification before full access.
    """
    _enforce_rate_limit(request, "signup", 3, 3600, [])
    try:
        # Step 1: Create user via sign_up (properly hashes password for login)
        # Then auto-confirm email via admin API so user can login immediately
        auth_res = None
        try:
            auth_res = supabase.auth.sign_up({"email": req.email, "password": req.password})
            logger.info(f"User created via sign_up: {req.email}")
            
            # Auto-confirm email via admin if sign_up didn't confirm it
            if auth_res and auth_res.user and not auth_res.user.email_confirmed_at:
                try:
                    import requests as _req
                    _req.post(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{auth_res.user.id}/confirm",
                        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                        timeout=10
                    )
                    logger.info(f"Auto-confirmed email for: {req.email}")
                except Exception as confirm_err:
                    logger.warning(f"Auto-confirm failed (non-fatal): {confirm_err}")
        except Exception as sign_err:
            # If user already exists via sign_up, try admin create as fallback
            logger.warning(f"sign_up failed: {sign_err}, trying admin create")
            try:
                auth_res = supabase.auth.admin.create_user({
                    "email": req.email,
                    "password": req.password,
                    "email_confirm": True
                })
                logger.info(f"User created via admin auth API: {req.email}")
            except Exception as admin_err:
                logger.error(f"Both signup methods failed: {admin_err}")
                raise HTTPException(status_code=400, detail="Failed to create account")

        if not auth_res or not auth_res.user:
            raise HTTPException(status_code=400, detail="Failed to register user via Supabase Auth")

        # Step 2: Send phone verification code (optional — skip if service not configured)
        phone_verified = False
        phone_verification_required = False

        if PhoneVerification:
            verification_result = PhoneVerification.send_verification_code(req.phone_number)
            if verification_result.get('success'):
                logger.info(f"Verification code sent to: {req.phone_number}")
                phone_verification_required = True
            else:
                # Verification send failed — log; do NOT mark the number verified.
                # Asserting a false "verified" state is worse than an unverified one.
                logger.warning(f"Verification code send failed (non-fatal): {verification_result.get('error')}")
                phone_verified = False
        else:
            # PhoneVerification not configured — the number stays unverified
            logger.info("PhoneVerification not configured — skipping phone verification for signup")
            phone_verified = False

        # Step 3: Save user metadata to users table
        import random
        user_id = f"#{random.randint(1000, 9999)}"
        
        user_data = {
            "email": req.email,
            "user_id": user_id,
            "phone_number": req.phone_number,
            "phone_verified": phone_verified,
            "niche": req.niche,
            "language_preference": req.language,
            "plan": "free",
            "credits_remaining": 100,
            "credits_used_this_month": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("users").upsert(user_data, on_conflict="email").execute()

        # Step 3.5: Save to user_preferences
        prefs_data = {
            "email": req.email,
            "niches": [req.niche] if req.niche != "all" else [],
            "languages": [req.language],
            "regions": ["IN"],
            "creator_language": req.language,
            "state": req.state if req.state else None,
            "creator_tier": req.tier if req.tier else "nano",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            supabase.table("user_preferences").upsert(prefs_data, on_conflict="email").execute()
        except Exception as e:
            logger.error(f"Failed to save user_preferences for {req.email}: {e}")

        # Log signup grant in credit_transactions
        try:
            user_id_res = supabase.table("users").select("id").eq("email", req.email).single().execute()
            if user_id_res.data:
                supabase.table("credit_transactions").insert({
                    "user_id": user_id_res.data["id"],
                    "amount": 100,
                    "reason": "signup_grant",
                    "endpoint": "signup",
                    "balance_after": 100,
                }).execute()
        except Exception:
            logger.warning(f"Failed to log signup credit grant for {req.email}")

        response: dict = {
            "success": True,
            "message": "Account created successfully!" if phone_verified else "Account created. Please verify your phone number to complete signup.",
            "user": {
                "email": req.email,
                "phone_number": req.phone_number,
                "phone_verified": phone_verified,
                "niche": req.niche,
                "language": req.language
            },
            "phone_verification_required": phone_verification_required
        }

        return response
    except Exception as e:
        logger.error(f"Signup failed: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/auth/verify-phone")
@limiter.limit("10/hour")
def verify_phone(request: Request, req: VerifyPhoneRequest):
    """
    Verify phone number with OTP code.
    Completes signup process and enables full account access.
    """
    _enforce_rate_limit(request, "verify_phone", 5, 3600, [req.phone_number])
    try:
        if not PhoneVerification:
            raise HTTPException(status_code=500, detail="Phone verification not configured")

        # Verify the code
        verification_result = PhoneVerification.verify_code(req.phone_number, req.code)
        
        if not verification_result.get('success'):
            logger.warning(f"Phone verification failed for {req.phone_number}: {verification_result.get('error')}")
            raise HTTPException(
                status_code=400,
                detail=verification_result.get('error', 'Invalid verification code')
            )

        # Update user record to mark phone as verified
        if supabase:
            user_res = supabase.table("users").select("*").eq("phone_number", req.phone_number).limit(1).execute()
            if not user_res.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            user = user_res.data[0]
            
            supabase.table("users").update({
                "phone_verified": True
            }).eq("phone_number", req.phone_number).execute()
            logger.info(f"Phone verified for: {req.phone_number}")

            return {
                "success": True,
                "message": "Phone verified successfully. Please log in to continue."
            }
        
        return {
            "success": True,
            "message": "Phone verified successfully."
        }
    except Exception as e:
        logger.error(f"Phone verification failed: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/auth/send-otp")
@limiter.limit("5/minute")
def send_otp(request: Request, req: SendOtpRequest):
    """Send verification code via SMS (auth endpoint, no session required)"""
    _enforce_rate_limit(request, "send_otp", 3, 60, [req.phone_number])
    if not PhoneVerification:
        raise HTTPException(status_code=500, detail="Phone verification not configured.")
    
    try:
        # Check 30-second cooldown in the database
        if supabase:
            db_res = supabase.table("phone_verifications").select("last_otp_sent_at").eq("phone_number", req.phone_number).execute()
            if db_res.data:
                last_sent = db_res.data[0].get("last_otp_sent_at")
                if last_sent:
                    last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                    if (datetime.now(timezone.utc) - last_sent_dt).total_seconds() < 30:
                        raise HTTPException(status_code=429, detail="Please wait 30 seconds before requesting another code.")

        result = PhoneVerification.send_verification_code(req.phone_number)
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to send verification code'))
        return result
    except Exception as e:
        logger.exception(f"Error sending verification code: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Failed to send verification code")


@router.post("/api/auth/login")
@limiter.limit("10/hour")
def login(request: Request, req: LoginRequest):
    """Login user via Supabase Auth and return access token"""
    _enforce_rate_limit(request, "login", 5, 900, [req.email])
    try:
        # Authenticate via Supabase Auth
        local_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        auth_res = local_supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
        
        if not auth_res or not auth_res.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # ── Locked user check (C2) — must happen BEFORE issuing any token ──────
        try:
            status_res = supabase.table("users").select("status, niche, language_preference").eq("email", req.email).limit(1).execute()
            if status_res.data:
                row = status_res.data[0]
                if row.get("status") == "locked":
                    # Sign back out so the Supabase session is not left open
                    try:
                        local_supabase.auth.sign_out()
                    except Exception:
                        pass
                    raise HTTPException(status_code=403, detail="Account is locked. Contact support.")
                niche = row.get("niche", "all")
                language = row.get("language_preference", "en")
            else:
                niche = "all"
                language = "en"
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to fetch user preferences/status: {e}")
            niche = "all"
            language = "en"

        return {
            "success": True,
            "message": "Login successful",
            "session_token": auth_res.session.access_token,
            "expires_at": datetime.fromtimestamp(auth_res.session.expires_at, tz=timezone.utc).isoformat() if auth_res.session.expires_at else None,
            "user": {
                "email": req.email,
                "niche": niche,
                "language": language
            }
        }
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/api/auth/logout")
@limiter.limit("20/hour")
def logout(request: Request, req: LogoutRequest):
    """Logout user: remove this device's active session row so the device
    slot is freed (previously a no-op, which let stale rows lock users out)."""
    try:
        if getattr(req, "session_token", None):
            import hashlib
            fp = hashlib.md5(req.session_token.encode("utf-8")).hexdigest()
            if supabase:
                supabase.table("active_sessions").delete().eq("device_fingerprint", fp).execute()
        return {"success": True, "message": "Logout successful"}
    except Exception as e:
        logger.error(f"Logout failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.api_route("/api/auth/verify", methods=["GET", "POST"])
@limiter.limit("30/hour")
def verify(request: Request, req: Optional[VerifyRequest] = None):
    """Verify session token and enforce active session limits"""
    try:
        email = None
        user = None
        
        # Extract token from body or Authorization Bearer header
        session_token = None
        if req and req.session_token:
            session_token = req.session_token
        else:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_token = auth_header.split("Bearer ")[1].strip()

        if not session_token:
            return {"success": False, "valid": False, "error": "No session token provided"}

        # 1. Try resolving session token in users database table first
        db_user_res = supabase.table("users").select("*").eq("auth_token", session_token).limit(1).execute()
        if db_user_res.data:
            user = db_user_res.data[0]
            email = user["email"]
        else:
            # 2. Try validating via Supabase JWT
            email = _email_from_supabase_jwt(session_token)
            if email:
                db_user_res2 = supabase.table("users").select("*").eq("email", email).limit(1).execute()
                if db_user_res2.data:
                    user = db_user_res2.data[0]
                
        if not email or not user:
            return {"success": False, "valid": False, "error": "Invalid session token"}
        
        # ── Locked user check (C2) ─────────────────────────────────────────────
        if user.get("status") == "locked":
            return {"success": False, "valid": False, "error": "Account is locked. Contact support."}
            
        user_id = user["id"]
        
        # 3. Fetch active sessions limit from user's tier
        tier_id = user.get("tier_id")
        if tier_id is not None:
            tier_res = supabase.table("subscription_tiers").select("max_active_sessions").eq("id", tier_id).limit(1).execute()
            max_active = tier_res.data[0]["max_active_sessions"] if tier_res.data else 1
        else:
            max_active = 1
        
        # 4. Check active sessions count — only RECENT sessions count toward
        #    the cap, otherwise abandoned devices permanently lock users out.
        #    Clean up stale sessions from DB so they don't accumulate forever.
        sessions_res = supabase.table("active_sessions").select("*").eq("user_id", user_id).order("last_active_at", desc=False).execute()
        active_sessions = sessions_res.data or []
        _stale_cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        _stale_cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        recent_sessions = []
        stale_ids = []
        for s in active_sessions:
            last_active = s.get("last_active_at") or ""
            if last_active >= _stale_cutoff_24h:
                recent_sessions.append(s)
            else:
                stale_ids.append(s.get("id"))
        # Delete stale sessions (>24h) from DB so they don't accumulate forever
        if stale_ids:
            for sid in stale_ids:
                try:
                    supabase.table("active_sessions").delete().eq("id", sid).execute()
                except Exception:
                    pass
        
        # If more sessions exist than max_active, delete the oldest excess ones
        # This handles the case where multiple logins pile up within 24h
        if len(recent_sessions) > max_active:
            excess = recent_sessions[:-max_active]  # keep only the newest max_active
            for s in excess:
                try:
                    supabase.table("active_sessions").delete().eq("id", s.get("id")).execute()
                except Exception:
                    pass
            recent_sessions = recent_sessions[-max_active:]
        
        device_label = "Web Session"
        import hashlib
        device_fingerprint = hashlib.md5(req.session_token.encode('utf-8')).hexdigest()
        
        matching_session = [s for s in active_sessions if s["device_fingerprint"] == device_fingerprint]
        
        if not matching_session:
            if len(recent_sessions) >= max_active:
                # Kick the oldest session to make room for the new device
                # (previously this was a hard reject that locked users out permanently)
                oldest_session = recent_sessions[0]
                try:
                    supabase.table("active_sessions").delete().eq("id", oldest_session.get("id")).execute()
                except Exception:
                    pass
                recent_sessions = recent_sessions[1:]
            
            # Register new session
            supabase.table("active_sessions").insert({
                "user_id": user_id,
                "device_fingerprint": device_fingerprint,
                "device_label": device_label,
                "last_active_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        else:
            # Update last active timestamp
            supabase.table("active_sessions").update({
                "last_active_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", matching_session[0]["id"]).execute()
            
        return {
            "success": True,
            "valid": True,
            "user": {
                "email": email,
                "niche": user.get("niche") or "all",
                "language": user.get("language_preference") or "all",
                "plan": user.get("plan") or "free"
            }
        }
    except Exception as e:
        logger.error(f"Verify failed: {e}", exc_info=True)
        print(f"VERIFY EXCEPTION: {e}")
        import traceback; traceback.print_exc()
        if isinstance(e, HTTPException):
            raise
        return {"success": False, "valid": False, "error": "Session verification failed"}


@router.post("/api/instagram/auth-url")
@limiter.limit("15/minute")
def get_instagram_auth_url(req: InstagramAuthRequest, request: Request, current_user_email: str = Depends(require_auth)):
    """Generate Instagram OAuth authorization URL for the user."""
    if current_user_email != "guest@trendrop.app" and req.user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot generate auth URL for another user")
    
    if not InstagramOAuth:
        raise HTTPException(status_code=501, detail="Instagram OAuth not configured")
    
    try:
        # Generate a state parameter for CSRF protection
        state = secrets.token_urlsafe(16)
        
        auth_url = InstagramOAuth.get_auth_url(state=state)
        
        logger.info(f"Generated Instagram auth URL for user: {req.user_email}")
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Error generating Instagram auth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate auth URL")


@router.get("/api/instagram/callback")
@limiter.limit("30/minute")
def instagram_callback_get(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handle GET redirect from Meta OAuth.
    Meta redirects here with ?code=... after user grants permission.
    We process the code server-side and redirect to the frontend settings page.
    The 'state' param is 'verify_flow_state' (hardcoded in auth URL).
    """
    frontend_url = os.getenv("FRONTEND_URL", "https://trendrop-black.vercel.app")
    settings_url = f"{frontend_url}/settings"

    if error:
        logger.warning(f"Instagram OAuth error from Meta: {error}")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{settings_url}?ig_error={error}", status_code=302)

    if not code:
        logger.warning("Instagram callback received with no code")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{settings_url}?ig_error=no_code", status_code=302)

    if not InstagramOAuth:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{settings_url}?ig_error=not_configured", status_code=302)

    try:
        # Exchange code for tokens
        token_data = InstagramOAuth.exchange_code_for_token(code)
        short_lived_token = token_data.get("access_token")
        if not short_lived_token:
            raise ValueError("No short-lived token returned")

        long_lived_data = InstagramOAuth.get_long_lived_token(short_lived_token)
        long_lived_token = long_lived_data.get("access_token")
        if not long_lived_token:
            raise ValueError("No long-lived token returned")

        # Get Instagram Business Account (uses direct Page ID fallback for Business Manager pages)
        ig_account = InstagramOAuth.get_instagram_business_account(long_lived_token)
        if not ig_account:
            logger.error("No Instagram Business Account found during GET callback")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"{settings_url}?ig_error=no_ig_account", status_code=302)

        ig_account_id = ig_account.get("id")
        ig_username = ig_account.get("username", "unknown")

        # Use a system/guest email for the callback flow since we don't have a user JWT here.
        # The token is associated with ig_account_id which is unique per IG account.
        # We store using ig_account_id as the primary key for lookup later.
        user_email = f"ig_{ig_account_id}@trendrop.app"

        stored = InstagramOAuth.store_token(
            user_email=user_email,
            token_data={"access_token": long_lived_token, "token_type": "long-lived"},
            ig_account_id=ig_account_id
        )

        if not stored:
            logger.error(f"Failed to store token for IG account {ig_account_id}")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"{settings_url}?ig_error=store_failed", status_code=302)

        # Sync posts in background
        def _sync():
            try:
                InstagramOAuth.sync_creator_posts(long_lived_token, ig_account_id, user_email)
            except Exception as ex:
                logger.warning(f"Background post sync failed for {ig_account_id}: {ex}")

        threading.Thread(target=_sync, daemon=True).start()

        logger.info(f"Successfully connected Instagram @{ig_username} (ID: {ig_account_id}) via GET callback")
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"{settings_url}?ig_success=1&ig_username={ig_username}&ig_id={ig_account_id}",
            status_code=302
        )

    except Exception as e:
        logger.error(f"Error in GET Instagram callback: {e}", exc_info=True)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{settings_url}?ig_error=server_error", status_code=302)


@router.post("/api/instagram/callback")
@limiter.limit("15/minute")
def instagram_callback(req: InstagramCallbackRequest, request: Request, current_user_email: str = Depends(require_auth)):
    """Handle Instagram OAuth callback and store the token."""
    if current_user_email != "guest@trendrop.app" and req.user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot handle callback for another user")
    
    if not InstagramOAuth:
        raise HTTPException(status_code=501, detail="Instagram OAuth not configured")
    
    try:
        # Exchange code for short-lived token
        token_data = InstagramOAuth.exchange_code_for_token(req.code)
        short_lived_token = token_data.get("access_token")
        
        if not short_lived_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Exchange for long-lived token (60 days)
        long_lived_data = InstagramOAuth.get_long_lived_token(short_lived_token)
        long_lived_token = long_lived_data.get("access_token")
        
        if not long_lived_token:
            raise HTTPException(status_code=400, detail="Failed to obtain long-lived token")
        
        # Get Instagram Business Account
        ig_account = InstagramOAuth.get_instagram_business_account(long_lived_token)
        
        if not ig_account:
            raise HTTPException(status_code=400, detail="No Instagram Business Account found. Please ensure you have a Business/Creator account connected to a Facebook Page.")
        
        ig_account_id = ig_account.get("id")
        ig_username = ig_account.get("username")
        
        # Store token in Supabase
        stored = InstagramOAuth.store_token(
            user_email=req.user_email,
            token_data={"access_token": long_lived_token, "token_type": "long-lived"},
            ig_account_id=ig_account_id
        )
        
        if not stored:
            raise HTTPException(status_code=500, detail="Failed to store token")
        
        logger.info(f"Successfully connected Instagram account for user: {req.user_email}")
        return {
            "success": True,
            "message": "Instagram account connected successfully",
            "ig_username": ig_username,
            "ig_account_id": ig_account_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Instagram callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to connect Instagram account")


@router.get("/api/instagram/insights")
@limiter.limit("30/minute")
def get_instagram_insights(request: Request, current_user_email: str = Depends(require_auth)):
    """Fetch Instagram Insights for the authenticated user."""
    if not InstagramOAuth:
        raise HTTPException(status_code=501, detail="Instagram OAuth not configured")
    
    try:
        # Get user's Instagram token
        token_record = InstagramOAuth.get_user_token(current_user_email)
        
        if not token_record:
            raise HTTPException(status_code=404, detail="No Instagram account connected. Please connect your account first.")
        
        access_token = token_record.get("access_token")
        ig_account_id = token_record.get("ig_account_id")
        
        if not access_token or not ig_account_id:
            raise HTTPException(status_code=400, detail="Invalid token data")
        
        # Fetch insights metrics
        metrics = ["impressions", "reach", "engagement", "follower_count", "profile_views"]
        insights_data = InstagramOAuth.get_insights(
            access_token=access_token,
            ig_account_id=ig_account_id,
            metrics=metrics,
            period="day"
        )
        
        if not insights_data or "data" not in insights_data:
            raise HTTPException(status_code=500, detail="Failed to fetch insights from Instagram")
        
        # Parse insights data
        insights = {}
        for item in insights_data["data"]:
            metric_name = item.get("name")
            values = item.get("values", [])
            if values:
                insights[metric_name] = values[0].get("value", 0)
        
        logger.info(f"Successfully fetched insights for user: {current_user_email}")
        return {
            "success": True,
            "insights": insights,
            "ig_username": token_record.get("ig_username"),
            "last_updated": token_record.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Instagram insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch Instagram insights")


@router.delete("/api/instagram/disconnect")
@limiter.limit("10/minute")
def disconnect_instagram(request: Request, current_user_email: str = Depends(require_auth)):
    """Disconnect Instagram account for the user."""
    if not InstagramOAuth:
        raise HTTPException(status_code=501, detail="Instagram OAuth not configured")
    
    try:
        if supabase:
            supabase.table("instagram_tokens").delete().eq("user_email", current_user_email).execute()
            logger.info(f"Disconnected Instagram account for user: {current_user_email}")
            return {"success": True, "message": "Instagram account disconnected successfully"}
        else:
            raise HTTPException(status_code=500, detail="Database not configured")
    except Exception as e:
        logger.error(f"Error disconnecting Instagram account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to disconnect Instagram account")


@router.post("/api/phone/send-code")
@limiter.limit("5/minute")
def send_phone_verification_code(
    request: Request,
    phone_number: str,
    current_user: str = Depends(require_auth)
):
    """Send verification code via SMS."""
    if not PhoneVerification:
        raise HTTPException(status_code=500, detail="Phone verification not configured.")
    
    try:
        result = PhoneVerification.send_verification_code(phone_number)
        return result
    except Exception as e:
        logger.exception(f"Error sending verification code: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification code")


@router.post("/api/phone/verify")
@limiter.limit("10/minute")
def verify_phone_code(
    request: Request,
    phone_number: str,
    code: str,
    current_user: str = Depends(require_auth)
):
    """Verify the submitted code."""
    if not PhoneVerification:
        raise HTTPException(status_code=500, detail="Phone verification not configured.")
    
    try:
        result = PhoneVerification.verify_code(phone_number, code)
        return result
    except Exception as e:
        logger.exception(f"Error verifying code: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify code")


@router.get("/api/phone/status")
@limiter.limit("30/minute")
def get_phone_verification_status(
    request: Request,
    phone_number: str,
    current_user: str = Depends(require_auth)
):
    """Check if a phone number is verified."""
    if not PhoneVerification:
        raise HTTPException(status_code=500, detail="Phone verification not configured.")
    
    try:
        is_verified = PhoneVerification.is_phone_verified(phone_number)
        return {
            'phone_number': phone_number,
            'verified': is_verified
        }
    except Exception as e:
        logger.exception(f"Error checking verification status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check verification status")


