"""
Yorglass Finans - Departmanlar Arasi Karsilastirma Modulu.

Lokasyon ve departman bazli karsilastirma analizleri.
"""
import pandas as pd


def calculate_utilization_matrix(matrix_df):
    """Kullanim orani matrisi hesapla."""
    df = matrix_df.copy()
    df["Kullanim_Orani"] = (df["Toplam_Gerceklesen"] / df["Toplam_Planlanan"] * 100).round(2)
    df["Fark"] = (df["Toplam_Planlanan"] - df["Toplam_Gerceklesen"]).round(2)
    return df


def rank_departments(matrix_df, by="Kullanim_Orani", ascending=True):
    """Departmanlari belirli bir metrige gore sirala."""
    df = calculate_utilization_matrix(matrix_df)
    df["Etiket"] = df["yer_ad"] + " - " + df["dept_ad"]
    return df.sort_values(by=by, ascending=ascending)


def location_totals(matrix_df):
    """Lokasyon bazli toplamlar."""
    return matrix_df.groupby(["yer_kod", "yer_ad"]).agg({
        "Toplam_Planlanan": "sum",
        "Toplam_Gerceklesen": "sum",
    }).reset_index()


def department_type_totals(matrix_df):
    """Departman tipi bazli toplamlar (tum lokasyonlar)."""
    return matrix_df.groupby(["dept_kod", "dept_ad"]).agg({
        "Toplam_Planlanan": "sum",
        "Toplam_Gerceklesen": "sum",
    }).reset_index()


def cross_location_comparison(matrix_df, dept_kod):
    """Ayni departman tipini lokasyonlar arasi karsilastir."""
    return matrix_df[matrix_df["dept_kod"] == dept_kod].copy()


def company_kpis(matrix_df):
    """Sirket geneli KPI'lar."""
    toplam_planlanan = matrix_df["Toplam_Planlanan"].sum()
    toplam_gerceklesen = matrix_df["Toplam_Gerceklesen"].sum()
    toplam_kalan = toplam_planlanan - toplam_gerceklesen
    kullanim = (toplam_gerceklesen / toplam_planlanan * 100) if toplam_planlanan > 0 else 0

    return {
        "toplam_planlanan": round(toplam_planlanan, 2),
        "toplam_gerceklesen": round(toplam_gerceklesen, 2),
        "toplam_kalan": round(toplam_kalan, 2),
        "kullanim_orani": round(kullanim, 2),
        "departman_sayisi": len(matrix_df),
        "lokasyon_sayisi": matrix_df["yer_kod"].nunique(),
    }
