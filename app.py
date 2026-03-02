"""
Yorglass Finans - Ana Sayfa.

Sirket geneli butce ozeti ve navigasyon.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from config import DB_PATH, SIRKET_ADI, VARSAYILAN_FIRE_ORANI, FIRE_ETKI_AGIRLIKLARI
from data_loader import connect_db, get_uretim_yerleri, load_budget_matrix, load_order_summary
from comparison import company_kpis, location_totals
from forecasting import generate_budget_forecast
from components import format_currency
from benchmarking import load_benchmark_data, calculate_yorglass_metrics, compare_with_benchmarks
from styles import inject_custom_css, apply_chart_style, render_nav_card

# --- Sayfa Ayarlari ---
st.set_page_config(
    page_title=f"{SIRKET_ADI} Butce Analiz Sistemi",
    page_icon="🏭",
    layout="wide",
)

inject_custom_css()

st.title(f"🏭 {SIRKET_ADI} Butce Analiz Sistemi")
st.markdown("Tum isletme ve departmanlarin butce, siparis ve malzeme verilerini analiz edin.")

# --- Sidebar: Ayarlar ---
st.sidebar.header("Ayarlar")
db_path = st.sidebar.text_input("Veritabani Yolu:", value=DB_PATH, key="db_path_main")
yil = st.sidebar.selectbox("Yil:", [2025, 2024, 2026], index=0, key="yil_main")

# Session state'e kaydet (diger sayfalar okuyacak)
st.session_state["db_path"] = db_path
st.session_state["yil"] = yil

# --- DB Baglantisi ---
conn, err = connect_db(db_path)
if err:
    st.error(f"Veritabani baglantisi basarisiz: {err}")
    st.info("Ornek veritabani olusturmak icin: `python create_database.py`")
    st.stop()

# --- Veri Yukle ---
matrix = load_budget_matrix(conn, yil)
if matrix.empty:
    st.warning("Secilen yil icin butce verisi bulunamadi.")
    conn.close()
    st.stop()

order_summary = load_order_summary(conn)
kpis = company_kpis(matrix)

# ============================
# SIRKET GENELI KPI
# ============================
st.header("Sirket Geneli Ozet")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Toplam Planlanan Butce", format_currency(kpis["toplam_planlanan"]))
with c2:
    st.metric("Toplam Gerceklesen", format_currency(kpis["toplam_gerceklesen"]))
with c3:
    st.metric("Kalan Butce", format_currency(kpis["toplam_kalan"]))
with c4:
    st.metric("Kullanim Orani", f"%{kpis['kullanim_orani']}")

st.progress(min(kpis["kullanim_orani"] / 100, 1.0))

st.caption(f"{kpis['lokasyon_sayisi']} isletme, {kpis['departman_sayisi']} departman")

st.divider()

# ============================
# ISLETME BAZLI KARSILASTIRMA
# ============================
st.header("Isletme Bazli Butce Dagilimi")

loc_totals = location_totals(matrix)
loc_totals["Kullanim_Orani"] = (loc_totals["Toplam_Gerceklesen"] / loc_totals["Toplam_Planlanan"] * 100).round(2)

fig_loc = go.Figure()
fig_loc.add_trace(go.Bar(
    x=loc_totals["yer_ad"], y=loc_totals["Toplam_Planlanan"],
    name="Planlanan", marker_color="#2196F3",
))
fig_loc.add_trace(go.Bar(
    x=loc_totals["yer_ad"], y=loc_totals["Toplam_Gerceklesen"],
    name="Gerceklesen", marker_color="#FF9800",
))
apply_chart_style(fig_loc,
    title="Isletme Bazli Toplam Butce",
    barmode="group", height=450, yaxis_title="Tutar (TL)",
)
st.plotly_chart(fig_loc, use_container_width=True)

# Kullanim orani tablosu
st.dataframe(
    loc_totals[["yer_ad", "Toplam_Planlanan", "Toplam_Gerceklesen", "Kullanim_Orani"]].rename(
        columns={
            "yer_ad": "Isletme",
            "Toplam_Planlanan": "Planlanan (TL)",
            "Toplam_Gerceklesen": "Gerceklesen (TL)",
            "Kullanim_Orani": "Kullanim %",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ============================
# SIPARIS OZETI
# ============================
if not order_summary.empty:
    st.divider()
    st.header("Siparis Ozeti")

    order_by_loc = order_summary.groupby("yer_ad").agg({
        "Siparis_Adet": "sum",
        "Toplam_Tutar": "sum",
    }).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig_o = px.bar(
            order_by_loc, x="yer_ad", y="Toplam_Tutar", color="yer_ad",
            title="Isletme Bazli Siparis Tutarlari",
        )
        apply_chart_style(fig_o, showlegend=False, height=400, xaxis_title="", yaxis_title="Tutar (TL)")
        st.plotly_chart(fig_o, use_container_width=True)

    with col2:
        fig_o2 = px.bar(
            order_by_loc, x="yer_ad", y="Siparis_Adet", color="yer_ad",
            title="Isletme Bazli Siparis Adetleri",
        )
        apply_chart_style(fig_o2, showlegend=False, height=400, xaxis_title="", yaxis_title="Adet")
        st.plotly_chart(fig_o2, use_container_width=True)

# ============================
# GELECEK YIL BUTCE TAHMINI
# ============================
st.divider()
st.header("Gelecek Yil Butce Tahmini")
st.markdown(
    f"**{yil}** yili verilerini analiz ederek **{yil + 1}** yili icin "
    "departman bazli butce tahmini olusturun."
)

# --- Tahmin Parametreleri ---
st.subheader("Tahmin Parametreleri")

param_col1, param_col2 = st.columns(2)

with param_col1:
    enflasyon_pct = st.slider(
        "Enflasyon Orani (%):",
        min_value=0, max_value=100, value=30, step=1,
        help="Yillik enflasyon tahmini",
        key="forecast_enflasyon",
    )
    guven_marji_pct = st.slider(
        "Guven Marji (%):",
        min_value=0, max_value=30, value=10, step=1,
        help="Emniyet tamponu — beklenmedik harcamalar icin ek butce",
        key="forecast_guven",
    )

with param_col2:
    fire_2025_pct = st.number_input(
        f"{yil} Fire Orani (%):",
        min_value=0.0, max_value=50.0,
        value=VARSAYILAN_FIRE_ORANI * 100,
        step=0.5,
        help="Cam uretimindeki mevcut fire (hurda/iskarta) orani",
        key="forecast_fire_2025",
    )
    fire_2026_pct = st.number_input(
        f"{yil + 1} Tahmini Fire Orani (%):",
        min_value=0.0, max_value=50.0,
        value=VARSAYILAN_FIRE_ORANI * 100,
        step=0.5,
        help="Gelecek yil icin hedeflenen fire orani",
        key="forecast_fire_2026",
    )

# Fire etki bilgisi
with st.expander("Fire Orani Etki Bilgisi"):
    st.markdown("""
    Fire orani degisimi her departmani farkli oranda etkiler:

    | Departman | Etki Agirligi | Aciklama |
    |-----------|:------------:|----------|
    | Uretim    | %100         | Dogrudan uretim hurda/iskartasi |
    | Bakim     | %30          | Yuksek fire → makine yipranmasi artar |
    | Kalite    | %20          | Yuksek fire → daha fazla test/kontrol |
    | Lojistik  | %15          | Yuksek fire → daha fazla malzeme tasima |
    | IT        | %0           | Etkilenmez |
    | IK        | %0           | Etkilenmez |
    """)

# --- Tahmin Butonu ---
if st.button("Butce Tahmini Olustur", type="primary", use_container_width=True):
    enflasyon = enflasyon_pct / 100
    guven_marji = guven_marji_pct / 100
    fire_2025 = fire_2025_pct / 100
    fire_2026 = fire_2026_pct / 100

    with st.spinner("Butce tahmini hesaplaniyor..."):
        forecast_df, ozet, aylik_tahmin_df = generate_budget_forecast(
            conn, yil, enflasyon, guven_marji, fire_2025, fire_2026
        )

    if forecast_df.empty:
        st.warning("Tahmin olusturulamadi — yeterli veri bulunamadi.")
    else:
        # --- Tahmin KPI Kartlari ---
        st.subheader("Tahmin Ozeti")

        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        with kpi_c1:
            st.metric(
                f"{yil} Planlanan",
                format_currency(ozet["toplam_planlanan_2025"]),
            )
        with kpi_c2:
            st.metric(
                f"{yil} Efektif Harcama",
                format_currency(ozet["toplam_efektif_2025"]),
            )
        with kpi_c3:
            st.metric(
                f"{yil + 1} Tahmin Butce",
                format_currency(ozet["toplam_tahmin_2026"]),
                delta=format_currency(ozet["toplam_fark"]),
            )
        with kpi_c4:
            st.metric(
                "Ortalama Degisim",
                f"%{ozet['ortalama_degisim']:.1f}",
            )

        # Etki dagilimlari
        etki_c1, etki_c2, etki_c3 = st.columns(3)
        with etki_c1:
            fire_delta = ozet["toplam_fire_etkisi"]
            fire_label = "Tasarruf" if fire_delta < 0 else "Ek Maliyet"
            st.metric(
                f"Fire Etkisi ({fire_label})",
                format_currency(abs(fire_delta)),
                delta=f"{fire_delta:+,.0f} TL",
                delta_color="inverse" if fire_delta < 0 else "normal",
            )
        with etki_c2:
            st.metric(
                "Enflasyon Etkisi",
                format_currency(ozet["toplam_enflasyon_etkisi"]),
            )
        with etki_c3:
            st.metric(
                "Guven Marji Etkisi",
                format_currency(ozet["toplam_guven_etkisi"]),
            )

        # Durum dagilimlari
        durum_c1, durum_c2, durum_c3 = st.columns(3)
        with durum_c1:
            st.metric("Butce Asan Dept.", ozet["asim_dept_sayisi"])
        with durum_c2:
            st.metric("Tasarruflu Dept.", ozet["tasarruf_dept_sayisi"])
        with durum_c3:
            st.metric("Dengeli Dept.", ozet["dengeli_dept_sayisi"])

        st.divider()

        # --- Karsilastirma Grafigi ---
        st.subheader(f"{yil} vs {yil + 1} Butce Karsilastirmasi")

        # Isletme bazli ozet
        loc_forecast = forecast_df.groupby("yer_ad").agg(
            Planlanan_2025=("Planlanan_2025", "sum"),
            Efektif_2025=("Efektif_2025", "sum"),
            Tahmin_2026=("Tahmin_2026", "sum"),
        ).reset_index()

        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            x=loc_forecast["yer_ad"], y=loc_forecast["Planlanan_2025"],
            name=f"{yil} Planlanan", marker_color="#2196F3",
        ))
        fig_compare.add_trace(go.Bar(
            x=loc_forecast["yer_ad"], y=loc_forecast["Efektif_2025"],
            name=f"{yil} Efektif", marker_color="#FF9800",
        ))
        fig_compare.add_trace(go.Bar(
            x=loc_forecast["yer_ad"], y=loc_forecast["Tahmin_2026"],
            name=f"{yil + 1} Tahmin", marker_color="#4CAF50",
        ))
        apply_chart_style(fig_compare,
            title=f"Isletme Bazli Butce Karsilastirmasi ({yil} vs {yil + 1})",
            barmode="group", height=450, yaxis_title="Tutar (TL)",
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        # --- Departman Bazli Karsilastirma ---
        st.subheader("Departman Bazli Tahmin")

        # Etiket kolonu ekle
        forecast_df["Etiket"] = forecast_df["yer_ad"] + " - " + forecast_df["dept_ad"]

        fig_dept = go.Figure()
        fig_dept.add_trace(go.Bar(
            y=forecast_df["Etiket"], x=forecast_df["Planlanan_2025"],
            name=f"{yil} Planlanan", marker_color="#2196F3",
            orientation="h",
        ))
        fig_dept.add_trace(go.Bar(
            y=forecast_df["Etiket"], x=forecast_df["Efektif_2025"],
            name=f"{yil} Efektif", marker_color="#FF9800",
            orientation="h",
        ))
        fig_dept.add_trace(go.Bar(
            y=forecast_df["Etiket"], x=forecast_df["Tahmin_2026"],
            name=f"{yil + 1} Tahmin", marker_color="#4CAF50",
            orientation="h",
        ))
        apply_chart_style(fig_dept,
            title=f"Departman Bazli Butce Karsilastirmasi",
            barmode="group", height=max(400, len(forecast_df) * 45),
            xaxis_title="Tutar (TL)", yaxis_title="",
        )
        st.plotly_chart(fig_dept, use_container_width=True)

        # --- Fire Etkisi Grafigi (sadece fabrika departmanlari) ---
        fabrika_forecast = forecast_df[forecast_df["dept_kod"].isin(
            [k for k, v in FIRE_ETKI_AGIRLIKLARI.items() if v > 0]
        )]

        if not fabrika_forecast.empty and fire_2025_pct != fire_2026_pct:
            st.subheader("Fire Orani Etkisi (Fabrika Departmanlari)")

            fig_fire = go.Figure()
            fig_fire.add_trace(go.Bar(
                y=fabrika_forecast["Etiket"],
                x=fabrika_forecast["Fire_Etkisi_TL"],
                orientation="h",
                marker_color=[
                    "#4CAF50" if v < 0 else "#F44336"
                    for v in fabrika_forecast["Fire_Etkisi_TL"]
                ],
                text=fabrika_forecast["Fire_Etkisi_TL"].apply(
                    lambda x: format_currency(x)
                ),
                textposition="outside",
            ))
            fire_yonu = "Azalis" if fire_2026_pct < fire_2025_pct else "Artis"
            apply_chart_style(fig_fire,
                title=f"Fire Orani Degisimi Etkisi ({fire_2025_pct}% → {fire_2026_pct}% | {fire_yonu})",
                height=max(300, len(fabrika_forecast) * 40),
                xaxis_title="Tutar Etkisi (TL)", yaxis_title="",
            )
            st.plotly_chart(fig_fire, use_container_width=True)

        # --- Kullanim Orani Analizi ---
        st.subheader(f"{yil} Kullanim Orani Analizi")

        fig_util = go.Figure()
        colors = []
        for _, r in forecast_df.iterrows():
            if r["Durum_2025"] == "Asim":
                colors.append("#F44336")
            elif r["Durum_2025"] == "Tasarruf":
                colors.append("#4CAF50")
            else:
                colors.append("#FF9800")

        fig_util.add_trace(go.Bar(
            y=forecast_df["Etiket"], x=forecast_df["Kullanim_Orani"],
            orientation="h", marker_color=colors,
            text=forecast_df["Kullanim_Orani"].apply(lambda x: f"%{x}"),
            textposition="outside",
        ))
        fig_util.add_vline(x=100, line_dash="dash", line_color="gray",
                          annotation_text="Butce Siniri (%100)")
        apply_chart_style(fig_util,
            title=f"{yil} Butce Kullanim Orani (Efektif / Planlanan)",
            height=max(400, len(forecast_df) * 40),
            xaxis_title="Kullanim Orani (%)", yaxis_title="",
        )
        st.plotly_chart(fig_util, use_container_width=True)

        st.divider()

        # --- Detay Tablosu ---
        st.subheader("Tahmin Detay Tablosu")

        display_forecast = forecast_df[[
            "yer_ad", "dept_ad", "Planlanan_2025", "Efektif_2025",
            "Kullanim_Orani", "Durum_2025", "Fire_Etkisi_TL",
            "Enflasyon_Etkisi_TL", "Tahmin_2026", "Degisim_Yuzde",
        ]].rename(columns={
            "yer_ad": "Isletme",
            "dept_ad": "Departman",
            "Planlanan_2025": f"Planlanan {yil} (TL)",
            "Efektif_2025": f"Efektif {yil} (TL)",
            "Kullanim_Orani": "Kullanim %",
            "Durum_2025": f"{yil} Durum",
            "Fire_Etkisi_TL": "Fire Etkisi (TL)",
            "Enflasyon_Etkisi_TL": "Enflasyon Etkisi (TL)",
            "Tahmin_2026": f"Tahmin {yil + 1} (TL)",
            "Degisim_Yuzde": "Degisim %",
        })

        st.dataframe(display_forecast, use_container_width=True, hide_index=True)

        # --- Aylik Kirilim ---
        with st.expander(f"{yil + 1} Aylik Tahmin Kirilimi"):
            if not aylik_tahmin_df.empty:
                aylik_pivot = aylik_tahmin_df.pivot_table(
                    values="Tahmin_2026",
                    index=["yer_ad", "dept_ad"],
                    columns="Ay",
                    aggfunc="first",
                ).reset_index()

                aylik_pivot.columns.name = None
                aylik_pivot = aylik_pivot.rename(columns={
                    "yer_ad": "Isletme",
                    "dept_ad": "Departman",
                })

                # Ay sutunlarini sirala
                ay_cols = [c for c in aylik_pivot.columns if c not in ["Isletme", "Departman"]]
                try:
                    ay_cols_sorted = sorted(ay_cols, key=lambda x: int(x))
                except ValueError:
                    ay_cols_sorted = sorted(ay_cols)

                ay_rename = {}
                ay_isimleri = [
                    "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
                    "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
                ]
                for ac in ay_cols_sorted:
                    try:
                        idx = int(ac) - 1
                        if 0 <= idx < 12:
                            ay_rename[ac] = ay_isimleri[idx]
                    except ValueError:
                        pass

                aylik_pivot = aylik_pivot.rename(columns=ay_rename)

                st.dataframe(aylik_pivot, use_container_width=True, hide_index=True)

# ============================
# SEKTOR KARSILASTIRMA OZETI
# ============================
st.divider()
st.header("Sektor Karsilastirma Ozeti")

benchmark_data = load_benchmark_data()
if benchmark_data:
    yorglass_metrics = calculate_yorglass_metrics(conn, yil)
    firms_df, dept_df, ranking_df, summary_bm = compare_with_benchmarks(yorglass_metrics, benchmark_data)

    # Fire orani ve birim maliyet karsilastirmasi
    bm_c1, bm_c2, bm_c3, bm_c4 = st.columns(4)

    with bm_c1:
        fire_fark_pct = summary_bm["fire_fark"] * 100
        fire_durum = "yuksek" if fire_fark_pct > 0 else "dusuk"
        st.metric(
            "Fire Orani (Yorglass)",
            f"%{summary_bm['yorglass_fire']*100:.1f}",
            delta=f"{fire_fark_pct:+.1f}% vs sektor",
            delta_color="inverse",
        )

    with bm_c2:
        st.metric(
            "Sektor Ort. Fire",
            f"%{summary_bm['sektor_fire_ort']*100:.1f}",
        )

    with bm_c3:
        st.metric(
            "Birim Maliyet (Yorglass)",
            f"{summary_bm['yorglass_maliyet']:,.0f} TL/ton",
            delta=f"{summary_bm['maliyet_fark']:+,.0f} TL vs sektor",
            delta_color="inverse",
        )

    with bm_c4:
        st.metric(
            "Sektor Ort. Birim Maliyet",
            f"{summary_bm['sektor_maliyet_ort']:,.0f} TL/ton",
        )

    # Guclu / Gelistirilmeli alan ozeti
    bm_c5, bm_c6, bm_c7 = st.columns(3)

    with bm_c5:
        st.metric("Karsilastirilan Firma", summary_bm["firma_sayisi"])
    with bm_c6:
        st.metric("Guclu Alanlar", f"{summary_bm['guclu_alanlar']} metrik")
    with bm_c7:
        st.metric("Gelistirilmeli Alanlar", f"{summary_bm['gelistirilmeli_alanlar']} metrik")

    # Yorglass pozisyon ozeti (kisa)
    with st.expander("Yorglass Sektor Pozisyonu"):
        for _, row in ranking_df.iterrows():
            durum = row["Durum"]
            icon = "🟢" if durum == "Iyi" else ("🟡" if durum == "Orta" else "🔴")
            st.markdown(
                f"{icon} **{row['Metrik']}**: {row['Yorglass_Sira']}/{row['Toplam_Firma']} sirada "
                f"— Yorglass: `{row['Yorglass']}` | Sektor Ort: `{row['Sektor_Ortalama']}` "
                f"| En Iyi: `{row['En_Iyi']}` ({row['En_Iyi_Firma']})"
            )

    st.info("📊 Detayli sektor karsilastirmasi icin kenar cubugundaki **Sektor Kiyas** sayfasina gidin.")
else:
    st.warning("Benchmark verisi bulunamadi. `sample_data/sektor_benchmark.json` dosyasini kontrol edin.")

# ============================
# SAYFA REHBERI
# ============================
st.divider()
st.header("Sayfa Rehberi")

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_nav_card("Genel Karsilastirma", "📊", [
        "Kullanim orani heatmap",
        "Departman siralamasi",
        "Lokasyonlar arasi analiz",
    ])

with col2:
    render_nav_card("Departman Detay", "📋", [
        "Butce grafikleri",
        "Siparis analizi",
        "Optimum butce hesaplama",
        "AI finansal yorum",
    ])

with col3:
    render_nav_card("Malzeme Analizi", "🔬", [
        "Mal grubu bazli harcamalar",
        "Departmanlar arasi alim tespiti",
        "Malzeme hareket detaylari",
    ])

with col4:
    render_nav_card("Sektor Kiyas", "🏭", [
        "Rakip firma karsilastirmasi",
        "Radar performans grafigi",
        "Fire orani & maliyet kiyas",
        "Departman dagilimi analizi",
    ])

conn.close()
