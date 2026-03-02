"""
SAP Open SQL Generator - Konfigurasyon.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parent.parent
    _env_path = _project_root / ".env"
    load_dotenv(_env_path, override=True)
except ImportError:
    pass

# API key: once st.secrets, sonra env var
def _resolve_api_key() -> str:
    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")

OPENAI_API_KEY = _resolve_api_key()
OPENAI_MODEL = "gpt-4o-mini"

# SAP Agent ayarlari
APP_TITLE = "SAP Open SQL Generator"
APP_ICON = "\U0001f527"
MAX_CHAT_HISTORY = 10
MAX_TOKENS_RESPONSE = 2000
TEMPERATURE = 0.2
