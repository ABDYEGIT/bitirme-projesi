import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data_loader import (
    connect_db,
    get_uretim_yerleri,
    get_uretim_yeri_departmanlar,
    load_mal_gruplari,
    load_malzeme_hareketleri,
    load_cross_department_purchases,
    load_material_summary_by_group,
)
from components import format_currency
from config import DB_PATH
from styles import inject_custom_css, apply_chart_style

st.set_page_config(page_title="Malzeme Analizi", page_icon="🔬", layout="wide")
inject_custom_css()
st.title("Malzeme Analizi")
st.markdown("Fabrika departmanlarının malzeme hareketleri ve departmanlar arası alım tespiti.")

db_path = st.session_state.get("db_path", DB_PATH)

conn, err = connect_db(db_path)
if err:
    st.error(err)
    st.stop()

st.sidebar.header("Filtre")

yerler = get_uretim_yerleri(conn)
fabrika_yerler = yerler[yerler["kod"] != "merkez"]

yer_options = ["Tüm Fabrikalar"] + fabrika_yerler["ad"].tolist()
yer_secim = st.sidebar.selectbox("İşletme:", yer_options, key="malz_yer")

yer_id = None
if yer_secim != "Tüm Fabrikalar":
    yer_row = yerler[yerler["ad"] == yer_secim].iloc[0]
    yer_id = int(yer_row["id"])

dept_id = None
if yer_id:
    deptlar = get_uretim_yeri_departmanlar(conn, yer_id)
    dept_options = ["Tüm Departmanlar"] + deptlar["ad"].tolist()
    dept_secim = st.sidebar.selectbox("Departman:", dept_options, key="malz_dept")
    if dept_secim != "Tüm Departmanlar":
        dept_row = deptlar[deptlar["ad"] == dept_secim].iloc[0]
        dept_id = int(dept_row["id"])

filtre_text = yer_secim
if dept_id and yer_id:
    filtre_text += f" → {dept_secim}"
st.caption(f"Filtre: {filtre_text}")

st.header("Mal Grupları")
mal_gruplari = load_mal_gruplari(conn)

if not mal_gruplari.empty:
    st.dataframe(
        mal_gruplari[["ad", "sorumlu_dept_ad"]].rename(
            columns={"ad": "Mal Grubu", "sorumlu_dept_ad": "Sorumlu Departman"}
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

st.header("Mal Grubu Bazlı Harcama Özeti")

mat_summary = load_material_summary_by_group(conn, yer_id, dept_id)

if not mat_summary.empty:
    fig_summary = px.bar(
        mat_summary, x="Mal_Grubu", y="Toplam_Tutar",
        color="Sorumlu_Departman",
        title="Mal Grubu Bazlı Toplam Harcama",
        text_auto=True,
    )
    apply_chart_style(fig_summary, height=450, xaxis_title="", yaxis_title="Tutar (TL)")
    st.plotly_chart(fig_summary, use_container_width=True)

    mat_summary["Cross_Dept_Oran"] = (
        mat_summary["Cross_Dept_Tutar"] / mat_summary["Toplam_Tutar"] * 100
    ).round(1)

    st.dataframe(
        mat_summary.rename(columns={
            "Mal_Grubu": "Mal Grubu",
            "Sorumlu_Departman": "Sorumlu Dept.",
            "Hareket_Sayisi": "Hareket",
            "Toplam_Miktar": "Miktar",
            "Toplam_Tutar": "Toplam (TL)",
            "Cross_Dept_Tutar": "Dept. Arası (TL)",
            "Cross_Dept_Oran": "Dept. Arası %",
        }),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Seçilen filtrelere göre malzeme hareketi bulunamadı.")

st.divider()

st.header("Departmanlar Arası Alım Tespiti")

cross_dept = load_cross_department_purchases(conn, yer_id, dept_id)

if not cross_dept.empty:
    toplam_cross_tutar = cross_dept["toplam_tutar"].sum()
    st.info(f"Toplam {len(cross_dept)} departmanlar arası alım tespit edildi. "
            f"Tutar: {format_currency(toplam_cross_tutar)}")

    cross_summary = cross_dept.groupby(["alan_departman", "sorumlu_departman"]).agg(
        Hareket_Sayisi=("toplam_tutar", "count"),
        Toplam_Tutar=("toplam_tutar", "sum"),
    ).reset_index().sort_values("Toplam_Tutar", ascending=False)

    fig_cross = px.bar(
        cross_summary, x="alan_departman", y="Toplam_Tutar",
        color="sorumlu_departman",
        title="Departmanlar Arası Alım Matrisi",
        labels={
            "alan_departman": "Alan Departman",
            "sorumlu_departman": "Mal Grubu Sorumlusu",
            "Toplam_Tutar": "Tutar (TL)",
        },
        text_auto=True,
    )
    apply_chart_style(fig_cross, height=450)
    st.plotly_chart(fig_cross, use_container_width=True)

    if yer_id is None:
        cross_by_loc = cross_dept.groupby("uretim_yeri").agg(
            Hareket=("toplam_tutar", "count"),
            Tutar=("toplam_tutar", "sum"),
        ).reset_index()

        col1, col2 = st.columns(2)
        with col1:
            fig_loc_cross = px.pie(
                cross_by_loc, values="Tutar", names="uretim_yeri",
                title="İşletme Bazlı Dept. Arası Alım Dağılımı",
            )
            st.plotly_chart(fig_loc_cross, use_container_width=True)

        with col2:
            fig_loc_bar = px.bar(
                cross_by_loc, x="uretim_yeri", y="Tutar",
                title="İşletme Bazlı Dept. Arası Alım Tutarları",
                text_auto=True,
            )
            apply_chart_style(fig_loc_bar, height=400, xaxis_title="", yaxis_title="Tutar (TL)")
            st.plotly_chart(fig_loc_bar, use_container_width=True)

    st.subheader("Özet Tablo")
    st.dataframe(
        cross_summary.rename(columns={
            "alan_departman": "Alan Dept.",
            "sorumlu_departman": "Sorumlu Dept.",
            "Hareket_Sayisi": "Hareket",
            "Toplam_Tutar": "Tutar (TL)",
        }),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Detaylı Departmanlar Arası Alım Tablosu"):
        st.dataframe(
            cross_dept[["uretim_yeri", "alan_departman", "sorumlu_departman",
                        "mal_grubu", "malzeme_adi", "tarih", "miktar", "toplam_tutar"]].rename(
                columns={
                    "uretim_yeri": "İşletme",
                    "alan_departman": "Alan Dept.",
                    "sorumlu_departman": "Sorumlu Dept.",
                    "mal_grubu": "Mal Grubu",
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
    st.success("Seçilen filtrelere göre departmanlar arası alım bulunmuyor.")

st.divider()

st.header("Malzeme Hareket Trendi")

hareketler = load_malzeme_hareketleri(conn, yer_id, dept_id)

if not hareketler.empty:
    st.caption(f"Toplam {len(hareketler)} hareket")

    hareketler_copy = hareketler.copy()
    hareketler_copy["tarih_dt"] = pd.to_datetime(hareketler_copy["tarih"], errors="coerce")
    hareketler_copy["Ay"] = hareketler_copy["tarih_dt"].dt.to_period("M").astype(str)
    aylik = hareketler_copy.groupby("Ay")["toplam_tutar"].sum().reset_index()

    fig_trend = go.Figure(go.Bar(
        x=aylik["Ay"], y=aylik["toplam_tutar"], marker_color="#00BCD4",
    ))
    apply_chart_style(fig_trend,
        title="Aylık Malzeme Harcama Trendi",
        height=400, yaxis_title="Tutar (TL)", xaxis_title="Ay",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    aylik_grup = hareketler_copy.groupby(["Ay", "mal_grubu"])["toplam_tutar"].sum().reset_index()
    fig_grup = px.bar(
        aylik_grup, x="Ay", y="toplam_tutar", color="mal_grubu",
        title="Aylık Malzeme Harcama - Mal Grubu Kırılımı",
    )
    apply_chart_style(fig_grup, height=450, yaxis_title="Tutar (TL)")
    st.plotly_chart(fig_grup, use_container_width=True)

    with st.expander("Tüm Malzeme Hareketleri"):
        st.dataframe(
            hareketler[["uretim_yeri", "departman", "malzeme_kodu", "malzeme_adi",
                        "mal_grubu", "tarih", "miktar", "birim_fiyat", "toplam_tutar"]].rename(
                columns={
                    "uretim_yeri": "İşletme",
                    "departman": "Departman",
                    "malzeme_kodu": "Kod",
                    "malzeme_adi": "Malzeme",
                    "mal_grubu": "Mal Grubu",
                    "tarih": "Tarih",
                    "miktar": "Miktar",
                    "birim_fiyat": "Birim Fiyat",
                    "toplam_tutar": "Tutar (TL)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("Seçilen filtrelere göre malzeme hareketi bulunamadı.")

conn.close()
