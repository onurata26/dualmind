import sys
import os
import json
import requests
from datetime import datetime

# Prompt definition for the factual brand context schema (origin, distributor, and related news)
PROMPT_TEMPLATE = """
You are an expert corporate intelligence analyst.
Analyze the following raw data collected about the brand '{brand}' (Category: '{category}', Region: '{region}').
Your task is to extract real, factual corporate context about this brand from the provided sources and output a SINGLE JSON object.

We do NOT want any subjective sentiment or consumer trust metrics (do NOT output trust_level, purchase_intent, valence, skepticism, strength, or consumer segments).
We only want the brand's origin, distributor, and a structured list of news/publications that relate to these facts.

RAW DATA COLLECTED:
{raw_data_json}

The current date is {current_date}.

You must format the output exactly as the following JSON structure:
{{
  "brand": "{brand}",
  "category": "{category}",
  "region": "{region}",
  "date_range": {{
    "from": "{date_from}",
    "to": "{date_to}"
  }},
  "origin": {{
    "country": "<Factual country of origin of the parent company, e.g. 'Amerika Birleşik Devletleri (ABD)'>",
    "details": "<Factual details about the company's origin, founding year, or main headquarters extracted from the sources.>"
  }},
  "distributor": {{
    "name": "<Name of the distributor, operator, master franchisee, or local partner in Turkey, e.g. 'Alshaya Group'>",
    "country": "<Country of origin of the distributor, e.g. 'Kuveyt'>",
    "details": "<Factual details about how the local distribution/franchise structure works in Turkey.>"
  }},
  "news_and_publications": [
    {{
      "source": "<e.g., 'pwc', 'deloitte', 'newsapi', 'eksisozluk'>",
      "source_type": "<e.g., 'report', 'news', 'forum'>",
      "title": "<Title of the article, post, or publication>",
      "url": "<URL of the resource>",
      "date": "<Estimated date of publication, if available, or current year>",
      "relevance_summary": "<Turkish description explaining why this item is relevant to the brand's origin, distributor, or local operations. Keep it strictly factual.>"
    }}
  ],
  "raw_items_count": {raw_items_count},
  "confidence_score": <Integer score 0-100 indicating confidence in the extracted corporate details>
}}

RULES FOR ANALYSIS:
1. Output ONLY a valid JSON block. Do not include markdown code fence wrappers (like ```json) in the response.
2. Focus strictly on corporate facts (brand origin, local distributor, distribution structure, and factual news/articles).
3. Do NOT invent or output consumer sentiment metrics, trust levels, or segments.
4. Keep the Turkish language grammatically correct, professional, and precise.
"""

def generate_mock_report(brand, category, region, raw_items_count):
    """
    Fallback heuristic mock report generator if no API keys are provided.
    Extracts corporate facts (origin, distributor, news) for Starbucks.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    facts = {
        "starbucks": {
            "origin": {
                "country": "Amerika Birleşik Devletleri (ABD)",
                "details": "Seattle, Washington merkezli, 1971 yılında kurulmuş küresel kahve evi zinciridir."
            },
            "distributor": {
                "name": "Alshaya Group",
                "country": "Kuveyt",
                "details": "Türkiye operasyonları, Kuveyt merkezli Shaya Kahve Sanayi ve Ticaret A.Ş. (Alshaya Group) lisans ortaklığı ve işletmesi altındadır."
            },
            "news_and_publications": [
                {
                    "source": "newsapi",
                    "source_type": "news",
                    "title": "Alshaya Group Türkiye Mağaza Zinciri ve Genişleme Planları",
                    "url": "https://webrazzi.com/tr/",
                    "date": "2026-03-15",
                    "relevance_summary": "Starbucks Türkiye distribütörü Alshaya Group'un perakende operasyonları ve yerel pazardaki şubeleşme yapısını ele alan sektörel haber."
                },
                {
                    "source": "pwc",
                    "source_type": "report",
                    "title": "Tüketici Eğilimleri ve Perakende Sektörü Raporu",
                    "url": "https://www.pwc.com.tr/tr/yayinlar.html",
                    "date": "2026-01-20",
                    "relevance_summary": "Türkiye'deki perakende gıda zincirlerinin operasyonel yapıları ve yerel lisans ortaklarının pazar büyüklüğü analizlerini içeren resmi rapor."
                },
                {
                    "source": "eksisozluk",
                    "source_type": "forum",
                    "title": "starbucks türkiye menşei ve ortaklık yapısı",
                    "url": "https://eksisozluk.com",
                    "date": "2026-05-18",
                    "relevance_summary": "Tüketicilerin markanın Amerikan menşeili olması ve Kuveyt merkezli Alshaya Group lisansıyla yönetilmesi hakkındaki kurumsal kimlik bilgilendirmeleri."
                }
            ]
        }
    }
    
    brand_key = brand.lower().strip()
    brand_facts = facts.get(brand_key, {
        "origin": {
            "country": "Bilinmiyor",
            "details": "Ham veri kaynaklarında menşe bilgisi doğrudan tespit edilememiştir."
        },
        "distributor": {
            "name": "Bilinmiyor",
            "country": "Bilinmiyor",
            "details": "Ham veri kaynaklarında yerel ortak veya distribütör yapısı tespit edilememiştir."
        },
        "news_and_publications": [
            {
                "source": "newsapi",
                "source_type": "news",
                "title": f"{brand} Hakkında Çıkan Sektörel Haberler",
                "url": "https://newsapi.org",
                "date": current_date,
                "relevance_summary": f"Markanın Türkiye'deki kurumsal varlığına ilişkin güncel haber taraması."
            }
        ]
    })
    
    return {
        "brand": brand,
        "category": category,
        "region": region,
        "date_range": {
            "from": "2026-04-01",
            "to": current_date
        },
        "origin": brand_facts["origin"],
        "distributor": brand_facts["distributor"],
        "news_and_publications": brand_facts["news_and_publications"],
        "raw_items_count": raw_items_count,
        "confidence_score": 75,
        "note": "API KEY BULUNAMADI: Bu rapor yapay zeka entegrasyonu olmadan kurumsal gerçekler şablonu üzerinden üretilmiştir. Gerçek LLM analizi için lütfen GEMINI_API_KEY tanımlayın."
    }

def synthesize_report(brand, category, region, raw_items):
    """
    Main entrypoint to synthesize raw items using available LLM API keys.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    date_from = "2026-04-01"
    
    raw_data_str = json.dumps(raw_items, ensure_ascii=False, indent=2)
    
    prompt = PROMPT_TEMPLATE.format(
        brand=brand,
        category=category,
        region=region,
        raw_data_json=raw_data_str,
        current_date=current_date,
        date_from=date_from,
        date_to=current_date,
        raw_items_count=len(raw_items)
    )
    
    # Try Gemini first
    if gemini_key:
        print(file=sys.stderr, "Using Gemini API for synthesis...")
        report = synthesize_with_gemini(prompt, gemini_key)
        if report:
            return report
            
    # Try OpenAI second
    if openai_key:
        print(file=sys.stderr, "Using OpenAI API for synthesis...")
        report = synthesize_with_openai(prompt, openai_key)
        if report:
            return report
            
    # Fallback to mock
    print(file=sys.stderr, "Warning: No LLM API key configured or request failed. Generating a heuristic report.")
    return generate_mock_report(brand, category, region, len(raw_items))

def synthesize_with_gemini(prompt, api_key):
    """
    Calls the Gemini API (gemini-2.5-flash) to synthesize the raw items.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text_response.strip())
        else:
            print(file=sys.stderr, f"Gemini API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(file=sys.stderr, f"Exception during Gemini synthesis: {str(e)}")
        return None

def synthesize_with_openai(prompt, api_key):
    """
    Calls the OpenAI Chat Completion API (gpt-4o-mini) to synthesize the raw items.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a precise data analysis system returning strict JSON format."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            text_response = result['choices'][0]['message']['content']
            return json.loads(text_response.strip())
        else:
            print(file=sys.stderr, f"OpenAI API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(file=sys.stderr, f"Exception during OpenAI synthesis: {str(e)}")
        return None
