"""
Yorglass Finans - AI Yorum Modulu.

OpenAI API ile dinamik finansal yorum uretimi.
Departman ve uretim yeri bazli context destegi.
"""
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv


def _get_api_key():
    """API anahtarini her seferinde taze oku (cache sorununu onler)."""
    load_dotenv(override=True)
    return os.getenv("OPENAI_API_KEY", "")


def get_system_prompt(dept_adi="", yer_adi=""):
    """Dinamik system prompt olustur."""
    context = ""
    if dept_adi and yer_adi:
        context = f"\nAnaliz edilen birim: {yer_adi} - {dept_adi} departmani.\n"
    elif dept_adi:
        context = f"\nAnaliz edilen departman: {dept_adi}.\n"

    return f"""Sen Yorglass cam fabrikasi icin calisan bir finansal analist yapay zekasin.
{context}
Sana verilen butce ve siparis verilerini analiz ederek Turkce profesyonel finansal yorumlar uretiyorsun.

ONEMLI KAVRAM - Efektif Gerceklesen:
Bir ayin gercek butce tuketimi sadece harcamalardan ibaret degildir. O ay acilan siparisler de
butceyi tuketir. Bu yuzden:
  Efektif Gerceklesen = Gerceklesen Harcama + Aylik Siparis Tutari
Analizlerinde bu efektif degeri kullan.

Yorumlarinda sunlari icermelisin:
1. Genel butce performansi degerlendirmesi (efektif bazli)
2. Ham gerceklesen ile efektif gerceklesen arasindaki fark ve bunun anlami
3. Siparis taahhutlerinin butceye etkisi
4. Dikkat ceken sapma noktalari ve aylar
5. Harcama trendleri hakkinda gozlemler
6. Olasi risk alanlari (butce asimi riski olan aylar)
7. Iyilestirme onerileri

Yorumlarini madde madde, net ve anlasilir bir sekilde yaz. Finansal terimler kullan ama
teknik olmayan kisilerin de anlayabilecegi bir dil kullan."""


DEMO_COMMENTARY = """## ⚠️ Demo Finansal Analiz Yorumu

> **Bu bir demo yorumdur.** Gercek AI yorumu icin OpenAI API anahtarinizi `.env` dosyasina ekleyin.

**Genel Degerlendirme:**
- Butce kullanim oranlari ve sapma yuzdeleri grafiklerden incelenebilir.
- Planlanan ve gerceklesen butce arasindaki farklar detay tablosunda goruntulelebilir.

**Oneriler:**
- OpenAI API anahtari ekledikten sonra detayli AI analizi alabilirsiniz.
- API anahtari almak icin: https://platform.openai.com/api-keys
"""


def generate_ai_commentary(analysis_summary, budget_df_text=None, order_df_text=None,
                            dept_adi="", yer_adi=""):
    """Analiz ozetinden AI yorumu uret."""
    api_key = _get_api_key()

    if not api_key:
        return DEMO_COMMENTARY

    system_prompt = get_system_prompt(dept_adi, yer_adi)

    user_message = f"""Asagidaki butce ve siparis analiz verilerini degerlendir ve detayli bir finansal yorum yap:

{analysis_summary}
"""
    if budget_df_text:
        user_message += f"\n\nDetayli Butce Tablosu:\n{budget_df_text}"

    if order_df_text:
        user_message += f"\n\nDetayli Siparis Tablosu:\n{order_df_text}"

    try:
        from config import OPENAI_MODEL
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        content = response.choices[0].message.content

        # Basarili AI yaniti - kaynak ve zaman bilgisi ekle
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        model_used = response.model
        footer = f"\n\n---\n*🤖 Bu yorum **OpenAI {model_used}** tarafindan {timestamp} tarihinde uretilmistir.*"

        return content + footer

    except Exception as e:
        return f"⚠️ **AI yorumu uretilirken hata olustu:**\n\n`{e}`\n\nAPI anahtarinizi kontrol edin."
