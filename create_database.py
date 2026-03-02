"""
Yorglass Finans Veritabani Olusturma Scripti.

5 isletme, 6 departman tipi, 18 kombinasyon.
Butce, siparis, malzeme ve departmanlar arasi alim verileri.

Kullanim:
  python create_database.py
"""
import sqlite3
import os
import random

from config import (
    DB_PATH,
    ORGANIZASYON,
    URETIM_YERLERI,
    DEPARTMANLAR,
    BUTCE_BAZLARI,
)

AY_LISTESI = [
    "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
    "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
]

# Fabrika bazinda buyukluk carpanlari
FABRIKA_CARPANLARI = {
    "merkez": 1.0,
    "cerkezkoy": 1.10,   # En buyuk fabrika
    "eskisehir": 0.95,
    "manisa": 0.85,
    "bolu": 0.75,
}


# ============================
# TABLO OLUSTURMA
# ============================

def create_tables(conn):
    """Tum tablolari olustur (eski tablolar varsa sil)."""
    cursor = conn.cursor()

    # Eski tablolari sil (siralama FK bagimliligina gore)
    for table in ["malzeme_hareketleri", "malzemeler", "mal_gruplari",
                  "siparisler", "butce", "uretim_yeri_departman",
                  "departmanlar", "uretim_yerleri"]:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uretim_yerleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT NOT NULL UNIQUE,
            ad TEXT NOT NULL,
            sira INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departmanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT NOT NULL UNIQUE,
            ad TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uretim_yeri_departman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_yeri_id INTEGER NOT NULL REFERENCES uretim_yerleri(id),
            departman_id INTEGER NOT NULL REFERENCES departmanlar(id),
            UNIQUE(uretim_yeri_id, departman_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS butce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_yeri_id INTEGER NOT NULL REFERENCES uretim_yerleri(id),
            departman_id INTEGER NOT NULL REFERENCES departmanlar(id),
            yil INTEGER NOT NULL DEFAULT 2025,
            ay TEXT NOT NULL,
            planlanan_butce REAL NOT NULL,
            gerceklesen_butce REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_yeri_id INTEGER NOT NULL REFERENCES uretim_yerleri(id),
            departman_id INTEGER NOT NULL REFERENCES departmanlar(id),
            siparis_no TEXT NOT NULL,
            tarih TEXT NOT NULL,
            tutar REAL NOT NULL,
            durum TEXT,
            aciklama TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mal_gruplari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT NOT NULL UNIQUE,
            ad TEXT NOT NULL,
            sorumlu_departman_id INTEGER REFERENCES departmanlar(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS malzemeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mal_grubu_id INTEGER NOT NULL REFERENCES mal_gruplari(id),
            malzeme_kodu TEXT NOT NULL UNIQUE,
            malzeme_adi TEXT NOT NULL,
            birim TEXT DEFAULT 'Adet',
            birim_fiyat REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS malzeme_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_yeri_id INTEGER NOT NULL REFERENCES uretim_yerleri(id),
            departman_id INTEGER NOT NULL REFERENCES departmanlar(id),
            malzeme_id INTEGER NOT NULL REFERENCES malzemeler(id),
            tarih TEXT NOT NULL,
            miktar REAL NOT NULL,
            birim_fiyat REAL NOT NULL,
            toplam_tutar REAL NOT NULL,
            hareket_tipi TEXT DEFAULT 'alis',
            kaynak_departman_id INTEGER REFERENCES departmanlar(id),
            kaynak_uretim_yeri_id INTEGER REFERENCES uretim_yerleri(id),
            aciklama TEXT
        )
    """)

    # Indexler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_butce_yer_dept ON butce(uretim_yeri_id, departman_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_siparisler_yer_dept ON siparisler(uretim_yeri_id, departman_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_malzeme_har_yer_dept ON malzeme_hareketleri(uretim_yeri_id, departman_id)")

    conn.commit()
    print("Tablolar olusturuldu (8 tablo).")


# ============================
# LOOKUP VERILERI
# ============================

def insert_lookup_data(conn):
    """Uretim yerleri, departmanlar ve junction verileri ekle."""
    cursor = conn.cursor()

    yer_sira = {"merkez": 1, "cerkezkoy": 2, "eskisehir": 3, "manisa": 4, "bolu": 5}
    for kod, ad in URETIM_YERLERI.items():
        cursor.execute(
            "INSERT INTO uretim_yerleri (kod, ad, sira) VALUES (?, ?, ?)",
            (kod, ad, yer_sira[kod]),
        )

    for kod, ad in DEPARTMANLAR.items():
        cursor.execute(
            "INSERT INTO departmanlar (kod, ad) VALUES (?, ?)",
            (kod, ad),
        )

    # Junction: hangi lokasyonda hangi departman var
    for yer_kod, dept_kodlari in ORGANIZASYON.items():
        for dept_kod in dept_kodlari:
            cursor.execute(
                """INSERT INTO uretim_yeri_departman (uretim_yeri_id, departman_id)
                   SELECT uy.id, d.id
                   FROM uretim_yerleri uy, departmanlar d
                   WHERE uy.kod = ? AND d.kod = ?""",
                (yer_kod, dept_kod),
            )

    conn.commit()
    print("Lookup verileri eklendi (5 yer, 6 departman, 18 junction).")


def get_id_maps(conn):
    """ID lookup tablolari olustur."""
    cursor = conn.cursor()

    cursor.execute("SELECT id, kod FROM uretim_yerleri")
    yer_map = {row[1]: row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT id, kod FROM departmanlar")
    dept_map = {row[1]: row[0] for row in cursor.fetchall()}

    return yer_map, dept_map


# ============================
# BUTCE VERILERI
# ============================

def insert_budget_data(conn, yer_map, dept_map):
    """18 kombinasyon x 12 ay = 216 butce kaydi olustur."""
    cursor = conn.cursor()
    random.seed(42)

    kayit_sayisi = 0
    for yer_kod, dept_kodlari in ORGANIZASYON.items():
        carpan = FABRIKA_CARPANLARI[yer_kod]

        for dept_kod in dept_kodlari:
            baz = BUTCE_BAZLARI[dept_kod]
            planlanan = round(baz * carpan, 2)

            for ay in AY_LISTESI:
                # Gerceklesen: %60-%120 arasi rastgele varyans
                rassal = random.uniform(0.60, 1.20)
                gerceklesen = round(planlanan * rassal, 2)

                cursor.execute(
                    """INSERT INTO butce
                       (uretim_yeri_id, departman_id, yil, ay, planlanan_butce, gerceklesen_butce)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (yer_map[yer_kod], dept_map[dept_kod], 2025, ay, planlanan, gerceklesen),
                )
                kayit_sayisi += 1

    conn.commit()
    print(f"Butce verileri eklendi ({kayit_sayisi} kayit).")


# ============================
# SIPARIS VERILERI
# ============================

def insert_order_data(conn, yer_map, dept_map):
    """Her departman icin 8-20 arasi siparis olustur."""
    cursor = conn.cursor()
    random.seed(123)

    siparis_sayac = 1
    durumlar = ["Tamamlandi", "Devam Ediyor", "Iptal"]
    durum_agirlik = [0.50, 0.35, 0.15]

    # Departman bazli aciklama sablonlari
    aciklama_sablonlari = {
        "it": [
            "Sunucu alımı", "Yazılım lisansı", "Network ekipmanı",
            "Güvenlik yazılımı", "Laptop", "Monitor", "UPS sistemi",
            "Firewall", "Switch", "Kablosuz erişim noktası",
        ],
        "ik": [
            "Eğitim hizmeti", "Danışmanlık", "Ofis mobilyası",
            "Personel etkinliği", "İş güvenliği ekipmanı",
            "Sağlık taraması", "Yemek hizmeti",
        ],
        "uretim": [
            "Cam hammadde alımı", "Üretim makine parçası", "Kalıp siparişi",
            "Fırın bakım malzemesi", "Cam kesme aleti", "Temperli cam ekipmanı",
            "Lamine hattı malzemesi", "PVB film alımı",
        ],
        "kalite": [
            "Test cihazı", "Kalibrasyon hizmeti", "Laboratuvar malzemesi",
            "Ölçüm aleti", "Numune seti", "Kalınlık ölçer",
            "Optik test ekipmanı",
        ],
        "bakim": [
            "Yedek parça", "Bakım kiti", "Yağ ve gres",
            "Elektrik malzemesi", "Kaynak malzemesi", "Rulman seti",
            "Pompa parçası", "Hidrolik hortum",
        ],
        "lojistik": [
            "Ambalaj malzemesi", "Palet", "Forklift parçası",
            "Etiketleme makinesi", "Streç film", "Karton kutu",
            "Konveyör bandı", "Barkod yazıcı",
        ],
    }

    toplam_siparis = 0
    for yer_kod, dept_kodlari in ORGANIZASYON.items():
        for dept_kod in dept_kodlari:
            baz_butce = BUTCE_BAZLARI[dept_kod]
            siparis_adet = random.randint(8, 20)

            for _ in range(siparis_adet):
                ay_num = random.randint(1, 12)
                gun = random.randint(1, 28)
                tarih = f"2025-{ay_num:02d}-{gun:02d}"

                # Tutar: butcenin %1-%15'i arasi
                tutar = round(baz_butce * random.uniform(0.01, 0.15), 2)
                durum = random.choices(durumlar, weights=durum_agirlik, k=1)[0]
                aciklama = random.choice(aciklama_sablonlari[dept_kod])

                siparis_no = f"SIP-{yer_kod[:3].upper()}-{dept_kod[:3].upper()}-{siparis_sayac:04d}"

                cursor.execute(
                    """INSERT INTO siparisler
                       (uretim_yeri_id, departman_id, siparis_no, tarih, tutar, durum, aciklama)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (yer_map[yer_kod], dept_map[dept_kod], siparis_no, tarih, tutar, durum, aciklama),
                )
                siparis_sayac += 1
                toplam_siparis += 1

    conn.commit()
    print(f"Siparis verileri eklendi ({toplam_siparis} kayit).")


# ============================
# MALZEME VERILERI
# ============================

def insert_material_data(conn, dept_map):
    """Mal gruplari ve malzemeleri ekle."""
    cursor = conn.cursor()

    # Mal gruplari: (kod, ad, sorumlu_departman_kodu)
    mal_gruplari = [
        ("cam_hammadde", "Cam Hammadde", "uretim"),
        ("kimyasal", "Kimyasal Malzeme", "uretim"),
        ("yedek_parca", "Yedek Parça", "bakim"),
        ("elektrik", "Elektrik Malzemesi", "bakim"),
        ("olcum_ekipman", "Ölçüm/Test Ekipmanı", "kalite"),
        ("ambalaj", "Ambalaj Malzemesi", "lojistik"),
        ("nakliye", "Nakliye Ekipmanı", "lojistik"),
    ]

    for kod, ad, dept_kod in mal_gruplari:
        cursor.execute(
            "INSERT INTO mal_gruplari (kod, ad, sorumlu_departman_id) VALUES (?, ?, ?)",
            (kod, ad, dept_map[dept_kod]),
        )

    # Malzemeler: (kodu, adi, birim, birim_fiyat, mal_grubu_kodu)
    malzemeler = [
        # Cam Hammadde -> Uretim
        ("CAM-001", "Düzcam 4mm", "m2", 85.0, "cam_hammadde"),
        ("CAM-002", "Lamine Cam 6mm", "m2", 145.0, "cam_hammadde"),
        ("CAM-003", "Temperli Cam 8mm", "m2", 210.0, "cam_hammadde"),
        ("CAM-004", "Cam Elyaf", "kg", 32.0, "cam_hammadde"),
        ("CAM-005", "Low-E Cam", "m2", 280.0, "cam_hammadde"),
        # Kimyasal -> Uretim
        ("KIM-001", "Silikon Yapistirici", "kg", 48.0, "kimyasal"),
        ("KIM-002", "PVB Film", "m2", 65.0, "kimyasal"),
        ("KIM-003", "Cam Boyasi", "lt", 120.0, "kimyasal"),
        ("KIM-004", "Temizleme Solusyonu", "lt", 25.0, "kimyasal"),
        # Yedek Parca -> Bakim
        ("YP-001", "Rulman 6205", "Adet", 35.0, "yedek_parca"),
        ("YP-002", "V-Kayis", "Adet", 28.0, "yedek_parca"),
        ("YP-003", "Hidrolik Motor", "Adet", 4500.0, "yedek_parca"),
        ("YP-004", "Pompa Kecesi", "Adet", 15.0, "yedek_parca"),
        ("YP-005", "Filtre Elemani", "Adet", 85.0, "yedek_parca"),
        # Elektrik -> Bakim
        ("ELK-001", "NH Sigorta 250A", "Adet", 45.0, "elektrik"),
        ("ELK-002", "Guc Kablosu 3x2.5", "metre", 12.0, "elektrik"),
        ("ELK-003", "Kontaktor 40A", "Adet", 180.0, "elektrik"),
        ("ELK-004", "Proximity Sensor", "Adet", 220.0, "elektrik"),
        # Olcum Ekipman -> Kalite
        ("OLC-001", "Dijital Mikrometre", "Adet", 850.0, "olcum_ekipman"),
        ("OLC-002", "Cam Kalinlik Olcer", "Adet", 1200.0, "olcum_ekipman"),
        ("OLC-003", "Sertlik Olcer", "Adet", 3500.0, "olcum_ekipman"),
        ("OLC-004", "Optik Duzlemlik Testi", "Adet", 5000.0, "olcum_ekipman"),
        # Ambalaj -> Lojistik
        ("AMB-001", "Karton Kutu (Cam)", "Adet", 8.5, "ambalaj"),
        ("AMB-002", "Strec Film", "Rulo", 45.0, "ambalaj"),
        ("AMB-003", "Kopuk Levha", "m2", 12.0, "ambalaj"),
        ("AMB-004", "Ahsap Palet", "Adet", 65.0, "ambalaj"),
        # Nakliye -> Lojistik
        ("NAK-001", "Forklift Lastigi", "Adet", 950.0, "nakliye"),
        ("NAK-002", "Konveyor Bant", "metre", 180.0, "nakliye"),
        ("NAK-003", "Barkod Etiketi", "Rulo", 35.0, "nakliye"),
    ]

    # Mal grubu id map
    cursor.execute("SELECT id, kod FROM mal_gruplari")
    mg_map = {row[1]: row[0] for row in cursor.fetchall()}

    for kodu, adi, birim, fiyat, mg_kod in malzemeler:
        cursor.execute(
            "INSERT INTO malzemeler (mal_grubu_id, malzeme_kodu, malzeme_adi, birim, birim_fiyat) VALUES (?, ?, ?, ?, ?)",
            (mg_map[mg_kod], kodu, adi, birim, fiyat),
        )

    conn.commit()
    print(f"Malzeme verileri eklendi ({len(mal_gruplari)} grup, {len(malzemeler)} malzeme).")


# ============================
# MALZEME HAREKETLERI
# ============================

def insert_material_movements(conn, yer_map, dept_map):
    """
    Her fabrika departmani icin malzeme hareketleri olustur.
    Departmanlar arasi alimlar da dahil (cross-department purchases).
    """
    cursor = conn.cursor()
    random.seed(456)

    # Malzemeleri mal grubu bilgisiyle yukle
    cursor.execute("""
        SELECT m.id, m.malzeme_kodu, m.birim_fiyat, mg.kod as mg_kod, mg.sorumlu_departman_id
        FROM malzemeler m
        JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
    """)
    malzeme_list = cursor.fetchall()

    # Malzemeleri gruplara ayir
    malzeme_by_group = {}
    for m_id, m_kod, m_fiyat, mg_kod, sorumlu_dept_id in malzeme_list:
        if mg_kod not in malzeme_by_group:
            malzeme_by_group[mg_kod] = []
        malzeme_by_group[mg_kod].append((m_id, m_kod, m_fiyat, sorumlu_dept_id))

    # Her departmanin malzeme alim dagilimi
    # Kendi sorumlu grubundan cok, digerlerinden az alir → cross-dept tespit
    dept_malzeme_dagilim = {
        "uretim": {
            "cam_hammadde": 0.35, "kimyasal": 0.30,
            "yedek_parca": 0.10, "elektrik": 0.08,
            "olcum_ekipman": 0.07,
            "ambalaj": 0.05, "nakliye": 0.05,
        },
        "bakim": {
            "yedek_parca": 0.35, "elektrik": 0.25,
            "cam_hammadde": 0.10, "kimyasal": 0.10,
            "olcum_ekipman": 0.08,
            "ambalaj": 0.06, "nakliye": 0.06,
        },
        "kalite": {
            "olcum_ekipman": 0.45,
            "kimyasal": 0.18, "cam_hammadde": 0.12,
            "elektrik": 0.10,
            "ambalaj": 0.08, "nakliye": 0.07,
        },
        "lojistik": {
            "ambalaj": 0.35, "nakliye": 0.25,
            "yedek_parca": 0.12, "elektrik": 0.08,
            "cam_hammadde": 0.10, "kimyasal": 0.05,
            "olcum_ekipman": 0.05,
        },
    }

    fabrika_yerler = ["cerkezkoy", "eskisehir", "manisa", "bolu"]
    fabrika_deptlar = ["uretim", "kalite", "bakim", "lojistik"]

    toplam_hareket = 0
    for yer_kod in fabrika_yerler:
        for dept_kod in fabrika_deptlar:
            hareket_sayisi = random.randint(25, 45)
            dagilim = dept_malzeme_dagilim.get(dept_kod, {})

            for _ in range(hareket_sayisi):
                mg_secim = random.choices(
                    list(dagilim.keys()),
                    weights=list(dagilim.values()),
                    k=1,
                )[0]

                if mg_secim not in malzeme_by_group:
                    continue

                malzeme = random.choice(malzeme_by_group[mg_secim])
                m_id, m_kod, m_fiyat, sorumlu_dept_id = malzeme

                ay_num = random.randint(1, 12)
                gun = random.randint(1, 28)
                tarih = f"2025-{ay_num:02d}-{gun:02d}"

                miktar = round(random.uniform(1, 100), 1)
                fiyat_varyans = m_fiyat * random.uniform(0.90, 1.10)
                toplam = round(miktar * fiyat_varyans, 2)

                alan_dept_id = dept_map[dept_kod]
                kaynak_dept_id = None
                kaynak_yer_id = None

                if sorumlu_dept_id != alan_dept_id:
                    kaynak_dept_id = sorumlu_dept_id
                    kaynak_yer_id = yer_map[yer_kod]

                aciklama = "Dept. arasi alim" if kaynak_dept_id else "Normal alim"

                cursor.execute(
                    """INSERT INTO malzeme_hareketleri
                       (uretim_yeri_id, departman_id, malzeme_id, tarih, miktar,
                        birim_fiyat, toplam_tutar, hareket_tipi,
                        kaynak_departman_id, kaynak_uretim_yeri_id, aciklama)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        yer_map[yer_kod], dept_map[dept_kod], m_id, tarih,
                        miktar, round(fiyat_varyans, 2), toplam,
                        "alis", kaynak_dept_id, kaynak_yer_id, aciklama,
                    ),
                )
                toplam_hareket += 1

    conn.commit()
    print(f"Malzeme hareketleri eklendi ({toplam_hareket} kayit).")


# ============================
# ANA FONKSIYON
# ============================

if __name__ == "__main__":
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"Eski veritabani silindi: {DB_PATH}")
        except PermissionError:
            # Dosya baska bir islem tarafindan kullaniliyor, yeniden adlandir
            backup = DB_PATH + ".old"
            try:
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(DB_PATH, backup)
                print(f"Eski veritabani yeniden adlandirildi: {backup}")
            except Exception:
                print("UYARI: Eski DB silinemedi/tasinamadi. Yeni DB uzerine yazilacak.")

    conn = sqlite3.connect(DB_PATH)

    create_tables(conn)
    insert_lookup_data(conn)

    yer_map, dept_map = get_id_maps(conn)

    insert_budget_data(conn, yer_map, dept_map)
    insert_order_data(conn, yer_map, dept_map)
    insert_material_data(conn, dept_map)
    insert_material_movements(conn, yer_map, dept_map)

    # Ozet
    print("\n--- Veritabani Ozeti ---")
    cursor = conn.cursor()
    for table in [
        "uretim_yerleri", "departmanlar", "uretim_yeri_departman",
        "butce", "siparisler", "mal_gruplari", "malzemeler", "malzeme_hareketleri",
    ]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} kayit")

    conn.close()
    print(f"\nVeritabani olusturuldu: {DB_PATH}")
