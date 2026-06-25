import os
import json
import logging
import requests

logger = logging.getLogger("llm")

def call_llm(system_prompt: str, user_prompt: str, response_mime_type: str = "application/json", timeout: int = 30) -> dict:
    """
    Unified LLM call supporting Gemini (default) and Grok / OpenAI compatible providers.
    Uses environment variables:
      - LLM_PROVIDER: "gemini" or "grok" or "openai"
      - GEMINI_API_KEY: for Gemini
      - GROK_API_KEY / LLM_API_KEY: for Grok / OpenAI compatible API
      - LLM_BASE_URL: default is https://api.x.ai/v1 for grok, or custom
      - LLM_MODEL: default is "grok-beta" for grok, or custom
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={gemini_key}"
        )
        
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {"responseMimeType": response_mime_type}
        }
        
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(gemini_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        
        rj = response.json()
        text = rj["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if response_mime_type == "application/json":
            if text.startswith("```"):
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    text = text[start:end + 1]
            return json.loads(text)
        return {"text": text}
        
    elif provider in ["grok", "openai"]:
        api_key = os.getenv("GROK_API_KEY") or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY or LLM_API_KEY is not configured.")
            
        base_url = os.getenv("LLM_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        model = os.getenv("LLM_MODEL", "grok-beta")
        
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2
        }
        
        if response_mime_type == "application/json":
            payload["response_format"] = {"type": "json_object"}
            
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        
        rj = response.json()
        text = rj["choices"][0]["message"]["content"].strip()
        
        if response_mime_type == "application/json":
            if text.startswith("```"):
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    text = text[start:end + 1]
            return json.loads(text)
        return {"text": text}
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
