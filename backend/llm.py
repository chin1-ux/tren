import os
import json
import logging
import requests

logger = logging.getLogger("llm")

# Verified available models for this API key (confirmed via /v1beta/models endpoint 2026-07-18):
# models/gemini-2.0-flash  — primary stable fallback
# models/gemini-2.0-flash-lite — secondary fallback if primary is rate-limited
_GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


def _collect_env_keys(prefixes: tuple[str, ...]) -> list[str]:
    keys = []
    for env_name, env_val in os.environ.items():
        if env_name.startswith(prefixes) and env_val.strip():
            for part in env_val.split(","):
                clean_part = part.strip()
                if clean_part and clean_part not in keys:
                    keys.append(clean_part)
    return keys

def call_gemini(system_prompt: str, user_prompt: str, gemini_key: str, response_mime_type: str = "application/json", timeout: int = 30) -> dict:
    model = os.getenv("GEMINI_MODEL", _GEMINI_FALLBACK_MODELS[0])
    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={gemini_key}"
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
    # Groq is the primary LLM provider; Gemini remains a fallback when Groq is exhausted
        
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
        # Primary-fallback: try each key until a request succeeds
        # Collect all keys from any env vars starting with GROQ_API_KEY or LLM_API_KEY
        keys = []
        for env_name, env_val in os.environ.items():
            if (env_name.startswith("GROQ_API_KEY") or env_name.startswith("LLM_API_KEY")) and env_val.strip():
                # Support comma-separated keys within a single env var as well
                for part in env_val.split(","):
                    clean_part = part.strip()
                    if clean_part and clean_part not in keys:
                        keys.append(clean_part)

        if not keys:
            raise ValueError("GROQ_API_KEY or LLM_API_KEY must be configured.")

        max_keys_raw = os.getenv("LLM_MAX_KEYS_PER_REQUEST")
        if max_keys_raw is not None and max_keys_raw.strip():
            max_keys = int(max_keys_raw)
            if max_keys > 0 and len(keys) > max_keys:
                logger.info(f"Limiting Groq key rotation to the first {max_keys} key(s) this request.")
                keys = keys[:max_keys]
        else:
            logger.info(f"Using all {len(keys)} configured Groq key(s) for this request.")

        # Apply cost optimisation defaults
        model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        # Groq returns HTTP 400 json_validate_failed for models that don't support
        # response_format: json_object. Skip for known-unsupported models; callers
        # still get JSON via prompt + markdown extraction at L163+.
        _GROQ_NO_JSON_FORMAT = set()
        if response_mime_type == "application/json" and model not in _GROQ_NO_JSON_FORMAT:
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
                    gemini_keys = _collect_env_keys(("GEMINI_API_KEY",))
                    if gemini_keys:
                        # Try each Gemini key and each Gemini model in order until one succeeds.
                        last_gemini_err = None
                        for gemini_idx, gemini_key in enumerate(gemini_keys, start=1):
                            for gemini_model in _GEMINI_FALLBACK_MODELS:
                                logger.warning(
                                    f"All Groq API keys failed. Attempting fallback to Gemini key #{gemini_idx} ({gemini_model})..."
                                )
                                try:
                                    prev_model = os.environ.get("GEMINI_MODEL")
                                    os.environ["GEMINI_MODEL"] = gemini_model
                                    res = call_gemini(system_prompt, user_prompt, gemini_key, response_mime_type, timeout)
                                    if prev_model is None:
                                        os.environ.pop("GEMINI_MODEL", None)
                                    else:
                                        os.environ["GEMINI_MODEL"] = prev_model
                                    logger.info(f"Fallback to Gemini key #{gemini_idx} ({gemini_model}) successful.")
                                    return res
                                except Exception as gemini_err:
                                    last_gemini_err = gemini_err
                                    logger.error(f"Gemini fallback key #{gemini_idx} ({gemini_model}) also failed: {gemini_err}")
                        raise RuntimeError(f"All Groq keys failed. All Gemini fallbacks failed. Last error: {last_gemini_err}") from e
                    raise RuntimeError("All Groq API keys failed.")
            except requests.RequestException as e:
                logger.warning(f"Groq request error with key #{idx}: {e}")
                if idx == len(keys):
                    gemini_keys = _collect_env_keys(("GEMINI_API_KEY",))
                    if gemini_keys:
                        # Try each Gemini key and each Gemini model in order until one succeeds.
                        last_gemini_err = None
                        for gemini_idx, gemini_key in enumerate(gemini_keys, start=1):
                            for gemini_model in _GEMINI_FALLBACK_MODELS:
                                logger.warning(
                                    f"All Groq API keys failed. Attempting fallback to Gemini key #{gemini_idx} ({gemini_model})..."
                                )
                                try:
                                    prev_model = os.environ.get("GEMINI_MODEL")
                                    os.environ["GEMINI_MODEL"] = gemini_model
                                    res = call_gemini(system_prompt, user_prompt, gemini_key, response_mime_type, timeout)
                                    if prev_model is None:
                                        os.environ.pop("GEMINI_MODEL", None)
                                    else:
                                        os.environ["GEMINI_MODEL"] = prev_model
                                    logger.info(f"Fallback to Gemini key #{gemini_idx} ({gemini_model}) successful.")
                                    return res
                                except Exception as gemini_err:
                                    last_gemini_err = gemini_err
                                    logger.error(f"Gemini fallback key #{gemini_idx} ({gemini_model}) also failed: {gemini_err}")
                        raise RuntimeError(f"All Groq keys failed. All Gemini fallbacks failed. Last error: {last_gemini_err}") from e
                    raise RuntimeError("All Groq API keys failed.")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
