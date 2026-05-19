# 🔮 CODEX PROJE DETAYLARI VE UÇTAN UCA YAZILIM TALİMATNAMESİ

Bu belge, **100-Agent Sentetik Tüketici Odak Grubu & Akran Müzakeresi Simülatörü** projesinin mimarisini ve kodlama detaylarını özetlemektedir. Bu metni başka bir yapay zeka modeline (Codex/LLM) doğrudan vererek **"Projeyi baştan sona kodla, Web UI'ı dahil tüm sistemleri entegre et"** talimatı ile çalıştırabilirsiniz.

---

## 🎯 PROJENİN AMACI VE VİZYONU
Kullanıcıdan alınan bir kampanya/ürün fikrini alıp; yerel MCP sunucularından pazar ve TÜİK verilerini çekerek akademik bir pazar araştırma raporu oluşturan, bu rapor doğrultusunda tam orantılı **100 adet sentetik tüketici ajanı** türeten, bu ajanların kampanyaya verdikleri ilk reaksiyonları bilişsel formüllerle hesaplayan (Bilinç 1), ardından ajanları çapraz eşleştirerek **Türkçe akran tartışmasına (debate)** sokan ve tartışma sonrası değişen fikirleri stochastically güncelleyen (Bilinç 2) uçtan uca bir backend ve frontend (Web UI) sistemidir. Simülasyon sonunda 3 adet stratejik yönetici raporu (Rapor 1, Rapor 2, Rapor 3) üretilir.

---

## 📂 KLASÖR VE DOSYA YAPISI (DIRECTORY STRUCTURE)
Proje şu modüllerden oluşmalı ve tamamen modüler kodlanmalıdır:
```text
agent_uretici/
├── .env                  # API anahtarları, model isimleri ve simülasyon parametreleri
├── requirements.txt      # python-dotenv, requests, beautifulsoup4, pandas, plotly, streamlit
├── llm_layer.py          # OpenAI ve Gemini entegrasyonu + Key olmadığında çalışan Yerel Türkçe Fallback
├── mcp_client.py         # Subprocess JSON-RPC standardı ile mcp_server.py'ye bağlanan istemci
├── agent_factory.py      # Matematiksel segmentasyon ve 100 orantılı ajan üreten fabrika
├── simulation_engine.py  # 4 aşamalı Bilişsel Skorlama ve Türkçe kotasyon üreten motor
├── pipeline.py           # 9 aşamalı tüm simülasyonu koordine eden arka plan boru hattı
├── app.py                # Streamlit/React tabanlı tüm KPIs, Grafikler ve Canlı Logları sunan Web UI
└── SYSTEM_DESIGN.md      # Mimarinin detaylı matematiksel manifestosu
```

---

## 📐 KRİTİK MATEMATİKSEL FORMÜLLER VE İŞLEYİŞ

### 1. Bilişsel Karar Aşamaları (simulation_engine.py)
Her ajanın kampanya fikrine vereceği tepki şu 4 aşamadan geçerek hesaplanır:
*   **Dikkat Aşaması (Attention):** Ajanın reklamı fark etme olasılığı.
    $$Attention = \text{clip}\left(\frac{\text{Reklam Duyarlılığı} \times 0.6 + \text{Teknoloji Yatkınlığı} \times 0.4}{10.0} \times \text{Bölge Eşleşme Çarpanı}, \, 0.1, \, 1.0\right)$$
*   **Değer Rezonansı (Resonance):** Kampanya metni ile Ajanın temel güdüsü (Çevre, Statü, Tasarruf, Nostalji) arasındaki uyum skoru (1.0 - 10.0).
*   **Ekonomik İtiraz (Objection):** Ajanın fiyat hassasiyeti ve geliri karşısında kampanyanın fiyat endeksine gösterdiği direnç (1.0 - 10.0).
    $$Objection = \text{clip}\left(\text{Fiyat Hassasiyeti} \times \text{Kampanya Fiyat Endeksi} \times \frac{50000.0}{\text{Ajan Geliri}}, \, 1.0, \, 10.0\right)$$
*   **Satın Alma Eğilimi (Purchase Likelihood - %):**
    $$Purchase\_Likelihood = Resonance \times 5.0 + (10.0 - Objection) \times 4.0 + Attention \times 10.0$$

### 2. Ajanlar Arası Çapraz Müzakere (Debate Layer - pipeline.py)
*   **Mantıksal Eşleşme:** Ajanlar satın alma yüzdelerine göre sıralanır. En yüksek olumlu karar veren ajan (örn. index 99) ile en olumsuz karar veren ajan (örn. index 0) **zıt kutuplu çiftler** halinde eşleştirilir.
*   **Diyalog:** Çiftler, LLM aracılığıyla Türkçe 3 turluk bir tartışma yürütür (Ekonomik itirazlara karşı sürdürülebilirlik/kalite argümanları paylaşılır).
*   **Fikir Kayması (Mind Shift):** Tartışma sonrası sosyal ikna gücüyle olasılıklar güncellenir:
    *   *Olumlu Ajandan Olumsuza Kayma Etkisi:*
        $$\Delta A = (Likelihood_B - Likelihood_A) \times 0.25$$
    *   *Olumsuz Ajanın Finansal Direnç Etkisi:*
        $$\Delta B = (Likelihood_A - Likelihood_B) \times 0.15$$
    *   Ajanların nihai kararları bu kaymalar sonrasında yeniden belirlenip diske kaydedilir.

---

## 📊 FİNAL RAPORLARI VE ÇIKTILAR (Rapor 1, 2, 3)
*   **Rapor 1 (`report_1_initial.md`):** Ajanların ham ilk kararlarının yüzdesel dağılımı (Bilinç 1).
*   **Rapor 2 (`report_2_post_debate.md`):** Akran tartışmaları sonrası ikna olanların oranları, sosyal etkileşim analizi (Bilinç 2).
*   **Rapor 3 (`report_3_final.md`):** İki aşamalı durumun ağırlıklı karşılaştırma matrisi ve marka için **3 finalize edilmiş stratejik aksiyon planı**.
*   **JSON Çıktıları:** `outputs/initial_reactions/` ve `outputs/final_reactions/` klasörlerine 100'er adet detaylı bireysel `agent_X.json` dosyası yazılır.

---

## 💻 WEB UI (FRONTEND TASARIM) GEREKSİNİMLERİ (app.py)
UI son derece şık, koyu mod (dark theme) ve cam kaplama (glassmorphism) stilinde olmalı, şu 4 sekmeyi sunmalıdır:
1.  **📊 Pazar Analizi:** Pazar araştırma metninin girilebildiği, raporun analiz edilerek segment dağılımlarının pastalarla (Plotly donut) gösterildiği alan.
2.  **👥 Persona Fabrikası:** Üretilen 100 adet sentetik profilin isimleri, MBTI tipleri, gelirleri ve hassasiyet bar-metreleriyle listelendiği, arama ve filtreleme sunan kartlar.
3.  **⚡ Odak Grubu Konsolu:** Kampanya detaylarının girildiği ve simülasyon tetiklendiğinde akan bir terminal log efektiyle (Live Console) ajanların bilişsel akışlarının canlı yansıtıldığı konsol.
4.  **📈 Yönetici Analitiği & Drill-Down:** 
    *   Genel Dönüşüm Oranı, Satın Alma Eğilimi, NPS gibi KPI metrikleri.
    *   Yaş/Gelir ve Segment dönüşüm grafikleri (Plotly).
    *   **Tekil Zihin Müfettişi (Drill-Down Inspector):** 100 ajan arasından seçilen bir ajanın zihnindeki 3 aşamalı bilişsel bar grafiklerini, debate partnerini ve tartışma sonrasında yazdığı **bireysel Türkçe yorumu (kotasyonu)** okuma alanı.
    *   Raporların Markdown formatında ekrana basılması ve indirilebilmesi.

---

## 🤖 CODEX'E VERİLECEK TALİMAT:
> "Sana tüm detaylarını sunduğum sentetik tüketici odak grubu ve müzakere simülatörü projesini **tamamen baştan sona kodla**. Modüller arasındaki veri akışını, matematiksel formülleri, MCP client subprocess yapısını ve 3 turluk diyalogları eksiksiz kur. En nihayetinde tüm bu arka plan motorunu sarmalayacak şık, modern, cam kaplama (glassmorphic) tasarıma sahip **Web UI (Streamlit/React/Next.js) katmanını dahil et ve tam entegre çalışır vaziyette teslim et**!"
