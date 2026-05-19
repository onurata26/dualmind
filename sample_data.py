# -*- coding: utf-8 -*-
"""
Sample Database and Pre-loaded Market Research Reports for the Agent Focus Group Simulator.
"""

SAMPLE_MARKET_RESEARCH_REPORT = """
================================================================================
TÜRKİYE KAHVE VE BELEŞ İÇECEK SEKTÖRÜ SOSYO-EKONOMİK VE TÜKETİCİ DAVRANIŞLARI RAPORU (2026)
================================================================================

1. YÜRÜTÜCÜ ÖZET VE MAKROEKONOMİK GÖRÜNÜM
Türkiye'de 2026 yılı itibarıyla kahve tüketim alışkanlıkları, makroekonomik dalgalanmalar, artan enflasyonist baskı ve değişen genç demografi tarafından radikal bir şekilde şekillendirilmektedir. Yıllık bölgesel TÜFE oranlarının %60-70 bandında seyretmesi, hanehalklarının harcanabilir gelirlerini kısıtlarken, dışarıda yeme-içme (COICOP 11) harcama paylarında belirgin bir polarizasyona yol açmıştır. Tüketiciler lüks tüketimden kaçınmakta, ancak kaliteli kahve ve sosyal sosyalleşme ihtiyaçlarını "küçük lüksler" veya "stres azaltıcı harcamalar" kapsamında korumaktadır.

Özellikle Ege ve Marmara bölgelerinde yüksek eğitimli genç iş gücü ve metropol profesyonelleri arasında nitelikli kahveye (nitelikli çekirdekler, adil ticaret, sürdürülebilirlik) olan talep güçlü kalmaya devam ederken, iç Anadolu ve Karadeniz gibi bölgelerde fiyat duyarlılığı ve geleneksel tat profilleri ön plana çıkmaktadır.

2. MATEMATİKSEL PAZAR SEGMENTASYONU VE COHORT ANALİZİ
Yapılan geniş ölçekli saha araştırmaları ve TÜİK ADNKS verilerinin entegrasyonu sonucunda, Türkiye kahve pazarını domine eden 4 ana tüketici segmenti tanımlanmıştır. Simülasyon modellemelerinde bu segmentlerin ağırlıkları ve matematiksel hassasiyet indeksleri aşağıda verilmiştir:

--------------------------------------------------------------------------------
A) SEGMENT 1: METROPOL GENÇ PROFESYONELLER (Ağırlık: %30)
--------------------------------------------------------------------------------
*   Demografik Tanım: 24-40 yaş aralığında, İstanbul, İzmir, Ankara gibi büyükşehirlerde yaşayan, özel sektör/teknoloji/finans çalışanı bekarlar veya çocuksuz çiftler.
*   Ortalama Aylık Gelir: 45.000 TL - 95.000 TL arası.
*   Hassasiyet İndeksleri (1-10 Ölçeğinde):
    *   Fiyat Duyarlılığı: 4/10 (Kalite ve prestij için prim ödemeye hazır).
    *   Sürdürülebilirlik/Etik Odak: 7/10.
    *   Marka Sadakati: 8/10.
    *   Teknoloji Kullanımı: 9/10 (Mobil ödeme, sadakat uygulamaları vazgeçilmez).
*   Temel Satın Alma Dinamikleri: Prestij, zaman tasarrufu, estetik kahve dükkanları, üçüncü nesil (3rd wave) kahve kültürü, vegan süt seçenekleri.

--------------------------------------------------------------------------------
B) SEGMENT 2: SÜRDÜRÜLEBİLİRLİK ODAKLI BİLİNÇLİ TÜKETİCİLER (Ağırlık: %20)
--------------------------------------------------------------------------------
*   Demografik Tanım: 18-35 yaş aralığında, genellikle üniversite öğrencileri veya genç mezunlar. İzmir (Ege), Muğla, Kadıköy (İstanbul) yoğunluklu.
*   Ortalama Aylık Gelir: 25.000 TL - 45.000 TL arası.
*   Hassasiyet İndeksleri:
    *   Fiyat Duyarlılığı: 6/10 (Bütçeleri kısıtlı olsa da etik değerler için esneyebilirler).
    *   Sürdürülebilirlik/Etik Odak: 9/10 (Sıfır atık, plastik poşet karşıtlığı, adil ticaret).
    *   Marka Sadakati: 6/10 (Yanlış bir etik duruşta markayı kolayca boykot edebilirler).
    *   Teknoloji Kullanımı: 8/10.
*   Temel Satın Alma Dinamikleri: Karbon ayak izi düşük lojistik, yerel kooperatif destekleri, plastik içermeyen geri dönüştürülebilir ambalajlar, şeffaf tedarik zinciri.

--------------------------------------------------------------------------------
C) SEGMENT 3: BÜTÇE HASSASİYETLİ GENİŞ AİLELER (Ağırlık: %35)
--------------------------------------------------------------------------------
*   Demografik Tanım: 30-55 yaş aralığında, evli ve en az 1-2 çocuklu aileler. Büyükşehir çeperleri veya Anadolu şehirlerinde ikamet eden, orta/alt-orta sınıf memur ve işçiler.
*   Ortalama Aylık Gelir: 30.000 TL - 50.000 TL arası (Hanehalkı toplam).
*   Hassasiyet İndeksleri:
    *   Fiyat Duyarlılığı: 9/10 (Enflasyon ve artan gıda fiyatlarından en çok etkilenen grup).
    *   Sürdürülebilirlik/Etik Odak: 3/10 (Sürdürülebilirlik lüks bir kavram olarak görülür).
    *   Marka Sadakati: 5/10 (Nerede indirim veya promosyon varsa oraya yönelirler).
    *   Teknoloji Kullanımı: 5/10.
*   Temel Satın Alma Dinamikleri: Birim fiyat avantajı, çoklu/ekonomik paketler, market markaları (Private Label), indirim kuponları, uzun raf ömrü.

--------------------------------------------------------------------------------
D) SEGMENT 4: GELENEKSEL VE EMEKLİ KAHVE SEVERLER (Ağırlık: %15)
--------------------------------------------------------------------------------
*   Demografik Tanım: 50 yaş ve üzeri, emekli veya ev hanımı ağırlıklı. Geleneksel alışkanlıklara bağlı nüfus.
*   Ortalama Aylık Gelir: 15.000 TL - 30.000 TL arası.
*   Hassasiyet İndeksleri:
    *   Fiyat Duyarlılığı: 8/10.
    *   Sürdürülebilirlik/Etik Odak: 4/10.
    *   Marka Sadakati: 9/10 (Alıştıkları markayı ve ritüelleri değiştirmek istemezler).
    *   Teknoloji Kullanımı: 3/10 (Yüz yüze iletişim ve nakit/fiziki kart kullanımı).
*   Temel Satın Alma Dinamikleri: Geleneksel Türk kahvesi, damla sakızlı profiller, tanıdık kurukahveci dükkanı esnaf ilişkileri, nostaljik tasarım, sadelik.

3. KATEGORİ TRENDLERİ VE TÜKETİCİ ENFLASYON HİSSİYATI
*   Enflasyon Algısı: Tüketicilerin %84'ü kahve fiyatlarının son bir yılda "fahiş" düzeyde arttığını belirtmektedir. Bu nedenle kahvesini evde demleyenlerin oranında %38'lik bir artış kaydedilmiştir.
*   Premium Talebi: Ekonomik zorluklara rağmen Metropol Profesyonelleri, "kaliteli çekirdek" deneyimini evde sürdürmek için nitelikli çekirdek aboneliklerine yatırım yapmaktadır.
*   Sosyal Sorumluluk: "Yeşil Aklama" (Greenwashing) konusunda duyarlılık artmıştır. Tüketiciler sadece ambalajda yeşil yaprak görmek değil, sertifikaları şeffafça incelemek istemektedir.
"""

SAMPLE_CAMPAIGNS = {
    "campaign_1": {
        "id": "campaign_1",
        "name": "Ege Craft Premium Ekolojik Kahve Üyelik Modeli",
        "brand": "Ege Craft Coffee",
        "category": "Premium Nitelikli Kahve",
        "price_level": "Premium (Yüksek)",
        "price_index": 1.45,  # 1.45x premium compared to market average
        "target_regions": ["Ege", "Marmara"],
        "description": (
            "İzmir ve Muğla kooperatiflerinden adil ticaret (Fair Trade) ilkeleriyle doğrudan aldığımız nitelikli "
            "tek köken (single-origin) kahve çekirdeklerini, %100 plastik içermeyen, tamamen kompost edilebilir (organik gübreye dönüşen) "
            "özel bez torbalarda aylık abonelik modeliyle kapınıza getiriyoruz. Karbon nötr kargo kullanarak doğaya sıfır zarar vermeyi hedefliyoruz. "
            "Ayrıca, enflasyona inat üye olan herkese ömür boyu %15 fiyat koruma garantisi sunuyoruz! Aylık üyelik bedeli 580 TL'dir."
        ),
        "key_selling_points": ["Adil Ticaret", "Kompost Edilebilir Bez Ambalaj", "Karbon Nötr Kargo", "Enflasyon Koruma Garantisi", "Nitelikli Çekirdek"]
    },
    "campaign_2": {
        "id": "campaign_2",
        "name": "Espresso GO! Hızlı Şarj & Cep Dostu Kiosk Zinciri",
        "brand": "Espresso GO!",
        "category": "Ekonomik / Hızlı Tüketim Kahvesi",
        "price_level": "Ekonomik (Düşük)",
        "price_index": 0.75,
        "target_regions": ["Marmara", "İç Anadolu", "Akdeniz", "Ege"],
        "description": (
            "Metropolün koşturmacasında pahalı ve yavaş kahvecilere son! Üniversite kampüsleri, metro çıkışları ve iş merkezlerinde kurulan "
            "tamamen otonom robotik kahve kiosklarımızdan sadece 40 saniyede taze demlenmiş İtalyan espressonuzu veya lattesinizi alın. "
            "Mobil uygulamamız üzerinden tek tıkla siparişinizi verin, QR kodunuzla sıraya girmeden teslim alın. "
            "Her 5 kahveye 1 kahve hediye! Enflasyona meydan okuyan fiyat politikamızla espresso sadece 45 TL, latte 55 TL. Plastik bardaklarımız geri dönüştürülmüştür."
        ),
        "key_selling_points": ["Çok Ucuz", "Son Derece Hızlı (40 Saniye)", "QR Kodlu Sırasız Sipariş", "Sadakat Puanları & Bedava Kahve", "Geri Dönüşümlü Plastik"]
    },
    "campaign_3": {
        "id": "campaign_3",
        "name": "Nostaljik Közde Türk Kahvesi & Damla Sakızı Hediye Seti",
        "brand": "Ata Kurukahvecisi",
        "category": "Geleneksel Türk Kahvesi",
        "price_level": "Orta Seviye",
        "price_index": 1.05,
        "target_regions": ["Tüm Bölgeler"],
        "description": (
            "1950'lerden gelen ata geleneğiyle, taş değirmenlerde özenle çekilmiş, köz kokusunu ve aromasını muhafaza eden "
            "özel pirinç kutusunda nostaljik Türk Kahvesi. Setin yanında, Çeşme kooperatifinden tedarik edilmiş hakiki organik "
            "damla sakızı macunu kavanozu ve geleneksel motiflerle süslü 2 adet porselen fincan hediye! Ailenizle yapacağınız bayram sohbetleri veya "
            "akşam oturmalarınız için birebir. Geleneksel yöntemlerle, hiçbir koruyucu madde içermeden hazırlanmıştır. Kutu fiyatı 240 TL'dir."
        ),
        "key_selling_points": ["Nostaljik Pirinç Kutu", "Taş Değirmen Çekimi", "Organik Damla Sakızı Hediyeli", "Fincan Seti Hediye", "Esnaf Güvencesi"]
    }
}
