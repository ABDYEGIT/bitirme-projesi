"""
Yorglass Finans - Chatbot Asistan Sayfasi.

Butce, siparis ve malzeme verileri hakkinda soru-cevap.
"""
import streamlit as st

from data_loader import (
    connect_db,
    load_budget_monthly_detail,
    load_budget_matrix,
    load_order_summary,
    load_material_summary_by_group,
    load_cross_department_purchases,
)
from chatbot import ask_chatbot, prepare_data_context
from ai_commentary import _get_api_key
from config import DB_PATH
from styles import inject_custom_css
from benchmarking import (
    load_benchmark_data,
    calculate_yorglass_metrics,
    compare_with_benchmarks,
    get_benchmark_context_for_chatbot,
)

# ============================
# SAYFA AYARLARI
# ============================
st.set_page_config(
    page_title="Yorglass - Chatbot Asistan",
    page_icon="💬",
    layout="wide",
)
inject_custom_css()


# ============================
# VERI YUKLEME (CACHE)
# ============================
@st.cache_data(ttl=300)
def _load_chat_context(db_path):
    """Veritabanindan chatbot icin veri context'i yukle."""
    conn, err = connect_db(db_path)
    if err or conn is None:
        return ""

    try:
        budget_monthly = load_budget_monthly_detail(conn, 2025)
        budget_matrix = load_budget_matrix(conn, 2025)
        order_summary = load_order_summary(conn)
        material_summary = load_material_summary_by_group(conn)
        cross_dept = load_cross_department_purchases(conn)
    finally:
        conn.close()

    # Aylik detay (her departman×lokasyon×ay)
    budget_monthly_text = budget_monthly.to_string(index=False) if not budget_monthly.empty else ""
    # Yillik toplamlar (departman×lokasyon)
    budget_yearly_text = budget_matrix.to_string(index=False) if not budget_matrix.empty else ""
    # Iki veriyi birlestir
    budget_text = ""
    if budget_monthly_text:
        budget_text += "AYLIK KIRILIM (Her ay, her departman, her lokasyon):\n" + budget_monthly_text
    if budget_yearly_text:
        budget_text += "\n\nYILLIK TOPLAMLAR (Departman x Lokasyon):\n" + budget_yearly_text

    order_text = order_summary.to_string(index=False) if not order_summary.empty else ""
    material_text = material_summary.to_string(index=False) if not material_summary.empty else ""

    # Capraz departman alimlari ozet
    cross_dept_text = ""
    if not cross_dept.empty:
        # Departman bazli ozet olustur
        cross_summary = cross_dept.groupby(
            ["uretim_yeri", "alan_departman", "sorumlu_departman"]
        )["toplam_tutar"].agg(["count", "sum"]).reset_index()
        cross_summary.columns = ["Uretim_Yeri", "Alan_Departman", "Sorumlu_Departman", "Alim_Sayisi", "Toplam_Tutar"]
        cross_dept_text = cross_summary.to_string(index=False)

    # Sektor benchmark verisi
    benchmark_text = ""
    benchmark_data = load_benchmark_data()
    if benchmark_data:
        conn2, err2 = connect_db(db_path)
        if not err2 and conn2:
            try:
                yorglass_metrics = calculate_yorglass_metrics(conn2, 2025)
                firms_df, dept_df, ranking_df, summary_bm = compare_with_benchmarks(
                    yorglass_metrics, benchmark_data
                )
                benchmark_text = get_benchmark_context_for_chatbot(firms_df, ranking_df, summary_bm)
            finally:
                conn2.close()

    return prepare_data_context(budget_text, order_text, material_text, cross_dept_text, benchmark_text)


# ============================
# SESSION STATE BASLAT
# ============================
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []


# ============================
# SIDEBAR
# ============================
with st.sidebar:
    st.header("💬 Chatbot Ayarlari")

    # API durumu
    api_key = _get_api_key()
    if api_key:
        st.success(f"✅ API bagli ({api_key[:8]}...{api_key[-4:]})")
    else:
        st.error("❌ API anahtari bulunamadi")

    st.divider()

    # Sohbeti temizle
    if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
        st.session_state["chat_messages"] = []
        st.rerun()

    # Mesaj sayisi
    msg_count = len(st.session_state["chat_messages"])
    st.caption(f"Mesaj sayisi: {msg_count}")


# ============================
# ANA ICERIK
# ============================
st.title("💬 Yorglass Finans Asistani")
st.markdown(
    "Butce, siparis ve malzeme verileri hakkinda sorularinizi sorun. "
    "Asistan, 2025 yili verilerini kullanarak sorularinizi yanitlayacaktir."
)

# Veri context'i yukle
data_context = _load_chat_context(DB_PATH)

if not data_context:
    st.error("Veritabanina baglanilamadi. Lutfen veritabani dosyasini kontrol edin.")
    st.stop()


# ============================
# CHAT GECMISINI GOSTER
# ============================
for msg in st.session_state["chat_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ============================
# CHAT INPUT
# ============================
if not api_key:
    st.warning(
        "⚠️ Chatbot icin OpenAI API anahtari gereklidir. "
        "`.env` dosyasina `OPENAI_API_KEY=sk-...` ekleyin."
    )
    st.chat_input("Soru sorun...", disabled=True)
else:
    if prompt := st.chat_input("Butce, siparis veya malzeme hakkinda bir soru sorun..."):
        # Kullanici mesajini goster ve kaydet
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Asistan yaniti
        with st.chat_message("assistant"):
            with st.spinner("Dusunuyor..."):
                # Onceki mesajlari (kullanicinin yeni mesaji haric) gecmis olarak gonder
                history = st.session_state["chat_messages"][:-1]
                response = ask_chatbot(prompt, data_context, history)
                st.markdown(response)

        # Asistan yanitini kaydet
        st.session_state["chat_messages"].append({"role": "assistant", "content": response})
