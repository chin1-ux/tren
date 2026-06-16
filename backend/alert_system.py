import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
import resend

# Configure logging
logging.basicConfig(
    filename="alert_system.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.resend_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "alerts@trendrop.ai")
        
        if not self.supabase_url or not self.supabase_key:
            logging.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing.")
            raise ValueError("Supabase credentials are missing from .env")
        if not self.resend_key:
            logging.error("RESEND_API_KEY is missing from environment variables.")
            raise ValueError("RESEND_API_KEY is missing from .env")
            
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize Resend
        resend.api_key = self.resend_key

    def send_trend_alerts(self, trend_ids: list):
        """
        Main method:
        STEP 1 — For each trend_id: Fetch full trend data from Supabase 'trends' table
        STEP 2 — Fetch matching users: Get all users from Supabase 'users' table and match niches/languages
        STEP 3 — Build and send email for each matching user
        STEP 4 — Log how many emails sent and handle errors gracefully
        """
        logging.info(f"Starting alert run for trend_ids: {trend_ids}")
        if not trend_ids:
            logging.info("No trend_ids provided. Exiting.")
            return
            
        # Fetch all users once to avoid querying database inside the loop
        try:
            users_res = self.supabase.table("users").select("*").execute()
            users = users_res.data or []
            logging.info(f"Loaded {len(users)} users from Supabase.")
        except Exception as e:
            logging.error(f"Failed to fetch users from Supabase: {e}", exc_info=True)
            print(f"Error fetching users: {e}")
            return
            
        total_emails_sent = 0
        
        for trend_id in trend_ids:
            try:
                # STEP 1 — Fetch trend data
                trend_res = self.supabase.table("trends").select("*").eq("id", trend_id).execute()
                if not trend_res.data:
                    logging.warning(f"Trend with ID {trend_id} not found in database. Skipping.")
                    continue
                trend = trend_res.data[0]
                
                audio_title = trend.get("audio_title", "Unknown Title")
                audio_artist = trend.get("audio_artist", "Unknown Artist")
                is_dance = trend.get("is_dance", False)
                window_hours_remaining = trend.get("window_hours_remaining", 24)
                velocity_avg = trend.get("velocity_avg", 1.0)
                content_type = trend.get("content_type") or "trend"
                language = trend.get("language")
                ideal_content_description = trend.get("ideal_content_description", "No description available.")
                camera_style = trend.get("camera_style", "handheld")
                edit_style = trend.get("edit_style", "fast_cuts")
                narrative_structure = trend.get("narrative_structure", "none")
                text_overlay_template = trend.get("text_overlay_template")
                
                # STEP 2 — Match users
                # user.niche == trend.content_type OR user.niche == 'all' OR user.language_preference == trend.language
                matching_users = []
                for user in users:
                    user_niche = (user.get("niche") or "").strip().lower()
                    user_lang = (user.get("language_preference") or "").strip().lower()
                    
                    match_niche = (user_niche == content_type.lower()) or (user_niche == "all")
                    match_lang = (language and user_lang == language.lower())
                    
                    if match_niche or match_lang:
                        matching_users.append(user)
                        
                logging.info(f"Trend '{audio_title}' (ID: {trend_id}) matched with {len(matching_users)} users.")
                
                # STEP 3 — Build email for each user
                for user in matching_users:
                    user_email = user.get("email")
                    if not user_email:
                        continue
                        
                    # Determine subject
                    if is_dance:
                        subject = f"💃 Dance Trend Alert: {audio_title} — {window_hours_remaining}hrs left"
                    else:
                        subject = f"🔥 New Trend Alert: {audio_title} — Generate your reel now"
                        
                    # Build HTML body
                    html_body = self._build_email_html(trend, is_dance, trend_id)
                    
                    try:
                        logging.info(f"Sending email to {user_email} for trend '{audio_title}'...")
                        resend.Emails.send({
                            "from": self.from_email,
                            "to": user_email,
                            "subject": subject,
                            "html": html_body
                        })
                        total_emails_sent += 1
                        logging.info(f"Successfully sent email to {user_email}.")
                    except Exception as resend_err:
                        logging.error(f"Resend error sending to {user_email}: {resend_err}", exc_info=True)
                        print(f"Failed to send email to {user_email}: {resend_err}")
                        # Don't crash if one email fails — continue to next user
                        continue
                        
            except Exception as trend_err:
                logging.error(f"Error processing trend_id {trend_id}: {trend_err}", exc_info=True)
                print(f"Error processing trend ID {trend_id}: {trend_err}")
                continue
                
        # STEP 4 — Log how many emails sent
        logging.info(f"Alert run completed. Total emails sent: {total_emails_sent}")
        print(f"Successfully processed alerts. Total emails sent: {total_emails_sent}")
        return total_emails_sent

    def _build_email_html(self, trend: dict, is_dance: bool, trend_id: int) -> str:
        """
        Builds a beautiful premium-designed HTML email template matching the requirements.
        """
        audio_title = trend.get("audio_title", "Unknown Title")
        audio_artist = trend.get("audio_artist", "Unknown Artist")
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
