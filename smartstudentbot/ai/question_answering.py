import json
from typing import Optional

# from utils.logger import logger # To be re-enabled later
# from utils.common import check_json_version
from config import FEATURE_FLAGS

# --- Lazy-loading for NLP model ---
_nlp_pipeline = None

def get_nlp_pipeline():
    """
    Lazily loads and returns the NLP pipeline.
    This function will only load the model on its first call.
    """
    global _nlp_pipeline
    if _nlp_pipeline is None:
        # Only import and load if the AI feature is enabled
        if FEATURE_FLAGS.get("AI"):
            print("AI feature enabled. Loading NLP model...") # Replace with logger
            try:
                from transformers import pipeline
                # Using a lighter model for faster loading in case it's ever used in dev
                _nlp_pipeline = pipeline("sentence-similarity", model="distilbert-base-multilingual-cased")
                print("NLP model loaded successfully.")
            except ImportError:
                print("Warning: 'transformers' library not installed. AI features will be disabled.")
                _nlp_pipeline = "failed" # Mark as failed to avoid retrying
            except Exception as e:
                print(f"Error loading NLP model: {e}")
                _nlp_pipeline = "failed"
        else:
            _nlp_pipeline = "disabled" # Mark as disabled

    return _nlp_pipeline if _nlp_pipeline not in ["failed", "disabled"] else None

# --- Main Answer Function ---
async def get_answer(question: str) -> Optional[str]:
    """
    Finds an answer to a question using a multi-layered approach.
    1. Checks a simple Q&A JSON file for direct matches.
    2. (If AI enabled) Uses a semantic search model on a knowledge base.
    """
    # logger.debug(f"Processing question: {question}")

    # Layer 1: Check for a direct match in a simple Q&A file
    # data = check_json_version("qna.json")
    # if data and question in data.get("questions", {}):
    #     return data["questions"][question]

    # Layer 2: Use the NLP model for semantic search
    nlp = get_nlp_pipeline()
    if nlp:
        # In a real implementation, this would search through `knowledge.json`
        # and find the most similar question.
        # For now, it's a placeholder.
        # logger.info(f"Using NLP model to find answer for: {question}")
        return "پاسخ از مدل AI (شبیه‌سازی شده)"

    # logger.info(f"No answer found for question: {question}")
    return None # Return None if no answer is found
