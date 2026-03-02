import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from data_loader import connect_db, load_budget_matrix
from comparison import (
    calculate_utilization_matrix,
    rank_departments,
    location_totals,
    department_type_totals,
    cross_location_comparison,
    company_kpis,
)
from components import format_currency
from config import DB_PATH, FABRIKA_DEPT_KODLARI
from styles import inject_custom_css, apply_chart_style

st.set_page_config(page_title="Genel Karşılaştırma", page_icon="📊", layout="wide")
inject_custom_css()
st.title("Genel Karşılaştırma")
st.markdown("Tüm işletme ve departmanların bütçe performansını karşılaştırın.")

db_path = st.session_state.get("db_path", DB_PATH)
yil = st.session_state.get("yil", 2025)

conn, err = connect_db(db_path)
if err:
    st.error(err)
    st.stop()

matrix = load_budget_matrix(conn, yil)
if matrix.empty:
    st.warning("Veri bulunamadı.")
    conn.close()
    st.stop()

util_matrix = calculate_utilization_matrix(matrix)
kpis = company_kpis(matrix)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Toplam Planlanan", format_currency(kpis["toplam_planlanan"]))
with c2:
    st.metric("Toplam Gerçekleşen", format_currency(kpis["toplam_gerceklesen"]))
with c3:
    st.metric("Kalan Bütçe", format_currency(kpis["toplam_kalan"]))
with c4:
    st.metric("Kullanım Oranı", f"%{kpis['kullanim_orani']}")

st.divider()

st.header("Kullanım Oranı Haritası")

pivot = util_matrix.pivot_table(
    values="Kullanim_Orani", index="yer_ad", columns="dept_ad", aggfunc="first",
)

fig_heat = go.Figure(data=go.Heatmap(
    z=pivot.values,
    x=pivot.columns.tolist(),
    y=pivot.index.tolist(),
    colorscale="RdYlGn_r",
    text=pivot.values.round(1),
    texttemplate="%{text}%",
    colorbar=dict(title="Kullanım %"),
))
apply_chart_style(fig_heat,
    title="İşletme x Departman Bütçe Kullanım Oranı (%)", height=400,
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

st.header("Departman Sıralaması")

col1, col2 = st.columns(2)
ranked = rank_departments(matrix, by="Kullanim_Orani", ascending=True)

with col1:
    st.subheader("En Verimli 5 Departman")
    top5 = ranked.head(5)
    fig_top = go.Figure(go.Bar(
        y=top5["Etiket"], x=top5["Kullanim_Orani"],
        orientation="h", marker_color="#4CAF50",
        text=top5["Kullanim_Orani"].apply(lambda x: f"%{x}"),
        textposition="outside",
    ))
    apply_chart_style(fig_top, height=300, xaxis_title="Kullanım Oranı (%)")
    st.plotly_chart(fig_top, use_container_width=True)

with col2:
    st.subheader("En Çok Aşan 5 Departman")
    bottom5 = ranked.tail(5).iloc[::-1]
    fig_bot = go.Figure(go.Bar(
        y=bottom5["Etiket"], x=bottom5["Kullanim_Orani"],
        orientation="h", marker_color="#F44336",
        text=bottom5["Kullanim_Orani"].apply(lambda x: f"%{x}"),
        textposition="outside",
    ))
    apply_chart_style(fig_bot, height=300, xaxis_title="Kullanım Oranı (%)")
    st.plotly_chart(fig_bot, use_container_width=True)

st.divider()

st.header("İşletme Bazlı Toplamlar")

loc_df = location_totals(matrix)
loc_df["Kullanim_Orani"] = (loc_df["Toplam_Gerceklesen"] / loc_df["Toplam_Planlanan"] * 100).round(2)

fig_loc = go.Figure()
fig_loc.add_trace(go.Bar(
    x=loc_df["yer_ad"], y=loc_df["Toplam_Planlanan"],
    name="Planlanan", marker_color="#2196F3",
))
fig_loc.add_trace(go.Bar(
    x=loc_df["yer_ad"], y=loc_df["Toplam_Gerceklesen"],
    name="Gerçekleşen", marker_color="#FF9800",
))
apply_chart_style(fig_loc, barmode="group", height=400, yaxis_title="Tutar (TL)")
st.plotly_chart(fig_loc, use_container_width=True)

st.divider()

st.header("Departman Tipi Karşılaştırması")

dept_types = department_type_totals(matrix)
dept_types["Kullanim_Orani"] = (
    dept_types["Toplam_Gerceklesen"] / dept_types["Toplam_Planlanan"] * 100
).round(2)

fig_dept = go.Figure()
fig_dept.add_trace(go.Bar(
    x=dept_types["dept_ad"], y=dept_types["Toplam_Planlanan"],
    name="Planlanan", marker_color="#2196F3",
))
fig_dept.add_trace(go.Bar(
    x=dept_types["dept_ad"], y=dept_types["Toplam_Gerceklesen"],
    name="Gerçekleşen", marker_color="#FF9800",
))
apply_chart_style(fig_dept,
    barmode="group", height=400, yaxis_title="Tutar (TL)",
    title="Departman Tipi Bazlı Bütçe",
)
st.plotly_chart(fig_dept, use_container_width=True)

st.divider()

st.header("Lokasyonlar Arası Departman Karşılaştırması")

fabrika_deptlari = util_matrix[util_matrix["dept_kod"].isin(FABRIKA_DEPT_KODLARI)]
dept_isimleri = fabrika_deptlari["dept_ad"].unique().tolist()

if dept_isimleri:
    secili_dept_ad = st.selectbox("Departman Seçin:", dept_isimleri)

    if secili_dept_ad:
        secili_dept_kod = fabrika_deptlari[fabrika_deptlari["dept_ad"] == secili_dept_ad]["dept_kod"].iloc[0]
        cross_df = cross_location_comparison(util_matrix, secili_dept_kod)

        if not cross_df.empty:
            fig_cross = go.Figure()
            fig_cross.add_trace(go.Bar(
                x=cross_df["yer_ad"], y=cross_df["Toplam_Planlanan"],
                name="Planlanan", marker_color="#2196F3",
            ))
            fig_cross.add_trace(go.Bar(
                x=cross_df["yer_ad"], y=cross_df["Toplam_Gerceklesen"],
                name="Gerçekleşen", marker_color="#FF9800",
            ))
            apply_chart_style(fig_cross,
                title=f"{secili_dept_ad} - Lokasyonlar Arası Karşılaştırma",
                barmode="group", height=400, yaxis_title="Tutar (TL)",
            )
            st.plotly_chart(fig_cross, use_container_width=True)

            fig_util = go.Figure(go.Bar(
                x=cross_df["yer_ad"], y=cross_df["Kullanim_Orani"],
                marker_color=["#4CAF50" if v <= 100 else "#F44336" for v in cross_df["Kullanim_Orani"]],
                text=cross_df["Kullanim_Orani"].apply(lambda x: f"%{x}"),
                textposition="outside",
            ))
            apply_chart_style(fig_util,
                title=f"{secili_dept_ad} - Kullanım Oranı Karşılaştırması",
                height=350, yaxis_title="Kullanım %",
            )
            st.plotly_chart(fig_util, use_container_width=True)

st.divider()

st.header("Detay Tablosu")

with st.expander("Tüm Departman Verileri", expanded=False):
    display_df = util_matrix[["yer_ad", "dept_ad", "Toplam_Planlanan", "Toplam_Gerceklesen", "Kullanim_Orani", "Fark"]].copy()
    display_df.columns = ["İşletme", "Departman", "Planlanan (TL)", "Gerçekleşen (TL)", "Kullanım %", "Fark (TL)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

conn.close()
