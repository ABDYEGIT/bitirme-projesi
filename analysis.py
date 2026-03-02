import pandas as pd
import numpy as np


AY_MAP = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
    5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
    9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
    "ocak": "Ocak", "subat": "Şubat", "şubat": "Şubat",
    "mart": "Mart", "nisan": "Nisan", "mayis": "Mayıs",
    "mayıs": "Mayıs", "haziran": "Haziran", "temmuz": "Temmuz",
    "agustos": "Ağustos", "ağustos": "Ağustos", "eylul": "Eylül",
    "eylül": "Eylül", "ekim": "Ekim", "kasim": "Kasım",
    "kasım": "Kasım", "aralik": "Aralık", "aralık": "Aralık",
}


def normalize_ay(ay_value):
    if isinstance(ay_value, (int, float)):
        return AY_MAP.get(int(ay_value), str(ay_value))
    s = str(ay_value).strip().lower()
    return AY_MAP.get(s, str(ay_value).strip().title())


def merge_budget_with_orders(budget_df, order_df):
    df = budget_df.copy()
    df["Ay_Normalized"] = df["Ay"].apply(normalize_ay)

    order_copy = order_df.copy()
    if "Tarih" in order_copy.columns and order_copy["Tarih"].notna().any():
        order_copy["Ay_Num"] = order_copy["Tarih"].dt.month
        order_copy["Ay_Normalized"] = order_copy["Ay_Num"].map(
            {i: AY_MAP[i] for i in range(1, 13)}
        )
        aylik_siparis = order_copy.groupby("Ay_Normalized")["Tutar"].sum().reset_index()
        aylik_siparis.columns = ["Ay_Normalized", "Siparis_Tutari"]

        df = df.merge(aylik_siparis, on="Ay_Normalized", how="left")
        df["Siparis_Tutari"] = df["Siparis_Tutari"].fillna(0)
    else:
        df["Siparis_Tutari"] = 0

    df["Efektif_Gerceklesen"] = df["Gerceklesen"] + df["Siparis_Tutari"]
    df = df.drop(columns=["Ay_Normalized"])

    return df


def calculate_budget_variance(budget_df):
    df = budget_df.copy()
    gerceklesen_col = "Efektif_Gerceklesen" if "Efektif_Gerceklesen" in df.columns else "Gerceklesen"

    df["Fark"] = df["Planlanan"] - df[gerceklesen_col]
    df["Sapma_Yuzde"] = ((df[gerceklesen_col] - df["Planlanan"]) / df["Planlanan"] * 100).round(2)
    df["Kullanim_Orani"] = (df[gerceklesen_col] / df["Planlanan"] * 100).round(2)
    return df


def calculate_remaining_budget(budget_df):
    df = budget_df.copy()
    gerceklesen_col = "Efektif_Gerceklesen" if "Efektif_Gerceklesen" in df.columns else "Gerceklesen"

    df["Kalan"] = df["Planlanan"] - df[gerceklesen_col]
    df["Kumulatif_Planlanan"] = df["Planlanan"].cumsum()
    df["Kumulatif_Gerceklesen"] = df[gerceklesen_col].cumsum()
    df["Kumulatif_Kalan"] = df["Kumulatif_Planlanan"] - df["Kumulatif_Gerceklesen"]
    return df


def calculate_spending_trend(budget_df):
    df = budget_df.copy()
    gerceklesen_col = "Efektif_Gerceklesen" if "Efektif_Gerceklesen" in df.columns else "Gerceklesen"

    df["Aylik_Degisim"] = df[gerceklesen_col].pct_change() * 100
    df["Aylik_Degisim"] = df["Aylik_Degisim"].round(2)
    return df


def calculate_budget_kpis(budget_df):
    gerceklesen_col = "Efektif_Gerceklesen" if "Efektif_Gerceklesen" in budget_df.columns else "Gerceklesen"

    toplam_planlanan = budget_df["Planlanan"].sum()
    toplam_gerceklesen_ham = budget_df["Gerceklesen"].sum()
    toplam_siparis = budget_df["Siparis_Tutari"].sum() if "Siparis_Tutari" in budget_df.columns else 0
    toplam_efektif = budget_df[gerceklesen_col].sum()
    toplam_kalan = toplam_planlanan - toplam_efektif
    kullanim_orani = (toplam_efektif / toplam_planlanan * 100) if toplam_planlanan > 0 else 0
    ortalama_aylik_harcama = budget_df[gerceklesen_col].mean()
    max_harcama_ay = budget_df.loc[budget_df[gerceklesen_col].idxmax(), "Ay"]
    min_harcama_ay = budget_df.loc[budget_df[gerceklesen_col].idxmin(), "Ay"]

    return {
        "toplam_planlanan": toplam_planlanan,
        "toplam_gerceklesen_ham": toplam_gerceklesen_ham,
        "toplam_siparis": toplam_siparis,
        "toplam_efektif": toplam_efektif,
        "toplam_kalan": toplam_kalan,
        "kullanim_orani": round(kullanim_orani, 2),
        "ortalama_aylik_harcama": round(ortalama_aylik_harcama, 2),
        "max_harcama_ay": max_harcama_ay,
        "min_harcama_ay": min_harcama_ay,
    }


def analyze_orders(order_df):
    toplam_siparis = len(order_df)
    toplam_tutar = order_df["Tutar"].sum()
    ortalama_tutar = order_df["Tutar"].mean()
    max_siparis = order_df["Tutar"].max()
    min_siparis = order_df["Tutar"].min()

    result = {
        "toplam_siparis": toplam_siparis,
        "toplam_tutar": round(toplam_tutar, 2),
        "ortalama_tutar": round(ortalama_tutar, 2),
        "max_siparis": round(max_siparis, 2),
        "min_siparis": round(min_siparis, 2),
    }

    if "Durum" in order_df.columns:
        durum_dagilim = order_df.groupby("Durum")["Tutar"].agg(["count", "sum"]).reset_index()
        durum_dagilim.columns = ["Durum", "Adet", "Toplam_Tutar"]
        result["durum_dagilim"] = durum_dagilim

    if "Tarih" in order_df.columns and order_df["Tarih"].notna().any():
        order_df_copy = order_df.copy()
        order_df_copy["Ay"] = order_df_copy["Tarih"].dt.to_period("M").astype(str)
        aylik_siparis = order_df_copy.groupby("Ay")["Tutar"].agg(["count", "sum"]).reset_index()
        aylik_siparis.columns = ["Ay", "Siparis_Sayisi", "Toplam_Tutar"]
        result["aylik_siparis"] = aylik_siparis

    return result


def calculate_optimal_budget(budget_df, guven_marji=0.10):
    df = budget_df.copy()
    n = len(df)
    x = np.arange(1, n + 1, dtype=float)

    ham_harcamalar = df["Gerceklesen"].values
    siparis_tutarlari = df["Siparis_Tutari"].values if "Siparis_Tutari" in df.columns else np.zeros(n)

    a_ham, b_ham = np.polyfit(x, ham_harcamalar, 1)
    tahmin_ham = a_ham * x + b_ham

    ort_siparis = np.mean(siparis_tutarlari)

    tahmin_toplam = tahmin_ham + ort_siparis
    optimum_butce = tahmin_toplam * (1 + guven_marji)
    optimum_butce = np.round(optimum_butce, 2)

    efektif_harcamalar = ham_harcamalar + siparis_tutarlari
    residuals = efektif_harcamalar - tahmin_toplam
    std_sapma = np.std(residuals, ddof=1) if n > 2 else np.std(residuals)

    ss_res = np.sum((ham_harcamalar - tahmin_ham) ** 2)
    ss_tot = np.sum((ham_harcamalar - np.mean(ham_harcamalar)) ** 2)
    r_kare = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    result_df = pd.DataFrame({
        "Ay": df["Ay"].values,
        "Mevcut_Butce": df["Planlanan"].values,
        "Ham_Harcama": ham_harcamalar,
        "Siparis_Tutari": siparis_tutarlari,
        "Efektif_Harcama": efektif_harcamalar,
        "Lineer_Tahmin": np.round(tahmin_toplam, 2),
        "Optimum_Butce": optimum_butce,
        "Fark_Mevcut_Optimum": np.round(df["Planlanan"].values - optimum_butce, 2),
    })

    result_df["Durum"] = result_df["Fark_Mevcut_Optimum"].apply(
        lambda val: "Tasarruf" if val > 0 else ("Ek Bütçe Gerekli" if val < 0 else "Dengeli")
    )

    toplam_mevcut = df["Planlanan"].sum()
    toplam_optimum = float(optimum_butce.sum())
    toplam_fark = toplam_mevcut - toplam_optimum

    ozet = {
        "toplam_mevcut_butce": round(toplam_mevcut, 2),
        "toplam_optimum_butce": round(toplam_optimum, 2),
        "toplam_fark": round(toplam_fark, 2),
        "yillik_tasarruf_yuzde": round((toplam_fark / toplam_mevcut * 100), 2) if toplam_mevcut > 0 else 0,
        "trend_egim": round(a_ham, 2),
        "trend_yonu": "Artış" if a_ham > 0 else ("Azalış" if a_ham < 0 else "Sabit"),
        "r_kare": round(r_kare, 4),
        "std_sapma": round(std_sapma, 2),
        "ort_siparis": round(ort_siparis, 2),
        "guven_marji_yuzde": guven_marji * 100,
        "ortalama_optimum_aylik": round(float(optimum_butce.mean()), 2),
    }

    return result_df, ozet


def generate_analysis_summary(budget_kpis, order_analysis=None):
    lines = []
    lines.append("=== BÜTÇE ANALİZ ÖZETİ ===")
    lines.append(f"Toplam Planlanan Bütçe: {budget_kpis['toplam_planlanan']:,.2f} TL")
    lines.append(f"Toplam Gerçekleşen Harcama (Ham): {budget_kpis['toplam_gerceklesen_ham']:,.2f} TL")
    lines.append(f"Toplam Açık Sipariş Tutarı: {budget_kpis['toplam_siparis']:,.2f} TL")
    lines.append(f"Efektif Gerçekleşen (Harcama + Siparişler): {budget_kpis['toplam_efektif']:,.2f} TL")
    lines.append(f"Kalan Bütçe (Efektif): {budget_kpis['toplam_kalan']:,.2f} TL")
    lines.append(f"Bütçe Kullanım Oranı (Efektif): %{budget_kpis['kullanim_orani']}")
    lines.append(f"Ortalama Aylık Efektif Harcama: {budget_kpis['ortalama_aylik_harcama']:,.2f} TL")
    lines.append(f"En Yüksek Harcama Yapılan Ay: {budget_kpis['max_harcama_ay']}")
    lines.append(f"En Düşük Harcama Yapılan Ay: {budget_kpis['min_harcama_ay']}")

    if order_analysis:
        lines.append("")
        lines.append("=== SİPARİŞ ANALİZ ÖZETİ ===")
        lines.append(f"Toplam Sipariş Sayısı: {order_analysis['toplam_siparis']}")
        lines.append(f"Toplam Sipariş Tutarı: {order_analysis['toplam_tutar']:,.2f} TL")
        lines.append(f"Ortalama Sipariş Tutarı: {order_analysis['ortalama_tutar']:,.2f} TL")
        lines.append(f"En Büyük Sipariş: {order_analysis['max_siparis']:,.2f} TL")
        lines.append(f"En Küçük Sipariş: {order_analysis['min_siparis']:,.2f} TL")

    return "\n".join(lines)


def calculate_cross_dept_budget_correction(budget_df, cross_dept_made, cross_dept_received):
    df = budget_df.copy()

    df["Ay_Normalized"] = df["Ay"].apply(normalize_ay)
    ay_sirasi = list(df["Ay_Normalized"])

    yanlis_aylik = pd.Series(0.0, index=range(len(df)))
    if cross_dept_made is not None and not cross_dept_made.empty:
        cdm = cross_dept_made.copy()
        cdm["tarih"] = pd.to_datetime(cdm["tarih"], errors="coerce")
        cdm = cdm.dropna(subset=["tarih"])
        if not cdm.empty:
            cdm["Ay_Num"] = cdm["tarih"].dt.month
            cdm["Ay_Normalized"] = cdm["Ay_Num"].map({i: AY_MAP[i] for i in range(1, 13)})
            aylik_yanlis = cdm.groupby("Ay_Normalized")["toplam_tutar"].sum()
            for idx, ay in enumerate(ay_sirasi):
                if ay in aylik_yanlis.index:
                    yanlis_aylik[idx] = aylik_yanlis[ay]

    eksik_aylik = pd.Series(0.0, index=range(len(df)))
    if cross_dept_received is not None and not cross_dept_received.empty:
        cdr = cross_dept_received.copy()
        cdr["tarih"] = pd.to_datetime(cdr["tarih"], errors="coerce")
        cdr = cdr.dropna(subset=["tarih"])
        if not cdr.empty:
            cdr["Ay_Num"] = cdr["tarih"].dt.month
            cdr["Ay_Normalized"] = cdr["Ay_Num"].map({i: AY_MAP[i] for i in range(1, 13)})
            aylik_eksik = cdr.groupby("Ay_Normalized")["toplam_tutar"].sum()
            for idx, ay in enumerate(ay_sirasi):
                if ay in aylik_eksik.index:
                    eksik_aylik[idx] = aylik_eksik[ay]

    gerceklesen_col = "Efektif_Gerceklesen" if "Efektif_Gerceklesen" in df.columns else "Gerceklesen"

    correction_df = pd.DataFrame({
        "Ay": df["Ay"].values,
        "Planlanan": df["Planlanan"].values,
        "Gerceklesen": df[gerceklesen_col].values,
        "Yanlis_Alim": yanlis_aylik.values,
        "Eksik_Alim": eksik_aylik.values,
    })
    correction_df["Duzeltilmis_Gerceklesen"] = (
        correction_df["Gerceklesen"]
        - correction_df["Yanlis_Alim"]
        + correction_df["Eksik_Alim"]
    )
    correction_df["Duzeltme_Etkisi"] = (
        correction_df["Duzeltilmis_Gerceklesen"] - correction_df["Gerceklesen"]
    )

    toplam_yanlis = float(yanlis_aylik.sum())
    toplam_eksik = float(eksik_aylik.sum())
    net_etki = toplam_eksik - toplam_yanlis
    toplam_gerceklesen = float(correction_df["Gerceklesen"].sum())
    toplam_duzeltilmis = float(correction_df["Duzeltilmis_Gerceklesen"].sum())
    toplam_planlanan = float(correction_df["Planlanan"].sum())

    ozet = {
        "toplam_yanlis_alim": round(toplam_yanlis, 2),
        "toplam_eksik_alim": round(toplam_eksik, 2),
        "net_duzeltme_etkisi": round(net_etki, 2),
        "orijinal_gerceklesen": round(toplam_gerceklesen, 2),
        "duzeltilmis_gerceklesen": round(toplam_duzeltilmis, 2),
        "orijinal_sapma": round(toplam_gerceklesen - toplam_planlanan, 2),
        "duzeltilmis_sapma": round(toplam_duzeltilmis - toplam_planlanan, 2),
    }

    return correction_df, ozet
