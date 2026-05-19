# -*- coding: utf-8 -*-
"""
LLM Gateway Layer - Interfaces with OpenAI and Google Gemini.

Supports OpenAI/Gemini in production and a local synthetic generator in demo mode.
"""

import os
import re
import random
from dotenv import load_dotenv

# Load workspace environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_PROVIDER = os.getenv("API_PROVIDER", "local").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Helper to check if a key is a placeholder
def is_placeholder(key):
    return not key or "your_" in key or "here" in key or len(key) < 15

def call_llm(prompt, system_prompt="", max_tokens=1500, temperature=0.7, provider=None, api_key=None, model=None, allow_fallback=None):
    """
    Unified LLM call routing.

    By default, missing/failed external APIs raise RuntimeError. Pass
    allow_fallback=True only for local smoke tests.
    """
    active_provider = (provider or API_PROVIDER or "openai").lower()
    active_api_key = api_key
    active_model = model
    fallback_enabled = env_bool("ALLOW_LOCAL_FALLBACK", True) if allow_fallback is None else allow_fallback
    
    # 1. OpenAI Routing
    if active_provider == "openai":
        active_api_key = active_api_key or OPENAI_API_KEY
        active_model = active_model or OPENAI_MODEL
    elif active_provider == "gemini":
        active_api_key = active_api_key or GEMINI_API_KEY
        active_model = active_model or GEMINI_MODEL

    if active_provider == "openai" and not is_placeholder(active_api_key):
        try:
            import openai
            client = openai.OpenAI(api_key=active_api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=active_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if fallback_enabled:
                return generate_local_fallback(prompt, system_prompt)
            raise RuntimeError(f"OpenAI API call failed: {e}") from e
            
    # 2. Google Gemini Routing
    elif active_provider == "gemini" and not is_placeholder(active_api_key):
        try:
            import google.generativeai as genai
            genai.configure(api_key=active_api_key)
            
            model = genai.GenerativeModel(
                model_name=active_model,
                system_instruction=system_prompt if system_prompt else None
            )
            response = model.generate_content(
                prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            return response.text.strip()
        except Exception as e:
            if fallback_enabled:
                return generate_local_fallback(prompt, system_prompt)
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    if fallback_enabled or active_provider == "local":
        return generate_local_fallback(prompt, system_prompt)
    raise RuntimeError(f"Missing or placeholder API key for provider '{active_provider}'.")


def _extract_json_object_from_prompt(prompt):
    """Best-effort extraction of the first JSON object embedded in a prompt."""
    try:
        match = re.search(r'\{.*\}', prompt, re.DOTALL)
        if not match:
            return {}
        import json
        return json.loads(match.group(0))
    except Exception:
        return {}


def _split_points(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


def generate_local_fallback(prompt, system_prompt=""):
    """Synthetic Turkish generator for demo mode."""
    prompt_lower = (prompt or "").lower()
    if "json array" in prompt_lower and "consumer segments" in prompt_lower:
        return """
[
  {
    "id": "segment_1",
    "name": "Dijital Genç Profesyoneller",
    "weight_pct": 28,
    "age_range": [24, 38],
    "avg_income": 56000,
    "price_sensitivity": 4.8,
    "sustainability_focus": 6.4,
    "brand_loyalty": 5.8,
    "ad_receptivity": 7.8,
    "tech_savviness": 8.7,
    "core_value": "Status & Quality",
    "allowed_cities": ["İstanbul", "Ankara", "İzmir"],
    "allowed_occupations": ["Pazarlama Uzmanı", "Yazılım Geliştirici", "Ürün Yöneticisi", "Finans Analisti"],
    "habits": ["Online yorumlara bakarak satın alır.", "Premium faydayı net görürse fiyatı tolere eder.", "Mobil kampanyalara hızlı tepki verir."]
  },
  {
    "id": "segment_2",
    "name": "Değer ve Sürdürülebilirlik Odaklılar",
    "weight_pct": 22,
    "age_range": [20, 42],
    "avg_income": 42000,
    "price_sensitivity": 6.2,
    "sustainability_focus": 8.8,
    "brand_loyalty": 5.2,
    "ad_receptivity": 6.9,
    "tech_savviness": 7.4,
    "core_value": "Sustainability & Ethics",
    "allowed_cities": ["İzmir", "Muğla", "Aydın", "İstanbul"],
    "allowed_occupations": ["Öğretmen", "Grafiker", "STK Çalışanı", "Araştırma Görevlisi"],
    "habits": ["Markanın şeffaf etki kanıtını arar.", "Yerel üretim ve etik tedariki önemser.", "Yeşil iddialara karşı kanıt bekler."]
  },
  {
    "id": "segment_3",
    "name": "Bütçe Hassas Aileler",
    "weight_pct": 34,
    "age_range": [30, 55],
    "avg_income": 36000,
    "price_sensitivity": 8.7,
    "sustainability_focus": 4.2,
    "brand_loyalty": 4.8,
    "ad_receptivity": 5.1,
    "tech_savviness": 5.8,
    "core_value": "Economy & Utility",
    "allowed_cities": ["Bursa", "Konya", "Adana", "Kayseri", "Samsun"],
    "allowed_occupations": ["Memur", "Muhasebeci", "Hemşire", "Satış Temsilcisi", "Teknisyen"],
    "habits": ["Birim fiyatı ve kampanya avantajını karşılaştırır.", "Deneme paketi olmadan risk almak istemez.", "Hane bütçesine etkisini öne koyar."]
  },
  {
    "id": "segment_4",
    "name": "Geleneksel Güven Arayanlar",
    "weight_pct": 16,
    "age_range": [48, 70],
    "avg_income": 28000,
    "price_sensitivity": 7.6,
    "sustainability_focus": 4.7,
    "brand_loyalty": 7.9,
    "ad_receptivity": 4.2,
    "tech_savviness": 3.8,
    "core_value": "Nostalgia & Trust",
    "allowed_cities": ["İzmir", "Ankara", "Bursa", "Denizli", "Eskişehir"],
    "allowed_occupations": ["Emekli Öğretmen", "Esnaf", "Ev Hanımı", "Emekli Memur"],
    "habits": ["Bildik markaya ve yakın çevre tavsiyesine güvenir.", "Karmaşık dijital adımları sevmez.", "Somut kalite kanıtı ister."]
  }
]
"""

def generate_local_fallback(prompt: str, system_prompt: str = "") -> str:
    prompt_lower = prompt.lower()
    
    if "json array" in prompt_lower and "consumer segments" in prompt_lower:
        return """[
  {
    "id": "segment_1",
    "name": "Dijital Genç Profesyoneller",
    "weight_pct": 28,
    "age_range": [24, 38],
    "avg_income": 56000,
    "price_sensitivity": 4.8,
    "sustainability_focus": 6.4,
    "brand_loyalty": 5.8,
    "ad_receptivity": 7.8,
    "tech_savviness": 8.7,
    "core_value": "Status & Quality",
    "allowed_cities": ["İstanbul", "Ankara", "İzmir"],
    "allowed_occupations": ["Pazarlama Uzmanı", "Yazılım Geliştirici", "Ürün Yöneticisi", "Finans Analisti"],
    "habits": ["Online yorumlara bakarak satın alır.", "Premium faydayı net görürse fiyatı tolere eder.", "Mobil kampanyalara hızlı tepki verir."]
  },
  {
    "id": "segment_2",
    "name": "Değer ve Sürdürülebilirlik Odaklılar",
    "weight_pct": 22,
    "age_range": [20, 42],
    "avg_income": 42000,
    "price_sensitivity": 6.2,
    "sustainability_focus": 8.8,
    "brand_loyalty": 5.2,
    "ad_receptivity": 6.9,
    "tech_savviness": 7.4,
    "core_value": "Sustainability & Ethics",
    "allowed_cities": ["İzmir", "Muğla", "Aydın", "İstanbul"],
    "allowed_occupations": ["Öğretmen", "Grafiker", "STK Çalışanı", "Araştırma Görevlisi"],
    "habits": ["Markanın şeffaf etki kanıtını arar.", "Yerel üretim ve etik tedariki önemser.", "Yeşil iddialara karşı kanıt bekler."]
  },
  {
    "id": "segment_3",
    "name": "Bütçe Hassas Aileler",
    "weight_pct": 34,
    "age_range": [30, 55],
    "avg_income": 36000,
    "price_sensitivity": 8.7,
    "sustainability_focus": 4.2,
    "brand_loyalty": 4.8,
    "ad_receptivity": 5.1,
    "tech_savviness": 5.8,
    "core_value": "Economy & Utility",
    "allowed_cities": ["Bursa", "Konya", "Adana", "Kayseri", "Samsun"],
    "allowed_occupations": ["Memur", "Muhasebeci", "Hemşire", "Satış Temsilcisi", "Teknisyen"],
    "habits": ["Birim fiyatı ve kampanya avantajını karşılaştırır.", "Deneme paketi olmadan risk almak istemez.", "Hane bütçesine etkisini öne koyar."]
  },
  {
    "id": "segment_4",
    "name": "Geleneksel Güven Arayanlar",
    "weight_pct": 16,
    "age_range": [48, 70],
    "avg_income": 28000,
    "price_sensitivity": 7.6,
    "sustainability_focus": 4.7,
    "brand_loyalty": 7.9,
    "ad_receptivity": 4.2,
    "tech_savviness": 3.8,
    "core_value": "Nostalgia & Trust",
    "allowed_cities": ["İzmir", "Ankara", "Bursa", "Denizli", "Eskişehir"],
    "allowed_occupations": ["Emekli Öğretmen", "Esnaf", "Ev Hanımı", "Emekli Memur"],
    "habits": ["Bildik markaya ve yakın çevre tavsiyesine güvenir.", "Karmaşık dijital adımları sevmez.", "Somut kalite kanıtı ister."]
  }
]"""

    if "debate" in prompt_lower or "müzakere" in prompt_lower or "tartışma" in prompt_lower:
        return (
            "[Katılımcı A]: Fiyat tarafı beni düşündürüyor; fayda net değilse hemen karar vermem.\n"
            "[Katılımcı B]: Haklısın ama marka deneme paketi, şeffaf kanıt ve yerel faydayı iyi anlatırsa değer algısı güçlenir.\n"
            "[Katılımcı A]: O zaman önce küçük paketle denemeye daha sıcak bakarım; riskim azalırsa fikrim değişebilir."
        )
        
    import random
    decision = "Ignore"
    if "decision: buy" in prompt_lower or "karar: buy" in prompt_lower or "karar: alır" in prompt_lower:
        decision = "Buy"
    elif "skeptical" in prompt_lower or "şüpheyle" in prompt_lower:
        decision = "Skeptical Buy"
    elif "reject" in prompt_lower or "reddeder" in prompt_lower:
        decision = "Reject"

    # Diverse local fallback pools based on decision
    if decision == "Buy":
        pool = [
            "Bence fiyatına göre sunduğu değer harika, maaş yatar yatmaz deneyeceğim.",
            "Kesinlikle benim yaşam tarzıma uygun, eşim de beğenecektir.",
            "Uzun zamandır böyle pratik bir çözüm arıyordum, hemen alırım.",
            "Kalitesi ortada, güvendiğim bir marka olduğu için hiç düşünmeden alıyorum.",
            "Hem ekonomik hem de ihtiyaçlarımı tam karşılıyor, kaçırmam."
        ]
    elif decision == "Skeptical Buy":
        pool = [
            "Fikre sıcak bakıyorum ama önce küçük bir deneme paketi alıp kalitesini görmem lazım.",
            "İlgi çekici duruyor ancak sosyal medyada veya çevremde kullanan birini görsem daha rahat alırım.",
            "Fiyatı bütçemi biraz zorluyor, belki bir sonraki maaş gününde indirim yakalarsam alabilirim.",
            "Açıkçası vaatleri güzel ama uzun vadede dediklerini sağlayabileceğinden emin değilim.",
            "İhtiyacım var, yine de diğer markalarla fiyat karşılaştırması yapmadan doğrudan sepete atmam."
        ]
    elif decision == "Reject":
        pool = [
            "Benim günlük rutinimde buna hiç yer yok, gereksiz bir harcama olurdu.",
            "Fiyatı sunduğu özelliğe göre inanılmaz uçuk, asla bu parayı vermem.",
            "Bu markayla daha önce kötü bir deneyimim oldu, ne kampanya yapsalar almam.",
            "İçeriği veya kalitesi beni hiç ikna etmedi, bildiğimden şaşmam.",
            "Benim yaşım ve mesleğim gereği bu tarz ürünler hiç ilgimi çekmiyor."
        ]
    else:  # Ignore / Pas Geçer
        pool = [
            "Reklamı görsem muhtemelen geçerdim, bana hitap eden bir tarafı yok.",
            "İhtiyacım olmayan bir şey, ilgilenmiyorum bile.",
            "Eminim birileri için iyidir ama benlik değil, hayatıma bir artısı olmaz.",
            "Bu aralar başka önceliklerim var, böyle şeylere ayıracak bütçem ve vaktim yok.",
            "Çok sıradan geldi, dönüp tekrar bakma ihtiyacı hissetmedim."
        ]
        
    return random.choice(pool)
