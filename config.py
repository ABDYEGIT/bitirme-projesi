import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ============================
# OPENAI AYARLARI
# ============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# ============================
# GENEL AYARLAR
# ============================
CURRENCY = "TL"
LOCALE = "tr_TR"
SIRKET_ADI = "Yorglass"

# Veritabani varsayilan yolu
DB_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "finans.db")

# ============================
# ORGANIZASYON YAPISI
# ============================

URETIM_YERLERI = {
    "merkez": "Merkez (Genel Müdürlük)",
    "cerkezkoy": "Çerkezköy İşletmesi",
    "eskisehir": "Eskişehir İşletmesi",
    "manisa": "Manisa İşletmesi",
    "bolu": "Bolu İşletmesi",
}

DEPARTMANLAR = {
    "it": "IT",
    "ik": "İnsan Kaynakları",
    "uretim": "Üretim",
    "kalite": "Kalite",
    "bakim": "Bakım",
    "lojistik": "Lojistik",
}

# Hangi isletmede hangi departmanlar var
ORGANIZASYON = {
    "merkez": ["it", "ik"],
    "cerkezkoy": ["uretim", "kalite", "bakim", "lojistik"],
    "eskisehir": ["uretim", "kalite", "bakim", "lojistik"],
    "manisa": ["uretim", "kalite", "bakim", "lojistik"],
    "bolu": ["uretim", "kalite", "bakim", "lojistik"],
}

# Merkez departmanlari (malzeme verisi YOK)
MERKEZ_DEPT_KODLARI = ["it", "ik"]

# Fabrika departmanlari (malzeme verisi VAR)
FABRIKA_DEPT_KODLARI = ["uretim", "kalite", "bakim", "lojistik"]

# Aylik baz butce buyuklukleri (TL)
BUTCE_BAZLARI = {
    "it": 1_000_000,
    "ik": 500_000,
    "uretim": 2_000_000,
    "kalite": 400_000,
    "bakim": 800_000,
    "lojistik": 600_000,
}

# ============================
# FIRE ORANI AYARLARI
# ============================

# Departman bazli fire etki agirliklari
# Fire orani degisimi her departmani farkli oranda etkiler
FIRE_ETKI_AGIRLIKLARI = {
    "uretim": 1.0,    # Dogrudan uretim hurda/iskartasi
    "bakim": 0.30,     # Yuksek fire → makine yipranmasi artar
    "kalite": 0.20,    # Yuksek fire → daha fazla test/kontrol
    "lojistik": 0.15,  # Yuksek fire → daha fazla malzeme tasima
    "it": 0.0,         # Etkilenmez
    "ik": 0.0,         # Etkilenmez
}

# 2025 yili icin varsayilan fire orani (%10)
VARSAYILAN_FIRE_ORANI = 0.10
