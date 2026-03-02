"""
Yorglass Finans - Departman Detay Sayfasi.

Tek bir departmanin detayli butce, siparis, malzeme analizi ve AI yorumu.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data_loader import (
    connect_db,
    get_uretim_yerleri,
    get_uretim_yeri_departmanlar,
    load_budget_data,
    load_order_data,
    load_malzeme_hareketleri,
    load_cross_department_purchases,
    load_material_summary_by_group,
)
from analysis import (
    merge_budget_with_orders,
    calculate_budget_variance,
    calculate_remaining_budget,
    calculate_spending_trend,
    calculate_budget_kpis,
    analyze_orders,
    calculate_cross_dept_budget_correction,
)
from components import (
    format_currency,
    render_kpi_cards,
    render_budget_bar_chart,
    render_variance_chart,
    render_cumulative_chart,
    render_stacked_spending_chart,
    render_order_section,
    render_optimal_budget_section,
    render_ai_commentary_section,
    render_cross_dept_correction_chart,
)
from config import DB_PATH, FABRIKA_DEPT_KODLARI
from styles import inject_custom_css, apply_chart_style

st.set_page_config(page_title="Departman Detay", page_icon="📋", layout="wide")
inject_custom_css()
st.title("Departman Detay Analizi")

# --- DB Baglantisi ---
db_path = st.session_state.get("db_path", DB_PATH)
yil = st.session_state.get("yil", 2025)

conn, err = connect_db(db_path)
if err:
    st.error(err)
    st.stop()

# ============================
# SIDEBAR: DEPARTMAN SECIMI
# ============================
st.sidebar.header("Departman Secimi")

yerler = get_uretim_yerleri(conn)
if yerler.empty:
    st.error("Uretim yeri verisi bulunamadi.")
    conn.close()
    st.stop()

yer_secim = st.sidebar.selectbox(
    "Isletme:", yerler["ad"].tolist(), key="dept_yer_secim",
)
yer_row = yerler[yerler["ad"] == yer_secim].iloc[0]
yer_id = int(yer_row["id"])
yer_kod = yer_row["kod"]

deptlar = get_uretim_yeri_departmanlar(conn, yer_id)
if deptlar.empty:
    st.warning("Bu isletmede departman bulunamadi.")
    conn.close()
    st.stop()

dept_secim = st.sidebar.selectbox(
    "Departman:", deptlar["ad"].tolist(), key="dept_dept_secim",
)
dept_row = deptlar[deptlar["ad"] == dept_secim].iloc[0]
dept_id = int(dept_row["id"])
dept_kod = dept_row["kod"]

st.markdown(f"**{yer_secim}** → **{dept_secim}** departmani ({yil})")

# ============================
# VERI YUKLE
# ============================
budget_data = load_budget_data(conn, yer_id, dept_id, yil)
order_data = load_order_data(conn, yer_id, dept_id)

if budget_data is None:
    st.warning("Secilen departman icin butce verisi bulunamadi.")
    conn.close()
    st.stop()

# --- Butce + Siparis Birlestirme ---
if order_data is not None:
    merged_budget = merge_budget_with_orders(budget_data, order_data)
    order_analysis = analyze_orders(order_data)
else:
    merged_budget = budget_data.copy()
    merged_budget["Siparis_Tutari"] = 0
    merged_budget["Efektif_Gerceklesen"] = merged_budget["Gerceklesen"]
    order_analysis = None

# --- Hesaplamalar ---
variance_df = calculate_budget_variance(merged_budget)
remaining_df = calculate_remaining_budget(merged_budget)
trend_df = calculate_spending_trend(merged_budget)
kpis = calculate_budget_kpis(merged_budget)

# ============================
# KPI KARTLARI
# ============================
st.header("Temel Gostergeler")
render_kpi_cards(kpis)

st.divider()

# ============================
# BUTCE GRAFIKLERI
# ============================
st.header("Butce Grafikleri")
render_budget_bar_chart(variance_df)

gcol1, gcol2 = st.columns(2)
with gcol1:
    render_variance_chart(variance_df)
with gcol2:
    render_cumulative_chart(remaining_df)

if order_data is not None:
    render_stacked_spending_chart(variance_df)

# ============================
# SIPARIS ANALIZI
# ============================
if order_analysis:
    st.divider()
    render_order_section(order_data, order_analysis)

# ============================
# CAPRAZ DEPARTMAN BUTCE DUZELTME ANALIZI
# ============================
if dept_kod in FABRIKA_DEPT_KODLARI:
    # Bu departmanin baska dept sorumlulugundan yaptigi alimlar
    cross_dept_made = load_cross_department_purchases(conn, yer_id, dept_id)

    # Baska departmanlarin bu departmanin sorumlulugundan aldiklari
    # Tum capraz alimlari cek, sonra bu dept'in sorumlu oldugu alanlari filtrele
    all_cross = load_cross_department_purchases(conn, yer_id)
    cross_dept_received = all_cross[all_cross["sorumlu_dept_kod"] == dept_kod] if not all_cross.empty else all_cross

    if (not cross_dept_made.empty) or (not cross_dept_received.empty):
        st.divider()
        correction_df, correction_ozet = calculate_cross_dept_budget_correction(
            merged_budget, cross_dept_made, cross_dept_received,
        )
        render_cross_dept_correction_chart(
            correction_df, correction_ozet,
            dept_adi=dept_secim, key_prefix="dept_",
        )

        # Detay tablosu
        with st.expander("Capraz Alim Detaylari"):
            if not cross_dept_made.empty:
                st.markdown(f"**Bu departmanin baska departman sorumlulugundan yaptigi alimlar** ({len(cross_dept_made)} hareket)")
                st.dataframe(
                    cross_dept_made[["sorumlu_departman", "mal_grubu", "malzeme_adi", "tarih", "toplam_tutar"]].rename(
                        columns={
                            "sorumlu_departman": "Sorumlu Dept.",
                            "mal_grubu": "Mal Grubu",
                            "malzeme_adi": "Malzeme",
                            "tarih": "Tarih",
                            "toplam_tutar": "Tutar (TL)",
                        }
                    ),
                    use_container_width=True, hide_index=True,
                )
            if not cross_dept_received.empty:
                st.markdown(f"**Baska departmanlarin bu departman sorumlulugundan aldiklari** ({len(cross_dept_received)} hareket)")
                st.dataframe(
                    cross_dept_received[["alan_departman", "mal_grubu", "malzeme_adi", "tarih", "toplam_tutar"]].rename(
                        columns={
                            "alan_departman": "Alan Dept.",
                            "mal_grubu": "Mal Grubu",
                            "malzeme_adi": "Malzeme",
                            "tarih": "Tarih",
                            "toplam_tutar": "Tutar (TL)",
                        }
                    ),
                    use_container_width=True, hide_index=True,
                )

# ============================
# MALZEME ANALIZI (SADECE FABRIKA DEPARTMANLARI)
# ============================
if dept_kod in FABRIKA_DEPT_KODLARI:
    st.divider()
    st.header("Malzeme Analizi")

    # Mal grubu bazli ozet
    mat_summary = load_material_summary_by_group(conn, yer_id, dept_id)
    if not mat_summary.empty:
        st.subheader("Mal Grubu Bazli Harcamalar")

        fig_mg = px.bar(
            mat_summary, x="Mal_Grubu", y="Toplam_Tutar",
            color="Sorumlu_Departman",
            title="Mal Grubu Bazli Toplam Harcama",
            text_auto=True,
        )
        apply_chart_style(fig_mg, height=400)
        st.plotly_chart(fig_mg, use_container_width=True)

        st.dataframe(
            mat_summary.rename(columns={
                "Mal_Grubu": "Mal Grubu",
                "Sorumlu_Departman": "Sorumlu Dept.",
                "Hareket_Sayisi": "Hareket",
                "Toplam_Tutar": "Toplam (TL)",
                "Cross_Dept_Tutar": "Dept. Arasi (TL)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Departmanlar arasi alimlar
    cross_dept = load_cross_department_purchases(conn, yer_id, dept_id)
    if not cross_dept.empty:
        st.subheader("Departmanlar Arasi Alimlar")
        st.info(
            f"Bu departmanin baska departmanlarin sorumlu oldugu mal gruplarindan "
            f"yaptigi alimlar ({len(cross_dept)} hareket)"
        )

        cross_summary = cross_dept.groupby(["sorumlu_departman", "mal_grubu"]).agg(
            Hareket_Sayisi=("toplam_tutar", "count"),
            Toplam_Tutar=("toplam_tutar", "sum"),
        ).reset_index().sort_values("Toplam_Tutar", ascending=False)

        fig_cross = px.bar(
            cross_summary, x="mal_grubu", y="Toplam_Tutar",
            color="sorumlu_departman",
            title="Departmanlar Arasi Alim Dagilimi",
            text_auto=True,
        )
        apply_chart_style(fig_cross, height=400)
        st.plotly_chart(fig_cross, use_container_width=True)

        toplam_cross = cross_dept["toplam_tutar"].sum()
        st.metric("Toplam Dept. Arasi Alim Tutari", format_currency(toplam_cross))

        with st.expander("Departmanlar Arasi Alim Detaylari"):
            st.dataframe(
                cross_dept[["mal_grubu", "sorumlu_departman", "malzeme_adi", "tarih", "miktar", "toplam_tutar"]].rename(
                    columns={
                        "mal_grubu": "Mal Grubu",
                        "sorumlu_departman": "Sorumlu Dept.",
                        "malzeme_adi": "Malzeme",
                        "tarih": "Tarih",
                        "miktar": "Miktar",
                        "toplam_tutar": "Tutar (TL)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.success("Bu departmanin baska departmanlardan malzeme alimi bulunmuyor.")

# ============================
# OPTIMUM BUTCE
# ============================
st.divider()
render_optimal_budget_section(merged_budget, key_prefix="dept_")

# ============================
# AI YORUM
# ============================
st.divider()
render_ai_commentary_section(
    kpis, order_analysis, variance_df, order_data,
    dept_adi=dept_secim, yer_adi=yer_secim, key_prefix="dept_",
)

# ============================
# DETAY TABLOLARI
# ============================
st.divider()
st.header("Detay Tablolari")

with st.expander("Butce Sapma Detaylari", expanded=False):
    display_cols = [
        "Ay", "Planlanan", "Gerceklesen", "Siparis_Tutari",
        "Efektif_Gerceklesen", "Fark", "Sapma_Yuzde", "Kullanim_Orani",
    ]
    available_cols = [c for c in display_cols if c in variance_df.columns]
    st.dataframe(variance_df[available_cols], use_container_width=True, hide_index=True)

with st.expander("Kalan Butce Detaylari", expanded=False):
    st.dataframe(remaining_df, use_container_width=True, hide_index=True)

if order_data is not None:
    with st.expander("Siparis Detaylari", expanded=False):
        st.dataframe(order_data, use_container_width=True, hide_index=True)

conn.close()
