import os
import sys
import json
import time

sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv('backend/.env')

from supabase import create_client
from llm import call_llm

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

TEST_QUERIES = [
    "sad slow songs blowing up right now",
    "what should i use for a gym reel today",
    "punjabi tracks that haven't peaked yet",
    "high energy bgm for food videos",
    "aesthetic hindi audio for travel vlog",
    "sounds similar to naina",
    "fastest growing audio this week",
    "dance trend i can do alone",
    "undiscovered beat for tech review",
    "what is trending in tamil reels"
]

system_prompt = (
    "You are Trendrop's creator trend search assistant. A creator asks a question or describes what audio/sound "
    "they are looking for on Instagram Reels.\n"
    "Analyze the query and return a valid JSON object with:\n"
    "{\n"
    '  "intent": "<short summary of creator search intent>",\n'
    '  "direct_answer": "<1-2 sentence direct, actionable advice or answer for the creator>",\n'
    '  "filters": {\n'
    '    "niche": "<niche if applicable: fitness, food, comedy, fashion, business, travel, beauty, devotional, tech, dance, narrative_edit, romance_relationship, or null>",\n'
    '    "language": "<language code if specified: hi, pa, ta, te, ml, kn, bn, mr, en, es, pt, ko, or null>",\n'
    '    "min_velocity": null,\n'
    '    "max_saturation": null,\n'
    '    "sort_by": "<newest | velocity | opportunity>",\n'
    '    "keywords": ["<keyword1>", "<keyword2>"]\n'
    "  }\n"
    "}\n"
    "Only output JSON. Do not include markdown or explanations outside the JSON."
)

def search_ask(q: str):
    t0 = time.time()
    # 1. LLM parse
    try:
        parsed = call_llm(system_prompt, f"Creator query: {q}")
    except Exception as e:
        parsed = {
            "intent": "Keyword search",
            "direct_answer": f"Searching active trends matching '{q}'.",
            "filters": {"keywords": q.split(), "sort_by": "velocity"}
        }
    
    intent = parsed.get("intent", "Search")
    direct_answer = parsed.get("direct_answer", "")
    filters = parsed.get("filters", {})
    
    # 2. Query Supabase
    cols = "id,audio_title,audio_artist,audio_id,audio_use_count,status,velocity_avg,opportunity_score,saturation_score,why_this_works,niche_tag,language"
    query = sb.table("trends").select(cols).eq("is_seed_data", False).eq("is_voiceover", False).gt("window_hours_remaining", 0)
    
    lang = filters.get("language")
    if lang:
        query = query.or_(f"language_final.eq.{lang},language.eq.{lang}")
        
    niche = filters.get("niche")
    if niche:
        query = query.or_(f"niche_tag.eq.{niche},semantic_niches.cs.{{{niche}}}")
        
    sort_by = filters.get("sort_by")
    if sort_by == "velocity":
        query = query.order("velocity_avg", desc=True)
    elif sort_by == "opportunity":
        query = query.order("opportunity_score", desc=True)
    else:
        query = query.order("first_detected_at", desc=True)
        
    query = query.limit(5)
    res = query.execute()
    data = res.data or []
    
    # Fallback to ILIKE if specific keyword like "naina" gave 0
    keywords = filters.get("keywords") or []
    if len(data) == 0 and keywords:
        kw = keywords[0]
        fb_query = sb.table("trends").select(cols).or_(f"audio_title.ilike.%{kw}%,why_this_works.ilike.%{kw}%").limit(5)
        fb_res = fb_query.execute()
        data = fb_res.data or []
        
    elapsed = time.time() - t0
    return {
        "query": q,
        "elapsed_sec": round(elapsed, 3),
        "intent": intent,
        "direct_answer": direct_answer,
        "results_count": len(data),
        "top_results": [
            {
                "id": t.get("id"),
                "title": t.get("audio_title"),
                "artist": t.get("audio_artist"),
                "status": t.get("status"),
                "velocity": t.get("velocity_avg"),
                "niche": t.get("niche_tag")
            } for t in data[:5]
        ]
    }

if __name__ == '__main__':
    print(f"Testing 10 Queries for Item 7...")
    all_results = []
    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/10] Query: '{q}'...")
        res = search_ask(q)
        all_results.append(res)
        print(f"     Time: {res['elapsed_sec']}s | Results: {res['results_count']} | Top: {res['top_results'][0]['title'] if res['top_results'] else 'None'}")
        
    with open("evidence/order77/item7_ask_search.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("ORDER 77 ITEM 7: ASK-IT SEARCH 10-QUERY VERIFICATION TEST\n")
        f.write("=" * 80 + "\n\n")
        for r in all_results:
            f.write(f"QUERY: {r['query']}\n")
            f.write(f"LATENCY: {r['elapsed_sec']} seconds\n")
            f.write(f"INTENT: {r['intent']}\n")
            f.write(f"DIRECT ANSWER: {r['direct_answer']}\n")
            f.write(f"RESULTS ({r['results_count']}):\n")
            for t in r['top_results']:
                f.write(f"  - [{t['id']}] \"{t['title']}\" by {t['artist']} (Status: {t['status']}, Velocity: {t['velocity']}, Niche: {t['niche']})\n")
            f.write("-" * 80 + "\n\n")
    print("\nSaved proof to evidence/order77/item7_ask_search.txt")
