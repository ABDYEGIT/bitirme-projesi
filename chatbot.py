"""
Yorglass Finans - Chatbot Asistan Modulu.

OpenAI API ile butce, siparis ve malzeme verilerine dayali
Turkce finansal soru-cevap asistani.
"""
from openai import OpenAI
from ai_commentary import _get_api_key
from config import OPENAI_MODEL


def get_chatbot_system_prompt(data_context: str) -> str:
    """Veri context'i ile system prompt olustur."""
    return f"""Sen Yorglass cam fabrikasi icin calisan bir finansal asistan yapay zekasin.
Asagida sana verilen butce, siparis ve malzeme verilerini kullanarak kullanicinin sorularini
Turkce olarak yanitliyorsun.

KURALLAR:
1. SADECE asagida verilen verilerle ilgili sorulara cevap ver.
2. Verilerden cikarim yapabilirsin: karsilastirma, trend analizi, ozet, en yuksek/en dusuk gibi.
3. Sektor benchmark verileri varsa, Yorglass'in sektordeki konumunu, rakip firmalarla
   karsilastirmasini ve guclu/zayif yonlerini analiz edebilirsin.
4. Eger soru asagidaki verilerle ALAKASIZ ise (genel bilgi, kisisel sorular, teknik destek,
   siyaset, spor, vb.) su sekilde cevap ver:
   "Bu soruya cevap veremiyorum. Ben sadece Yorglass butce, siparis, malzeme ve sektor karsilastirma verileri hakkinda yardimci olabilirim."
5. Yanitlarini kisa, net ve profesyonel tut.
6. Sayisal verilerde TL formatini kullan (ornegin: 1,500,000.00 TL).
7. Tablolari markdown formatinda goster.
8. Kullaniciya her zaman kibar ve yardimci ol.

=== MEVCUT VERILER ===

{data_context}

=== VERILER SONU ===

Yukaridaki verileri kullanarak kullanicinin sorularini yanitla."""


def prepare_data_context(budget_text: str, order_text: str, material_text: str,
                         cross_dept_text: str = "", benchmark_text: str = "") -> str:
    """Veri metinlerini tek bir context string'e birlestir."""
    parts = []

    if budget_text:
        parts.append("--- BUTCE VERILERI (2025) ---")
        parts.append("Lokasyon ve departman bazli yillik planlanan ve gerceklesen butceler:")
        parts.append(budget_text)

    if order_text:
        parts.append("\n--- SIPARIS VERILERI ---")
        parts.append("Lokasyon ve departman bazli siparis ozeti:")
        parts.append(order_text)

    if material_text:
        parts.append("\n--- MALZEME VERILERI ---")
        parts.append("Mal grubuna gore malzeme harcama ozeti:")
        parts.append(material_text)

    if cross_dept_text:
        parts.append("\n--- CAPRAZ DEPARTMAN ALIMLARI ---")
        parts.append(
            "Asagidaki tablo, bir departmanin baska departmanin sorumlu oldugu mal grubundan "
            "yapilan alimlari gosterir. 'alan_departman' alimi yapan, 'sorumlu_departman' ise "
            "o mal grubunun aslinda sorumlusu olan departmandir. Bu alimlar butce sapmalarinin "
            "gercek nedenini gizleyebilir."
        )
        parts.append(cross_dept_text)

    if benchmark_text:
        parts.append("\n" + benchmark_text)

    return "\n".join(parts) if parts else "Veri bulunamadi."


def ask_chatbot(question: str, data_context: str, chat_history: list) -> str:
    """
    Kullanici sorusunu OpenAI'a gonder ve yanit al.

    Parametreler:
      - question: Kullanicinin sordugu soru
      - data_context: Veritabanindan hazirlanan veri metni
      - chat_history: Onceki mesajlar [{"role": "user"|"assistant", "content": "..."}]

    Dondurulen:
      - str: Asistanin yaniti
    """
    api_key = _get_api_key()

    if not api_key:
        return "⚠️ OpenAI API anahtari bulunamadi. Chatbot icin `.env` dosyasina `OPENAI_API_KEY=sk-...` eklemeniz gerekiyor."

    system_prompt = get_chatbot_system_prompt(data_context)

    # Mesaj listesi olustur
    messages = [{"role": "system", "content": system_prompt}]

    # Chat gecmisini ekle (son 10 mesaj — token limiti icin)
    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    for msg in recent_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Kullanicinin yeni sorusunu ekle
    messages.append({"role": "user", "content": question})

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ **Yanit uretilirken hata olustu:**\n\n`{e}`\n\nAPI anahtarinizi kontrol edin."
