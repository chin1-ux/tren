from pydantic import BaseModel, EmailStr
from typing import List, Optional

# ── Pydantic Models ────────────────────────────────────────────────────────────

class TargetRequest(BaseModel):
    action: str  # "target" or "untarget"

class SubscribeRequest(BaseModel):
    email: EmailStr
    niche: str
    language: str

class FeedbackRequest(BaseModel):
    trend_id: int
    feedback_type: str  # "too_late" | "too_early" | "perfect" | "stale"
    comment: Optional[str] = None


class PrePostRequest(BaseModel):
    niche: str
    hook: str
    audio_title: str
    caption: str
    hashtags: List[str]
    post_time: str


class ScoreReelRequest(BaseModel):
    audio: str
    caption: str
    posting_time: str
    niche: str


class HookRequest(BaseModel):
    niche: Optional[str] = None
    topic: Optional[str] = None
    trend: Optional[str] = None
    content_description: Optional[str] = None


class GenerateHooksRequest(BaseModel):
    trend: str
    content_description: str


class VideoUrlRequest(BaseModel):
    video_url: str



class SeoCaptionRequest(BaseModel):
    description: str
    platform: Optional[str] = "instagram"


class CalendarRequest(BaseModel):
    user_email: Optional[str] = None
    niche: str
    language: str
    frequency: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    phone_number: str
    niche: str = "all"
    language: str = "en"
    state: str = ""
    tier: str = "nano"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class LogoutRequest(BaseModel):
    session_token: str


class VerifyRequest(BaseModel):
    session_token: str


class CreatorProfileRequest(BaseModel):
    instagram_username: str
    niche: str
    followers: int
    engagement_rate: float
    trend_score: float
    portfolio_links: List[str]
    price_per_post: int


class MemoryRequest(BaseModel):
    trend_id: int
    format_name: str
    hook_variant: str
    planned_mode: str
    outcome_score: Optional[float] = None
    notes: Optional[str] = None


class TrialPlanRequest(BaseModel):
    creator_niche: Optional[str] = None
    creator_language: Optional[str] = None


class VerifyPhoneRequest(BaseModel):
    phone_number: str
    code: str

class SendOtpRequest(BaseModel):
    phone_number: str

class CreateOrderRequest(BaseModel):
    email: EmailStr

class PaymentWebhookRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str
    email:               EmailStr

class SubscriptionWebhookRequest(BaseModel):
    event: str  # subscription.cancelled, subscription.halted, payment.failed
    payload: dict

class CancellationReasonRequest(BaseModel):
    reason: str  # Free text or multiple choice

class MilestoneInput(BaseModel):
    milestone_name: str
    amount: float
    due_date: str # ISO string

class CreateDealRequest(BaseModel):
    brand_name: str
    deliverables: str
    rate_amount: float
    currency: str = "INR"
    usage_rights: str = ""
    exclusivity_clause: str = ""
    timeline_start: str = ""
    timeline_end: str = ""
    cover_note_type: str = "english"
    milestones: List[MilestoneInput]

class ApplyDealRequest(BaseModel):
    deal_id: int
    user_email: str
    pitch: str

class CollabRequest(BaseModel):
    from_email: str
    to_email: str
    message: str

class InstagramAuthRequest(BaseModel):
    user_email: str

class InstagramCallbackRequest(BaseModel):
    code: str
    user_email: str

class LogEventRequest(BaseModel):
    event_name: str

class FeedbackRequest(BaseModel):
    deal_id: int
    rating: str
    comment: str

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserPreferencesRequest(BaseModel):
    niches: List[str] = []
    languages: List[str] = ["en"]
    regions: List[str] = ["IN"]
    creator_language: str = "en"
    state: Optional[str] = None
    global_enabled: bool = False
    notification_triggers: dict = {}
    creator_tier: str = "nano"
    platform_focus: List[str] = ["instagram"]
