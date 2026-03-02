import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from styles import apply_chart_style


def format_currency(value):
    return f"{value:,.2f} TL"


def render_kpi_cards(kpis):
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Toplam Planlanan", format_currency(kpis["toplam_planlanan"]))
    with col2:
        st.metric("Gerçekleşen (Ham)", format_currency(kpis["toplam_gerceklesen_ham"]))
    with col3:
        st.metric("Açık Siparişler", format_currency(kpis["toplam_siparis"]))
    with col4:
        st.metric(
            "Efektif Gerçekleşen",
            format_currency(kpis["toplam_efektif"]),
            help="Gerçekleşen harcama + açık sipariş tutarları",
        )
    with col5:
        delta_color = "inverse" if kpis["toplam_kalan"] >= 0 else "normal"
        st.metric("Kalan Bütçe", format_currency(kpis["toplam_kalan"]), delta_color=delta_color)

    st.markdown(f"**Bütçe Kullanım Oranı (Efektif): %{kpis['kullanim_orani']}**")
    st.progress(min(kpis["kullanim_orani"] / 100, 1.0))


def render_budget_bar_chart(variance_df):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=variance_df["Ay"], y=variance_df["Planlanan"],
        name="Planlanan", marker_color="#2196F3",
    ))
    fig.add_trace(go.Bar(
        x=variance_df["Ay"], y=variance_df["Gerceklesen"],
        name="Gerceklesen", marker_color="#FF9800",
    ))

    if "Efektif_Gerceklesen" in variance_df.columns:
        fig.add_trace(go.Bar(
            x=variance_df["Ay"], y=variance_df["Efektif_Gerceklesen"],
            name="Efektif (Gerçekleşen + Sipariş)", marker_color="#F44336",
        ))

    apply_chart_style(fig,
        title="Aylık Planlanan vs Gerçekleşen vs Efektif Bütçe",
        xaxis_title="Ay", yaxis_title="Tutar (TL)",
        barmode="group", height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_variance_chart(variance_df):
    colors = ["#4CAF50" if v <= 0 else "#F44336" for v in variance_df["Sapma_Yuzde"]]
    fig = go.Figure(go.Bar(
        x=variance_df["Ay"], y=variance_df["Sapma_Yuzde"],
        marker_color=colors,
        text=variance_df["Sapma_Yuzde"].apply(lambda x: f"%{x}"),
        textposition="outside",
    ))
    apply_chart_style(fig,
        title="Aylık Efektif Bütçe Sapma Oranı (%)",
        xaxis_title="Ay", yaxis_title="Sapma (%)", height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_cumulative_chart(remaining_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=remaining_df["Ay"], y=remaining_df["Kumulatif_Planlanan"],
        name="Kümülatif Planlanan", line=dict(color="#2196F3", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=remaining_df["Ay"], y=remaining_df["Kumulatif_Gerceklesen"],
        name="Kümülatif Efektif Gerçekleşen", line=dict(color="#F44336", width=2),
    ))
    apply_chart_style(fig,
        title="Kümülatif Bütçe Takibi (Efektif)",
        xaxis_title="Ay", yaxis_title="Tutar (TL)", height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_stacked_spending_chart(variance_df):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=variance_df["Ay"], y=variance_df["Gerceklesen"],
        name="Gerçekleşen Harcama", marker_color="#FF9800",
    ))
    fig.add_trace(go.Bar(
        x=variance_df["Ay"], y=variance_df["Siparis_Tutari"],
        name="Sipariş Taahhüdü", marker_color="#9C27B0",
    ))
    fig.add_trace(go.Scatter(
        x=variance_df["Ay"], y=variance_df["Planlanan"],
        name="Planlanan Bütçe", line=dict(color="#2196F3", width=3, dash="dash"),
    ))
    apply_chart_style(fig,
        title="Harcama Dağılımı: Gerçekleşen + Sipariş vs Planlanan",
        xaxis_title="Ay", yaxis_title="Tutar (TL)",
        barmode="stack", height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_order_section(order_data, order_analysis):
    st.header("Sipariş Analizi")

    ocol1, ocol2 = st.columns(2)
    with ocol1:
        st.metric("Toplam Sipariş", order_analysis["toplam_siparis"])
        st.metric("Toplam Tutar", format_currency(order_analysis["toplam_tutar"]))
    with ocol2:
        st.metric("Ortalama Sipariş", format_currency(order_analysis["ortalama_tutar"]))
        st.metric("En Büyük Sipariş", format_currency(order_analysis["max_siparis"]))

    if "aylik_siparis" in order_analysis:
        fig = go.Figure(go.Bar(
            x=order_analysis["aylik_siparis"]["Ay"],
            y=order_analysis["aylik_siparis"]["Toplam_Tutar"],
            name="Siparis Tutari", marker_color="#9C27B0",
        ))
        apply_chart_style(fig,
            title="Aylık Sipariş Tutarları",
            xaxis_title="Ay", yaxis_title="Tutar (TL)", height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    if "durum_dagilim" in order_analysis:
        fig = px.pie(
            order_analysis["durum_dagilim"],
            values="Toplam_Tutar", names="Durum",
            title="Sipariş Durum Dağılımı (Tutara Göre)",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_optimal_budget_section(merged_budget, key_prefix=""):
    from analysis import calculate_optimal_budget

    st.header("Optimum Bütçe Belirleme")

    guven_marji = st.slider(
        "Güven Marjı (emniyet tamponu %)",
        min_value=5, max_value=30, value=10, step=5,
        help="Beklenmedik harcamalar için ekstra tampon yüzdesi.",
        key=f"{key_prefix}opt_slider",
    )

    if st.button("Optimum Bütçe Belirle", type="primary", key=f"{key_prefix}opt_btn"):
        with st.spinner("Lineer regresyon ile optimum bütçe hesaplanıyor..."):
            opt_df, opt_ozet = calculate_optimal_budget(merged_budget, guven_marji=guven_marji / 100)

            st.subheader("Optimizasyon Sonucu")
            kcol1, kcol2, kcol3, kcol4 = st.columns(4)

            with kcol1:
                st.metric("Mevcut Yıllık Bütçe", format_currency(opt_ozet["toplam_mevcut_butce"]))
            with kcol2:
                st.metric("Önerilen Yıllık Bütçe", format_currency(opt_ozet["toplam_optimum_butce"]))
            with kcol3:
                fark = opt_ozet["toplam_fark"]
                st.metric("Tasarruf" if fark > 0 else "Ek Bütçe Gerekli", format_currency(abs(fark)))
            with kcol4:
                st.metric("Harcama Trendi", opt_ozet["trend_yonu"],
                          help=f"Egim: {opt_ozet['trend_egim']:,.0f} TL | R2: {opt_ozet['r_kare']}")

            st.caption(
                f"Egim: {opt_ozet['trend_egim']:,.0f} TL/ay | "
                f"R2: {opt_ozet['r_kare']} | Std Sapma: {opt_ozet['std_sapma']:,.0f} TL | "
                f"Ort. Siparis: {opt_ozet['ort_siparis']:,.0f} TL/ay | "
                f"Guven Marji: %{opt_ozet['guven_marji_yuzde']:.0f}"
            )

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=opt_df["Ay"], y=opt_df["Efektif_Harcama"],
                name="Efektif Harcama", mode="lines+markers",
                line=dict(color="#FF9800", width=2), marker=dict(size=8),
            ))
            fig.add_trace(go.Scatter(
                x=opt_df["Ay"], y=opt_df["Lineer_Tahmin"],
                name="Lineer Tahmin", mode="lines",
                line=dict(color="#9E9E9E", width=2, dash="dot"),
            ))
            fig.add_trace(go.Bar(
                x=opt_df["Ay"], y=opt_df["Mevcut_Butce"],
                name="Mevcut Bütçe", marker_color="rgba(33, 150, 243, 0.4)",
            ))
            fig.add_trace(go.Bar(
                x=opt_df["Ay"], y=opt_df["Optimum_Butce"],
                name="Önerilen Optimum", marker_color="rgba(76, 175, 80, 0.6)",
            ))
            apply_chart_style(fig,
                title="Mevcut vs Optimum Bütçe vs Gerçek Harcama",
                xaxis_title="Ay", yaxis_title="Tutar (TL)",
                barmode="group", height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Optimum Bütçe Detay Tablosu", expanded=True):
                display_df = opt_df.copy()
                st.dataframe(display_df, use_container_width=True)


def render_cross_dept_correction_chart(correction_df, ozet, dept_adi="", key_prefix=""):

    st.header("Çapraz Departman Bütçe Düzeltme Analizi")
    st.caption(
        "Eğer her departman sadece kendi sorumluluğundaki mal grubundan alım yapsaydı "
        "bütçe gerçekleşmesi nasıl olurdu?"
    )

    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric(
            "Yanlış Dept'tan Yapılan Alım",
            format_currency(ozet["toplam_yanlis_alim"]),
            help="Bu departmanın başka departman sorumluluğundan yaptığı alımlar",
        )
    with mcol2:
        st.metric(
            "Başka Dept'lerin Bu Dept'ten Alması Gereken",
            format_currency(ozet["toplam_eksik_alim"]),
            help="Başka departmanların bu departmanın sorumlu olduğu mal grubundan aldıkları",
        )
    with mcol3:
        net = ozet["net_duzeltme_etkisi"]
        delta_label = f"{net:+,.2f} TL"
        st.metric(
            "Net Düzeltme Etkisi",
            format_currency(abs(net)),
            delta=delta_label,
            delta_color="inverse",
        )

    scol1, scol2 = st.columns(2)
    with scol1:
        sapma_orig = ozet["orijinal_sapma"]
        renk = "🔴" if sapma_orig > 0 else "🟢"
        st.markdown(f"**Orijinal Bütçe Sapması:** {renk} {sapma_orig:,.2f} TL")
    with scol2:
        sapma_duz = ozet["duzeltilmis_sapma"]
        renk = "🔴" if sapma_duz > 0 else "🟢"
        st.markdown(f"**Düzeltilmiş Bütçe Sapması:** {renk} {sapma_duz:,.2f} TL")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=correction_df["Ay"], y=correction_df["Planlanan"],
        name="Planlanan Bütçe", marker_color="#2196F3", opacity=0.5,
    ))

    fig.add_trace(go.Bar(
        x=correction_df["Ay"], y=correction_df["Gerceklesen"],
        name="Mevcut Gerçekleşen", marker_color="#FF9800",
    ))

    fig.add_trace(go.Bar(
        x=correction_df["Ay"], y=correction_df["Duzeltilmis_Gerceklesen"],
        name="Düzeltilmiş Gerçekleşen", marker_color="#4CAF50",
    ))

    apply_chart_style(fig,
        title=f"{dept_adi} - Mevcut vs Düzeltilmiş Bütçe Gerçekleşmesi",
        xaxis_title="Ay",
        yaxis_title="Tutar (TL)",
        barmode="group",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=12)),
    )
    st.plotly_chart(fig, use_container_width=True)

    has_effect = (correction_df["Yanlis_Alim"].sum() > 0) or (correction_df["Eksik_Alim"].sum() > 0)
    if has_effect:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=correction_df["Ay"], y=-correction_df["Yanlis_Alim"],
            name="Yanlış Alım (çıkarılan)", marker_color="#F44336",
        ))
        fig2.add_trace(go.Bar(
            x=correction_df["Ay"], y=correction_df["Eksik_Alim"],
            name="Eksik Alım (eklenen)", marker_color="#4CAF50",
        ))
        fig2.add_trace(go.Scatter(
            x=correction_df["Ay"], y=correction_df["Duzeltme_Etkisi"],
            name="Net Etki", mode="lines+markers",
            line=dict(color="#9C27B0", width=3),
        ))
        apply_chart_style(fig2,
            title="Aylık Çapraz Departman Düzeltme Detayı",
            xaxis_title="Ay", yaxis_title="Tutar (TL)",
            barmode="relative", height=400,
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_ai_commentary_section(kpis, order_analysis, variance_df, order_data,
                                  dept_adi="", yer_adi="", key_prefix=""):
    from analysis import generate_analysis_summary
    from ai_commentary import generate_ai_commentary, _get_api_key

    st.header("AI Finansal Yorum")

    api_key = _get_api_key()
    if not api_key:
        st.warning("⚠️ API anahtarı bulunamadı. `.env` dosyasına `OPENAI_API_KEY=sk-...` ekleyin.")
    else:
        st.success("✅ AI analiz servisi aktif")

    state_key = f"{key_prefix}ai_commentary_{yer_adi}_{dept_adi}"

    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        generate_clicked = st.button(
            "🤖 AI Analiz Yorumu Üret", type="primary",
            key=f"{key_prefix}ai_btn", use_container_width=True,
        )
    with btn_col2:
        clear_clicked = st.button(
            "🗑️ Temizle", key=f"{key_prefix}ai_clear",
            use_container_width=True,
        )

    if clear_clicked and state_key in st.session_state:
        del st.session_state[state_key]
        st.rerun()

    if generate_clicked:
        with st.spinner("🤖 AI'dan yanıt bekleniyor..."):
            summary = generate_analysis_summary(kpis, order_analysis)
            budget_text = variance_df.to_string(index=False)
            order_text = order_data.to_string(index=False) if order_data is not None else None
            commentary = generate_ai_commentary(summary, budget_text, order_text, dept_adi, yer_adi)
            st.session_state[state_key] = commentary

    if state_key in st.session_state:
        st.markdown(st.session_state[state_key])
