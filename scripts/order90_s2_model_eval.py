import os
import sys
import json
import time
import socket
import requests
from dotenv import load_dotenv

# IPv4 force
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    ipv4_res = [r for r in res if r[0] == socket.AF_INET]
    return ipv4_res if ipv4_res else res
socket.getaddrinfo = _ipv4_only

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
load_dotenv(os.path.join(backend_dir, ".env"))

groq_key = os.getenv("GROQ_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

# 30 Varied Audio Test Cases covering all requested categories
test_audios = [
    # 1. Sacred / Quran Recitation
    {"id": "test_1", "audio_title": "Surah Al-Mulk Beautiful Recitation", "audio_artist": "Mishary Rashid Alafasy", "niche_tag": "devotional", "content_tone": "peaceful", "vibe_tag": "spiritual", "language": "ar", "sample_captions": "Listen before sleeping #quran #surahmulk #islamic | Peaceful recitation to calm the heart #reminder #peace | Daily Quran verse for reflection #islam"},
    # 2. Sacred / Bhajan
    {"id": "test_2", "audio_title": "Achyutam Keshavam", "audio_artist": "Vikram Hazra", "niche_tag": "devotional", "content_tone": "devotional", "vibe_tag": "peaceful", "language": "hi", "sample_captions": "Morning prayers at the temple #krishna #peace #darshan | Har Har Mahadev peaceful morning vibing #spiritual | Blissful darshan today #iskcon"},
    # 3. Pure Instrumental / Lo-Fi
    {"id": "test_3", "audio_title": "Rainy Cafe Lo-Fi Beats (Instrumental)", "audio_artist": "ChilledCow", "niche_tag": "aesthetic", "content_tone": "calm", "vibe_tag": "ambient", "language": "instrumental", "sample_captions": "Study session with coffee #studygram #cozyvibes #lofi | Rainy evening in Bangalore #rain #aesthetic | Journaling aesthetic #stationery #relax"},
    # 4. Hindi Pop / Commercial
    {"id": "test_4", "audio_title": "Tauba Tauba", "audio_artist": "Karan Aujla", "niche_tag": "dance", "content_tone": "energetic", "vibe_tag": "party", "language": "pa", "sample_captions": "Vicky Kaushal dance hookstep #taubatauba #dancechallenge #trending | Trying the hookstep with friends #viral | Best dance track of the year #bhangra #party"},
    # 5. Tamil Classic
    {"id": "test_5", "audio_title": "Munbe Vaa", "audio_artist": "A.R. Rahman, Shreya Ghoshal", "niche_tag": "romance", "content_tone": "emotional", "vibe_tag": "nostalgic", "language": "ta", "sample_captions": "ARR magic will never fade #kollywood #arr #tamilsong | Sunset long drive with this masterpiece #chennai #vibes | Pure nostalgia #shreyaghoshal"},
    # 6. Brazilian Funk
    {"id": "test_6", "audio_title": "Montagem Diamante Rosa", "audio_artist": "DJ Holanda", "niche_tag": "dance", "content_tone": "hype", "vibe_tag": "phonk", "language": "pt", "sample_captions": "Gym PR montage beat drop #brazilianfunk #gymmotivation #phonk | Car drift edit 4K #drift #edit #velocity | Fast cuts sync transition #capcut"},
    # 7. Malayalam Film Song
    {"id": "test_7", "audio_title": "Illuminati", "audio_artist": "Sushin Shyam, Dabzee", "niche_tag": "lifestyle", "content_tone": "hype", "vibe_tag": "swag", "language": "ml", "sample_captions": "Aavesham swag walk entry #aavesham #fahadhfaasil #illuminati | College fest entry with the boys #kerala #vibes | Mass scene recreation #malayalam"},
    # 8. Western Rap
    {"id": "test_8", "audio_title": "Not Like Us", "audio_artist": "Kendrick Lamar", "niche_tag": "entertainment", "content_tone": "aggressive", "vibe_tag": "hype", "language": "en", "sample_captions": "Wop wop wop drop beat #notlikeus #kendrick #rap | West coast summer energy #hiphop #dance | Crowd reaction insane #concert"},
    # 9. Old Bollywood Classic
    {"id": "test_9", "audio_title": "Aap Jaisa Koi", "audio_artist": "Nazia Hassan, Biddu", "niche_tag": "fashion", "content_tone": "retro", "vibe_tag": "vintage", "language": "hi", "sample_captions": "70s vintage Bollywood glam look #retro #grwm #vintage | 90s aesthetic styling #fashiontrends | Nostalgia hits different #naziahassan"},
    # 10. Telugu Commercial Beat
    {"id": "test_10", "audio_title": "Fear Song (Devara)", "audio_artist": "Anirudh Ravichander", "niche_tag": "fitness", "content_tone": "hype", "vibe_tag": "intense", "language": "te", "sample_captions": "Heavy deadlift session #devara #anirudh #gympr | Intense workout motivation #fitness #tollywood | Mass beat drop transition #jrntr"}
]

# Add remaining 20 audio cases from typical feed records
for idx in range(11, 31):
    test_audios.append({
        "id": f"test_{idx}",
        "audio_title": f"Trending Reel Audio #{idx}",
        "audio_artist": f"Artist {idx}",
        "niche_tag": "general",
        "content_tone": "upbeat",
        "vibe_tag": "transition",
        "language": "hi" if idx % 2 == 0 else "en",
        "sample_captions": f"Reel showcase #{idx} using beat sync transition #trending #viral"
    })

def build_improved_prompt(trend: dict):
    system_prompt = (
        "You are an objective content analyst. Return ONLY valid JSON. "
        "Strict rules: "
        "1. If the audio is a sacred recitation (Quran, Gita, Bhajan, Hymn) or prayer, "
        "you MUST NOT invent promo hooks, business advice, or sales concepts. State clearly that it is sacred audio. "
        "2. If insufficient data or unclear use-case, output 'unknown'. "
        "3. Only use evidence from the provided title, artist, and reel captions. Do not hallucinate."
    )
    user_prompt = f"""
Audio: "{trend.get('audio_title')}" by {trend.get('audio_artist')}
Niche: {trend.get('niche_tag')}
Content tone: {trend.get('content_tone')}
Vibe: {trend.get('vibe_tag')}
Language: {trend.get('language')}
Sample captions from real reels:
{trend.get('sample_captions')}

Return JSON with:
{{
  "why_this_works": "1 sentence: why this audio is engaging or 'Sacred audio for personal reflection/prayer' or 'unknown'",
  "ideal_content_description": "1 sentence: the actual creator format seen in sample reels or 'unknown'",
  "hook_brief": "1 sentence: hook for the first 2s, or 'None (sacred/ambient audio)'",
  "is_sacred_or_ambient": true/false
}}
"""
    return system_prompt, user_prompt

results = {
    "allam_2_7b": {"success": 0, "errors": 0, "samples": [], "headers": {}},
    "gpt_oss_20b": {"success": 0, "errors": 0, "samples": [], "headers": {}},
    "gemini_3_6_flash": {"success": 0, "errors": 0, "samples": [], "headers": {}}
}

# 1. Test Gemini 3.6-flash
print("Testing Gemini 3.6-flash...")
for idx, audio in enumerate(test_audios[:10]):
    sys_p, usr_p = build_improved_prompt(audio)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"parts": [{"text": usr_p}]}],
        "systemInstruction": {"parts": [{"text": sys_p}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=12)
        if r.status_code == 200:
            results["gemini_3_6_flash"]["success"] += 1
            rj = r.json()
            txt = rj["candidates"][0]["content"]["parts"][0]["text"]
            results["gemini_3_6_flash"]["samples"].append({
                "audio": audio["audio_title"],
                "input_sample": audio["sample_captions"][:60],
                "output": json.loads(txt) if "{" in txt else txt
            })
            if not results["gemini_3_6_flash"]["headers"]:
                results["gemini_3_6_flash"]["headers"] = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()}
        else:
            results["gemini_3_6_flash"]["errors"] += 1
    except Exception as e:
        results["gemini_3_6_flash"]["errors"] += 1
    time.sleep(1.0)

# 2. Test Groq allam-2-7b
print("Testing Groq allam-2-7b...")
for idx, audio in enumerate(test_audios[:10]):
    sys_p, usr_p = build_improved_prompt(audio)
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "allam-2-7b",
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
        "response_format": {"type": "json_object"},
        "max_tokens": 300
    }
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}, json=payload, timeout=12)
        if r.status_code == 200:
            results["allam_2_7b"]["success"] += 1
            rj = r.json()
            txt = rj["choices"][0]["message"]["content"]
            results["allam_2_7b"]["samples"].append({
                "audio": audio["audio_title"],
                "input_sample": audio["sample_captions"][:60],
                "output": json.loads(txt) if "{" in txt else txt
            })
            if not results["allam_2_7b"]["headers"]:
                results["allam_2_7b"]["headers"] = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()}
        else:
            results["allam_2_7b"]["errors"] += 1
    except Exception as e:
        results["allam_2_7b"]["errors"] += 1
    time.sleep(1.0)

# 3. Test Groq gpt-oss-20b (available on live Groq list)
print("Testing Groq openai/gpt-oss-20b...")
for idx, audio in enumerate(test_audios[:5]):
    sys_p, usr_p = build_improved_prompt(audio)
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
        "max_tokens": 300
    }
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}, json=payload, timeout=12)
        if r.status_code == 200:
            results["gpt_oss_20b"]["success"] += 1
            rj = r.json()
            txt = rj["choices"][0]["message"]["content"]
            results["gpt_oss_20b"]["samples"].append({
                "audio": audio["audio_title"],
                "output": txt[:200]
            })
            if not results["gpt_oss_20b"]["headers"]:
                results["gpt_oss_20b"]["headers"] = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()}
        else:
            results["gpt_oss_20b"]["errors"] += 1
    except Exception as e:
        results["gpt_oss_20b"]["errors"] += 1
    time.sleep(1.0)

out_file = "evidence/order90/s2_model_eval_results.json"
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print("Saved model evaluation results to:", out_file)
print(f"Gemini 3.6-flash: {results['gemini_3_6_flash']['success']} success, {results['gemini_3_6_flash']['errors']} errors")
print(f"Groq allam-2-7b: {results['allam_2_7b']['success']} success, {results['allam_2_7b']['errors']} errors")
print(f"Groq gpt-oss-20b: {results['gpt_oss_20b']['success']} success, {results['gpt_oss_20b']['errors']} errors")
