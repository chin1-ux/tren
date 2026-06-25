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
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    # Gemini block removed – Groq is now the default LLM provider
        
    if provider in ["grok", "openai"]:
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
        
    elif provider == "groq":
        # Primary‑fallback: try each key until a request succeeds
        raw_keys = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        if not raw_keys:
            raise ValueError("GROQ_API_KEY or LLM_API_KEY must be configured.")
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        # Apply cost optimisation defaults
        payload = {
            "model": os.getenv("LLM_MODEL", "grok-beta"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        if response_mime_type == "application/json":
            payload["response_format"] = {"type": "json_object"}
        headers_common = {"Content-Type": "application/json"}
        for idx, key in enumerate(keys, start=1):
            headers = {**headers_common, "Authorization": f"Bearer {key}"}
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
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
            except requests.HTTPError as e:
                logger.warning(f"Groq request failed with key #{idx}: {e}")
                if idx == len(keys):
                    raise RuntimeError("All Groq API keys failed.")
            except requests.RequestException as e:
                logger.warning(f"Groq request error with key #{idx}: {e}")
                if idx == len(keys):
                    raise RuntimeError("All Groq API keys failed.")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
