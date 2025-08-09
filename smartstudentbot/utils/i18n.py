import json
import os
from typing import Dict, Optional

_translations = {}

def load_translations(lang_dir: str = "lang"):
    """
    Loads all translation files from the specified directory into memory.
    """
    base_path = os.path.join(os.path.dirname(__file__), '..', lang_dir)
    for filename in os.listdir(base_path):
        if filename.endswith(".json"):
            lang_code = filename.split(".")[0]
            try:
                with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
                    _translations[lang_code] = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load language file {filename}. Error: {e}")

def get_text(key: str, lang_code: str = "en") -> str:
    """
    Retrieves a translated string for a given key and language.
    Falls back to English if the key is not found in the specified language.
    """
    lang_code = lang_code.split('-')[0] if lang_code else 'en' # 'fa-IR' -> 'fa'

    # Get translation from the specific language, fallback to English
    translation = _translations.get(lang_code, {}).get(key)
    if translation:
        return translation

    # Fallback to English if key not found in the target language
    fallback_translation = _translations.get("en", {}).get(key)
    if fallback_translation:
        return fallback_translation

    # If key is not found anywhere, return the key itself as a last resort
    return key

# Load translations on module import
load_translations()
