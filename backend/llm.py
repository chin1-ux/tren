import os
import json
import logging
import re
import socket
import requests

logger = logging.getLogger("llm")

# Force IPv4 — IPv6 is broken on some environments causing hangs
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(*args, **kwargs):
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

# Available Gemini models (verified 2026-08-24):
# gemini-3.6-flash — latest stable, primary
# gemini-3.5-flash-lite — secondary fallback
_GEMINI_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
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

def call_gemini(system_prompt: str, user_prompt: str, gemini_key: str, response_mime_type: str = "application/json", timeout: int = 30, model: str | None = None) -> dict:
    if model is None:
        model = _GEMINI_FALLBACK_MODELS[0]
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
    Unified LLM call with automatic fallback: Groq → Gemini → OpenRouter.
    Environment variables:
      - GROQ_API_KEY: primary provider (required)
      - GEMINI_API_KEY: fallback when Groq fails
      - OPENROUTER_API_KEY: last-resort fallback (free models)
      - LLM_MODEL: override default model (default: allam-2-7b)
      - LLM_PROVIDER: "groq" (default) or "grok"/"openai" for custom providers
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
        model = os.getenv("LLM_MODEL", "allam-2-7b")
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
                    try:
                        return _try_gemini_fallback(system_prompt, user_prompt, response_mime_type, timeout)
                    except RuntimeError:
                        try:
                            return _try_openrouter_fallback(system_prompt, user_prompt, response_mime_type, timeout)
                        except RuntimeError:
                            raise RuntimeError("All Groq keys failed. All Gemini fallbacks failed. All OpenRouter fallbacks failed.") from e
            except requests.RequestException as e:
                logger.warning(f"Groq request error with key #{idx}: {e}")
                if idx == len(keys):
                    try:
                        return _try_gemini_fallback(system_prompt, user_prompt, response_mime_type, timeout)
                    except RuntimeError:
                        try:
                            return _try_openrouter_fallback(system_prompt, user_prompt, response_mime_type, timeout)
                        except RuntimeError:
                            raise RuntimeError("All Groq keys failed. All Gemini fallbacks failed. All OpenRouter fallbacks failed.") from e
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _try_gemini_fallback(system_prompt: str, user_prompt: str, response_mime_type: str, timeout: int) -> dict:
    """Try all Gemini keys and models as fallback when Groq fails. Thread-safe (no os.environ mutation)."""
    gemini_keys = _collect_env_keys(("GEMINI_API_KEY",))
    if not gemini_keys:
        raise RuntimeError("All Groq API keys failed. No Gemini keys configured for fallback.")
    
    last_err = None
    for gemini_idx, gemini_key in enumerate(gemini_keys, start=1):
        for gemini_model in _GEMINI_FALLBACK_MODELS:
            logger.warning(f"All Groq API keys failed. Attempting Gemini fallback key #{gemini_idx} ({gemini_model})...")
            try:
                res = call_gemini(system_prompt, user_prompt, gemini_key, response_mime_type, timeout, model=gemini_model)
                logger.info(f"Gemini fallback key #{gemini_idx} ({gemini_model}) successful.")
                return res
            except Exception as gemini_err:
                last_err = gemini_err
                logger.error(f"Gemini fallback key #{gemini_idx} ({gemini_model}) also failed: {gemini_err}")
    raise RuntimeError(f"All Groq keys failed. All Gemini fallbacks failed. Last error: {last_err}")


# Verified free models on OpenRouter (2026-08-24)
_OPENROUTER_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "liquid/lfm-2.5-2.6b:free",
]


def _try_openrouter_fallback(system_prompt: str, user_prompt: str, response_mime_type: str, timeout: int) -> dict:
    """Try OpenRouter free models as last-resort fallback."""
    keys = _collect_env_keys(("OPENROUTER_API_KEY",))
    if not keys:
        raise RuntimeError("No OPENROUTER_API_KEY configured.")

    last_err = None
    for key_idx, api_key in enumerate(keys, start=1):
        for model in _OPENROUTER_MODELS:
            logger.warning(f"Attempting OpenRouter fallback key #{key_idx} ({model})...")
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://trendrop.app",
                    "X-Title": "Trendrop",
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                }
                # Free models on OpenRouter don't support response_format

                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                rj = response.json()
                content = rj["choices"][0]["message"]["content"]
                if content is None:
                    logger.warning(f"OpenRouter returned null content for {model}")
                    continue
                text = content.strip()

                if response_mime_type == "application/json":
                    # Handle markdown code blocks: ```json\n{...}\n```
                    if "```" in text:
                        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
                        if m:
                            text = m.group(1).strip()
                    # If still not JSON, try to extract the outermost {...}
                    if not text.startswith("{"):
                        start = text.find("{")
                        end = text.rfind("}")
                        if start != -1 and end != -1:
                            text = text[start:end + 1]
                    return json.loads(text)
                return {"text": text}
            except Exception as err:
                last_err = err
                logger.error(f"OpenRouter key #{key_idx} ({model}) failed: {err}")
    raise RuntimeError(f"All OpenRouter fallbacks failed. Last error: {last_err}")
