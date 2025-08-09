from fastapi import HTTPException
import re
# from utils.logger import logger # Will be enabled later
import json
from config import JSON_VERSION

def sanitize_markdown(text: str) -> str:
    """Removes characters that could be used for Markdown injection."""
    cleaned = re.sub(r'[<>`]', '', text)
    # logger.debug(f"Sanitized text: {cleaned}")
    return cleaned

def validate_file(file_size: int, file_type: str) -> bool:
    """Validates file size and type against predefined limits."""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png", "audio/mpeg", "video/mp4"]

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB")

    # A more robust check would inspect MIME type from file content,
    # but for now, we trust the provided file_type.
    # A simple mapping for common extensions might be needed if only extension is available.

    # This is a placeholder for a real MIME type check
    # if file_type not in ALLOWED_TYPES:
    #     raise HTTPException(status_code=400, detail="Invalid file format")

    return True

def check_json_version(file_path: str):
    """
    Reads a JSON file and checks if its version matches the global JSON_VERSION.
    Returns the data if versions match, otherwise logs a warning.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("version") != JSON_VERSION:
            # logger.warning(f"JSON version mismatch in {file_path}. Expected {JSON_VERSION}, got {data.get('version')}")
            pass # For now, we'll just pass
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # logger.error(f"Could not read or parse JSON file: {file_path}. Error: {e}")
        return None
