# 100-Agent Tüketici Odak Grubu Motoru

Bu uygulama şu an **sentetik demo modunda çalışır** durumdadır. API anahtarı veya MCP entegrasyonu eksik olsa bile demo pazar verisi, demo segmentler, 100 anlık profil, ilk tepki, akran müzakeresi ve 3 rapor üretir.

## Şu Anki Çalışma Modu

`.env` içinde:

```env
API_PROVIDER=local
STRICT_EXTERNAL_DATA=false
AGENT_COUNT=100
```

Bu ayarlar uygulamayı demo moduna alır.

- MCP varsa pazar verisini denemeye çalışır.
- MCP tool'u hata verirse sentetik MCP payload kullanır.
- OpenAI/Gemini API key yoksa yerel sentetik LLM çıktısı kullanır.
- 100 profil, sentetik segment ağırlıklarına göre içeride anlık oluşur.
- Raporlar ve grafikler yine tam akışla üretilir.

## Gerçek API/MCP Moduna Dönmek

Gerçek entegrasyon için `.env` dosyası aşağıdaki gibi güncellenmelidir (Örn: Gemini kullanarak):

```env
API_PROVIDER=gemini
GEMINI_API_KEY=AIza...
STRICT_EXTERNAL_DATA=true
MCP_TUIK_SERVER_PATH=/absolute/path/to/tuik_data/mcp_server.py
MCP_BRAND_SERVER_PATH=/absolute/path/to/sector_news/mcp_server.py
```

Bu modda API/MCP hata verirse veya limit aşılırsa sistem güvenli şekilde durur.

## Çalıştırma

```bash
git clone https://github.com/onurata26/dualmind.git
cd dualmind
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Demo için gerekli; .env yoksa analiz hata verir
python3 -m streamlit run app.py
```

Varsayılan adres: `http://localhost:8501`

Bu makinede standart portlar doluysa farklı portla çalıştır:

```bash
python3 -m streamlit run app.py --server.port 8617
```

### Docker ile Çalıştırma

```bash
cp .env.example .env   # Önce .env oluştur
docker build -t dualmind .
docker run -p 8501:8501 --env-file .env dualmind
```

## Akış

1. Kullanıcı firma, ürün/kampanya ve açıklama girer.
2. Bölge, yaş grubu ve hedef kullanıcı briefi alınır.
3. Sistem MCP veya sentetik demo verisiyle pazar bağlamı oluşturur.
4. LLM veya yerel demo LLM segmentleri üretir.
5. `agent_factory.py`, segmentlere göre 100 profili anlık oluşturur.
6. `simulation_engine.py`, attention, resonance, objection ve purchase likelihood skorlarını hesaplar.
7. `pipeline.py`, zıt kutuplu profilleri tartıştırır ve fikir kaymasını uygular.
8. UI ilk survey, akran müzakeresi ve ağırlıklı final raporlarını gösterir.

## Önemli Dosyalar

- `app.py`: Streamlit UI.
- `pipeline.py`: Ana orkestrasyon.
- `mcp_client.py`: MCP bağlantısı ve demo MCP payloadları.
- `llm_layer.py`: OpenAI/Gemini veya yerel sentetik LLM fallback.
- `agent_factory.py`: Segmentlerden 100 profili oluşturur.
- `simulation_engine.py`: Bilişsel skorlar ve yorum üretimi.
- `.env`: Demo/gerçek mod ayarları.
- `outputs/`: Üretilen raporlar ve profil JSON çıktıları.

## Karar Matematiği

```text
Attention = clip(((Ad_Receptivity * 0.6 + Tech_Savviness * 0.4) / 10.0) * Region_Match, 0.1, 1.0)
Objection = clip(Price_Sensitivity * Price_Index * (50000.0 / Ajan_Geliri), 1.0, 10.0)
Purchase_Likelihood = Resonance * 5.0 + (10.0 - Objection) * 4.0 + Attention * 10.0

Delta_A = (Likelihood_B - Likelihood_A) * 0.25
Delta_B = (Likelihood_A - Likelihood_B) * 0.15
```

## Not

Demo modunda çıkan sonuçlar gerçek araştırma sonucu değildir; uygulamanın uçtan uca çalıştığını göstermek için sentetik verilerle üretilir. Gerçek kullanımda API key ve MCP entegrasyonları tamamlanmalıdır.
