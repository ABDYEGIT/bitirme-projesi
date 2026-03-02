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

st.set_page_config(
    page_title=f"{SIRKET_ADI} Bütçe Analiz Sistemi",
    page_icon="🏭",
    layout="wide",
)

inject_custom_css()

st.title(f"🏭 {SIRKET_ADI} Bütçe Analiz Sistemi")
st.markdown("Tüm işletme ve departmanların bütçe, sipariş ve malzeme verilerini analiz edin.")

st.sidebar.header("Ayarlar")
db_path = st.sidebar.text_input("Veritabanı Yolu:", value=DB_PATH, key="db_path_main")
yil = st.sidebar.selectbox("Yıl:", [2025, 2024, 2026], index=0, key="yil_main")

st.session_state["db_path"] = db_path
st.session_state["yil"] = yil

conn, err = connect_db(db_path)
if err:
    st.error(f"Veritabanı bağlantısı başarısız: {err}")
    st.info("Örnek veritabanı oluşturmak için: `python create_database.py`")
    st.stop()

matrix = load_budget_matrix(conn, yil)
if matrix.empty:
    st.warning("Seçilen yıl için bütçe verisi bulunamadı.")
    conn.close()
    st.stop()

order_summary = load_order_summary(conn)
kpis = company_kpis(matrix)

st.header("Şirket Geneli Özet")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Toplam Planlanan Bütçe", format_currency(kpis["toplam_planlanan"]))
with c2:
    st.metric("Toplam Gerçekleşen", format_currency(kpis["toplam_gerceklesen"]))
with c3:
    st.metric("Kalan Bütçe", format_currency(kpis["toplam_kalan"]))
with c4:
    st.metric("Kullanım Oranı", f"%{kpis['kullanim_orani']}")

st.progress(min(kpis["kullanim_orani"] / 100, 1.0))

st.caption(f"{kpis['lokasyon_sayisi']} işletme, {kpis['departman_sayisi']} departman")

st.divider()

st.header("İşletme Bazlı Bütçe Dağılımı")

loc_totals = location_totals(matrix)
loc_totals["Kullanim_Orani"] = (loc_totals["Toplam_Gerceklesen"] / loc_totals["Toplam_Planlanan"] * 100).round(2)

fig_loc = go.Figure()
fig_loc.add_trace(go.Bar(
    x=loc_totals["yer_ad"], y=loc_totals["Toplam_Planlanan"],
    name="Planlanan", marker_color="#2196F3",
))
fig_loc.add_trace(go.Bar(
    x=loc_totals["yer_ad"], y=loc_totals["Toplam_Gerceklesen"],
    name="Gerçekleşen", marker_color="#FF9800",
))
apply_chart_style(fig_loc,
    title="İşletme Bazlı Toplam Bütçe",
    barmode="group", height=450, yaxis_title="Tutar (TL)",
)
st.plotly_chart(fig_loc, use_container_width=True)

st.dataframe(
    loc_totals[["yer_ad", "Toplam_Planlanan", "Toplam_Gerceklesen", "Kullanim_Orani"]].rename(
        columns={
            "yer_ad": "İşletme",
            "Toplam_Planlanan": "Planlanan (TL)",
            "Toplam_Gerceklesen": "Gerçekleşen (TL)",
            "Kullanim_Orani": "Kullanım %",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

if not order_summary.empty:
    st.divider()
    st.header("Sipariş Özeti")

    order_by_loc = order_summary.groupby("yer_ad").agg({
        "Siparis_Adet": "sum",
        "Toplam_Tutar": "sum",
    }).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig_o = px.bar(
            order_by_loc, x="yer_ad", y="Toplam_Tutar", color="yer_ad",
            title="İşletme Bazlı Sipariş Tutarları",
        )
        apply_chart_style(fig_o, showlegend=False, height=400, xaxis_title="", yaxis_title="Tutar (TL)")
        st.plotly_chart(fig_o, use_container_width=True)

    with col2:
        fig_o2 = px.bar(
            order_by_loc, x="yer_ad", y="Siparis_Adet", color="yer_ad",
            title="İşletme Bazlı Sipariş Adetleri",
        )
        apply_chart_style(fig_o2, showlegend=False, height=400, xaxis_title="", yaxis_title="Adet")
        st.plotly_chart(fig_o2, use_container_width=True)

st.divider()
st.header("Gelecek Yıl Bütçe Tahmini")
st.markdown(
    f"**{yil}** yılı verilerini analiz ederek **{yil + 1}** yılı için "
    "departman bazlı bütçe tahmini oluşturun."
)

st.subheader("Tahmin Parametreleri")

param_col1, param_col2 = st.columns(2)

with param_col1:
    enflasyon_pct = st.slider(
        "Enflasyon Oranı (%):",
        min_value=0, max_value=100, value=30, step=1,
        help="Yıllık enflasyon tahmini",
        key="forecast_enflasyon",
    )
    guven_marji_pct = st.slider(
        "Güven Marjı (%):",
        min_value=0, max_value=30, value=10, step=1,
        help="Emniyet tamponu — beklenmedik harcamalar için ek bütçe",
        key="forecast_guven",
    )

with param_col2:
    fire_2025_pct = st.number_input(
        f"{yil} Fire Oranı (%):",
        min_value=0.0, max_value=50.0,
        value=VARSAYILAN_FIRE_ORANI * 100,
        step=0.5,
        help="Cam üretimindeki mevcut fire (hurda/iskarta) oranı",
        key="forecast_fire_2025",
    )
    fire_2026_pct = st.number_input(
        f"{yil + 1} Tahmini Fire Oranı (%):",
        min_value=0.0, max_value=50.0,
        value=VARSAYILAN_FIRE_ORANI * 100,
        step=0.5,
        help="Gelecek yıl için hedeflenen fire oranı",
        key="forecast_fire_2026",
    )

with st.expander("Fire Oranı Etki Bilgisi"):
    st.markdown("""
    Fire oranı değişimi her departmanı farklı oranda etkiler:

    | Departman | Etki Ağırlığı | Açıklama |
    |-----------|:------------:|----------|
    | Üretim    | %100         | Doğrudan üretim hurda/iskartası |
    | Bakım     | %30          | Yüksek fire → makine yıpranması artar |
    | Kalite    | %20          | Yüksek fire → daha fazla test/kontrol |
    | Lojistik  | %15          | Yüksek fire → daha fazla malzeme taşıma |
    | IT        | %0           | Etkilenmez |
    | IK        | %0           | Etkilenmez |
    """)

if st.button("Bütçe Tahmini Oluştur", type="primary", use_container_width=True):
    enflasyon = enflasyon_pct / 100
    guven_marji = guven_marji_pct / 100
    fire_2025 = fire_2025_pct / 100
    fire_2026 = fire_2026_pct / 100

    with st.spinner("Bütçe tahmini hesaplanıyor..."):
        forecast_df, ozet, aylik_tahmin_df = generate_budget_forecast(
            conn, yil, enflasyon, guven_marji, fire_2025, fire_2026
        )

    if forecast_df.empty:
        st.warning("Tahmin oluşturulamadı — yeterli veri bulunamadı.")
    else:
        st.subheader("Tahmin Özeti")

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
                f"{yil + 1} Tahmin Bütçe",
                format_currency(ozet["toplam_tahmin_2026"]),
                delta=format_currency(ozet["toplam_fark"]),
            )
        with kpi_c4:
            st.metric(
                "Ortalama Değişim",
                f"%{ozet['ortalama_degisim']:.1f}",
            )

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
                "Güven Marjı Etkisi",
                format_currency(ozet["toplam_guven_etkisi"]),
            )

        durum_c1, durum_c2, durum_c3 = st.columns(3)
        with durum_c1:
            st.metric("Bütçe Aşan Dept.", ozet["asim_dept_sayisi"])
        with durum_c2:
            st.metric("Tasarruflu Dept.", ozet["tasarruf_dept_sayisi"])
        with durum_c3:
            st.metric("Dengeli Dept.", ozet["dengeli_dept_sayisi"])

        st.divider()

        st.subheader(f"{yil} vs {yil + 1} Bütçe Karşılaştırması")

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
            title=f"İşletme Bazlı Bütçe Karşılaştırması ({yil} vs {yil + 1})",
            barmode="group", height=450, yaxis_title="Tutar (TL)",
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        st.subheader("Departman Bazlı Tahmin")

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
            title=f"Departman Bazlı Bütçe Karşılaştırması",
            barmode="group", height=max(400, len(forecast_df) * 45),
            xaxis_title="Tutar (TL)", yaxis_title="",
        )
        st.plotly_chart(fig_dept, use_container_width=True)

        fabrika_forecast = forecast_df[forecast_df["dept_kod"].isin(
            [k for k, v in FIRE_ETKI_AGIRLIKLARI.items() if v > 0]
        )]

        if not fabrika_forecast.empty and fire_2025_pct != fire_2026_pct:
            st.subheader("Fire Oranı Etkisi (Fabrika Departmanları)")

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
            fire_yonu = "Azalış" if fire_2026_pct < fire_2025_pct else "Artış"
            apply_chart_style(fig_fire,
                title=f"Fire Oranı Değişimi Etkisi ({fire_2025_pct}% → {fire_2026_pct}% | {fire_yonu})",
                height=max(300, len(fabrika_forecast) * 40),
                xaxis_title="Tutar Etkisi (TL)", yaxis_title="",
            )
            st.plotly_chart(fig_fire, use_container_width=True)

        st.subheader(f"{yil} Kullanım Oranı Analizi")

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
                          annotation_text="Bütçe Sınırı (%100)")
        apply_chart_style(fig_util,
            title=f"{yil} Bütçe Kullanım Oranı (Efektif / Planlanan)",
            height=max(400, len(forecast_df) * 40),
            xaxis_title="Kullanım Oranı (%)", yaxis_title="",
        )
        st.plotly_chart(fig_util, use_container_width=True)

        st.divider()

        st.subheader("Tahmin Detay Tablosu")

        display_forecast = forecast_df[[
            "yer_ad", "dept_ad", "Planlanan_2025", "Efektif_2025",
            "Kullanim_Orani", "Durum_2025", "Fire_Etkisi_TL",
            "Enflasyon_Etkisi_TL", "Tahmin_2026", "Degisim_Yuzde",
        ]].rename(columns={
            "yer_ad": "İşletme",
            "dept_ad": "Departman",
            "Planlanan_2025": f"Planlanan {yil} (TL)",
            "Efektif_2025": f"Efektif {yil} (TL)",
            "Kullanim_Orani": "Kullanım %",
            "Durum_2025": f"{yil} Durum",
            "Fire_Etkisi_TL": "Fire Etkisi (TL)",
            "Enflasyon_Etkisi_TL": "Enflasyon Etkisi (TL)",
            "Tahmin_2026": f"Tahmin {yil + 1} (TL)",
            "Degisim_Yuzde": "Değişim %",
        })

        st.dataframe(display_forecast, use_container_width=True, hide_index=True)

        with st.expander(f"{yil + 1} Aylık Tahmin Kırılımı"):
            if not aylik_tahmin_df.empty:
                aylik_pivot = aylik_tahmin_df.pivot_table(
                    values="Tahmin_2026",
                    index=["yer_ad", "dept_ad"],
                    columns="Ay",
                    aggfunc="first",
                ).reset_index()

                aylik_pivot.columns.name = None
                aylik_pivot = aylik_pivot.rename(columns={
                    "yer_ad": "İşletme",
                    "dept_ad": "Departman",
                })

                ay_cols = [c for c in aylik_pivot.columns if c not in ["İşletme", "Departman"]]
                try:
                    ay_cols_sorted = sorted(ay_cols, key=lambda x: int(x))
                except ValueError:
                    ay_cols_sorted = sorted(ay_cols)

                ay_rename = {}
                ay_isimleri = [
                    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
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

st.divider()
st.header("Sektör Karşılaştırma Özeti")

benchmark_data = load_benchmark_data()
if benchmark_data:
    yorglass_metrics = calculate_yorglass_metrics(conn, yil)
    firms_df, dept_df, ranking_df, summary_bm = compare_with_benchmarks(yorglass_metrics, benchmark_data)

    bm_c1, bm_c2, bm_c3, bm_c4 = st.columns(4)

    with bm_c1:
        fire_fark_pct = summary_bm["fire_fark"] * 100
        fire_durum = "yüksek" if fire_fark_pct > 0 else "düşük"
        st.metric(
            "Fire Oranı (Yorglass)",
            f"%{summary_bm['yorglass_fire']*100:.1f}",
            delta=f"{fire_fark_pct:+.1f}% vs sektör",
            delta_color="inverse",
        )

    with bm_c2:
        st.metric(
            "Sektör Ort. Fire",
            f"%{summary_bm['sektor_fire_ort']*100:.1f}",
        )

    with bm_c3:
        st.metric(
            "Birim Maliyet (Yorglass)",
            f"{summary_bm['yorglass_maliyet']:,.0f} TL/ton",
            delta=f"{summary_bm['maliyet_fark']:+,.0f} TL vs sektör",
            delta_color="inverse",
        )

    with bm_c4:
        st.metric(
            "Sektör Ort. Birim Maliyet",
            f"{summary_bm['sektor_maliyet_ort']:,.0f} TL/ton",
        )

    bm_c5, bm_c6, bm_c7 = st.columns(3)

    with bm_c5:
        st.metric("Karşılaştırılan Firma", summary_bm["firma_sayisi"])
    with bm_c6:
        st.metric("Güçlü Alanlar", f"{summary_bm['guclu_alanlar']} metrik")
    with bm_c7:
        st.metric("Geliştirilmeli Alanlar", f"{summary_bm['gelistirilmeli_alanlar']} metrik")

    with st.expander("Yorglass Sektör Pozisyonu"):
        for _, row in ranking_df.iterrows():
            durum = row["Durum"]
            icon = "🟢" if durum == "Iyi" else ("🟡" if durum == "Orta" else "🔴")
            st.markdown(
                f"{icon} **{row['Metrik']}**: {row['Yorglass_Sira']}/{row['Toplam_Firma']} sırada "
                f"— Yorglass: `{row['Yorglass']}` | Sektör Ort: `{row['Sektor_Ortalama']}` "
                f"| En İyi: `{row['En_Iyi']}` ({row['En_Iyi_Firma']})"
            )

    st.info("📊 Detaylı sektör karşılaştırması için kenar çubuğundaki **Sektör Kıyas** sayfasına gidin.")
else:
    st.warning("Benchmark verisi bulunamadı. `sample_data/sektor_benchmark.json` dosyasını kontrol edin.")

st.divider()
st.header("Sayfa Rehberi")

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_nav_card("Genel Karşılaştırma", "📊", [
        "Kullanım oranı heatmap",
        "Departman sıralaması",
        "Lokasyonlar arası analiz",
    ])

with col2:
    render_nav_card("Departman Detay", "📋", [
        "Bütçe grafikleri",
        "Sipariş analizi",
        "Optimum bütçe hesaplama",
        "AI finansal yorum",
    ])

with col3:
    render_nav_card("Malzeme Analizi", "🔬", [
        "Mal grubu bazlı harcamalar",
        "Departmanlar arası alım tespiti",
        "Malzeme hareket detayları",
    ])

with col4:
    render_nav_card("Sektör Kıyas", "🏭", [
        "Rakip firma karşılaştırması",
        "Radar performans grafiği",
        "Fire oranı & maliyet kıyas",
        "Departman dağılımı analizi",
    ])

conn.close()
