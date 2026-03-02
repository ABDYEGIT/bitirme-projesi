"""
Ornek SAP tablo metadata Excel dosyasi olusturma scripti.
Bir kere calistirilir, sample_metadata.xlsx dosyasini uretir.
"""
import pandas as pd
from pathlib import Path

# Sheet 1: Tablolar
tablolar_data = [
    # MARA - Malzeme Ana Verileri
    {"TABLO_ADI": "MARA", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARA", "ALAN_ADI": "MTART", "ALAN_ACIKLAMASI": "Malzeme Tipi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "MARA", "ALAN_ADI": "MATKL", "ALAN_ACIKLAMASI": "Malzeme Grubu", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "MARA", "ALAN_ADI": "MEINS", "ALAN_ACIKLAMASI": "Temel Olcu Birimi", "VERI_TIPI": "UNIT", "ANAHTAR": ""},
    {"TABLO_ADI": "MARA", "ALAN_ADI": "MAKTX", "ALAN_ACIKLAMASI": "Malzeme Kisa Metni", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # MARC - Malzeme Tesis Verileri
    {"TABLO_ADI": "MARC", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARC", "ALAN_ADI": "WERKS", "ALAN_ACIKLAMASI": "Uretim Yeri (Tesis)", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARC", "ALAN_ADI": "LGORT", "ALAN_ACIKLAMASI": "Varsayilan Depo Yeri", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "MARC", "ALAN_ADI": "DISMM", "ALAN_ACIKLAMASI": "MRP Tipi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "MARC", "ALAN_ADI": "DISPO", "ALAN_ACIKLAMASI": "MRP Kontroloru", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # MARD - Malzeme Depo Verileri
    {"TABLO_ADI": "MARD", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARD", "ALAN_ADI": "WERKS", "ALAN_ACIKLAMASI": "Uretim Yeri (Tesis)", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARD", "ALAN_ADI": "LGORT", "ALAN_ACIKLAMASI": "Depo Yeri", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MARD", "ALAN_ADI": "LABST", "ALAN_ACIKLAMASI": "Serbest Kullanim Stoku", "VERI_TIPI": "QUAN", "ANAHTAR": ""},
    {"TABLO_ADI": "MARD", "ALAN_ADI": "INSME", "ALAN_ACIKLAMASI": "Kalite Kontrol Stoku", "VERI_TIPI": "QUAN", "ANAHTAR": ""},
    {"TABLO_ADI": "MARD", "ALAN_ADI": "SPEME", "ALAN_ACIKLAMASI": "Bloke Stok", "VERI_TIPI": "QUAN", "ANAHTAR": ""},
    # ZMM_T_RENK - Custom Renk Tablosu
    {"TABLO_ADI": "ZMM_T_RENK", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "ZMM_T_RENK", "ALAN_ADI": "RENK", "ALAN_ACIKLAMASI": "Renk Kodu", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "ZMM_T_RENK", "ALAN_ADI": "RENK_TANIMI", "ALAN_ACIKLAMASI": "Renk Tanimi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # MAKT - Malzeme Kisa Metinleri
    {"TABLO_ADI": "MAKT", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MAKT", "ALAN_ADI": "SPRAS", "ALAN_ACIKLAMASI": "Dil Anahtari", "VERI_TIPI": "LANG", "ANAHTAR": "PK"},
    {"TABLO_ADI": "MAKT", "ALAN_ADI": "MAKTX", "ALAN_ACIKLAMASI": "Malzeme Kisa Metni", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # EKKO - Satin Alma Belge Basi
    {"TABLO_ADI": "EKKO", "ALAN_ADI": "EBELN", "ALAN_ACIKLAMASI": "Satin Alma Belge Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "EKKO", "ALAN_ADI": "BUKRS", "ALAN_ACIKLAMASI": "Sirket Kodu", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "EKKO", "ALAN_ADI": "BSART", "ALAN_ACIKLAMASI": "Belge Turu", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "EKKO", "ALAN_ADI": "LIFNR", "ALAN_ACIKLAMASI": "Tedarikci Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "EKKO", "ALAN_ADI": "AEDAT", "ALAN_ACIKLAMASI": "Olusturma Tarihi", "VERI_TIPI": "DATS", "ANAHTAR": ""},
    # EKPO - Satin Alma Belge Kalemi
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "EBELN", "ALAN_ACIKLAMASI": "Satin Alma Belge Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "EBELP", "ALAN_ACIKLAMASI": "Kalem Numarasi", "VERI_TIPI": "NUMC", "ANAHTAR": "PK"},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "MENGE", "ALAN_ACIKLAMASI": "Siparis Miktari", "VERI_TIPI": "QUAN", "ANAHTAR": ""},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "MEINS", "ALAN_ACIKLAMASI": "Siparis Birimi", "VERI_TIPI": "UNIT", "ANAHTAR": ""},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "NETPR", "ALAN_ACIKLAMASI": "Net Fiyat", "VERI_TIPI": "CURR", "ANAHTAR": ""},
    {"TABLO_ADI": "EKPO", "ALAN_ADI": "WERKS", "ALAN_ACIKLAMASI": "Tesis", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # LFA1 - Tedarikci Ana Verileri
    {"TABLO_ADI": "LFA1", "ALAN_ADI": "LIFNR", "ALAN_ACIKLAMASI": "Tedarikci Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "LFA1", "ALAN_ADI": "NAME1", "ALAN_ACIKLAMASI": "Tedarikci Adi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "LFA1", "ALAN_ADI": "ORT01", "ALAN_ACIKLAMASI": "Sehir", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "LFA1", "ALAN_ADI": "LAND1", "ALAN_ACIKLAMASI": "Ulke Kodu", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    # ZMM_T_KALITE - Custom Kalite Tablosu
    {"TABLO_ADI": "ZMM_T_KALITE", "ALAN_ADI": "MATNR", "ALAN_ACIKLAMASI": "Malzeme Numarasi", "VERI_TIPI": "CHAR", "ANAHTAR": "PK"},
    {"TABLO_ADI": "ZMM_T_KALITE", "ALAN_ADI": "KALITE_SINIFI", "ALAN_ACIKLAMASI": "Kalite Sinifi", "VERI_TIPI": "CHAR", "ANAHTAR": ""},
    {"TABLO_ADI": "ZMM_T_KALITE", "ALAN_ADI": "SON_KONTROL_TARIHI", "ALAN_ACIKLAMASI": "Son Kalite Kontrol Tarihi", "VERI_TIPI": "DATS", "ANAHTAR": ""},
]

# Sheet 2: Iliskiler
iliskiler_data = [
    {"KAYNAK_TABLO": "MARA", "KAYNAK_ALAN": "MATNR", "HEDEF_TABLO": "MARC", "HEDEF_ALAN": "MATNR", "ILISKI_TIPI": "1:N"},
    {"KAYNAK_TABLO": "MARC", "KAYNAK_ALAN": "MATNR+WERKS", "HEDEF_TABLO": "MARD", "HEDEF_ALAN": "MATNR+WERKS", "ILISKI_TIPI": "1:N"},
    {"KAYNAK_TABLO": "MARA", "KAYNAK_ALAN": "MATNR", "HEDEF_TABLO": "MAKT", "HEDEF_ALAN": "MATNR", "ILISKI_TIPI": "1:N"},
    {"KAYNAK_TABLO": "ZMM_T_RENK", "KAYNAK_ALAN": "MATNR", "HEDEF_TABLO": "MARA", "HEDEF_ALAN": "MATNR", "ILISKI_TIPI": "N:1"},
    {"KAYNAK_TABLO": "EKKO", "KAYNAK_ALAN": "EBELN", "HEDEF_TABLO": "EKPO", "HEDEF_ALAN": "EBELN", "ILISKI_TIPI": "1:N"},
    {"KAYNAK_TABLO": "EKPO", "KAYNAK_ALAN": "MATNR", "HEDEF_TABLO": "MARA", "HEDEF_ALAN": "MATNR", "ILISKI_TIPI": "N:1"},
    {"KAYNAK_TABLO": "EKKO", "KAYNAK_ALAN": "LIFNR", "HEDEF_TABLO": "LFA1", "HEDEF_ALAN": "LIFNR", "ILISKI_TIPI": "N:1"},
    {"KAYNAK_TABLO": "ZMM_T_KALITE", "KAYNAK_ALAN": "MATNR", "HEDEF_TABLO": "MARA", "HEDEF_ALAN": "MATNR", "ILISKI_TIPI": "N:1"},
]

# Excel olustur
output_path = Path(__file__).resolve().parent / "sample_metadata.xlsx"

df_tablolar = pd.DataFrame(tablolar_data)
df_iliskiler = pd.DataFrame(iliskiler_data)

with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    df_tablolar.to_excel(writer, sheet_name="Tablolar", index=False)
    df_iliskiler.to_excel(writer, sheet_name="Iliskiler", index=False)

print(f"sample_metadata.xlsx olusturuldu: {output_path}")
print(f"  Tablolar: {df_tablolar['TABLO_ADI'].nunique()} tablo, {len(df_tablolar)} alan")
print(f"  Iliskiler: {len(df_iliskiler)} iliski")
