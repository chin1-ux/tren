import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
import resend

# Configure logging
try:
    logging.basicConfig(
        filename="alert_system.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception as _log_cfg_err:
    # File-based log handler unavailable (e.g. read-only fs on Vercel).
    # Fall back to stdout so the error is still surfaced.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.warning(f"alert_system: could not open log file, falling back to stdout: {_log_cfg_err}")

class AlertSystem:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Fallback to backend/.env if not loaded (e.g. when run from workspace root)
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)
                
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        self.resend_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "alerts@trendrop.ai")
        
        if not self.supabase_url or not self.supabase_key:
            logging.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing.")
            raise ValueError("Supabase credentials are missing from .env")
        if not self.resend_key:
            logging.warning("RESEND_API_KEY is missing — email alerts disabled.")
            
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize Resend
        resend.api_key = self.resend_key

    def send_trend_alerts(self, trend_ids: list):
        """
        STEP 1 - Fetch trend data from Supabase
        STEP 2 - Fetch matching users by niche/language
        STEP 3 - Build email with urgency tier + caption kit
        STEP 4 - Send via Resend
        """
        logging.info(f"Starting alert run for trend_ids: {trend_ids}")
        if not trend_ids:
            logging.info("No trend_ids provided. Exiting.")
            return
        if not self.resend_key:
            logging.warning("RESEND_API_KEY not set — skipping email alerts.")
            return 0

        try:
            # Load user preferences instead of just users table
            prefs_res = self.supabase.table("user_preferences").select("*").execute()
            user_prefs = prefs_res.data or []
            logging.info(f"Loaded {len(user_prefs)} user preferences from Supabase.")
        except Exception as e:
            logging.error(f"Failed to fetch user_preferences: {e}", exc_info=True)
            return

        total_emails_sent = 0

        for trend_id in trend_ids:
            try:
                trend_res = self.supabase.table("trends").select("*").eq("id", trend_id).execute()
                if not trend_res.data:
                    # Maybe it's a content_trend
                    ct_res = self.supabase.table("content_trends").select("*").eq("id", trend_id).execute()
                    if not ct_res.data:
                        logging.warning(f"Trend {trend_id} not found in trends or content_trends. Skipping.")
                        continue
                    trend = ct_res.data[0]
                else:
                    trend = trend_res.data[0]

                trend_type = trend.get("trend_type", "audio")
                audio_title = trend.get("trend_name") or trend.get("audio_title") or "Unknown Title"
                audio_artist = trend.get("audio_artist", "")
                is_dance = trend.get("is_dance", False)
                window_hours = trend.get("window_hours_remaining", 24)
                velocity_avg = trend.get("velocity_avg", 1.0)
                status = trend.get("status", "rising")
                saturation_score = trend.get("saturation_score", 0.0)
                niche_relevance = trend.get("niche_relevance", {})
                
                # Niche-specific trigger logic variables
                viral_potential = trend.get("confidence", 0) if trend_type != "audio" else 0

                # Fetch cached caption kit if available
                caption_kit = None
                try:
                    cap_res = self.supabase.table("trend_captions") \
                        .select("caption_data") \
                        .eq("trend_id", trend_id) \
                        .execute()
                    if cap_res.data:
                        caption_kit = cap_res.data[0].get("caption_data")
                except Exception as ce:
                    logging.warning(f"Could not fetch caption kit for trend {trend_id}: {ce}")

                # Match users based on D1 triggers
                matching_users = []
                for pref in user_prefs:
                    user_niches = pref.get("niches", [])
                    user_state = pref.get("state", "").lower()
                    
                    if not user_niches:
                        user_niches = ["all"]
                        
                    is_match = False
                    urgency_prefix = "🔥 Trending"
                    
                    for niche in user_niches:
                        # 1. Audio < 15% saturation in user's niche
                        if trend_type == "audio" and saturation_score < 0.15:
                            # If audio is relevant to niche or they accept all
                            if niche == "all" or niche_relevance.get(niche, 0) > 0.2:
                                is_match = True
                                urgency_prefix = "🚨 EARLY SIGNAL"
                                break
                                
                        # 2. News event viral_potential > 70 for user's niche
                        if trend_type == "news_event" and viral_potential > 70:
                            if niche == "all" or niche_relevance.get(niche, 0) > 0.4:
                                is_match = True
                                urgency_prefix = "🚨 BREAKING NEWS"
                                break
                                
                        # 3. Cultural event 3 days out in user's state/region
                        if trend_type == "predictable_event":
                            # We check window_hours_remaining roughly ~72 hours (3 days)
                            if window_hours <= 72 and window_hours > 0:
                                # For regional logic we assume trend text or niche relevance targets it
                                if niche == "all" or niche_relevance.get(niche, 0) > 0.3:
                                    is_match = True
                                    urgency_prefix = "📅 UPCOMING FESTIVAL"
                                    break
                                    
                        # 4. Format trend spreading into user's niche
                        if trend_type == "format" and niche_relevance.get(niche, 0) > 0.6:
                            is_match = True
                            urgency_prefix = "⚡ EARLY MOVER FORMAT"
                            break

                    if is_match:
                        matching_users.append({"email": pref.get("email"), "urgency": urgency_prefix})

                logging.info(f"Trend '{audio_title}' matched {len(matching_users)} users")

                for user in matching_users:
                    user_email = user.get("email")
                    urgency_prefix = user.get("urgency")
                    if not user_email:
                        continue
                        
                    subject = f"{urgency_prefix}: {audio_title} — Generate your reel now!"

                    html_body = self._build_email_html(
                        trend, is_dance, trend_id, caption_kit, urgency_prefix, saturation_score
                    )
                    try:
                        resend.Emails.send({
                            "from": self.from_email,
                            "to": user_email,
                            "subject": subject,
                            "html": html_body
                        })
                        total_emails_sent += 1
                        logging.info(f"Email sent to {user_email}")
                    except Exception as resend_err:
                        logging.error(f"Resend error to {user_email}: {resend_err}", exc_info=True)
                        continue

            except Exception as trend_err:
                logging.error(f"Error processing trend {trend_id}: {trend_err}", exc_info=True)
                continue

        logging.info(f"Alert run complete. Emails sent: {total_emails_sent}")
        print(f"Total emails sent: {total_emails_sent}")
        return total_emails_sent

    def _build_email_html(
        self, trend: dict, is_dance: bool, trend_id: int,
        caption_kit: dict = None, urgency_prefix: str = "🔥 Trending",
        saturation_score: float = 0.0
    ) -> str:
        audio_title = trend.get("audio_title", "Unknown Title")
        audio_artist = trend.get("audio_artist", "Unknown Artist")
        velocity_avg = trend.get("velocity_avg", 1.0)
        window_hours = trend.get("window_hours_remaining", 24)
        content_type = trend.get("content_type") or "trend"
        language = trend.get("language")
        ideal_content_description = trend.get("ideal_content_description", "")
        camera_style = trend.get("camera_style", "handheld")
        edit_style = trend.get("edit_style", "fast_cuts")
        text_overlay_template = trend.get("text_overlay_template")
        why_this_works = trend.get("why_this_works", "")
        audio_cue_second = trend.get("audio_cue_second")
        optimal_post_hour = trend.get("optimal_post_hour_ist")
        best_platform = trend.get("best_platform_first", "instagram")
        status = trend.get("status", "rising")

        # Urgency banner color
        if "BREAKING" in urgency_prefix:
            urgency_color = "#ff006e"
            urgency_bg = "#ffe8f5"
        elif "HOT" in urgency_prefix:
            urgency_color = "#E63946"
            urgency_bg = "#ffe8e8"
        else:
            urgency_color = "#f4a261"
            urgency_bg = "#fff5ea"

        # Saturation message
        sat_pct = int(saturation_score * 100)
        if sat_pct < 20:
            sat_text = f"Only {sat_pct}% saturated — you are VERY EARLY on this trend!"
            sat_color = "#155724"
            sat_bg = "#d4edda"
        elif sat_pct < 50:
            sat_text = f"{sat_pct}% saturated — still a great time to post."
            sat_color = "#856404"
            sat_bg = "#fff3cd"
        else:
            sat_text = f"{sat_pct}% saturated — post in the next {window_hours}h before it peaks."
            sat_color = "#721c24"
            sat_bg = "#f8d7da"

        # Language badge
        lang_badge = ""
        if language and language.lower() not in ["en", "english"]:
            lang_badge = f'<span style="background:#f0f0f0;color:#333;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;">🌍 {language.upper()}</span>'

        # Caption kit section
        caption_section = ""
        if caption_kit and caption_kit.get("captions"):
            top_caption = caption_kit["captions"][0].get("text", "")
            hashtag_str = " ".join(
                f"#{h.lstrip('#')}" for h in (caption_kit.get("hashtags") or [])[:10]
            )
            audio_cue_text = caption_kit.get("audio_cue", "Start filming from the first chorus")
            caption_section = f"""
            <div style="background:#f0f7ff;border-left:4px solid #007bff;padding:16px;margin:20px 0;border-radius:4px;">
                <h4 style="margin:0 0 8px;font-size:14px;font-weight:bold;color:#0d47a1;">📋 AI Caption Kit</h4>
                <p style="margin:4px 0;font-size:13px;color:#1a1a2e;line-height:1.5;">{top_caption}</p>
                <p style="margin:8px 0 4px;font-size:12px;font-weight:bold;color:#555;">Hashtags:</p>
                <p style="margin:0;font-size:12px;color:#007bff;">{hashtag_str}</p>
                <p style="margin:12px 0 0;font-size:12px;background:#e8f4fd;padding:8px;border-radius:4px;color:#1565c0;">🎵 Audio cue: {audio_cue_text}</p>
            </div>
            """

        # Content guide section
        if is_dance:
            content_guide = f"""
            <div style="background:#fff3cd;border-left:4px solid #ffc107;color:#856404;padding:16px;margin:20px 0;border-radius:4px;">
                <h4 style="margin:0 0 8px;font-size:16px;font-weight:bold;">💃 Dance Trend — Film Yourself!</h4>
                <p style="margin:4px 0;font-size:14px;"><strong>What to film:</strong> {ideal_content_description}</p>
                <p style="margin:4px 0;font-size:14px;"><strong>Camera style:</strong> {camera_style}</p>
                <p style="margin:4px 0;font-size:14px;"><strong>Use exact song:</strong> "{audio_title}" by {audio_artist}</p>
            </div>
            """
        else:
            content_guide = f"""
            <div style="background:#d4edda;border-left:4px solid #28a745;color:#155724;padding:16px;margin:20px 0;border-radius:4px;">
                <h4 style="margin:0 0 8px;font-size:16px;font-weight:bold;">✅ Auto-generate this reel!</h4>
                <p style="margin:4px 0;font-size:14px;"><strong>What photos to use:</strong> {ideal_content_description}</p>
                <p style="margin:4px 0;font-size:14px;"><strong>Edit style:</strong> {edit_style.replace('_', ' ').title()}</p>
                {f'<p style="margin:4px 0;font-size:14px;"><strong>Text overlay:</strong> "{text_overlay_template}"</p>' if text_overlay_template else ''}
            </div>
            """

        # Posting strategy section
        platform_label = "YouTube Shorts" if best_platform == "youtube_shorts" else "Instagram Reels"
        posting_tip = ""
        if optimal_post_hour is not None:
            period = "PM" if optimal_post_hour >= 12 else "AM"
            h12 = optimal_post_hour % 12 or 12
            posting_tip = f"<p style='font-size:13px;color:#555;'>🕐 Best time to post: <strong>{h12} {period} IST</strong> on {platform_label}</p>"

        why_it_works_html = ""
        if why_this_works:
            why_it_works_html = f'<p style="font-size:13px;color:rgba(255,255,255,0.5);font-style:italic;margin-bottom:20px;">💡 Why it\'s viral: {why_this_works}</p>'

        # WhatsApp share
        wa_text = f"🔥 Trending now: '{audio_title}' by {audio_artist}\nPost on {platform_label} NOW — {window_hours}h left!\nCheck Trendrop → https://trendrop.vercel.app"
        encoded_wa_text = wa_text.replace(' ', '%20').replace('\n', '%0A')
        wa_link = f"https://wa.me/?text={encoded_wa_text}"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trendrop Alert</title>
        </head>
        <body style="margin:0;padding:20px;background:#07070e;font-family:Helvetica,Arial,sans-serif;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px;margin:0 auto;background:#111120;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">

                <!-- Header -->
                <tr>
                    <td style="background:linear-gradient(135deg,#E63946,#f4a261);padding:24px;text-align:center;">
                        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:800;letter-spacing:2px;">◈ TRENDROP</h1>
                        <p style="color:rgba(255,255,255,0.85);margin:4px 0 0;font-size:13px;">India's Trend Intelligence</p>
                    </td>
                </tr>

                <!-- Urgency Banner -->
                <tr>
                    <td style="background:{urgency_bg};padding:12px 24px;text-align:center;border-bottom:1px solid rgba(0,0,0,0.1);">
                        <span style="color:{urgency_color};font-size:15px;font-weight:800;">{urgency_prefix} — {window_hours}h window remaining</span>
                    </td>
                </tr>

                <!-- Main Body -->
                <tr>
                    <td style="padding:28px;color:#f0f0ff;">

                        <!-- Velocity badge -->
                        <div style="text-align:center;margin-bottom:20px;">
                            <span style="background:rgba(230,57,70,0.15);color:#E63946;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;display:inline-block;border:1px solid rgba(230,57,70,0.3);">
                                🔥 {velocity_avg:.0f}x viral velocity
                            </span>
                            {lang_badge}
                        </div>

                        <!-- Song name -->
                        <h2 style="font-size:26px;font-weight:800;color:#fff;text-align:center;margin:0 0 6px;">{audio_title}</h2>
                        <h3 style="font-size:16px;font-weight:500;color:rgba(255,255,255,0.5);text-align:center;margin:0 0 20px;">by {audio_artist}</h3>

                        <!-- Meta badges -->
                        <div style="text-align:center;margin-bottom:20px;">
                            <span style="background:rgba(255,255,255,0.08);color:#aaa;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:bold;display:inline-block;">🎬 {content_type.title()}</span>
                            <span style="background:rgba(244,162,97,0.15);color:#f4a261;padding:4px 10px;border-radius:4px;font-size:12px;font-weight:bold;margin-left:8px;display:inline-block;">⏰ {window_hours}h left</span>
                        </div>

                        <!-- Saturation alert -->
                        <div style="background:{sat_bg};border-left:4px solid {sat_color};color:{sat_color};padding:12px 16px;margin-bottom:20px;border-radius:4px;font-size:13px;font-weight:600;">
                            {sat_text}
                        </div>

                        {why_it_works_html}

                        <!-- Content Guide -->
                        {content_guide}

                        <!-- Caption Kit -->
                        {caption_section}

                        <!-- Posting Strategy -->
                        {posting_tip}

                        <!-- CTA Buttons -->
                        <div style="text-align:center;margin:28px 0 16px;">
                            <a href="https://trendrop.vercel.app/generate?trendId={trend_id}" target="_blank"
                               style="background:#28a745;color:#fff;padding:14px 28px;border-radius:10px;font-size:15px;font-weight:800;text-decoration:none;display:inline-block;letter-spacing:0.5px;">🎬 Generate My Reel →</a>
                        </div>
                        <div style="text-align:center;margin-bottom:24px;">
                            <a href="{wa_link}" target="_blank"
                               style="background:#25D366;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:700;text-decoration:none;display:inline-block;">📲 Share on WhatsApp</a>
                        </div>
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background:rgba(255,255,255,0.03);padding:20px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);color:rgba(255,255,255,0.35);font-size:12px;">
                        <p style="margin:0 0 6px;">Made with ❤️ for Indian creators — Trendrop</p>
                        <p style="margin:0;"><a href="https://trendrop.vercel.app/unsubscribe" style="color:rgba(255,255,255,0.3);text-decoration:underline;">Unsubscribe</a></p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        velocity_avg = trend.get("velocity_avg", 1.0)
        window_hours_remaining = trend.get("window_hours_remaining", 24)
        content_type = trend.get("content_type") or "trend"
        language = trend.get("language")
        ideal_content_description = trend.get("ideal_content_description", "")
        camera_style = trend.get("camera_style", "handheld")
        edit_style = trend.get("edit_style", "fast_cuts")
        narrative_structure = trend.get("narrative_structure", "none")
        text_overlay_template = trend.get("text_overlay_template")

        # Determine language badge HTML if not English
        lang_badge_html = ""
        if language and language.lower() not in ["en", "english"]:
            lang_badge_html = f'<span style="background-color: #f0f0f0; color: #333333; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px; display: inline-block;">🌍 {language.upper()} trend</span>'

        # Build dynamic boxes
        dynamic_boxes_html = ""
        
        if is_dance:
            dynamic_boxes_html += f"""
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; color: #856404; padding: 16px; margin: 20px 0; border-radius: 4px; font-family: 'Inter', Helvetica, Arial, sans-serif;">
                <h4 style="margin-top: 0; margin-bottom: 8px; font-size: 16px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                    💃 This is a DANCE TREND
                </h4>
                <p style="margin: 4px 0; font-size: 14px;"><strong>You need to film yourself for this one.</strong></p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>What to film:</strong> {ideal_content_description}</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>Camera style:</strong> {camera_style}</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>Use this exact song:</strong> {audio_title} by {audio_artist}</p>
            </div>
            """
        else:
            dynamic_boxes_html += f"""
            <div style="background-color: #d4edda; border-left: 4px solid #28a745; color: #155724; padding: 16px; margin: 20px 0; border-radius: 4px; font-family: 'Inter', Helvetica, Arial, sans-serif;">
                <h4 style="margin-top: 0; margin-bottom: 8px; font-size: 16px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                    ✅ We can generate this reel for you automatically!
                </h4>
                <p style="margin: 4px 0; font-size: 14px;"><strong>What photos to use:</strong> {ideal_content_description}</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>Edit style:</strong> {edit_style}</p>
                <p style="margin: 4px 0; font-size: 14px;"><strong>Transitions:</strong> {narrative_structure}</p>
            </div>
            """

        if text_overlay_template:
            dynamic_boxes_html += f"""
            <div style="background-color: #f3e5f5; border-left: 4px solid #9c27b0; color: #4a148c; padding: 16px; margin: 20px 0; border-radius: 4px; font-family: 'Inter', Helvetica, Arial, sans-serif;">
                <p style="margin: 0; font-size: 14px;"><strong>📝 Text to use in your reel:</strong> "{text_overlay_template}"</p>
            </div>
            """

        # Return full beautiful email template
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Trendrop Alert</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #f8f9fa;
                    font-family: 'Inter', Helvetica, Arial, sans-serif;
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 20px; background-color: #f8f9fa;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <!-- Header -->
                <tr>
                    <td style="background-color: #ff3b30; padding: 30px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;">
                            TRENDROP
                        </h1>
                    </td>
                </tr>
                
                <!-- Main Body -->
                <tr>
                    <td style="padding: 30px; color: #2d3748;">
                        <div style="text-align: center; margin-bottom: 24px;">
                            <span style="background-color: #ffe5e5; color: #d32f2f; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-block; text-transform: uppercase; letter-spacing: 0.5px;">
                                HOW VIRAL: {velocity_avg:.0f}x normal
                            </span>
                        </div>
                        
                        <h2 style="font-size: 24px; font-weight: 800; color: #1a202c; text-align: center; margin: 0 0 10px 0; line-height: 1.3;">
                            {audio_title}
                        </h2>
                        <h3 style="font-size: 18px; font-weight: 600; color: #718096; text-align: center; margin: 0 0 24px 0;">
                            by {audio_artist}
                        </h3>
                        
                        <div style="text-align: center; margin-bottom: 24px;">
                            <span style="background-color: #e2e8f0; color: #4a5568; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; display: inline-block;">
                                🎬 {content_type}
                            </span>
                            <span style="background-color: #ffe8d6; color: #dd6b20; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px; display: inline-block;">
                                ⏰ {window_hours_remaining} hours left
                            </span>
                            {lang_badge_html}
                        </div>
                        
                        <!-- Dynamic Boxes -->
                        {dynamic_boxes_html}
                        
                        <!-- CTA Button -->
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://trendrop.ai/generate/{trend_id}" target="_blank" style="background-color: #28a745; color: #ffffff; padding: 14px 28px; border-radius: 8px; font-size: 16px; font-weight: bold; text-decoration: none; display: inline-block; box-shadow: 0 4px 6px rgba(40,167,69,0.2); transition: background-color 0.2s;">
                                Generate My Reel Now →
                            </a>
                        </div>
                    </td>
                </tr>
                
                <!-- Footer -->
                <tr>
                    <td style="background-color: #f7fafc; padding: 24px; text-align: center; border-top: 1px solid #edf2f7; color: #718096; font-size: 12px; font-family: 'Inter', Helvetica, Arial, sans-serif;">
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #4a5568;">Made with ❤️ by Trendrop</p>
                        <p style="margin: 0;"><a href="https://trendrop.ai/unsubscribe" style="color: #a0aec0; text-decoration: underline;">Unsubscribe</a></p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
