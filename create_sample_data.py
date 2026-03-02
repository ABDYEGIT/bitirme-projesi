"""Ornek Excel dosyalari olusturma scripti."""
import pandas as pd
import os

output_dir = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(output_dir, exist_ok=True)

# --- Butce Verisi ---
budget_data = {
    "Ay": ["Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
           "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"],
    "Planlanan_Butce": [1_000_000, 1_000_000, 1_000_000, 1_000_000, 1_000_000, 1_000_000,
                        1_000_000, 1_000_000, 1_000_000, 1_000_000, 1_000_000, 1_000_000],
    "Gerceklesen_Butce": [800_000, 950_000, 1_100_000, 750_000, 1_200_000, 900_000,
                          1_050_000, 880_000, 970_000, 1_150_000, 820_000, 1_380_000],
}

budget_df = pd.DataFrame(budget_data)
budget_path = os.path.join(output_dir, "butce_planlanan_gerceklesen.xlsx")
budget_df.to_excel(budget_path, index=False, engine="openpyxl")
print(f"Butce dosyasi olusturuldu: {budget_path}")

# --- Siparis Verisi ---
order_data = {
    "Siparis_No": [f"SIP-2025-{str(i).zfill(4)}" for i in range(1, 31)],
    "Tarih": pd.date_range("2025-01-05", periods=30, freq="12D"),
    "Tutar": [45_000, 120_000, 15_000, 230_000, 8_500, 67_000, 340_000, 22_000, 55_000, 18_000,
              95_000, 410_000, 12_500, 78_000, 165_000, 33_000, 290_000, 7_800, 52_000, 88_000,
              145_000, 19_500, 62_000, 380_000, 27_000, 41_000, 115_000, 9_200, 73_000, 205_000],
    "Durum": ["Tamamlandi", "Tamamlandi", "Tamamlandi", "Devam Ediyor", "Tamamlandi",
              "Tamamlandi", "Devam Ediyor", "Tamamlandi", "Iptal", "Tamamlandi",
              "Tamamlandi", "Devam Ediyor", "Tamamlandi", "Tamamlandi", "Devam Ediyor",
              "Tamamlandi", "Tamamlandi", "Iptal", "Tamamlandi", "Devam Ediyor",
              "Tamamlandi", "Tamamlandi", "Devam Ediyor", "Tamamlandi", "Tamamlandi",
              "Iptal", "Devam Ediyor", "Tamamlandi", "Tamamlandi", "Devam Ediyor"],
    "Aciklama": ["Sunucu alimi", "Network ekipmanlari", "Kablo malzemesi", "ERP lisansi",
                 "Fare ve klavye", "Guvenlik yazilimi", "Veri merkezi", "Printer toneri",
                 "UPS sistemi", "Monitor", "Yazici", "Bulut hizmeti", "USB bellek",
                 "Firewall", "Sunucu bakimi", "Laptop cantasi", "Yazilim lisansi",
                 "Kirtasiye", "Switch", "Dizustu bilgisayar", "Projektor", "Harddisk",
                 "Kamera sistemi", "Sunucu rafi", "Access point", "Adaptör", "VPN lisansi",
                 "Mouse pad", "Telefon sistemi", "Yedekleme sistemi"],
}

order_df = pd.DataFrame(order_data)
order_path = os.path.join(output_dir, "siparisler.xlsx")
order_df.to_excel(order_path, index=False, engine="openpyxl")
print(f"Siparis dosyasi olusturuldu: {order_path}")

print("\nOrnek veriler basariyla olusturuldu!")
