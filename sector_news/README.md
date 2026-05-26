# Brand Context & Sentiment MCP Server (Şirket Analiz ve Raporlama Sistemi)

Bu proje, bir yapay zekanın (LLM) veya ana sisteminizin istekleri doğrultusunda aranan herhangi bir marka/şirket hakkında güncel haberleri ve sektörel raporları otomatik olarak toplayan ve LLM tüketimine uygun **tüketici-duygu (consumer-valence) şeması** formatında yapılandırılmış JSON raporu üreten bir **Model Context Protocol (MCP)** sunucusudur.

Sistem, hedef şirket hakkında çok boyutlu bir perspektif kazanmak için hem resmi verileri (APIs/Raporlar) hem de tüketici algısını (Forumlar/Şikayetler) tarar ve analiz eder.

---

## 🚀 Temel Özellikler

1. **Çok Kanallı Veri Toplama (Scraping & APIs):**
   - **PwC Türkiye Yayınları (`pwc.com.tr`):** Sektörel öngörüler, yönetici araştırmaları ve trend analizleri.
   - **Deloitte Türkiye Raporları (`deloitte.com/tr`):** Sektörel pazar analizleri.
   - **NewsAPI (`newsapi.org`) & Haber Tarayıcı:** Global ve yerel güncel haberler (Webrazzi, Bloomberg HT vb. entegrasyonuyla).
   - **Şikayetvar (`sikayetvar.com`):** Markanın müşteri memnuniyeti sorunları ve kronik şikayetleri.
   - **Ekşi Sözlük (`eksisozluk.com`):** Tüketici algısı, söylemler ve forum tartışmaları.
   - **Reddit (`reddit.com`):** Topluluk temelli marka ve boykot tartışmaları.

2. **Gelişmiş LLM Sentezi (Synthesis):**
   - Toplanan ham veriyi analiz eder.
   - Belirlenen **tüketici segmentleri, marka boykot/destek sinyalleri, satın alma eğilimleri, güven endeksi** gibi karmaşık metrikleri hesaplar.
   - `GEMINI_API_KEY` (Gemini 2.5 Flash) veya `OPENAI_API_KEY` (GPT-4o-mini) kullanarak doğrudan REST API'ler üzerinden sıfır bağımlılıkla çalışır.

3. **Model Context Protocol (MCP) Uyumlu:**
   - LLM istemcileri (Claude Desktop, Cursor vb.) ve otomasyon araçları (n8n vb.) ile doğrudan entegre edilebilir.
   - JSON-RPC 2.0 stdio protokolünü sıfır-dış bağımlılıkla Python 3.9+ üzerinde çalıştırır.

---

## 🛠️ Sistem Mimarisi ve Kod Yapısı

Proje modüler ve sürdürülebilir bir yapıda tasarlanmıştır:

- 🔍 **`search_engine.py`**: Arama motorlarını (DuckDuckGo HTML) kullanarak web sitelerini dinamik JavaScript'e takılmadan, hızlı ve hafif bir şekilde sorgulayan tarayıcı modülü.
- 📰 **`news_client.py`**: `NewsAPI` entegrasyonu ve API anahtarı olmadığında popüler haber kaynaklarını otomatik tarayan haber istemcisi.
- 🧠 **`llm_synthesizer.py`**: Toplanan ham veriyi LLM'e besleyip, kullanıcının talep ettiği **tüketici-duygu JSON şemasına** dönüştüren modül.
- ⚙️ **`gather_brand_data.py`**: Tüm veri toplama ve LLM sentezleme süreçlerini uçtan uca koordine eden ana boru hattı (pipeline).
- 🔌 **`mcp_server.py`**: LLM'lerin bu arama ve sentezleme araçlarını doğrudan kullanabilmesini sağlayan MCP stdio sunucusu.
- 🧪 **`test_mcp.py`**: MCP protokolünün uyumluluğunu test eden simülasyon aracı.

---

## 📋 Gereksinimler ve Kurulum

Sistem sadece standart kütüphaneleri ve HTTP istekleri için yaygın olarak kullanılan iki paketi (`requests`, `beautifulsoup4`) gerektirir.

### 1. Bağımlılıkların Kurulumu
```bash
pip3 install requests beautifulsoup4
```

### 2. Çevre Değişkenlerinin Tanımlanması (Opsiyonel ama Önerilen)
LLM analizi ve haber toplama kalitesini en üst düzeye çıkarmak için çevre değişkenlerinizi tanımlayın:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
# VE/VEYA
export OPENAI_API_KEY="your-openai-api-key"

# Gerçek haber API entegrasyonu için (Opsiyonel, yoksa otomatik kazıma yapar)
export NEWS_API_KEY="your-newsapi-key"
```

---

## 💻 Kullanım Kılavuzu

### A. Komut Satırından Çalıştırma (CLI)

Herhangi bir marka hakkında hızlıca analiz başlatıp JSON dosyasını kaydetmek için:

```bash
python3 gather_brand_data.py --brand "Starbucks" --category "coffee" --region "TR"
```

**Çıktı:**
Bulunduğunuz dizine `starbucks_report.json` adında bir rapor kaydedilir. Rapor içeriği tam olarak talep ettiğiniz formatta olacaktır.

### B. MCP Sunucusu Olarak Entegrasyon

#### 1. Claude Desktop veya Cursor Entegrasyonu
MCP sunucusunu Claude Desktop uygulamasına bağlamak için `claude_desktop_config.json` dosyanıza şu konfigürasyonu ekleyin:

```json
{
  "mcpServers": {
    "brand-context-server": {
      "command": "python3",
      "args": ["/Users/onurataoral/sektor ve haberler/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY",
        "NEWS_API_KEY": "YOUR_NEWS_API_KEY"
      }
    }
  }
}
```

#### 2. Sunulan MCP Araçları (Tools)

- **`fetch_raw_sources`**:
  * **Açıklama:** Belirtilen marka hakkında PwC, Deloitte, Şikayetvar, Ekşi Sözlük, Reddit ve NewsAPI'den ham metin verilerini toplar.
  * **Parametreler:** `brand` (zorunlu), `category` (zorunlu), `region` (opsiyonel), `sector` (opsiyonel).

- **`generate_report`**:
  * **Açıklama:** Ham verileri toplar, LLM kullanarak analiz eder ve tüketici sinyalleri, duyguları ve segmentlerini içeren şemaya uygun rapor üretir.
  * **Parametreler:** `brand` (zorunlu), `category` (zorunlu), `region` (opsiyonel), `sector` (opsiyonel).
