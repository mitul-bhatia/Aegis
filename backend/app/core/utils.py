import json
import logging
from typing import Any, Union

logger = logging.getLogger(__name__)

def extract_json_from_response(text: str) -> Union[dict, list]:
    """
    Safely extract JSON from an LLM response string.
    Finds the first '{' or '[' and the last '}' or ']' and attempts to parse it.
    """
    text = text.strip()
    
    # Try finding the first JSON array or object
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')
    
    # Determine if it's likely an object or array based on which bracket appears first
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        if last_brace != -1 and last_brace >= first_brace:
            json_str = text[first_brace:last_brace+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON object: {e}")
                
    elif first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
        if last_bracket != -1 and last_bracket >= first_bracket:
            json_str = text[first_bracket:last_bracket+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON array: {e}")
                
    # Fallback to standard json.loads if no brackets found (e.g., bare primitive)
    try:
        if not text:
            raise ValueError("Empty response from LLM.")
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Could not extract valid JSON from LLM response. Raw text: {repr(text)}")
