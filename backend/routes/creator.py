from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from api_globals import standard_queue
from schemas import *

router = APIRouter()

@router.post("/api/user/cancellation-reason")
@limiter.limit("5/hour")
def submit_cancellation_reason(
    request: Request,
    req: CancellationReasonRequest,
    current_user: str = Depends(require_auth)
):
    """
    Allow users to submit cancellation reason when cancelling subscription.
    Stores reason in users table for churn analysis.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured.")
        
        # Update user record with cancellation reason and date
        update_data = {
            "cancellation_reason": req.reason,
            "cancellation_date": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("users").update(update_data).eq("email", current_user).execute()
        
        logger.info(f"Cancellation reason submitted by {current_user}: {req.reason}")
        
        return {
            "success": True,
            "message": "Cancellation reason recorded. Thank you for your feedback."
        }
    except Exception as e:
        logger.error(f"Failed to record cancellation reason: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to record cancellation reason.")


@router.get("/api/user/plan")
@limiter.limit("30/minute")
def get_user_plan(request: Request, current_user: str = Depends(require_auth)):
    """
    Return the server-side plan for the authenticated user.
    Frontend MUST use this (not localStorage) to gate Pro features.
    """
    email = current_user
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")
    try:
        res = supabase.table("users").select("plan, credits_remaining, credits_used_this_month").eq("email", email).execute()
        if not res.data:
            return {"plan": "free", "credits_remaining": 100, "credits_used_this_month": 0}
        row = res.data[0]
        return {
            "plan": row.get("plan", "free"),
            "credits_remaining": row.get("credits_remaining", 100),
            "credits_used_this_month": row.get("credits_used_this_month", 0),
        }
    except Exception as e:
        logger.error(f"get_user_plan failed for {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/user/credits")
@limiter.limit("30/minute")
def get_user_credits(request: Request, current_user: str = Depends(require_auth)):
    """Return current credit balance and recent transaction history."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")
    try:
        user_res = supabase.table("users") \
            .select("id, credits_remaining, credits_used_this_month, credits_reset_at") \
            .eq("email", current_user).single().execute()
        if not user_res.data:
            return {"credits_remaining": 100, "credits_used_this_month": 0, "transactions": []}

        user_id = user_res.data["id"]
        tx_res = supabase.table("credit_transactions") \
            .select("amount, reason, endpoint, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(50).execute()

        return {
            "credits_remaining": user_res.data.get("credits_remaining", 100),
            "credits_used_this_month": user_res.data.get("credits_used_this_month", 0),
            "credits_reset_at": user_res.data.get("credits_reset_at"),
            "transactions": tx_res.data or [],
        }
    except Exception as e:
        logger.error(f"get_user_credits failed for {current_user}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/marketplace/profiles")
@limiter.limit("30/minute")
def get_creator_profiles(request: Request, niche: Optional[str] = None):
    try:
        q = supabase.table("creator_profiles").select("instagram_username, niche, followers, engagement_rate, trend_score, price_per_post, is_active").eq("is_active", True)
        if niche and niche != "all":
            q = q.eq("niche", niche)
        res = q.order("followers", desc=True).limit(100).execute()
        return res.data or []
    except Exception as e:
        logger.exception(f"Error getting creator profiles: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/marketplace/profile")
@limiter.limit("10/minute")
def create_or_update_profile(request: Request, req: CreatorProfileRequest, current_user_email: str = Depends(require_auth)):
    try:
        profile_data = {
            "user_email": current_user_email,
            "instagram_username": req.instagram_username,
            "niche": req.niche,
            "followers": req.followers,
            "engagement_rate": req.engagement_rate,
            "trend_score": req.trend_score,
            "portfolio_links": req.portfolio_links,
            "price_per_post": req.price_per_post,
            "is_active": True
        }
        res = supabase.table("creator_profiles").upsert(profile_data, on_conflict="user_email").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.exception(f"Error saving/updating creator profile: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/deals")
@limiter.limit("15/minute")
def create_creator_deal(
    request: Request,
    req: CreateDealRequest,
    current_user_email: str = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        from contract_generator import generate_contract_pdf
        user_sb = get_user_supabase_client(authorization)
        
        # 1. Insert brand deal (without PDF first)
        deal_data = {
            "creator_id": current_user_email,
            "brand_name": req.brand_name,
            "deliverables": req.deliverables,
            "rate_amount": req.rate_amount,
            "currency": req.currency,
            "usage_rights": req.usage_rights,
            "exclusivity_clause": req.exclusivity_clause,
            "timeline_start": req.timeline_start or None,
            "timeline_end": req.timeline_end or None,
            "cover_note_type": req.cover_note_type,
            "status": "active"
        }
        res_deal = user_sb.table("brand_deals").insert(deal_data).execute()
        if not res_deal.data:
            raise HTTPException(status_code=500, detail="Failed to create brand deal in database")
            
        deal = res_deal.data[0]
        deal_id = deal["id"]
        
        # 2. Insert milestones
        inserted_milestones = []
        for m in req.milestones:
            m_data = {
                "deal_id": deal_id,
                "milestone_name": m.milestone_name,
                "amount": m.amount,
                "due_date": m.due_date,
                "paid_status": "unpaid"
            }
            res_m = user_sb.table("deal_payment_milestones").insert(m_data).execute()
            if res_m.data:
                inserted_milestones.append(res_m.data[0])
                
        # 3. Generate Contract PDF base64
        try:
            b64_pdf = generate_contract_pdf(
                creator_email=current_user_email,
                brand_name=req.brand_name,
                deliverables=req.deliverables,
                rate_amount=req.rate_amount,
                currency=req.currency,
                usage_rights=req.usage_rights,
                exclusivity_clause=req.exclusivity_clause,
                timeline_start=req.timeline_start,
                timeline_end=req.timeline_end,
                milestones=inserted_milestones,
                cover_note_type=req.cover_note_type
            )
            
            # 4. Update brand deal with PDF content
            user_sb.table("brand_deals").update({"contract_pdf": b64_pdf}).eq("id", deal_id).execute()
            deal["contract_pdf"] = b64_pdf
        except Exception as pdf_err:
            logger.error(f"Error generating contract PDF: {pdf_err}", exc_info=True)
            deal["contract_pdf"] = None
            
        deal["milestones"] = inserted_milestones
        return deal
    except Exception as e:
        logger.exception(f"Error creating creator brand deal: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/deals")
@limiter.limit("30/minute")
def get_creator_deals(
    request: Request,
    current_user_email: str = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        user_sb = get_user_supabase_client(authorization)
        # Apply filter at API layer in addition to database RLS
        res_deals = user_sb.table("brand_deals").select("*").eq("creator_id", current_user_email).order("created_at", desc=True).limit(100).execute()
        deals = res_deals.data or []
        
        for deal in deals:
            res_m = user_sb.table("deal_payment_milestones").select("*").eq("deal_id", deal["id"]).order("due_date", desc=False).limit(100).execute()
            deal["milestones"] = res_m.data or []
            
        return deals
    except Exception as e:
        logger.exception(f"Error getting creator brand deals: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/deals/{deal_id}/download")
@limiter.limit("20/minute")
def download_deal_contract(
    deal_id: int,
    request: Request,
    current_user_email: str = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        user_sb = get_user_supabase_client(authorization)
        res_deal = user_sb.table("brand_deals").select("contract_pdf, brand_name, creator_id").eq("id", deal_id).execute()
        if not res_deal.data:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        deal = res_deal.data[0]
        # Though DB-level RLS handles it, double check in API layer
        if deal["creator_id"] != current_user_email:
            raise HTTPException(status_code=403, detail="Forbidden: You do not own this deal")
            
        b64_pdf = deal.get("contract_pdf")
        if not b64_pdf:
            raise HTTPException(status_code=404, detail="Contract PDF not found for this deal")
            
        pdf_bytes = base64.b64decode(b64_pdf)
        filename = f"Contract_{deal['brand_name'].replace(' ', '_')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error downloading deal contract: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/deals/{deal_id}/pay-milestone/{milestone_id}")
@limiter.limit("30/minute")
def pay_deal_milestone(
    deal_id: int, 
    milestone_id: int, 
    request: Request, 
    current_user_email: str = Depends(get_current_user),
    _credit_check: str = Depends(require_credits(CREDIT_COSTS['export'])),
    authorization: Optional[str] = Header(None)
):
    try:
        user_sb = get_user_supabase_client(authorization)
        
        # Confirm that current user owns the deal via user_sb client
        res_deal = user_sb.table("brand_deals").select("creator_id").eq("id", deal_id).execute()
        if not res_deal.data or res_deal.data[0]["creator_id"] != current_user_email:
            raise HTTPException(status_code=403, detail="Forbidden: You do not own this deal")
            
        res_m = user_sb.table("deal_payment_milestones").update({"paid_status": "paid"}).eq("id", milestone_id).eq("deal_id", deal_id).execute()
        return res_m.data[0] if res_m.data else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error marking milestone as paid: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/deals/run-reminders")
@limiter.limit("2/hour")
def run_milestone_reminders_manual(request: Request):
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret:
        logger.error("CRON_SECRET not configured - run-reminders blocked")
        raise HTTPException(status_code=500, detail="Cron configuration error")
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {cron_secret}":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        from cron_job import check_and_send_milestone_reminders
        emails_sent = check_and_send_milestone_reminders()
        return {"success": True, "emails_sent": emails_sent}
    except Exception as e:
        logger.error(f"Error running reminders manual job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/brand-deals/{user_email}")
@limiter.limit("30/minute")
def get_brand_deals_marketplace(
    user_email: str, 
    request: Request, 
    page: int = 1,
    limit: int = 50,
    current_user_email: str = Depends(require_auth)
):
    if user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You can only view your own brand deals")

    from plan_enforcement import PlanEnforcement
    from datetime import datetime, timezone, timedelta

    # Get user plan and tier config
    user_plan = PlanEnforcement.get_user_plan(user_email)
    tier_config = PlanEnforcement.BRAND_DEALS_CONFIG.get(user_plan, PlanEnforcement.BRAND_DEALS_CONFIG['free'])
    
    delay_hours = tier_config['delay_hours']
    max_deals = tier_config['max_deals']

    # Adjust pagination based on max_deals
    original_limit = limit
    if max_deals is not None:
        if (page - 1) * original_limit >= max_deals:
            limit = 0 # Page is beyond max deals
        elif page * original_limit > max_deals:
            limit = max_deals - (page - 1) * original_limit

    # Get user niche
    niche = "lifestyle"
    if supabase:
        try:
            res_user = supabase.table("creator_profiles").select("niche").eq("user_email", user_email).execute()
            if res_user.data:
                niche = res_user.data[0].get("niche", "lifestyle")
        except Exception as e:
            logger.exception(f"Error loading niche for brand deals marketplace user {user_email}: {e}")

    # Cache key includes plan and pagination to prevent poisoning
    cache_key = f"deals:{niche}:{user_plan}:{page}:{original_limit}"
    if standard_queue and standard_queue.connection:
        try:
            cached_data = standard_queue.connection.get(cache_key)
            if cached_data:
                logger.info(f"Serving brand deals from cache for key: {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.exception(f"Redis fetch error for deals: {e}")

    try:
        # 1. Fetch all deals from DB (both open and pending)
        deals = []
        if supabase and limit > 0:
            try:
                query = supabase.table("brand_deals").select("*")
                
                # Apply tier-gating delay
                if delay_hours > 0:
                    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=delay_hours)).isoformat()
                    query = query.lt("created_at", cutoff_time)
                
                # Apply ordering and pagination
                query = query.order("created_at", desc=True)
                offset = (page - 1) * original_limit
                query = query.range(offset, offset + limit - 1)
                
                res = query.execute()
                deals = res.data or []
            except Exception as e:
                logger.exception(f"Error fetching brand deals from DB: {e}")
        
        # 2. Fetch user's applications to see which ones they already applied for
        user_apps = []
        if supabase:
            try:
                res_apps = supabase.table("brand_deal_applications").select("*").eq("user_email", user_email).limit(100).execute()
                user_apps = res_apps.data or []
            except Exception as e:
                logger.exception(f"Error fetching user applications: {e}")

        applied_deal_ids = {app["deal_id"] for app in user_apps if "deal_id" in app}

        # Format deals to add "applied" status
        formatted_deals = []
        for deal in deals:
            # handle field names safely
            deal_id = deal.get("id")
            deal_data = {
                "id": deal_id,
                "brand_name": deal.get("brand_name"),
                "deal_amount": deal.get("deal_amount"),
                "commission_amount": deal.get("commission_amount") or (deal.get("deal_amount", 0) * 0.15),
                "status": deal.get("status") or "open",
                "details": deal.get("details"),
                "requirements": deal.get("requirements") or "Minimum 10k followers, niche: any, engagement rate > 3.0%",
                "applied": deal_id in applied_deal_ids
            }
            formatted_deals.append(deal_data)

        # 3. Compute stats for this user
        # Total Earnings: sum of completed/active deals for this creator
        total_earnings = 0
        active_deals = 0
        if supabase:
            try:
                res_my_deals = supabase.table("brand_deals").select("deal_amount, commission_amount, status").eq("creator_email", user_email).limit(100).execute()
                my_deals = res_my_deals.data or []
                for d in my_deals:
                    stat = d.get("status", "").lower()
                    amt = d.get("deal_amount", 0) - d.get("commission_amount", 0)
                    if stat in ["completed", "active"]:
                        total_earnings += amt
                    if stat == "active":
                        active_deals += 1
            except Exception as e:
                logger.exception(f"Error computing marketplace stats for {user_email}: {e}")

        stats = {
            "total_earnings": total_earnings,
            "active_partnerships": active_deals,
            "pending_applications": len(user_apps)
        }

        result = {
            "deals": formatted_deals,
            "stats": stats
        }
        
        # Cache brand deals list for 15 minutes
        if standard_queue and standard_queue.connection:
            try:
                standard_queue.connection.setex(cache_key, 900, json.dumps(result))
            except Exception as e:
                logger.error(f"Redis write error for deals: {e}")
                
        return result

    except Exception as e:
        logger.exception(f"Error in GET /api/brand-deals: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/collab-matches/{user_email}")
@limiter.limit("30/minute")
def get_collab_matches(user_email: str, request: Request, current_user_email: str = Depends(require_auth)):
    if user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access another user's collab matches")
    try:
        # Get user's profile to match niche
        user_niche = "fashion"
        if supabase:
            try:
                res_user = supabase.table("creator_profiles").select("niche").eq("user_email", user_email).execute()
                if res_user.data:
                    user_niche = res_user.data[0].get("niche", "fashion")
            except Exception as e:
                logger.exception(f"Error loading collab niche for {user_email}: {e}")


        # Fetch other profiles
        profiles = []
        if supabase:
            try:
                res_prof = supabase.table("creator_profiles").select("*").neq("user_email", user_email).eq("is_active", True).limit(100).execute()
                profiles = res_prof.data or []
            except Exception as e:
                logger.exception(f"Error fetching collab profiles for {user_email}: {e}")



        # Fetch collab requests sent by this user
        sent_requests = set()
        if supabase:
            try:
                res_reqs = supabase.table("collab_requests").select("to_email").eq("from_email", user_email).limit(100).execute()
                sent_requests = {r["to_email"] for r in res_reqs.data or [] if "to_email" in r}
            except Exception as e:
                logger.exception(f"Error fetching sent collab requests for {user_email}: {e}")

        # Calculate compatibility score for each profile
        matches = []
        for p in profiles:
            p_niche = (p.get("niche") or "fashion").lower()
            u_niche = user_niche.lower()

            # compatibility score calculation
            if p_niche == u_niche:
                score = 95
            elif (p_niche == "dance" and u_niche == "fitness") or (p_niche == "fitness" and u_niche == "dance"):
                score = 89
            elif (p_niche == "fashion" and u_niche == "travel") or (p_niche == "travel" and u_niche == "fashion"):
                score = 87
            elif (p_niche == "dance" and u_niche == "fashion") or (p_niche == "fashion" and u_niche == "dance"):
                score = 85
            else:
                score = 73

            matches.append({
                "instagram_username": p.get("instagram_username"),
                "user_email": p.get("user_email"),
                "niche": p.get("niche"),
                "followers": p.get("followers"),
                "engagement_rate": p.get("engagement_rate"),
                "trend_score": p.get("trend_score"),
                "compatibility_score": score,
                "request_sent": p.get("user_email") in sent_requests
            })

        # Sort matches by compatibility score descending
        matches.sort(key=lambda x: x["compatibility_score"], desc=True)
        return matches

    except Exception as e:
        logger.error(f"Error in GET /api/collab-matches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/creator/feedback")
@limiter.limit("20/minute")
def submit_creator_feedback(
    request: Request,
    req: FeedbackRequest,
    current_user_email: str = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        user_sb = get_user_supabase_client(authorization)
        user_sb.table("creator_feedback").insert({
            "creator_id": current_user_email,
            "deal_id": req.deal_id,
            "rating": req.rating,
            "comment": req.comment
        }).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error submitting creator feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/creator/metrics")
@limiter.limit("30/minute")
def get_creator_metrics(
    request: Request,
    days_back: int = 30,
    current_user: str = Depends(require_auth)
):
    """Get comprehensive metrics for a creator."""
    if not CreatorAnalyticsEngine:
        raise HTTPException(status_code=500, detail="Creator analytics engine not configured.")
    
    try:
        analytics = CreatorAnalyticsEngine()
        metrics = analytics.get_creator_metrics(current_user, days_back=days_back)
        
        return {
            'creator_email': metrics.creator_email,
            'total_reels_analyzed': metrics.total_reels_analyzed,
            'total_views': metrics.total_views,
            'total_likes': metrics.total_likes,
            'total_comments': metrics.total_comments,
            'total_shares': metrics.total_shares,
            'avg_engagement_rate': metrics.avg_engagement_rate,
            'avg_velocity_score': metrics.avg_velocity_score,
            'top_performing_content': metrics.top_performing_content,
            'content_categories': metrics.content_categories,
            'trend_adoption_rate': metrics.trend_adoption_rate,
            'viral_content_count': metrics.viral_content_count,
            'growth_trend': metrics.growth_trend,
            'peak_performance_hours': metrics.peak_performance_hours,
            'optimal_posting_times': metrics.optimal_posting_times,
            'is_connected': getattr(metrics, 'is_connected', True)
        }
    except Exception as e:
        logger.exception(f"Error getting creator metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get creator metrics")


@router.get("/api/creator/trend-adoption")
@limiter.limit("30/minute")
def get_trend_adoption_history(
    request: Request,
    days_back: int = 90,
    current_user: str = Depends(require_auth)
):
    """Get creator's trend adoption history."""
    if not CreatorAnalyticsEngine:
        raise HTTPException(status_code=500, detail="Creator analytics engine not configured.")
    
    try:
        analytics = CreatorAnalyticsEngine()
        adoption = analytics.get_trend_adoption_history(current_user, days_back=days_back)
        
        return {
            'trend_adoption': [
                {
                    'trend_id': ad.trend_id,
                    'trend_name': ad.trend_name,
                    'adoption_date': ad.adoption_date.isoformat(),
                    'content_created': ad.content_created,
                    'avg_performance': ad.avg_performance,
                    'success_score': ad.success_score,
                    'timing_score': ad.timing_score,
                    'category_fit': ad.category_fit
                }
                for ad in adoption
            ],
            'total_adoptions': len(adoption)
        }
    except Exception as e:
        logger.exception(f"Error getting trend adoption history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend adoption history")


@router.get("/api/creator/performance-over-time")
@limiter.limit("30/minute")
def get_content_performance_over_time(
    request: Request,
    days_back: int = 30,
    current_user: str = Depends(require_auth)
):
    """Get content performance data over time for charts."""
    if not CreatorAnalyticsEngine:
        raise HTTPException(status_code=500, detail="Creator analytics engine not configured.")
    
    try:
        analytics = CreatorAnalyticsEngine()
        performance = analytics.get_content_performance_over_time(current_user, days_back=days_back)
        return {
            'performance_data': performance,
            'days_analyzed': days_back
        }
    except Exception as e:
        logger.exception(f"Error getting performance over time: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance data")


@router.get("/api/creator/recommendations")
@limiter.limit("30/minute")
def get_success_recommendations(
    request: Request,
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("advanced_analytics"))
):
    """Get personalized success recommendations for a creator."""
    if not CreatorAnalyticsEngine:
        raise HTTPException(status_code=500, detail="Creator analytics engine not configured.")
    
    try:
        analytics = CreatorAnalyticsEngine()
        recommendations = analytics.get_success_recommendations(current_user)
        return {
            'recommendations': recommendations,
            'total_recommendations': len(recommendations)
        }
    except Exception as e:
        logger.exception(f"Error getting success recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


@router.post("/api/user/performance/store")
@limiter.limit("10/minute")
def store_user_performance(
    request: Request,
    user_email: str,
    instagram_data: dict,
    current_user: str = Depends(require_auth)
):
    """Store user performance data from Instagram."""
    if user_email != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: cannot store performance data for another user")
    if not UserPerformanceTracker:
        raise HTTPException(status_code=500, detail="User performance tracker not configured.")
    
    try:
        result = UserPerformanceTracker.store_user_performance(user_email, instagram_data)
        return result
    except Exception as e:
        logger.exception(f"Error storing user performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to store user performance")


@router.get("/api/user/performance")
@limiter.limit("30/minute")
def get_user_performance(
    request: Request,
    user_email: str,
    days: int = 30,
    current_user: str = Depends(require_auth)
):
    """Get user performance data. UNVERIFIED — blocked on P-DB-7."""
    if user_email != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: cannot read another user's performance data")
    if not UserPerformanceTracker:
        raise HTTPException(status_code=500, detail="User performance tracker not configured.")
    
    try:
        performance = UserPerformanceTracker.get_user_performance(user_email, days)
        return performance
    except Exception as e:
        logger.exception(f"Error getting user performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user performance")


@router.get("/api/user/performance/growth")
@limiter.limit("30/minute")
def get_user_growth_rate(
    request: Request,
    user_email: str,
    days: int = 30,
    current_user: str = Depends(require_auth)
):
    """Get user growth rate. UNVERIFIED — blocked on P-DB-7."""
    if user_email != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: cannot read another user's growth data")
    if not UserPerformanceTracker:
        raise HTTPException(status_code=500, detail="User performance tracker not configured.")
    
    try:
        growth = UserPerformanceTracker.calculate_growth_rate(user_email, days)
        return growth
    except Exception as e:
        logger.exception(f"Error calculating growth rate: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate growth rate")


@router.get("/api/user/performance/top-media")
@limiter.limit("30/minute")
def get_user_top_media(
    request: Request,
    user_email: str,
    limit: int = 5,
    current_user: str = Depends(require_auth)
):
    """Get user's top performing media. UNVERIFIED — blocked on P-DB-7."""
    if user_email != current_user:
        raise HTTPException(status_code=403, detail="Forbidden: cannot read another user's top media")
    if not UserPerformanceTracker:
        raise HTTPException(status_code=500, detail="User performance tracker not configured.")
    
    try:
        top_media = UserPerformanceTracker.get_top_performing_media(user_email, limit)
        return top_media
    except Exception as e:
        logger.exception(f"Error getting top media: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top media")


