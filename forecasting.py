import pandas as pd
import numpy as np

from config import FIRE_ETKI_AGIRLIKLARI, FABRIKA_DEPT_KODLARI


def _calculate_fire_adjustment(dept_kod, fire_2025, fire_2026):
    agirlik = FIRE_ETKI_AGIRLIKLARI.get(dept_kod, 0.0)

    if agirlik == 0.0:
        return 1.0

    fire_faktor = (1 + fire_2026) / (1 + fire_2025)
    adjustment = fire_faktor ** agirlik

    return adjustment


def _distribute_monthly(yillik_tahmin, aylik_oranlar):
    if not aylik_oranlar or sum(aylik_oranlar.values()) == 0:
        aylik = yillik_tahmin / 12
        return {f"{i}": round(aylik, 2) for i in range(1, 13)}

    toplam_oran = sum(aylik_oranlar.values())
    result = {}
    for ay, oran in aylik_oranlar.items():
        normalized = oran / toplam_oran
        result[ay] = round(yillik_tahmin * normalized, 2)

    return result


def generate_budget_forecast(conn, yil, enflasyon, guven_marji, fire_2025, fire_2026):
    from data_loader import load_budget_with_orders_matrix, load_budget_data

    matrix = load_budget_with_orders_matrix(conn, yil)

    if matrix.empty:
        return pd.DataFrame(), {}, pd.DataFrame()

    forecast_rows = []
    aylik_rows = []

    for _, row in matrix.iterrows():
        yer_id = int(row["yer_id"])
        dept_id = int(row["dept_id"])
        yer_kod = row["yer_kod"]
        yer_ad = row["yer_ad"]
        dept_kod = row["dept_kod"]
        dept_ad = row["dept_ad"]
        planlanan_2025 = float(row["Toplam_Planlanan"])
        gerceklesen_2025 = float(row["Toplam_Gerceklesen"])
        siparis_2025 = float(row["Toplam_Siparis"])
        efektif_2025 = float(row["Efektif"])

        kullanim_orani = (efektif_2025 / planlanan_2025 * 100) if planlanan_2025 > 0 else 0
        if kullanim_orani > 105:
            durum_2025 = "Aşım"
        elif kullanim_orani < 90:
            durum_2025 = "Tasarruf"
        else:
            durum_2025 = "Dengeli"

        baz = efektif_2025

        fire_adj = _calculate_fire_adjustment(dept_kod, fire_2025, fire_2026)
        baz_duzenli = baz * fire_adj
        fire_etkisi_tl = baz_duzenli - baz

        enflasyonlu = baz_duzenli * (1 + enflasyon)
        enflasyon_etkisi_tl = enflasyonlu - baz_duzenli

        tahmin_2026 = enflasyonlu * (1 + guven_marji)
        guven_etkisi_tl = tahmin_2026 - enflasyonlu

        fark = tahmin_2026 - planlanan_2025
        degisim_yuzde = (fark / planlanan_2025 * 100) if planlanan_2025 > 0 else 0

        forecast_rows.append({
            "yer_kod": yer_kod,
            "yer_ad": yer_ad,
            "dept_kod": dept_kod,
            "dept_ad": dept_ad,
            "Planlanan_2025": round(planlanan_2025, 2),
            "Gerceklesen_2025": round(gerceklesen_2025, 2),
            "Siparis_2025": round(siparis_2025, 2),
            "Efektif_2025": round(efektif_2025, 2),
            "Kullanim_Orani": round(kullanim_orani, 1),
            "Durum_2025": durum_2025,
            "Fire_Etkisi_TL": round(fire_etkisi_tl, 2),
            "Enflasyon_Etkisi_TL": round(enflasyon_etkisi_tl, 2),
            "Guven_Etkisi_TL": round(guven_etkisi_tl, 2),
            "Tahmin_2026": round(tahmin_2026, 2),
            "Fark_2025_2026": round(fark, 2),
            "Degisim_Yuzde": round(degisim_yuzde, 1),
        })

        budget_aylik = load_budget_data(conn, yer_id, dept_id, yil)
        aylik_oranlar = {}

        if budget_aylik is not None and not budget_aylik.empty:
            toplam_gerc = budget_aylik["Gerceklesen"].sum()
            if toplam_gerc > 0:
                for _, b_row in budget_aylik.iterrows():
                    ay = str(b_row["Ay"])
                    aylik_oranlar[ay] = float(b_row["Gerceklesen"])

        aylik_dagilim = _distribute_monthly(tahmin_2026, aylik_oranlar)

        for ay, tutar in aylik_dagilim.items():
            aylik_rows.append({
                "yer_kod": yer_kod,
                "yer_ad": yer_ad,
                "dept_kod": dept_kod,
                "dept_ad": dept_ad,
                "Ay": ay,
                "Tahmin_2026": tutar,
            })

    forecast_df = pd.DataFrame(forecast_rows)
    aylik_tahmin_df = pd.DataFrame(aylik_rows)

    ozet = {}
    if not forecast_df.empty:
        ozet = {
            "toplam_planlanan_2025": forecast_df["Planlanan_2025"].sum(),
            "toplam_efektif_2025": forecast_df["Efektif_2025"].sum(),
            "toplam_tahmin_2026": forecast_df["Tahmin_2026"].sum(),
            "toplam_fire_etkisi": forecast_df["Fire_Etkisi_TL"].sum(),
            "toplam_enflasyon_etkisi": forecast_df["Enflasyon_Etkisi_TL"].sum(),
            "toplam_guven_etkisi": forecast_df["Guven_Etkisi_TL"].sum(),
            "toplam_fark": forecast_df["Fark_2025_2026"].sum(),
            "ortalama_degisim": forecast_df["Degisim_Yuzde"].mean(),
            "asim_dept_sayisi": len(forecast_df[forecast_df["Durum_2025"] == "Aşım"]),
            "tasarruf_dept_sayisi": len(forecast_df[forecast_df["Durum_2025"] == "Tasarruf"]),
            "dengeli_dept_sayisi": len(forecast_df[forecast_df["Durum_2025"] == "Dengeli"]),
            "dept_sayisi": len(forecast_df),
        }

    return forecast_df, ozet, aylik_tahmin_df
