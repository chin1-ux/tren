import os, sys, json, requests

sys.path.insert(0, "backend")
from dotenv import load_dotenv
load_dotenv("backend/.env")

cookies_path = "backend/cookies.json"
with open(cookies_path) as f:
    cookies_list = json.load(f)

session = requests.Session()
for c in cookies_list:
    session.cookies.set(c["name"], c["value"], domain=c.get("domain", ".instagram.com"))

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/",
    "Origin": "https://www.instagram.com",
})

resp = session.get(
    f"https://www.instagram.com/api/v1/tags/web_info/?tag_name=trending",
    headers={
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/explore/tags/trending/",
    },
    timeout=20
)

if resp.status_code == 200:
    data = resp.json()
    sections = data.get("data", {}).get("top", {}).get("sections", [])
    for section in sections:
        layout_content = section.get("layout_content") or {}
        for m_wrapper in layout_content.get("medias", []):
            media = m_wrapper.get("media")
            if media and media.get("media_type") in (2, 8):
                print("Keys in media:", list(media.keys()))
                print("video_versions:", media.get("video_versions"))
                print("video_url:", media.get("video_url"))
                sys.exit(0)
