from openai import OpenAI
from ai_commentary import _get_api_key
from config import OPENAI_MODEL


def get_chatbot_system_prompt(data_context: str) -> str:
    return f"""Sen Yorglass cam fabrikası için çalışan bir finansal asistan yapay zekasın.
Aşağıda sana verilen bütçe, sipariş ve malzeme verilerini kullanarak kullanıcının sorularını
Türkçe olarak yanıtlıyorsun.

KURALLAR:
1. SADECE aşağıda verilen verilerle ilgili sorulara cevap ver.
2. Verilerden çıkarım yapabilirsin: karşılaştırma, trend analizi, özet, en yüksek/en düşük gibi.
3. Sektör benchmark verileri varsa, Yorglass'ın sektördeki konumunu, rakip firmalarla
   karşılaştırmasını ve güçlü/zayıf yönlerini analiz edebilirsin.
4. Eğer soru aşağıdaki verilerle ALAKASIZ ise (genel bilgi, kişisel sorular, teknik destek,
   siyaset, spor, vb.) şu şekilde cevap ver:
   "Bu soruya cevap veremiyorum. Ben sadece Yorglass bütçe, sipariş, malzeme ve sektör karşılaştırma verileri hakkında yardımcı olabilirim."
5. Yanıtlarını kısa, net ve profesyonel tut.
6. Sayısal verilerde TL formatını kullan (örneğin: 1,500,000.00 TL).
7. Tabloları markdown formatında göster.
8. Kullanıcıya her zaman kibar ve yardımcı ol.

=== MEVCUT VERİLER ===

{data_context}

=== VERİLER SONU ===

Yukarıdaki verileri kullanarak kullanıcının sorularını yanıtla."""


def prepare_data_context(budget_text: str, order_text: str, material_text: str,
                         cross_dept_text: str = "", benchmark_text: str = "") -> str:
    parts = []

    if budget_text:
        parts.append("--- BÜTÇE VERİLERİ (2025) ---")
        parts.append("Lokasyon ve departman bazlı yıllık planlanan ve gerçekleşen bütçeler:")
        parts.append(budget_text)

    if order_text:
        parts.append("\n--- SİPARİŞ VERİLERİ ---")
        parts.append("Lokasyon ve departman bazlı sipariş özeti:")
        parts.append(order_text)

    if material_text:
        parts.append("\n--- MALZEME VERİLERİ ---")
        parts.append("Mal grubuna göre malzeme harcama özeti:")
        parts.append(material_text)

    if cross_dept_text:
        parts.append("\n--- ÇAPRAZ DEPARTMAN ALIMLARI ---")
        parts.append(
            "Aşağıdaki tablo, bir departmanın başka departmanın sorumlu olduğu mal grubundan "
            "yapılan alımları gösterir. 'alan_departman' alımı yapan, 'sorumlu_departman' ise "
            "o mal grubunun aslında sorumlusu olan departmandır. Bu alımlar bütçe sapmalarının "
            "gerçek nedenini gizleyebilir."
        )
        parts.append(cross_dept_text)

    if benchmark_text:
        parts.append("\n" + benchmark_text)

    return "\n".join(parts) if parts else "Veri bulunamadı."


def ask_chatbot(question: str, data_context: str, chat_history: list) -> str:
    api_key = _get_api_key()

    if not api_key:
        return "⚠️ OpenAI API anahtarı bulunamadı. Chatbot için `.env` dosyasına `OPENAI_API_KEY=sk-...` eklemeniz gerekiyor."

    system_prompt = get_chatbot_system_prompt(data_context)

    messages = [{"role": "system", "content": system_prompt}]

    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    for msg in recent_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

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
        return f"⚠️ **Yanıt üretilirken hata oluştu:**\n\n`{e}`\n\nAPI anahtarınızı kontrol edin."
