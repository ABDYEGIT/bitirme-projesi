import json
import os
import pandas as pd

from config import DB_PATH, VARSAYILAN_FIRE_ORANI


BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "sektor_benchmark.json")


def load_benchmark_data(path=None):
    filepath = path or BENCHMARK_PATH
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def calculate_yorglass_metrics(conn, yil=2025):
    query = """
        SELECT
            d.kod as dept_kod,
            SUM(b.planlanan_butce) as Toplam_Planlanan,
            SUM(b.gerceklesen_butce) as Toplam_Gerceklesen
        FROM butce b
        JOIN departmanlar d ON b.departman_id = d.id
        WHERE b.yil = ?
        GROUP BY d.kod
    """
    budget_df = pd.read_sql_query(query, conn, params=(yil,))

    toplam_planlanan = budget_df["Toplam_Planlanan"].sum()
    toplam_gerceklesen = budget_df["Toplam_Gerceklesen"].sum()

    dept_dagilim = {}
    for _, row in budget_df.iterrows():
        if toplam_gerceklesen > 0:
            dept_dagilim[row["dept_kod"]] = round(row["Toplam_Gerceklesen"] / toplam_gerceklesen, 2)
        else:
            dept_dagilim[row["dept_kod"]] = 0

    benchmark_data = load_benchmark_data()
    sabitler = benchmark_data.get("yorglass_sabitler", {}) if benchmark_data else {}

    yorglass = {
        "firma_adi": "Yorglass",
        "firma_tipi": "Orta Ölçekli",
        "yillik_uretim_butcesi": round(toplam_planlanan, 2),
        "yillik_gerceklesen": round(toplam_gerceklesen, 2),
        "fire_orani": VARSAYILAN_FIRE_ORANI,
        "calisan_sayisi": sabitler.get("calisan_sayisi", 1200),
        "yillik_ciro": sabitler.get("yillik_ciro", 350000000),
        "pazar_payi": sabitler.get("pazar_payi", 0.04),
        "birim_maliyet_ton": sabitler.get("birim_maliyet_ton", 4500),
        "kapasite_kullanim": sabitler.get("kapasite_kullanim", 0.75),
        "arge_oran": sabitler.get("arge_oran", 0.01),
        "fabrika_sayisi": sabitler.get("fabrika_sayisi", 4),
        "departman_dagilim": dept_dagilim,
    }

    return yorglass


def compare_with_benchmarks(yorglass_metrics, benchmark_data):
    firmalar = benchmark_data.get("firmalar", [])

    all_firms = [yorglass_metrics] + firmalar

    rows = []
    for firma in all_firms:
        rows.append({
            "Firma": firma["firma_adi"],
            "Tip": firma.get("firma_tipi", ""),
            "Uretim_Butcesi_TL": firma.get("yillik_uretim_butcesi", 0),
            "Fire_Orani": firma.get("fire_orani", 0),
            "Calisan_Sayisi": firma.get("calisan_sayisi", 0),
            "Yillik_Ciro_TL": firma.get("yillik_ciro", 0),
            "Pazar_Payi": firma.get("pazar_payi", 0),
            "Birim_Maliyet_Ton": firma.get("birim_maliyet_ton", 0),
            "Kapasite_Kullanim": firma.get("kapasite_kullanim", 0),
            "ARGE_Oran": firma.get("arge_oran", 0),
            "Fabrika_Sayisi": firma.get("fabrika_sayisi", 0),
        })

    firms_df = pd.DataFrame(rows)

    dept_rows = []
    for firma in all_firms:
        dag = firma.get("departman_dagilim", {})
        dept_rows.append({
            "Firma": firma["firma_adi"],
            "Uretim": dag.get("uretim", 0),
            "Bakim": dag.get("bakim", 0),
            "Kalite": dag.get("kalite", 0),
            "Lojistik": dag.get("lojistik", 0),
            "IT": dag.get("it", 0),
            "IK": dag.get("ik", 0),
        })
    dept_df = pd.DataFrame(dept_rows)

    ranking_metrics = {
        "Fire_Orani": {"ascending": True, "label": "Fire Oranı", "format": "percent", "best": "düşük"},
        "Birim_Maliyet_Ton": {"ascending": True, "label": "Birim Maliyet (TL/ton)", "format": "currency", "best": "düşük"},
        "Kapasite_Kullanim": {"ascending": False, "label": "Kapasite Kullanımı", "format": "percent", "best": "yüksek"},
        "ARGE_Oran": {"ascending": False, "label": "AR-GE Oranı", "format": "percent", "best": "yüksek"},
        "Pazar_Payi": {"ascending": False, "label": "Pazar Payı", "format": "percent", "best": "yüksek"},
        "Yillik_Ciro_TL": {"ascending": False, "label": "Yıllık Ciro", "format": "currency", "best": "yüksek"},
    }

    ranking_rows = []
    for metric, info in ranking_metrics.items():
        sorted_df = firms_df.sort_values(metric, ascending=info["ascending"]).reset_index(drop=True)
        yorglass_rank = sorted_df[sorted_df["Firma"] == "Yorglass"].index[0] + 1
        total = len(sorted_df)

        yorglass_val = firms_df[firms_df["Firma"] == "Yorglass"][metric].values[0]
        sektor_ort = firms_df[firms_df["Firma"] != "Yorglass"][metric].mean()
        en_iyi = sorted_df.iloc[0][metric]
        en_iyi_firma = sorted_df.iloc[0]["Firma"]

        ranking_rows.append({
            "Metrik": info["label"],
            "Yorglass": yorglass_val,
            "Sektor_Ortalama": round(sektor_ort, 4),
            "En_Iyi": en_iyi,
            "En_Iyi_Firma": en_iyi_firma,
            "Yorglass_Sira": yorglass_rank,
            "Toplam_Firma": total,
            "Durum": "Iyi" if yorglass_rank <= 2 else ("Orta" if yorglass_rank == 3 else "Gelistirilmeli"),
        })

    ranking_df = pd.DataFrame(ranking_rows)

    yorglass_fire = yorglass_metrics["fire_orani"]
    sektor_fire_ort = firms_df[firms_df["Firma"] != "Yorglass"]["Fire_Orani"].mean()
    yorglass_maliyet = yorglass_metrics["birim_maliyet_ton"]
    sektor_maliyet_ort = firms_df[firms_df["Firma"] != "Yorglass"]["Birim_Maliyet_Ton"].mean()

    summary = {
        "firma_sayisi": len(all_firms),
        "yorglass_fire": yorglass_fire,
        "sektor_fire_ort": round(sektor_fire_ort, 4),
        "fire_fark": round(yorglass_fire - sektor_fire_ort, 4),
        "yorglass_maliyet": yorglass_maliyet,
        "sektor_maliyet_ort": round(sektor_maliyet_ort, 2),
        "maliyet_fark": round(yorglass_maliyet - sektor_maliyet_ort, 2),
        "guclu_alanlar": len(ranking_df[ranking_df["Durum"] == "Iyi"]),
        "gelistirilmeli_alanlar": len(ranking_df[ranking_df["Durum"] == "Gelistirilmeli"]),
    }

    return firms_df, dept_df, ranking_df, summary


def get_benchmark_context_for_chatbot(firms_df, ranking_df, summary):
    lines = []
    lines.append("--- SEKTÖR BENCHMARK KARŞILAŞTIRMASI ---")
    lines.append(f"Toplam {summary['firma_sayisi']} firma karşılaştırılıyor (Yorglass dahil)")
    lines.append("")

    lines.append("FİRMA METRİKLERİ:")
    lines.append(firms_df.to_string(index=False))
    lines.append("")

    lines.append("YORGLASS SIRALAMA ANALİZİ:")
    for _, row in ranking_df.iterrows():
        lines.append(
            f"  {row['Metrik']}: Yorglass {row['Yorglass_Sira']}/{row['Toplam_Firma']} "
            f"(Yorglass: {row['Yorglass']}, Sektör Ort: {row['Sektor_Ortalama']}, "
            f"En İyi: {row['En_Iyi']} - {row['En_Iyi_Firma']}) → {row['Durum']}"
        )

    lines.append("")
    lines.append(f"Fire Oranı: Yorglass %{summary['yorglass_fire']*100:.1f} vs Sektör Ort %{summary['sektor_fire_ort']*100:.1f}")
    lines.append(f"Birim Maliyet: Yorglass {summary['yorglass_maliyet']:,.0f} TL/ton vs Sektör Ort {summary['sektor_maliyet_ort']:,.0f} TL/ton")

    return "\n".join(lines)
