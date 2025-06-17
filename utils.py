# utils.py
import os
import logging

def get_env_variable(key: str, default: str = None) -> str:
    """
    Safely retrieve environment variables.
    Raises an error if not found and no default is provided.
    """
    value = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Missing required env variable: {key}")
    return value

def sanitize_text(text: str) -> str:
    """
    Basic HTML sanitization — strips potentially dangerous tags or symbols.
    Expand this as needed.
    """
    return text.replace("<", "&lt;").replace(">", "&gt;")

def log_info(message: str):
    """
    Central logging utility.
    """
    logging.info(f"[FeedForwarder] {message}")
