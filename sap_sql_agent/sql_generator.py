"""
SAP Open SQL Generator - LLM Agent Modulu.

OpenAI API ile dogal dilden SAP Open SQL sorgusu uretimi.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config import OPENAI_MODEL, MAX_CHAT_HISTORY, MAX_TOKENS_RESPONSE, TEMPERATURE
from prompts import get_system_prompt
from metadata_loader import format_metadata_for_prompt, find_relevant_tables


def _get_api_key() -> str:
    """API anahtarini taze okur (st.secrets veya .env)."""
    try:
        import streamlit as st
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    try:
        _env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(_env_path, override=True)
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


def generate_sql(
    question: str,
    tables: dict,
    relationships: list,
    chat_history: list,
) -> tuple:
    """
    Dogal dil sorusundan SAP Open SQL sorgusu uretir.

    Args:
        question: Kullanicinin Turkce sorusu
        tables: Metadata dict (tablo -> alanlar)
        relationships: Iliski listesi
        chat_history: Onceki mesajlar

    Returns:
        (full_response_text, list_of_used_table_names)
    """
    api_key = _get_api_key()
    if not api_key:
        return "API anahtari bulunamadi. .env dosyanizi kontrol edin.", []

    # Token tasarrufu: sadece ilgili tablolari gonder
    relevant_tables, relevant_rels = find_relevant_tables(
        tables, relationships, question
    )

    if not relevant_tables:
        relevant_tables = tables
        relevant_rels = relationships

    metadata_text = format_metadata_for_prompt(relevant_tables, relevant_rels)
    system_prompt = get_system_prompt(metadata_text)

    messages = [{"role": "system", "content": system_prompt}]

    # Chat gecmisini ekle (son N mesaj)
    recent = chat_history[-MAX_CHAT_HISTORY:]
    for msg in recent:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS_RESPONSE,
        )
        content = response.choices[0].message.content

        # Yanittan kullanilan tablolari cikart
        used_tables = extract_used_tables(content, tables)

        return content, used_tables

    except Exception as e:
        return f"Hata olustu: {e}", []


def extract_used_tables(response: str, all_tables: dict) -> list:
    """
    LLM yanitindan kullanilan tablo adlarini cikarir.

    Strateji:
    1. ```abap ... ``` blogundan SQL'i parse et
    2. FROM ve JOIN sonrasi tablo adlarini bul
    3. Bilinen tablo adlariyla karsilastir
    """
    used = set()

    # abap code blogundan SQL'i cikart
    code_match = re.search(r"```abap\s*(.*?)\s*```", response, re.DOTALL)
    if code_match:
        sql_text = code_match.group(1).upper()
        for table_name in all_tables:
            if re.search(rf"\b{re.escape(table_name.upper())}\b", sql_text):
                used.add(table_name)

    # Fallback: tum yanit icerisinde tablo adlarini ara
    if not used:
        upper_response = response.upper()
        for table_name in all_tables:
            if table_name.upper() in upper_response:
                used.add(table_name)

    return list(used)


def extract_sql_block(response: str):
    """Yanittan ```abap ... ``` code blogunu cikarir."""
    match = re.search(r"```abap\s*(.*?)\s*```", response, re.DOTALL)
    return match.group(1).strip() if match else None
