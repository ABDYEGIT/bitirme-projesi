import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv


def _get_api_key():
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    load_dotenv(override=True)
    return os.getenv("OPENAI_API_KEY", "")


def get_system_prompt(dept_adi="", yer_adi=""):
    context = ""
    if dept_adi and yer_adi:
        context = f"\nAnaliz edilen birim: {yer_adi} - {dept_adi} departmanı.\n"
    elif dept_adi:
        context = f"\nAnaliz edilen departman: {dept_adi}.\n"

    return f"""Sen Yorglass cam fabrikası için çalışan bir finansal analist yapay zekasın.
{context}
Sana verilen bütçe ve sipariş verilerini analiz ederek Türkçe profesyonel finansal yorumlar üretiyorsun.

ÖNEMLİ KAVRAM - Efektif Gerçekleşen:
Bir ayın gerçek bütçe tüketimi sadece harcamalardan ibaret değildir. O ay açılan siparişler de
bütçeyi tüketir. Bu yüzden:
  Efektif Gerçekleşen = Gerçekleşen Harcama + Aylık Sipariş Tutarı
Analizlerinde bu efektif değeri kullan.

Yorumlarında şunları içermelisin:
1. Genel bütçe performansı değerlendirmesi (efektif bazlı)
2. Ham gerçekleşen ile efektif gerçekleşen arasındaki fark ve bunun anlamı
3. Sipariş taahhütlerinin bütçeye etkisi
4. Dikkat çeken sapma noktaları ve aylar
5. Harcama trendleri hakkında gözlemler
6. Olası risk alanları (bütçe aşımı riski olan aylar)
7. İyileştirme önerileri

Yorumlarını madde madde, net ve anlaşılır bir şekilde yaz. Finansal terimler kullan ama
teknik olmayan kişilerin de anlayabileceği bir dil kullan."""


DEMO_COMMENTARY = """## Demo Finansal Analiz Yorumu

> **Bu bir demo yorumdur.** Gerçek AI yorumu için OpenAI API anahtarınızı `.env` dosyasına ekleyin.

**Genel Değerlendirme:**
- Bütçe kullanım oranları ve sapma yüzdeleri grafiklerden incelenebilir.
- Planlanan ve gerçekleşen bütçe arasındaki farklar detay tablosunda görüntülenebilir.

**Öneriler:**
- OpenAI API anahtarı ekledikten sonra detaylı AI analizi alabilirsiniz.
- API anahtarı almak için: https://platform.openai.com/api-keys
"""


def generate_ai_commentary(analysis_summary, budget_df_text=None, order_df_text=None,
                            dept_adi="", yer_adi=""):
    api_key = _get_api_key()

    if not api_key:
        return DEMO_COMMENTARY

    system_prompt = get_system_prompt(dept_adi, yer_adi)

    user_message = f"""Aşağıdaki bütçe ve sipariş analiz verilerini değerlendir ve detaylı bir finansal yorum yap:

{analysis_summary}
"""
    if budget_df_text:
        user_message += f"\n\nDetaylı Bütçe Tablosu:\n{budget_df_text}"

    if order_df_text:
        user_message += f"\n\nDetaylı Sipariş Tablosu:\n{order_df_text}"

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

        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        model_used = response.model
        footer = f"\n\n---\n*Bu yorum **OpenAI {model_used}** tarafından {timestamp} tarihinde üretilmiştir.*"

        return content + footer

    except Exception as e:
        return f"**AI yorumu üretilirken hata oluştu:**\n\n`{e}`\n\nAPI anahtarınızı kontrol edin."
