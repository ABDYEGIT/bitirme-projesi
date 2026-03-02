import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

CURRENCY = "TL"
LOCALE = "tr_TR"
SIRKET_ADI = "Yorglass"

DB_PATH = os.path.join(os.path.dirname(__file__), "sample_data", "finans.db")

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

ORGANIZASYON = {
    "merkez": ["it", "ik"],
    "cerkezkoy": ["uretim", "kalite", "bakim", "lojistik"],
    "eskisehir": ["uretim", "kalite", "bakim", "lojistik"],
    "manisa": ["uretim", "kalite", "bakim", "lojistik"],
    "bolu": ["uretim", "kalite", "bakim", "lojistik"],
}

MERKEZ_DEPT_KODLARI = ["it", "ik"]

FABRIKA_DEPT_KODLARI = ["uretim", "kalite", "bakim", "lojistik"]

BUTCE_BAZLARI = {
    "it": 1_000_000,
    "ik": 500_000,
    "uretim": 2_000_000,
    "kalite": 400_000,
    "bakim": 800_000,
    "lojistik": 600_000,
}

FIRE_ETKI_AGIRLIKLARI = {
    "uretim": 1.0,
    "bakim": 0.30,
    "kalite": 0.20,
    "lojistik": 0.15,
    "it": 0.0,
    "ik": 0.0,
}

VARSAYILAN_FIRE_ORANI = 0.10
