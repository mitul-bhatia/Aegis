import logging
import json
import requests
from groq import Groq
from backend.app.config import settings

logger = logging.getLogger("aegis.core.llm_client")

_groq_keys = []
if settings.GROQ_API_KEYS:
    _groq_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
if not _groq_keys and settings.GROQ_API_KEY:
    _groq_keys = [settings.GROQ_API_KEY.strip()]

_groq_index = 0

def get_llm_response(system_prompt: str, user_prompt: str, model: str = None, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    """
    Get LLM response with Groq round-robin key rotation and Gemini fallback.
    """
    global _groq_index
    target_model = model or settings.GROQ_MODEL
    
    # Try Groq keys in a round-robin fashion
    num_keys = len(_groq_keys)
    for _ in range(num_keys):
        current_key = _groq_keys[_groq_index]
        _groq_index = (_groq_index + 1) % num_keys
        
        try:
            client = Groq(api_key=current_key)
            response = client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                logger.warning(f"Groq rate limit hit with a key, trying next... ({e})")
                continue
            else:
                logger.error(f"Groq API error: {e}")
                # For non-429 errors, we can also fallback or retry, but let's break and try Gemini
                break
                
    # If all Groq keys fail or list is empty, fallback to Gemini
    if settings.GEMINI_API_KEY:
        logger.info("Falling back to Gemini API...")
        try:
            return _get_gemini_response(system_prompt, user_prompt, temperature, max_tokens)
        except Exception as gemini_e:
            logger.error(f"Gemini fallback failed: {gemini_e}")
            raise RuntimeError(f"All LLM providers failed. Last Groq error, Gemini error: {gemini_e}")
            
    raise RuntimeError("LLM request failed: No valid Groq keys available and no Gemini fallback configured.")


def _get_gemini_response(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    gemini_key = settings.GEMINI_API_KEY
    # Use gemini-1.5-pro by default
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={gemini_key}"
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise ValueError(f"Gemini API returned {resp.status_code}: {resp.text}")
        
    data = resp.json()
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return content
    except (KeyError, IndexError) as e:
        raise ValueError(f"Failed to parse Gemini response: {data}") from e
