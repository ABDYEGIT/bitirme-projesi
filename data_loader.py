"""
Yorglass Finans - Veri Yukleme Modulu.

Cok lokasyonlu SQLite sorgulari.
Butce, siparis ve malzeme verilerini yukler.
"""
import sqlite3
import pandas as pd


# ============================
# VERITABANI BAGLANTISI
# ============================

def connect_db(db_path):
    """SQLite veritabanina baglan."""
    try:
        conn = sqlite3.connect(db_path)
        return conn, None
    except Exception as e:
        return None, f"Veritabani baglantisi basarisiz: {e}"


# ============================
# LOOKUP SORGULARI
# ============================

def get_uretim_yerleri(conn):
    """Tum uretim yerlerini dondur."""
    query = "SELECT id, kod, ad FROM uretim_yerleri ORDER BY sira"
    return pd.read_sql_query(query, conn)


def get_departmanlar(conn):
    """Tum departmanlari dondur."""
    query = "SELECT id, kod, ad FROM departmanlar"
    return pd.read_sql_query(query, conn)


def get_uretim_yeri_departmanlar(conn, yer_id):
    """Belirli bir uretim yerindeki departmanlari dondur."""
    query = """
        SELECT d.id, d.kod, d.ad
        FROM departmanlar d
        JOIN uretim_yeri_departman uyd ON d.id = uyd.departman_id
        WHERE uyd.uretim_yeri_id = ?
        ORDER BY d.id
    """
    return pd.read_sql_query(query, conn, params=(yer_id,))


# ============================
# BUTCE SORGULARI
# ============================

def load_budget_data(conn, yer_id, dept_id, yil=2025):
    """
    Belirli uretim yeri + departman icin butce verisini yukle.
    analysis.py uyumlu format: [Ay, Planlanan, Gerceklesen]
    """
    query = """
        SELECT ay as Ay, planlanan_butce as Planlanan, gerceklesen_butce as Gerceklesen
        FROM butce
        WHERE uretim_yeri_id = ? AND departman_id = ? AND yil = ?
    """
    df = pd.read_sql_query(query, conn, params=(yer_id, dept_id, yil))

    df["Planlanan"] = pd.to_numeric(df["Planlanan"], errors="coerce")
    df["Gerceklesen"] = pd.to_numeric(df["Gerceklesen"], errors="coerce")
    df = df.dropna(subset=["Planlanan", "Gerceklesen"])

    return df if not df.empty else None


def load_budget_monthly_detail(conn, yil=2025):
    """
    Tum lokasyon x departman icin AYLIK butce detayini yukle.
    Chatbot icin: her ay, her departman, her lokasyonun planlanan/gerceklesen degerleri.
    """
    query = """
        SELECT
            uy.ad as Uretim_Yeri,
            d.ad as Departman,
            b.ay as Ay,
            b.planlanan_butce as Planlanan,
            b.gerceklesen_butce as Gerceklesen
        FROM butce b
        JOIN uretim_yerleri uy ON b.uretim_yeri_id = uy.id
        JOIN departmanlar d ON b.departman_id = d.id
        WHERE b.yil = ?
        ORDER BY uy.sira, d.id, b.ay
    """
    return pd.read_sql_query(query, conn, params=(yil,))


def load_budget_matrix(conn, yil=2025):
    """
    Tum lokasyon x departman butce ozeti matrisini yukle.
    Genel karsilastirma sayfasi icin kullanilir.
    """
    query = """
        SELECT
            uy.kod as yer_kod,
            uy.ad as yer_ad,
            d.kod as dept_kod,
            d.ad as dept_ad,
            SUM(b.planlanan_butce) as Toplam_Planlanan,
            SUM(b.gerceklesen_butce) as Toplam_Gerceklesen
        FROM butce b
        JOIN uretim_yerleri uy ON b.uretim_yeri_id = uy.id
        JOIN departmanlar d ON b.departman_id = d.id
        WHERE b.yil = ?
        GROUP BY uy.kod, uy.ad, d.kod, d.ad
        ORDER BY uy.sira, d.id
    """
    return pd.read_sql_query(query, conn, params=(yil,))


# ============================
# SIPARIS SORGULARI
# ============================

def load_order_data(conn, yer_id, dept_id):
    """
    Belirli uretim yeri + departman icin siparis verisini yukle.
    analysis.py uyumlu format: [SiparisNo, Tarih, Tutar, Durum]
    """
    query = """
        SELECT siparis_no as SiparisNo, tarih as Tarih, tutar as Tutar, durum as Durum
        FROM siparisler
        WHERE uretim_yeri_id = ? AND departman_id = ?
        ORDER BY tarih
    """
    df = pd.read_sql_query(query, conn, params=(yer_id, dept_id))

    df["Tutar"] = pd.to_numeric(df["Tutar"], errors="coerce")
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
    df = df.dropna(subset=["Tutar"])

    return df if not df.empty else None


def load_order_summary(conn):
    """Tum lokasyon x departman siparis ozetini yukle."""
    query = """
        SELECT
            uy.kod as yer_kod,
            uy.ad as yer_ad,
            d.kod as dept_kod,
            d.ad as dept_ad,
            COUNT(*) as Siparis_Adet,
            SUM(s.tutar) as Toplam_Tutar
        FROM siparisler s
        JOIN uretim_yerleri uy ON s.uretim_yeri_id = uy.id
        JOIN departmanlar d ON s.departman_id = d.id
        GROUP BY uy.kod, uy.ad, d.kod, d.ad
        ORDER BY uy.sira, d.id
    """
    return pd.read_sql_query(query, conn)


# ============================
# MALZEME SORGULARI
# ============================

def load_mal_gruplari(conn):
    """Mal gruplarini sorumlu departman bilgisiyle yukle."""
    query = """
        SELECT mg.id, mg.kod, mg.ad, d.kod as sorumlu_dept_kod, d.ad as sorumlu_dept_ad
        FROM mal_gruplari mg
        LEFT JOIN departmanlar d ON mg.sorumlu_departman_id = d.id
    """
    return pd.read_sql_query(query, conn)


def load_malzemeler(conn, mal_grubu_id=None):
    """Malzemeleri yukle (opsiyonel mal grubu filtresi)."""
    if mal_grubu_id:
        query = """
            SELECT m.*, mg.ad as mal_grubu_ad
            FROM malzemeler m
            JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
            WHERE m.mal_grubu_id = ?
        """
        return pd.read_sql_query(query, conn, params=(mal_grubu_id,))
    else:
        query = """
            SELECT m.*, mg.ad as mal_grubu_ad
            FROM malzemeler m
            JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
        """
        return pd.read_sql_query(query, conn)


def load_malzeme_hareketleri(conn, yer_id=None, dept_id=None):
    """
    Malzeme hareketlerini yukle.
    Opsiyonel filtre: uretim yeri ve/veya departman.
    """
    query = """
        SELECT
            mh.id,
            uy.ad as uretim_yeri,
            d.ad as departman,
            m.malzeme_kodu,
            m.malzeme_adi,
            mg.ad as mal_grubu,
            mg.kod as mal_grubu_kod,
            mh.tarih,
            mh.miktar,
            mh.birim_fiyat,
            mh.toplam_tutar,
            mh.hareket_tipi,
            d_kaynak.ad as kaynak_departman,
            mh.aciklama
        FROM malzeme_hareketleri mh
        JOIN uretim_yerleri uy ON mh.uretim_yeri_id = uy.id
        JOIN departmanlar d ON mh.departman_id = d.id
        JOIN malzemeler m ON mh.malzeme_id = m.id
        JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
        LEFT JOIN departmanlar d_kaynak ON mh.kaynak_departman_id = d_kaynak.id
        WHERE 1=1
    """
    params = []

    if yer_id:
        query += " AND mh.uretim_yeri_id = ?"
        params.append(yer_id)

    if dept_id:
        query += " AND mh.departman_id = ?"
        params.append(dept_id)

    query += " ORDER BY mh.tarih"

    return pd.read_sql_query(query, conn, params=params)


def load_cross_department_purchases(conn, yer_id=None, dept_id=None):
    """
    Departmanlar arasi alimlari tespit et.
    Bir departmanin, baska departmanin sorumlu oldugu mal grubundan alim yapmasi.
    """
    query = """
        SELECT
            uy.ad as uretim_yeri,
            d_alan.ad as alan_departman,
            d_alan.kod as alan_dept_kod,
            d_sorumlu.ad as sorumlu_departman,
            d_sorumlu.kod as sorumlu_dept_kod,
            mg.ad as mal_grubu,
            m.malzeme_kodu,
            m.malzeme_adi,
            mh.tarih,
            mh.miktar,
            mh.birim_fiyat,
            mh.toplam_tutar
        FROM malzeme_hareketleri mh
        JOIN uretim_yerleri uy ON mh.uretim_yeri_id = uy.id
        JOIN departmanlar d_alan ON mh.departman_id = d_alan.id
        JOIN malzemeler m ON mh.malzeme_id = m.id
        JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
        JOIN departmanlar d_sorumlu ON mg.sorumlu_departman_id = d_sorumlu.id
        WHERE mh.departman_id != mg.sorumlu_departman_id
    """
    params = []

    if yer_id:
        query += " AND mh.uretim_yeri_id = ?"
        params.append(yer_id)

    if dept_id:
        query += " AND mh.departman_id = ?"
        params.append(dept_id)

    query += " ORDER BY mh.toplam_tutar DESC"

    return pd.read_sql_query(query, conn, params=params)


def load_budget_with_orders_matrix(conn, yil=2025):
    """
    Butce matrisi + siparis verilerini birlestirerek efektif harcamayi hesapla.
    Forecasting modulu icin kullanilir.

    Dondurur: DataFrame [yer_kod, yer_ad, dept_kod, dept_ad, yer_id, dept_id,
                          Toplam_Planlanan, Toplam_Gerceklesen, Toplam_Siparis, Efektif]
    """
    # Butce matrisi
    budget_query = """
        SELECT
            uy.id as yer_id,
            uy.kod as yer_kod,
            uy.ad as yer_ad,
            d.id as dept_id,
            d.kod as dept_kod,
            d.ad as dept_ad,
            SUM(b.planlanan_butce) as Toplam_Planlanan,
            SUM(b.gerceklesen_butce) as Toplam_Gerceklesen
        FROM butce b
        JOIN uretim_yerleri uy ON b.uretim_yeri_id = uy.id
        JOIN departmanlar d ON b.departman_id = d.id
        WHERE b.yil = ?
        GROUP BY uy.id, uy.kod, uy.ad, d.id, d.kod, d.ad
        ORDER BY uy.sira, d.id
    """
    budget_df = pd.read_sql_query(budget_query, conn, params=(yil,))

    # Siparis toplami
    order_query = """
        SELECT
            s.uretim_yeri_id as yer_id,
            s.departman_id as dept_id,
            SUM(s.tutar) as Toplam_Siparis
        FROM siparisler s
        GROUP BY s.uretim_yeri_id, s.departman_id
    """
    order_df = pd.read_sql_query(order_query, conn)

    # Birlestir
    merged = budget_df.merge(
        order_df, on=["yer_id", "dept_id"], how="left"
    )
    merged["Toplam_Siparis"] = merged["Toplam_Siparis"].fillna(0)
    merged["Efektif"] = merged["Toplam_Gerceklesen"] + merged["Toplam_Siparis"]

    return merged


def load_material_summary_by_group(conn, yer_id=None, dept_id=None):
    """Mal grubuna gore malzeme harcama ozeti."""
    query = """
        SELECT
            mg.ad as Mal_Grubu,
            d_sorumlu.ad as Sorumlu_Departman,
            COUNT(*) as Hareket_Sayisi,
            SUM(mh.miktar) as Toplam_Miktar,
            SUM(mh.toplam_tutar) as Toplam_Tutar,
            SUM(CASE WHEN mh.departman_id != mg.sorumlu_departman_id
                 THEN mh.toplam_tutar ELSE 0 END) as Cross_Dept_Tutar
        FROM malzeme_hareketleri mh
        JOIN malzemeler m ON mh.malzeme_id = m.id
        JOIN mal_gruplari mg ON m.mal_grubu_id = mg.id
        LEFT JOIN departmanlar d_sorumlu ON mg.sorumlu_departman_id = d_sorumlu.id
        WHERE 1=1
    """
    params = []

    if yer_id:
        query += " AND mh.uretim_yeri_id = ?"
        params.append(yer_id)

    if dept_id:
        query += " AND mh.departman_id = ?"
        params.append(dept_id)

    query += " GROUP BY mg.ad, d_sorumlu.ad ORDER BY Toplam_Tutar DESC"

    return pd.read_sql_query(query, conn, params=params)
