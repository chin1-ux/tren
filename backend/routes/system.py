from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from schemas import *

router = APIRouter()

@router.get("/api/proof", tags=["Proof"])
@limiter.limit("10/minute")
def get_proof_data(request: Request):
    """Public endpoint returning early detection proof — trends detected before peaking."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not connected")
    try:
        res = supabase.table("trends").select(
            "id, audio_title, audio_artist, status, first_detected_at, "
            "velocity_avg, niche_tag, language"
        ).eq("is_seed_data", False).in_("status", ["rising", "peaked", "expired"]).not_.is_(
            "first_detected_at", "null"
        ).order("first_detected_at", desc=True).limit(20).execute()
        trends = res.data or []
        proof_items = []
        for t in trends:
            detected = t.get("first_detected_at")
            peak = None # not stored currently
            hours_early = None
            if detected and peak:
                try:
                    from datetime import datetime
                    d = datetime.fromisoformat(detected.replace("Z", "+00:00"))
                    p = datetime.fromisoformat(peak.replace("Z", "+00:00"))
                    hours_early = round((p - d).total_seconds() / 3600, 1)
                except Exception:
                    pass
            proof_items.append({
                "trend_id": t.get("id"),
                "title": t.get("audio_title"),
                "artist": t.get("audio_artist"),
                "audio_name": t.get("audio_title"),
                "status": t.get("status"),
                "detected_at": detected,
                "peak_at": peak,
                "hours_early": hours_early,
                "velocity_score": t.get("velocity_avg"),
                "niche": t.get("niche_tag"),
                "language": t.get("language"),
            })
        return {"proof": proof_items, "count": len(proof_items)}
    except Exception as e:
        logger.exception(f"Error fetching proof data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch proof data")




@router.get("/health")
def health_check():
    # Check Database connection
    db_status = "unconfigured"
    if supabase:
        try:
            # Quick query to test connection
            supabase.table("trends").select("id").limit(1).execute()
            db_status = "healthy"
        except Exception as e:
            db_status = "unhealthy"
            
    # Check Disk space
    try:
        total, used, free = shutil.disk_usage("/")
        disk_free_gb = free / (2**30)
        disk_status = "healthy" if disk_free_gb > 1.0 else "low_space"
    except Exception as e:
        logger.exception(f"Disk health check failed: {e}")
        total, used, free = 0, 0, 0
        disk_free_gb = 0
        disk_status = "unknown"
        
    # Check Memory usage (using standard library or system info safely)
    mem_status = "unknown"
    mem_percent = 0.0
    try:
        if os.name == 'posix':
            # Linux memory checks
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            mem_total = 0
            mem_free = 0
            for line in lines:
                if 'MemTotal' in line:
                    mem_total = int(line.split()[1])
                elif 'MemFree' in line:
                    mem_free = int(line.split()[1])
            if mem_total > 0:
                mem_percent = ((mem_total - mem_free) / mem_total) * 100
                mem_status = "healthy" if mem_percent < 90 else "high_usage"
        elif os.name == 'nt':
            # Windows memory checks using built-in system command or fallback
            mem_status = "healthy"
    except Exception as e:
        logger.exception(f"Memory health check failed: {e}")

    return {
        "status": "ok",
        "version": "2.0",
        "product": "Trendrop India",
        "database": db_status,
        "disk": {
            "status": disk_status,
            "free_gb": round(disk_free_gb, 2)
        },
        "memory": {
            "status": mem_status,
            "used_percent": round(mem_percent, 1)
        }
    }


@router.post("/api/subscribe")
@limiter.limit("5/hour")
def subscribe(request: Request, req: SubscribeRequest):
    """Save user subscription to Supabase users table and return auth_token."""
    try:
        # Check if user already exists
        res = supabase.table("users").select("auth_token").eq("email", req.email).execute()
        token = None
        if res.data and len(res.data) > 0:
            token = res.data[0].get("auth_token")

        if not token:
            token = secrets.token_hex(16)

        user_data = {
            "email": req.email,
            "niche": req.niche,
            "language_preference": req.language,
            "auth_token": token
        }
        supabase.table("users").upsert(user_data, on_conflict="email").execute()
        return {"success": True, "message": "You are subscribed!", "auth_token": token, "email": req.email}
    except Exception as e:
        logger.error(f"Subscribe failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/payment/create-order")
@limiter.limit("10/minute")
def create_payment_order(request: Request, req: CreateOrderRequest, current_user: str = Depends(require_auth)):
    """
    Create a Razorpay order for the Pro plan (₹499/month).
    Returns order_id, amount, currency, and key_id for the Razorpay checkout widget.
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured. Contact support.")

    try:
        import razorpay  # type: ignore
    except ImportError:
        raise HTTPException(status_code=503, detail="Razorpay library not installed on server.")

    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount":   PRO_AMOUNT_PAISE,
            "currency": PRO_CURRENCY,
            "receipt":  f"trendrop_pro_{req.email[:30]}",
            "notes": {
                "email": req.email,
                "plan":  "pro",
            }
        })
        logger.info(f"Razorpay order created: {order['id']} for {req.email}")
        return {
            "order_id": order["id"],
            "amount":   order["amount"],
            "currency": order["currency"],
            "key_id":   RAZORPAY_KEY_ID,
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create payment order. Please try again.")


@router.post("/api/payment/webhook")
@limiter.limit("20/minute")
def payment_webhook(request: Request, req: PaymentWebhookRequest):
    """
    Verify Razorpay payment signature and upgrade the user plan to 'pro'.
    This is the ONLY server-side path that grants Pro access.
    The signature check prevents any client-side forgery.
    """
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    # ── Signature verification (HMAC-SHA256) ───────────────────────────────────
    payload      = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    expected_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, req.razorpay_signature):
        logger.warning(f"Invalid Razorpay signature for order {req.razorpay_order_id} / email {req.email}")
        raise HTTPException(status_code=400, detail="Payment verification failed — invalid signature.")

    # ── Signature valid — upgrade plan ─────────────────────────────────────────
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured.")

    try:
        # ── C5 Fix: Prevent Replay Attacks (Enforce payment uniqueness) ────────
        existing_res = supabase.table("users").select("email").eq("razorpay_payment_id", req.razorpay_payment_id).limit(1).execute()
        if existing_res.data:
            existing_email = existing_res.data[0].get("email")
            if existing_email != req.email:
                logger.warning(f"Replay attack: payment {req.razorpay_payment_id} already claimed by {existing_email}")
                raise HTTPException(status_code=400, detail="Payment has already been processed for another account.")
            return {"success": True, "plan": "pro", "message": "Welcome to Pro!"}
            
        # Read old balance before upgrade (for credit_transactions delta)
        old_user = supabase.table("users").select("id, credits_remaining").eq("email", req.email).single().execute()
        old_balance = old_user.data.get("credits_remaining", 0) if old_user.data else 0
        user_id = old_user.data["id"] if old_user.data else None

        # Upgrade plan and grant 1000 credits
        supabase.table("users").upsert(
            {
                "email": req.email,
                "plan":  "pro",
                "credits_remaining": 1000,
                "credits_used_this_month": 0,
                "razorpay_payment_id": req.razorpay_payment_id,
                "razorpay_order_id":   req.razorpay_order_id,
            },
            on_conflict="email"
        ).execute()
        
        # Log the upgrade credit grant (delta = 1000 - old_balance)
        if user_id:
            delta = 1000 - old_balance
            supabase.table("credit_transactions").insert({
                "user_id": user_id,
                "amount": delta,
                "reason": "plan_upgrade",
                "endpoint": "payment/webhook",
                "balance_after": 1000,
            }).execute()
        
        invalidate_cached_user_profile(req.email)
        
        logger.info(f"Plan upgraded to pro for {req.email} | payment {req.razorpay_payment_id}")
        return {"success": True, "plan": "pro", "message": "Welcome to Pro!"}
    except HTTPException:
        raise  # replay rejection and other explicit 4xx/5xx must propagate
    except Exception as e:
        logger.error(f"Plan upgrade DB write failed for {req.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Payment verified but plan upgrade failed. Contact support.")


@router.get("/api/reels/feed")
@limiter.limit("30/minute")
def get_user_reels_feed(
    request: Request, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("unlimited_trends")),
    _usage_log: str = Depends(log_endpoint_usage("unlimited_trends"))
):
    """Fetch reels matching the user's preferred languages. Pro/Agency feature only."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        import psycopg2
        db_url = os.getenv("SUPABASE_DB_URL")
        languages = ['english', 'hindi']
        
        if current_user and current_user != "guest@trendrop.app":
            try:
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute("""
                    SELECT up.languages
                    FROM user_preferences up
                    JOIN auth.users u ON up.user_id = u.id
                    WHERE u.email = %s
                """, (current_user,))
                row = cur.fetchone()
                if row and row[0]:
                    languages = row[0]
            except Exception as e:
                logger.error(f"Error getting user preferences: {e}")
            finally:
                if 'cur' in locals(): cur.close()
                if 'conn' in locals(): conn.close()

        q = supabase.table("reels") \
            .select("*") \
            .not_.is_("audio_title", "null") \
            .neq("audio_title", "Original audio") \
            .in_("caption_language", languages) \
            .order("created_at", desc=True) \
            .limit(50)
        res = q.execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in getUserFeed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/reels/cross-cultural")
@limiter.limit("30/minute")
def get_cross_cultural_reels(
    request: Request, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("india_features")),
    _usage_log: str = Depends(log_endpoint_usage("india_features"))
):
    """Fetch global trends entering India — is_cross_cultural=True, origin != IN, india_saturation < 40%. Pro/Agency feature only."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        from datetime import datetime, timedelta, timezone
        threshold = (datetime.now(timezone.utc) - timedelta(hours=60)).isoformat()
        
        q = supabase.table("reels") \
            .select("*") \
            .eq("is_cross_cultural", True) \
            .not_.is_("audio_title", "null") \
            .neq("audio_title", "Original audio") \
            .not_.is_("owner_username", "null") \
            .neq("owner_username", "") \
            .not_.is_("reel_id", "null") \
            .neq("reel_id", "") \
            .in_("caption_language", ["en", "english"]) \
            .neq("trend_origin", "IN") \
            .neq("trend_origin", "in") \
            .neq("trend_origin", "unknown") \
            .neq("trend_origin", "UNKNOWN") \
            .not_.is_("trend_origin", "null") \
            .gt("velocity_score", 0.3) \
            .gt("view_count", 2000) \
            .gte("scraped_at", threshold) \
            .lt("india_saturation_pct", 40) \
            .order("scraped_at", desc=True) \
            .limit(10)
        res = q.execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error in getCrossCulturalTrends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/feedback")
@limiter.limit("20/minute")
def submit_feedback(request: Request, req: FeedbackRequest, current_user_email: str = Depends(require_auth)):
    """
    Creator feedback on a trend: too_late | too_early | perfect | stale.
    Stored in trend_feedback table for future ML training signal.
    """
    try:
        feedback_data = {
            "trend_id": req.trend_id,
            "feedback_type": req.feedback_type,
            "comment": req.comment,
            "user_email": current_user_email,
        }
        supabase.table("trend_feedback").insert(feedback_data).execute()
        return {"success": True, "message": "Feedback received. Thank you!"}
    except Exception as e:
        logger.error(f"Feedback save failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/job-status/{job_id}")
@limiter.limit("60/minute")
def get_job_status(request: Request, job_id: str, current_user: str = Depends(require_auth)):
    try:
        if not job_id.isdigit():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")
        res = supabase.table("jobs").select("*").eq("id", int(job_id)).execute()
        job = res.data[0] if res.data else None
        if not job or job.get("user_email") != current_user:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return {
            "status": job.get("status"),
            "progress": job.get("progress"),
            "output_url": job.get("output_url"),
            "error_message": job.get("error_message")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/reel-status/{job_id}")
@limiter.limit("60/minute")
def get_reel_status(request: Request, job_id: str, current_user: str = Depends(require_auth)):
    return get_job_status(request, job_id, current_user)


@router.post("/api/run-scraper")
@limiter.limit("2/minute")
def trigger_scraper(request: Request, background_tasks: BackgroundTasks, admin_info: dict = Depends(require_admin)):
    """Manually trigger the full scraper + trend detection pipeline. Protected by Admin API Key."""
    try:
        job_id = create_job_record("scraper", "admin@trendrop.ai", {})
        background_tasks.add_task(run_scrapers_background, job_id)
        return {"status": "pending", "job_id": job_id, "message": "Pipeline started in background"}
    except Exception as e:
        logger.error(f"Scraper trigger failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/apply-deal")
@limiter.limit("15/minute")
def apply_brand_deal(req: ApplyDealRequest, request: Request, current_user_email: str = Depends(require_auth)):
    if current_user_email != "guest@trendrop.app" and req.user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot apply for a brand deal on behalf of another user")
    try:
        if supabase:
            try:
                app_data = {
                    "deal_id": req.deal_id,
                    "user_email": req.user_email,
                    "pitch": req.pitch
                }
                supabase.table("brand_deal_applications").insert(app_data).execute()
                return {"success": True, "message": "Application submitted successfully!"}
            except Exception as e:
                logger.exception(f"Failed to submit application: {e}")
                raise HTTPException(status_code=500, detail="Database submission failed")
        else:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable. Please try again.")
    except Exception as e:
        logger.exception(f"Error in POST /api/apply-deal: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/send-collab-request")
@limiter.limit("15/minute")
def send_collab_request(req: CollabRequest, request: Request, current_user_email: str = Depends(require_auth)):
    if current_user_email != "guest@trendrop.app" and req.from_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot send collab requests on behalf of another user")
    try:
        if supabase:
            try:
                req_data = {
                    "from_email": req.from_email,
                    "to_email": req.to_email,
                    "message": req.message
                }
                supabase.table("collab_requests").insert(req_data).execute()
                return {"success": True, "message": "Collab request sent successfully!"}
            except Exception as e:
                logger.error(f"Failed to save collab request: {e}")
                raise HTTPException(status_code=500, detail="Database request submission failed")
        else:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable. Please try again.")
    except Exception as e:
        logger.error(f"Error in POST /api/send-collab-request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/analytics/log")
@limiter.limit("60/minute")
def log_analytics_event(
    request: Request,
    req: LogEventRequest,
    current_user_email: str = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    event_name = req.event_name.strip()
    if not event_name:
        raise HTTPException(status_code=422, detail="event_name is required")
    if len(event_name) > 128:
        raise HTTPException(status_code=422, detail="event_name is too long")
    try:
        user_sb = get_user_supabase_client(authorization)
        user_sb.table("analytics_events").insert({
            "user_id": current_user_email if current_user_email != "guest@trendrop.app" else None,
            "event_name": event_name
        }).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error logging event {event_name} for user {current_user_email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to log analytics event")


@router.get("/api/events/active")
@limiter.limit("60/minute")
def get_active_events(
    request: Request,
    days_ahead: int = 30,
    days_behind: int = 7,
    current_user: str = Depends(get_current_user)
):
    """Get active global events that could impact social media content."""
    if not EventMonitor:
        raise HTTPException(status_code=500, detail="Event monitoring system not configured.")
    
    try:
        monitor = EventMonitor()
        events = monitor.get_active_events(days_ahead=days_ahead, days_behind=days_behind)
        
        return {
            'events': [
                {
                    'id': event.id,
                    'name': event.name,
                    'type': event.event_type.value,
                    'impact': event.impact.value,
                    'start_date': event.start_date.isoformat(),
                    'end_date': event.end_date.isoformat(),
                    'hashtags': event.hashtags,
                    'content_themes': event.content_themes,
                    'creator_opportunities': event.creator_opportunities,
                    'target_audiences': event.target_audiences,
                    'platform_relevance': event.platform_relevance,
                    'viral_potential': event.viral_potential,
                    'trending_now': event.trending_now,
                    'estimated_creator_participation': event.estimated_creator_participation,
                    'days_until_start': (event.start_date - datetime.now(timezone.utc)).days
                }
                for event in events
            ],
            'total_events': len(events),
            'query_params': {'days_ahead': days_ahead, 'days_behind': days_behind}
        }
    except Exception as e:
        logger.exception(f"Error getting active events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active events")


@router.get("/api/events/{event_id}/opportunities")
@limiter.limit("30/minute")
def get_event_opportunities(
    request: Request,
    event_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get detailed creator opportunities for a specific event."""
    if not EventMonitor:
        raise HTTPException(status_code=500, detail="Event monitoring system not configured.")
    
    try:
        monitor = EventMonitor()
        opportunities = monitor.get_creator_opportunities_for_event(event_id)
        return opportunities
    except Exception as e:
        logger.exception(f"Error getting event opportunities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get event opportunities")


@router.get("/api/events/hashtag-spikes")
@limiter.limit("30/minute")
def detect_hashtag_spikes(
    request: Request,
    hours_window: int = 24,
    current_user: str = Depends(get_current_user)
):
    """Detect sudden spikes in hashtag usage that might indicate trending events."""
    if not EventMonitor:
        raise HTTPException(status_code=500, detail="Event monitoring system not configured.")
    
    try:
        monitor = EventMonitor()
        spikes = monitor.detect_event_hashtag_spikes(hours_window=hours_window)
        return {
            'spikes': spikes,
            'hours_window': hours_window,
            'total_spikes': len(spikes)
        }
    except Exception as e:
        logger.exception(f"Error detecting hashtag spikes: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect hashtag spikes")


@router.get("/api/early-detection/trends")
@limiter.limit("30/minute")
def get_early_detection_trends(
    request: Request,
    limit: int = 10,
    current_user: str = Depends(require_feature("early_detection"))
):
    """Get trends with high early detection scores (about to go viral)."""
    if not EarlyTrendDetector:
        raise HTTPException(status_code=500, detail="Early trend detection not configured.")
    
    try:
        trends = EarlyTrendDetector.get_early_detection_trends(limit)
        return {
            'trends': trends,
            'total': len(trends)
        }
    except Exception as e:
        logger.exception(f"Error getting early detection trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get early detection trends")


@router.get("/api/early-detection/predict/{trend_id}")
@limiter.limit("30/minute")
def predict_trend_viral_potential(
    request: Request,
    trend_id: int,
    current_user: str = Depends(require_feature("early_detection"))
):
    """Predict viral potential of a specific trend."""
    if not EarlyTrendDetector:
        raise HTTPException(status_code=500, detail="Early trend detection not configured.")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
    
    try:
        # Get trend data
        res = supabase.table('trends') \
            .select('*') \
            .eq('is_seed_data', False) \
            .eq('id', trend_id) \
            .single() \
            .execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Trend not found")
        
        trend_data = res.data
        prediction = EarlyTrendDetector.predict_viral_potential(trend_data)
        
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error predicting trend viral potential: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict viral potential")


@router.post("/api/virality/predict")
@limiter.limit("10/minute")
def predict_content_virality(
    request: Request,
    content_data: dict,
    trend_id: int,
    creator_email: Optional[str] = None,
    current_user: str = Depends(require_auth)
):
    """Predict virality of content before posting."""
    if not ViralityPredictor:
        raise HTTPException(status_code=500, detail="Virality prediction not configured.")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
    
    try:
        # Get trend data
        res = supabase.table('trends') \
            .select('*') \
            .eq('is_seed_data', False) \
            .eq('id', trend_id) \
            .single() \
            .execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Trend not found")
        
        trend_data = res.data
        prediction = ViralityPredictor.predict_content_virality(content_data, trend_data, creator_email)
        
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error predicting content virality: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict content virality")


@router.get("/api/virality/improvements")
@limiter.limit("30/minute")
def get_virality_improvements(
    request: Request,
    content_data: dict,
    trend_id: int,
    current_user: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))
):
    """Get improvement suggestions to increase virality."""
    if not ViralityPredictor:
        raise HTTPException(status_code=500, detail="Virality prediction not configured.")
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
    
    try:
        # Get trend data
        res = supabase.table('trends') \
            .select('*') \
            .eq('is_seed_data', False) \
            .eq('id', trend_id) \
            .single() \
            .execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Trend not found")
        
        trend_data = res.data
        suggestions = ViralityPredictor.get_improvement_suggestions(content_data, trend_data)
        
        return {
            'suggestions': suggestions,
            'total': len(suggestions)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting virality improvements: {e}")
        raise HTTPException(status_code=500, detail="Failed to get improvement suggestions")


