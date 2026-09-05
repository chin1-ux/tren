from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from schemas import *

router = APIRouter()

@router.get("/api/admin/analytics-summary")
def get_analytics_summary(
    days: int = 30,
    admin_info: dict = Depends(require_admin)
):
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        res = supabase.table("analytics_events") \
            .select("event_name") \
            .gte("created_at", cutoff) \
            .order("created_at", desc=True) \
            .limit(5000) \
            .execute()
        events = res.data or []
        summary = {}
        for ev in events:
            name = ev["event_name"]
            summary[name] = summary.get(name, 0) + 1
        return {"success": True, "event_counts": summary, "total_events": len(events), "days": days}
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/admin/login")
@limiter.limit("5/minute")
def admin_login(request: Request, req: AdminLoginRequest):
    """Admin login endpoint with rate limiting, lockout, and audit logging."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Check if login attempts are allowed (not locked out)
        if not check_and_update_login_attempts(req.email):
            log_admin_login_attempt(req.email, False, client_ip, user_agent)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed login attempts. Try again in 15 minutes."
            )
        
        # Get admin user
        admin_user = get_admin_user_by_email(req.email)
        
        if not admin_user:
            logger.warning(f"Admin user not found for email: {req.email}")
            log_admin_login_attempt(req.email, False, client_ip, user_agent)
            record_failed_login_attempt(req.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        password_valid = verify_password(req.password, admin_user["password_hash"])
        logger.info(f"Password verification for {req.email}: {password_valid}")
        
        if not password_valid:
            logger.warning(f"Invalid password for {req.email}")
            log_admin_login_attempt(req.email, False, client_ip, user_agent)
            record_failed_login_attempt(req.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Reset failed attempts on successful login
        reset_login_attempts(req.email)
        
        # Log successful login
        log_admin_login_attempt(req.email, True, client_ip, user_agent)
        
        # Create JWT token
        token_data = {
            "sub": admin_user["email"],
            "role": admin_user["role"]
        }
        access_token = create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "email": admin_user["email"],
            "role": admin_user["role"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error during admin login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/api/admin/change-password")
@limiter.limit("10/minute")
def admin_change_password(request: Request, req: AdminChangePasswordRequest, admin_info: dict = Depends(require_admin)):
    """Change admin password (requires valid JWT)."""
    try:
        email = admin_info["email"]
        
        # Get current admin user
        admin_user = get_admin_user_by_email(email)
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found"
            )
        
        # Verify current password
        if not verify_password(req.current_password, admin_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = hash_password(req.new_password)
        
        # Update password in database
        supabase.table("admin_users").update({
            "password_hash": new_password_hash
        }).eq("email", email).execute()
        
        # Log password change
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        supabase.table("admin_audit_log_enhanced").insert({
            "admin_email": email,
            "action": "password_change",
            "details": {},
            "ip_address": client_ip,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        return {"success": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error changing admin password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/api/admin/validate-token")
@limiter.limit("30/minute")
def admin_validate_token(request: Request, admin_info: dict = Depends(require_admin)):
    """Validate admin JWT token."""
    return {"valid": True, "email": admin_info["email"], "role": admin_info["role"]}


@router.get("/api/admin/users", tags=["Admin"])
@limiter.limit("30/minute")
def admin_get_users(
    request: Request,
    search: Optional[str] = None,
    plan_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin_info: dict = Depends(require_admin)
):
    """Retrieve users list for management page."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        query = supabase.table("users").select("*").order("created_at", desc=True)
        if search:
            query = query.ilike("email", f"%{search}%")
        if plan_filter and plan_filter != "all":
            query = query.eq("plan", plan_filter)
        
        query = query.range(offset, offset + limit - 1)
        res = query.execute()
        return {"users": res.data or []}
    except Exception as e:
        logger.exception(f"Error getting admin users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/api/admin/users/{email}", tags=["Admin"])
@limiter.limit("30/minute")
def admin_get_user_details(
    request: Request,
    email: str,
    admin_info: dict = Depends(require_admin)
):
    """Get single user detailed statistics and active devices."""
    if not supabase:
         raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        user_res = supabase.table("users").select("*").eq("email", email).limit(1).execute()
        if not user_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_res.data[0]
        
        # Load usage stats from usage_tracker
        stats = {}
        if UsageTracker:
            stats = UsageTracker.get_user_usage_stats(email, 30)
            
        # Get active sessions
        sessions = supabase.table("active_sessions").select("*").eq("user_id", user_data.get("id")).execute()
        
        return {
            "user": user_data,
            "usage_stats": stats,
            "devices": sessions.data or []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user details")


@router.post("/api/admin/users/{email}/plan", tags=["Admin"])
@limiter.limit("10/minute")
def admin_update_user_plan(
    request: Request,
    email: str,
    payload: dict,
    admin_info: dict = Depends(require_admin)
):
    """Change subscription plan tier via plan_overrides table."""
    new_plan = payload.get("new_plan")
    reason = payload.get("reason", "Admin update")
    expires_in_days = payload.get("expires_in_days")
    
    if not new_plan:
        raise HTTPException(status_code=400, detail="new_plan required")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        # Get target user ID
        target_res = supabase.table("users").select("id").eq("email", email).single().execute()
        if not target_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        target_user_id = target_res.data.get("id")
        
        # Get admin user ID
        admin_email = admin_info["email"]
        admin_res = supabase.table("users").select("id").eq("email", admin_email).execute()
        admin_id = admin_res.data[0].get("id") if admin_res.data else None
        
        # Calculate expiration date if provided
        from datetime import datetime, timezone, timedelta
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
        
        # Insert or update plan override
        supabase.table("plan_overrides").upsert({
            "user_id": target_user_id,
            "tier": new_plan,
            "granted_by": admin_id,
            "expires_at": expires_at
        }).execute()
        
        # Log admin action
        supabase.table("admin_audit_log_enhanced").insert({
            "admin_email": admin_email,
            "action": "plan_override",
            "target_user_email": email,
            "details": {
                "new_plan": new_plan,
                "reason": reason,
                "expires_at": expires_at
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        invalidate_cached_user_profile(email)
        
        return {"success": True, "message": f"Plan override set to {new_plan}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to update plan")


@router.post("/api/admin/users/{email}/lock", tags=["Admin"])
@limiter.limit("10/minute")
def admin_lock_user(
    request: Request,
    email: str,
    payload: dict,
    admin_info: dict = Depends(require_admin)
):
    """Lock user account."""
    reason = payload.get("reason", "Admin lock")
    admin_email = admin_info["email"]
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        # Get target user ID
        target_res = supabase.table("users").select("id").eq("email", email).single().execute()
        if not target_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        target_user_id = target_res.data.get("id")
        
        update_res = supabase.table("users").update({"status": "locked"}).eq("email", email).execute()
        if not update_res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Log admin action
        supabase.table("admin_audit_log_enhanced").insert({
            "admin_email": admin_email,
            "action": "account_lock",
            "target_user_email": email,
            "details": {"reason": reason},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        return {"success": True, "message": "User account locked"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error locking account: {e}")
        raise HTTPException(status_code=500, detail="Failed to lock account")


@router.post("/api/admin/users/{email}/unlock", tags=["Admin"])
@limiter.limit("10/minute")
def admin_unlock_user(
    request: Request,
    email: str,
    payload: dict,
    admin_info: dict = Depends(require_admin)
):
    """Unlock user account."""
    reason = payload.get("reason", "Admin unlock")
    admin_email = admin_info["email"]
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        # Get target user ID
        target_res = supabase.table("users").select("id").eq("email", email).single().execute()
        if not target_res.data:
            raise HTTPException(status_code=404, detail="User not found")
        target_user_id = target_res.data.get("id")
        
        update_res = supabase.table("users").update({"status": "active"}).eq("email", email).execute()
        if not update_res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Log admin action
        supabase.table("admin_audit_log_enhanced").insert({
            "admin_email": admin_email,
            "action": "account_unlock",
            "target_user_email": email,
            "details": {"reason": reason},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        return {"success": True, "message": "User account unlocked"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error unlocking account: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlock account")


@router.get("/api/admin/plan-features", tags=["Admin"])
@limiter.limit("30/minute")
def admin_get_plan_features(
    request: Request,
    admin_info: dict = Depends(require_admin)
):
    """Fetch subscription plans config."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = supabase.table("subscription_tiers").select("*").execute()
        # Remap properties to match existing frontend expectations if needed
        frontend_plans = []
        for tier in (res.data or []):
            frontend_plans.append({
                "plan_name": tier["name"],
                "display_name": tier["name"].capitalize(),
                "price_monthly": tier["price_inr_monthly"],
                "price_yearly": tier["price_inr_monthly"] * 10,  # Computed fallback
                "api_limit_per_day": -1 if tier["api_access"] else 10,
                "trend_views_per_day": -1,
                "features": ["Access: " + ("Immediate after scrape" if tier["data_delay_hours"] == 0 else f"{tier['data_delay_hours']}h delay after scrape"), "Max Saved Niches: " + str(tier["max_saved_niches"])]
            })
        return {"plan_features": frontend_plans}
    except Exception as e:
        logger.exception(f"Error listing plan features: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch plan features")


@router.post("/api/admin/plan-features", tags=["Admin"])
@limiter.limit("10/minute")
def admin_create_plan_feature(
    request: Request,
    payload: dict,
    admin_info: dict = Depends(require_admin)
):
    """Upsert tier definitions."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        plan_name = payload.get("plan_name")
        price_monthly = payload.get("price_monthly", 0)
        
        # Update price_inr_monthly inside subscription_tiers
        update_res = supabase.table("subscription_tiers").update({
            "price_inr_monthly": int(price_monthly)
        }).eq("name", plan_name).execute()
        
        return {"success": True, "data": update_res.data}
    except Exception as e:
        logger.exception(f"Error creating plan feature: {e}")
        raise HTTPException(status_code=500, detail="Failed to modify plan features")


@router.get("/api/business/metrics")
@limiter.limit("30/minute")
def get_business_metrics(
    request: Request,
    days: int = 30,
    admin_info: dict = Depends(require_admin)
):
    """Get business metrics for pre-seed preparation."""
    if not BusinessMetrics:
        raise HTTPException(status_code=500, detail="Business metrics not configured.")
    
    try:
        metrics = BusinessMetrics.get_all_metrics(days)
        return metrics
    except Exception as e:
        logger.exception(f"Error getting business metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get business metrics")


@router.get("/api/business/user-metrics")
@limiter.limit("30/minute")
def get_user_metrics_endpoint(
    request: Request,
    days: int = 30,
    admin_info: dict = Depends(require_admin)
):
    """Get user acquisition metrics."""
    if not BusinessMetrics:
        raise HTTPException(status_code=500, detail="Business metrics not configured.")
    
    try:
        metrics = BusinessMetrics.get_user_metrics(days)
        return metrics
    except Exception as e:
        logger.exception(f"Error getting user metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user metrics")


@router.get("/api/business/revenue")
@limiter.limit("30/minute")
def get_revenue_metrics_endpoint(
    request: Request,
    days: int = 30,
    admin_info: dict = Depends(require_admin)
):
    """Get revenue metrics."""
    if not RevenueTracker:
        raise HTTPException(status_code=500, detail="Revenue tracker not configured.")
    
    try:
        metrics = RevenueTracker.get_all_revenue_metrics(days)
        return metrics
    except Exception as e:
        logger.exception(f"Error getting revenue metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get revenue metrics")


@router.get("/api/business/mrr")
@limiter.limit("30/minute")
def get_mrr_endpoint(
    request: Request,
    admin_info: dict = Depends(require_admin)
):
    """Get Monthly Recurring Revenue (MRR)."""
    if not RevenueTracker:
        raise HTTPException(status_code=500, detail="Revenue tracker not configured.")
    
    try:
        mrr = RevenueTracker.calculate_mrr()
        return mrr
    except Exception as e:
        logger.exception(f"Error calculating MRR: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate MRR")


@router.get("/api/business/subscription-breakdown")
@limiter.limit("30/minute")
def get_subscription_breakdown_endpoint(
    request: Request,
    current_user: str = Depends(require_admin)
):
    """Get subscription breakdown by plan."""
    if not RevenueTracker:
        raise HTTPException(status_code=500, detail="Revenue tracker not configured.")
    
    try:
        breakdown = RevenueTracker.get_subscription_breakdown()
        return breakdown
    except Exception as e:
        logger.exception(f"Error getting subscription breakdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription breakdown")


@router.get("/api/business/cac-ltv")
@limiter.limit("30/minute")
def get_cac_ltv_endpoint(
    request: Request,
    current_user: str = Depends(require_admin)
):
    """Get Customer Acquisition Cost (CAC) and Lifetime Value (LTV)."""
    if not BusinessMetrics:
        raise HTTPException(status_code=500, detail="Business metrics not configured.")
    
    try:
        metrics = BusinessMetrics.calculate_cac_ltv()
        return metrics
    except Exception as e:
        logger.exception(f"Error calculating CAC/LTV: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate CAC/LTV")


@router.get("/api/case-studies")
@limiter.limit("30/minute")
def get_case_studies(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Get sample case studies for pre-seed preparation."""
    if not get_sample_case_studies:
        raise HTTPException(status_code=500, detail="Case study templates not configured.")
    
    try:
        case_studies = get_sample_case_studies()
        return {
            'case_studies': case_studies,
            'total': len(case_studies)
        }
    except Exception as e:
        logger.exception(f"Error getting case studies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get case studies")


@router.get("/api/pitch-deck")
@limiter.limit("30/minute")
def get_pitch_deck(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Get pitch deck structure for pre-seed preparation."""
    if not generate_pitch_deck_content:
        raise HTTPException(status_code=500, detail="Pitch deck structure not configured.")
    
    try:
        pitch_deck = generate_pitch_deck_content()
        return pitch_deck
    except Exception as e:
        logger.exception(f"Error getting pitch deck: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pitch deck")


@router.get("/api/pitch-deck/markdown")
@limiter.limit("30/minute")
def get_pitch_deck_markdown(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Get pitch deck in markdown format."""
    if not export_pitch_deck_to_markmark:
        raise HTTPException(status_code=500, detail="Pitch deck structure not configured.")
    
    try:
        markdown = export_pitch_deck_to_markmark()
        return {
            'markdown': markdown,
            'exported_at': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.exception(f"Error exporting pitch deck to markdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to export pitch deck")


@router.get("/api/admin/audit-log", tags=["Admin"])
def admin_get_audit_log(
    admin_user: dict = Depends(require_admin),
    admin_email_filter: Optional[str] = None,
    action_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
):
    """Get admin audit log with optional filters."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        query = supabase.table("admin_actions").select("*").order("created_at", desc=True)
        
        if admin_email_filter:
            admin_res = supabase.table("users").select("id").eq("email", admin_email_filter).single().execute()
            if admin_res.data:
                query = query.eq("admin_id", admin_res.data.get("id"))
        
        if action_filter:
            query = query.eq("action", action_filter)
        
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)
        
        query = query.limit(limit)
        res = query.execute()
        
        # Enrich with email addresses
        enriched_logs = []
        for log in (res.data or []):
            admin_email = None
            target_email = None
            
            if log.get("admin_id"):
                admin_res = supabase.table("users").select("email").eq("id", log["admin_id"]).single().execute()
                admin_email = admin_res.data.get("email") if admin_res.data else None
            
            if log.get("target_user_id"):
                target_res = supabase.table("users").select("email").eq("id", log["target_user_id"]).single().execute()
                target_email = target_res.data.get("email") if target_res.data else None
            
            enriched_logs.append({
                **log,
                "admin_email": admin_email,
                "target_user_email": target_email
            })
        
        return {"audit_log": enriched_logs}
    except Exception as e:
        logger.exception(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit log")


