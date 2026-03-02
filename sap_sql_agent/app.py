"""
SAP Open SQL Generator - Ana Uygulama.

Dogal dilden SAP Open SQL sorgusu uretimi icin Streamlit chat arayuzu.
"""
import sys
from pathlib import Path

# Modul import'lari icin path ayarla
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import streamlit.components.v1 as components

from config import APP_TITLE, APP_ICON
from styles import inject_sap_css
from metadata_loader import load_metadata_from_excel, get_table_summary
from sql_generator import generate_sql, extract_sql_block, _get_api_key
from visualizer import create_er_diagram_html, extract_fields_from_sql

# ============================
# SAYFA AYARLARI
# ============================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
)
inject_sap_css()

# ============================
# SESSION STATE BASLAT
# ============================
if "sap_chat_messages" not in st.session_state:
    st.session_state["sap_chat_messages"] = []
if "sap_tables" not in st.session_state:
    st.session_state["sap_tables"] = None
if "sap_relationships" not in st.session_state:
    st.session_state["sap_relationships"] = None

# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.header("Metadata Yukleme")

    uploaded_file = st.file_uploader(
        "SAP Tablo Metadata Excel",
        type=["xlsx"],
        help="Tablolar ve Iliskiler sayfalarini iceren Excel dosyasi yukleyin",
    )

    if uploaded_file is not None:
        tables, relationships, error = load_metadata_from_excel(uploaded_file)
        if error:
            st.error(f"Excel okuma hatasi: {error}")
        else:
            st.session_state["sap_tables"] = tables
            st.session_state["sap_relationships"] = relationships
            st.success(f"{len(tables)} tablo yuklendi")

    # Ornek metadata yukleme butonu
    sample_path = Path(__file__).resolve().parent / "sample_metadata.xlsx"
    if sample_path.exists() and not st.session_state["sap_tables"]:
        if st.button("Ornek Metadata Yukle", use_container_width=True, type="primary"):
            tables, relationships, error = load_metadata_from_excel(str(sample_path))
            if error:
                st.error(f"Hata: {error}")
            else:
                st.session_state["sap_tables"] = tables
                st.session_state["sap_relationships"] = relationships
                st.rerun()

    # Yuklenmis tablo ozeti
    if st.session_state["sap_tables"]:
        st.divider()
        st.subheader("Yuklenmis Tablolar")
        summary = get_table_summary(st.session_state["sap_tables"])
        st.markdown(summary, unsafe_allow_html=True)

    st.divider()

    # API durumu
    api_key = _get_api_key()
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:]
        st.markdown(f'<span class="status-ok">API Bagli</span> ({masked})', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">API anahtari bulunamadi</span>', unsafe_allow_html=True)

    st.divider()

    # Sohbeti temizle
    if st.button("Sohbeti Temizle", use_container_width=True):
        st.session_state["sap_chat_messages"] = []
        st.rerun()

    # Ornek sorular
    st.subheader("Ornek Sorular")
    example_questions = [
        "Malzemenin bulundugu depolari getir",
        "Bu malzemenin rengi nedir?",
        "Serbest stoku sifirdan buyuk malzemeleri listele",
        "Malzeme tipi FERT olan malzemelerin tesis bilgilerini getir",
    ]
    for q in example_questions:
        st.markdown(f"- _{q}_")

# ============================
# ANA ICERIK
# ============================
st.title(f"{APP_ICON} {APP_TITLE}")
st.markdown(
    "SAP tablo metadata'nizi yukleyin ve dogal dilde soru sorarak "
    "**SAP Open SQL (ABAP)** sorgusu uretin."
)

# Metadata yuklenmemisse uyari goster
if not st.session_state["sap_tables"]:
    st.info(
        "Baslamak icin sol panelden SAP tablo metadata Excel dosyanizi yukleyin. "
        "Excel dosyasinda **Tablolar** ve **Iliskiler** adinda iki sayfa olmalidir."
    )
    st.stop()


def _render_assistant_message(msg: dict, msg_index: int):
    """Asistan mesajini SQL blogu, aciklama ve diyagramla render eder."""
    st.markdown(msg["content"])

    used_tables = msg.get("used_tables", [])
    if used_tables:
        tables = st.session_state["sap_tables"]
        rels = st.session_state["sap_relationships"]
        sql_code = extract_sql_block(msg["content"])
        highlighted = extract_fields_from_sql(sql_code) if sql_code else None

        with st.expander("📊 Tablo Iliski Diyagrami", expanded=True):
            html, height = create_er_diagram_html(tables, rels, used_tables, highlighted, sql_text=sql_code)
            display_h = min(height, 650)
            components.html(html, height=display_h, scrolling=True)


# ============================
# CHAT GECMISINI GOSTER
# ============================
for i, msg in enumerate(st.session_state["sap_chat_messages"]):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            _render_assistant_message(msg, i)
        else:
            st.markdown(msg["content"])

# ============================
# CHAT INPUT
# ============================
if not api_key:
    st.warning("OpenAI API anahtari bulunamadi. Lutfen `.env` dosyanizi kontrol edin.")
    st.chat_input("Soru sorun...", disabled=True)
else:
    if prompt := st.chat_input("SAP tablosu hakkinda bir soru sorun..."):
        # Kullanici mesajini kaydet ve goster
        st.session_state["sap_chat_messages"].append({
            "role": "user",
            "content": prompt,
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        # Asistan yaniti
        with st.chat_message("assistant"):
            with st.spinner("SQL sorgusu uretiliyor..."):
                tables = st.session_state["sap_tables"]
                rels = st.session_state["sap_relationships"]
                history = st.session_state["sap_chat_messages"][:-1]

                response_text, used_tables = generate_sql(
                    prompt, tables, rels, history
                )

                # Yapilandirilmis gosterim
                st.markdown(response_text)

                # ER diyagrami
                if used_tables:
                    sql_code = extract_sql_block(response_text)
                    highlighted = extract_fields_from_sql(sql_code) if sql_code else None

                    with st.expander("📊 Tablo Iliski Diyagrami", expanded=True):
                        html, height = create_er_diagram_html(tables, rels, used_tables, highlighted, sql_text=sql_code)
                        display_h = min(height, 650)
                        components.html(html, height=display_h, scrolling=True)

        # Asistan yanitini kaydet
        st.session_state["sap_chat_messages"].append({
            "role": "assistant",
            "content": response_text,
            "used_tables": used_tables,
        })
