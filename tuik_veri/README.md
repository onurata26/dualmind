# TÜİK Live & RAG Numerical MCP Server 📊🔮

Bu sunucu, Türkiye İstatistik Kurumu (TÜİK) verilerini gerçek zamanlı olarak kazıyan (scraping) ve yerel RAG veri tabanından bölgesel/sektörel sayısal göstergeleri sorgulayan bağımsız, yüksek performanslı bir **Model Context Protocol (MCP)** sunucusudur.

Diğer LLM (Yapay Zeka) katmanlarınız bu sunucuyu bir araç (Tool) olarak kullanarak tamamen sayısal matrisler alabilir, bunları birleştirebilir ve kendi formülleriyle nihai analizleri yapabilir.

---

## 🛠️ MCP Sunucu Mimarisi & Araçları (Tools)

Sunucu `stdio` protokolü üzerinden standart JSON-RPC 2.0 formatında çalışır ve 4 adet güçlü sayısal araç sunar:

### 1. `get_market_dynamics`
TÜİK ADNKS ve COICOP bütçe dağılımlarını sayısal matrisler halinde döner:
*   **Demografi:** Yaş grubu nüfusları, aktif iş gücüne katılım, işsizlik, yükseköğretim mezuniyet oranları ve hanehalkı büyüklükleri.
*   **Ekonomi:** Yıllık kullanılabilir hanehalkı geliri, Bölgesel Satınalma Gücü Paritesi (SGP) ve Gini katsayıları.
*   **Tüketici Harcamaları:** Resmi COICOP bütçe payları (Gıda 01, Giyim 03, Lokantalar 11 vb.) ile dijital e-ticaret penetrasyon oranları.

### 2. `get_brand_context`
İlgili markanın pazar payı, fiyat primi indeksi, sadakat indeksi ve rekabet yoğunluk oranlarını sayısal olarak döner.

### 3. `get_current_context`
Bölgesel yıllık TÜFE (enflasyon) oranları, Tüketici Güven Endeksi ve mevsimsel talep indekslerini sayısal olarak döner.

### 4. `fetch_live_tuik_data` (Canlı Arama & Kazıma)
Belirtilen konuyu (örn: "enflasyon", "işsizlik") TÜİK portalında gerçek zamanlı olarak arar, resmi bülten linklerini bulur ve bültenlerin içindeki ham sayısal tabloları ve açıklayıcı metin bloklarını ayıklayarak temiz bir JSON formatında LLM'e sunar.

---

## 📂 RAG Veri Yapısı (`rag_storage/`)
Yerel veriler resmi TÜİK istatistik standartlarına uygun olarak şu sayısal JSON tablolarında tutulmaktadır:
*   `tuik_demographics.json`: ADNKS nüfus, istihdam ve eğitim matrisleri.
*   `tuik_economic_indicators.json`: Bölgesel gelir, SGP paritesi ve güven indeksleri.
*   `tuik_consumer_spending.json`: COICOP tüketim harcamaları payları ve bilişim teknolojileri kullanım oranları.

---

## 🚀 Kurulum ve Entegrasyon

### 1. Gereksinimler
Sistem sadece standart kütüphaneleri ve veri çekme modüllerini kullanır:
```bash
pip install requests beautifulsoup4
```

#### Playwright Kurulumu (Tavsiye Edilir):
TÜİK'in React tabanlı sayfalarının içindeki **sayısal tabloları ham veri olarak okuyabilmek için** tarayıcı motorunun sisteminizde kurulu olması gerekir:
```bash
pip install playwright
playwright install chromium
```
*Not: Eğer Playwright kurulu değilse, sunucu WAF korumasını aşmak için LLM'e ilgili bültenlerin başlıklarını ve doğrudan URL bağlantılarını dönecektir.*

### 2. Cursor veya Claude Desktop Entegrasyonu
Bu sunucuyu kendi Antigravity veya Cursor/Claude istemcinize entegre etmek için istemci ayarlarına (MCP sunucuları bölümü) şu JSON bloğunu eklemeniz yeterlidir:

```json
"mcpServers": {
  "tuik-live-mcp": {
    "command": "python3",
    "args": ["/Users/onurataoral/tuik_veri/mcp_server.py"]
  }
}
```

### 3. Bağımsız Çalıştırma
Sunucuyu stdio üzerinden doğrudan başlatmak isterseniz:
```bash
./run_mcp.sh
```

---

## 🧪 Boru Hattı Test Çalıştırması

Sayısal verilerin ve canlı arama motorunun düzgün çalıştığını doğrulamak için hazırladığımız CLI test programını çalıştırabilirsiniz:
```bash
python3 test_run.py
```
Çıktı, LLM'inizin doğrudan parse edip matematiksel kararlar üretebileceği tamamen temiz, sayısal JSON yapılarından oluşacaktır.
