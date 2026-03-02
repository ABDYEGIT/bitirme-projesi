import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from data_loader import connect_db
from benchmarking import (
    load_benchmark_data,
    calculate_yorglass_metrics,
    compare_with_benchmarks,
)
from components import format_currency
from config import DB_PATH
from styles import inject_custom_css, apply_chart_style

st.set_page_config(page_title="Sektör Kıyas", page_icon="🏭", layout="wide")
inject_custom_css()
st.title("🏭 Sektör Kıyas Analizi")
st.markdown("Yorglass'ın cam sektörü içerisindeki konumunu rakip firmalarla karşılaştırın.")

db_path = st.session_state.get("db_path", DB_PATH)
yil = st.session_state.get("yil", 2025)

conn, err = connect_db(db_path)
if err:
    st.error(err)
    st.stop()

benchmark_data = load_benchmark_data()
if not benchmark_data:
    st.error("Benchmark verisi bulunamadı. `sample_data/sektor_benchmark.json` dosyasını kontrol edin.")
    conn.close()
    st.stop()

yorglass_metrics = calculate_yorglass_metrics(conn, yil)
firms_df, dept_df, ranking_df, summary = compare_with_benchmarks(yorglass_metrics, benchmark_data)
conn.close()

st.header("Genel Bakış")

kcol1, kcol2, kcol3, kcol4 = st.columns(4)
with kcol1:
    st.metric(
        "Yorglass Fire Oranı",
        f"%{summary['yorglass_fire']*100:.1f}",
        delta=f"{summary['fire_fark']*100:+.1f}% vs sektör",
        delta_color="inverse",
    )
with kcol2:
    st.metric(
        "Sektör Ort. Fire Oranı",
        f"%{summary['sektor_fire_ort']*100:.1f}",
    )
with kcol3:
    st.metric(
        "Yorglass Birim Maliyet",
        f"{summary['yorglass_maliyet']:,.0f} TL/ton",
        delta=f"{summary['maliyet_fark']:+,.0f} TL vs sektör",
        delta_color="inverse",
    )
with kcol4:
    st.metric(
        "Sektör Ort. Birim Maliyet",
        f"{summary['sektor_maliyet_ort']:,.0f} TL/ton",
    )

kcol5, kcol6, kcol7, kcol8 = st.columns(4)
with kcol5:
    st.metric("Karşılaştırılan Firma", summary["firma_sayisi"])
with kcol6:
    yorglass_kap = yorglass_metrics["kapasite_kullanim"]
    sektor_kap = firms_df[firms_df["Firma"] != "Yorglass"]["Kapasite_Kullanim"].mean()
    st.metric(
        "Kapasite Kullanımı",
        f"%{yorglass_kap*100:.0f}",
        delta=f"{(yorglass_kap - sektor_kap)*100:+.0f}% vs sektör",
        delta_color="normal",
    )
with kcol7:
    st.metric("Güçlü Alanlar", f"{summary['guclu_alanlar']} metrik")
with kcol8:
    st.metric("Geliştirilmeli Alanlar", f"{summary['gelistirilmeli_alanlar']} metrik")

st.divider()

st.header("Firma Performans Karşılaştırması (Radar)")

radar_metrics = ["Fire_Orani", "Birim_Maliyet_Ton", "Kapasite_Kullanim", "ARGE_Oran", "Pazar_Payi"]
radar_labels = ["Fire Oranı\n(düşük=iyi)", "Birim Maliyet\n(düşük=iyi)", "Kapasite\nKullanımı", "AR-GE\nOranı", "Pazar\nPayı"]
inverse_metrics = {"Fire_Orani", "Birim_Maliyet_Ton"}

fig_radar = go.Figure()

colors = {"Yorglass": "#FF5722", "Sisecam": "#2196F3", "Trakya Cam": "#4CAF50",
          "Korfez Cam": "#FF9800", "Anadolu Cam": "#9C27B0"}

for _, row in firms_df.iterrows():
    values = []
    for metric in radar_metrics:
        col_min = firms_df[metric].min()
        col_max = firms_df[metric].max()
        if col_max == col_min:
            norm_val = 0.5
        elif metric in inverse_metrics:
            norm_val = 1 - (row[metric] - col_min) / (col_max - col_min)
        else:
            norm_val = (row[metric] - col_min) / (col_max - col_min)
        values.append(round(norm_val, 3))

    values.append(values[0])
    firma_adi = row["Firma"]
    line_width = 4 if firma_adi == "Yorglass" else 2

    fig_radar.add_trace(go.Scatterpolar(
        r=values,
        theta=radar_labels + [radar_labels[0]],
        name=firma_adi,
        line=dict(width=line_width, color=colors.get(firma_adi, "#999")),
        fill="toself" if firma_adi == "Yorglass" else None,
        opacity=0.8 if firma_adi == "Yorglass" else 0.6,
    ))

apply_chart_style(fig_radar,
    polar=dict(radialaxis=dict(visible=True, range=[0, 1],
               gridcolor="rgba(255,255,255,0.1)")),
    title="Normalize Performans Karşılaştırması (1 = En İyi)",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=12)),
)
st.plotly_chart(fig_radar, use_container_width=True)

st.divider()

st.header("Fire Oranı Karşılaştırması")

fire_sorted = firms_df.sort_values("Fire_Orani")
bar_colors = ["#FF5722" if f == "Yorglass" else "#2196F3" for f in fire_sorted["Firma"]]

fig_fire = go.Figure(go.Bar(
    x=fire_sorted["Firma"],
    y=fire_sorted["Fire_Orani"] * 100,
    marker_color=bar_colors,
    text=[f"%{v*100:.1f}" for v in fire_sorted["Fire_Orani"]],
    textposition="outside",
))
fig_fire.add_hline(
    y=firms_df[firms_df["Firma"] != "Yorglass"]["Fire_Orani"].mean() * 100,
    line_dash="dash", line_color="gray",
    annotation_text="Sektör Ort.",
)
apply_chart_style(fig_fire,
    title="Fire (Hurda/Iskarta) Oranı Karşılaştırması",
    yaxis_title="Fire Oranı (%)", height=400,
)
st.plotly_chart(fig_fire, use_container_width=True)

bcol1, bcol2 = st.columns(2)

with bcol1:
    st.subheader("Birim Maliyet (TL/ton)")
    maliyet_sorted = firms_df.sort_values("Birim_Maliyet_Ton")
    bar_colors_m = ["#FF5722" if f == "Yorglass" else "#4CAF50" for f in maliyet_sorted["Firma"]]
    fig_m = go.Figure(go.Bar(
        x=maliyet_sorted["Firma"],
        y=maliyet_sorted["Birim_Maliyet_Ton"],
        marker_color=bar_colors_m,
        text=[f"{v:,.0f}" for v in maliyet_sorted["Birim_Maliyet_Ton"]],
        textposition="outside",
    ))
    apply_chart_style(fig_m, yaxis_title="TL/ton", height=400)
    st.plotly_chart(fig_m, use_container_width=True)

with bcol2:
    st.subheader("Kapasite Kullanım Oranı")
    kap_sorted = firms_df.sort_values("Kapasite_Kullanim", ascending=False)
    bar_colors_k = ["#FF5722" if f == "Yorglass" else "#FF9800" for f in kap_sorted["Firma"]]
    fig_k = go.Figure(go.Bar(
        x=kap_sorted["Firma"],
        y=kap_sorted["Kapasite_Kullanim"] * 100,
        marker_color=bar_colors_k,
        text=[f"%{v*100:.0f}" for v in kap_sorted["Kapasite_Kullanim"]],
        textposition="outside",
    ))
    apply_chart_style(fig_k, yaxis_title="Kullanım (%)", height=400)
    st.plotly_chart(fig_k, use_container_width=True)

st.divider()

st.header("Departman Bütçe Dağılımı Karşılaştırması")

dept_melted = dept_df.melt(id_vars="Firma", var_name="Departman", value_name="Oran")
fig_dept = px.bar(
    dept_melted, x="Firma", y="Oran", color="Departman",
    title="Firma Bazlı Departman Bütçe Dağılımı (%)",
    text_auto=".0%",
    color_discrete_map={
        "Uretim": "#2196F3", "Bakim": "#FF9800", "Kalite": "#4CAF50",
        "Lojistik": "#9C27B0", "IT": "#00BCD4", "IK": "#E91E63",
    },
)
apply_chart_style(fig_dept, barmode="stack", height=500, yaxis_tickformat=".0%")
st.plotly_chart(fig_dept, use_container_width=True)

st.divider()

st.header("Yorglass Pozisyon Analizi")

for _, row in ranking_df.iterrows():
    sira = row["Yorglass_Sira"]
    toplam = row["Toplam_Firma"]
    durum = row["Durum"]

    if durum == "Iyi":
        icon = "🟢"
    elif durum == "Orta":
        icon = "🟡"
    else:
        icon = "🔴"

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"{icon} **{row['Metrik']}**: {sira}/{toplam} sırada "
                    f"— Yorglass: `{row['Yorglass']}` | Sektör Ort: `{row['Sektor_Ortalama']}` "
                    f"| En İyi: `{row['En_Iyi']}` ({row['En_Iyi_Firma']})")
    with col_b:
        st.markdown(f"**{durum}**")

st.divider()

st.header("Detay Tablosu")

with st.expander("Tüm Firma Metrikleri", expanded=True):
    display_df = firms_df.copy()
    display_df["Fire_Orani"] = (display_df["Fire_Orani"] * 100).round(1).astype(str) + "%"
    display_df["Pazar_Payi"] = (display_df["Pazar_Payi"] * 100).round(1).astype(str) + "%"
    display_df["Kapasite_Kullanim"] = (display_df["Kapasite_Kullanim"] * 100).round(0).astype(str) + "%"
    display_df["ARGE_Oran"] = (display_df["ARGE_Oran"] * 100).round(1).astype(str) + "%"

    display_df = display_df.rename(columns={
        "Firma": "Firma",
        "Tip": "Ölçek",
        "Uretim_Butcesi_TL": "Üretim Bütçesi (TL)",
        "Fire_Orani": "Fire %",
        "Calisan_Sayisi": "Çalışan",
        "Yillik_Ciro_TL": "Yıllık Ciro (TL)",
        "Pazar_Payi": "Pazar Payı",
        "Birim_Maliyet_Ton": "Birim Maliyet (TL/ton)",
        "Kapasite_Kullanim": "Kapasite %",
        "ARGE_Oran": "AR-GE %",
        "Fabrika_Sayisi": "Fabrika",
    })

    st.dataframe(display_df, use_container_width=True, hide_index=True)

with st.expander("Departman Dağılımı Detayı"):
    dept_display = dept_df.copy()
    for col in ["Uretim", "Bakim", "Kalite", "Lojistik", "IT", "IK"]:
        dept_display[col] = (dept_display[col] * 100).round(1).astype(str) + "%"
    st.dataframe(dept_display, use_container_width=True, hide_index=True)
