# Proje Şartnamesi: Anchor (Akıllı Clickbait & İçerik Uyuşmazlığı Analiz Sistemi)
**Sürüm:** 1.2.0  
**Geliştirici Altyapısı:** Antigravity API  
**Hedef Platformlar:** Chrome Tarayıcı Uzantısı (Extension) & Python FastAPI Yerel Backend Sunucusu  

---

## 1. Projenin Vizyonu ve Temel Mantığı
Anchor, geleneksel sadece "başlığa bakan" yüzeysel clickbait tespit yöntemlerini reddeder. Bir haberin veya YouTube videosunun başlığı ne kadar sansasyonel olursa olsun, içerikle uyuştuğu sürece dürüst kabul edilmelidir. 

Anchor; **Başlık-İçerik Çelişkisini (Incongruence)**, uzun metinleri zaman damgalı bölümlere ayıran **Zaman Damgalı Bölümleme (Timestamped Segmentation)** algoritmasını ve **Kullanıcı Reaksiyonlarını (Yorum Analizi)** bir arada kullanarak tarayıcı üzerinde dinamik görsel geri bildirimler sunan akıllı bir yardımcıdır.

---

## 2. Kullanıcı Deneyimi ve Arayüz (UI/UX) Tasarımı
* **Dinamik Anchor Halkası (Doğruluk İkonu):** Haber sitelerindeki kartların veya YouTube ana sayfasındaki video thumbnail'lerinin sağ üst köşesinde küçük, dairesel bir halka (Anchor Halkası) belirir.
* **Renk Derecelendirmesi (Skala):**
  * Yeşil (%0 - %20 Çelişki): Başlık ve içerik tamamen tutarlı, dürüst bilgi.
  * Sarı (%21 - %50 Çelişki): Başlıkta hafif abartı veya merak uyandırma unsurları mevcut.
  * Turuncu (%51 - %80 Çelişki): Başlık içerikten belirgin şekilde sapmış, yanıltıcı dil kullanılmış.
  * Kırmızı (%81 - %100 Çelişki / Yoğun Negatif Yorum): Tamamen uyuşmazlık, yalan başlık veya yoğun kullanıcı sitemi tespiti.
* **Hover Kartı (Detaylı Bilgi Kutusu):** Kullanıcı imleci halkanın üzerine getirdiğinde (hover) şık, yarı saydam, modern bir bilgi kartı açılır. Kartın içeriği:
  1. Yapay Zeka Doğruluk Skoru: Örn: %85 Clickbait Riski.
  2. Dürüst Başlık Önerisi: Yapay zekanın içerikten ürettiği dürüst başlık alternatifi.
  3. Özet Çelişki/Doğrulama Raporu: "Başlıkta X olayı iddia ediliyor. Bu olay videonun [04:12 - 06:15] dakikaları arasında doğrulanmıştır." ya da "Yorumlar ve içerik, olayın sadece bir bilgisayar oyunundan ibaret olduğunu göstermektedir."

---

## 3. Sistem Mimarisi ve Teknik İş Akışı

[Tarayıcı Uzantısı] 
       │
       ├─► (Haber) ──► Başlık + Makale Gövdesi ─────────────────────┐
       │                                                            ▼
       └─► (YouTube) ► Başlık + Zaman Damgalı Altyazı + Yorumlar ──► [FastAPI Yerel Sunucusu]
                                                                            │
[Anchor Halkası & Kart] ◄── (Yüzdelik Skor + Detaylı Rapor) ◄───────────────┘

### A. YouTube Akışı
1. Uzantı, YouTube sayfasından videoId'yi yakalar.
2. youtube-transcript-api kütüphanesi kullanılarak videonun zaman damgalı altyazı dökümü (transcript) çekilir.
3. YouTube API'si veya kazıcı (scraper) yardımıyla en çok beğeni alan ilk 10 yorum analiz edilmek üzere toplanır.
4. Veriler yerel FastAPI sunucusuna gönderilir.

### B. Haber Siteleri Akışı
1. Uzantı, haber sayfasındaki başlığı (h1) ve ana makale gövdesini (article) ayıklar.
2. Verileri FastAPI sunucusuna iletir.

---

## 4. Yapay Zeka Altyapısı ve Algoritmik Mantık

Sistem, iki dilli (Türkçe + İngilizce) çalışabilen, yerel CPU/GPU dostu ve çok yüksek tutarlılığa sahip Hugging Face modellerini temel alır.

### A. Haber Analiz Altyapısı
* Model: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2cl
* Çalışma Şekli: Başlık "Hipotez" (Hypothesis), haber gövdesi ise "Öncül" (Premise) olarak modele beslenir. Model doğrudan Entailment (Uyumlu) ve Contradiction (Çelişkili) olasılık skorlarını üretir.

### B. YouTube "Zaman Damgalı Bölümleme" Algoritması
Çok uzun altyazıların (512 token sınırını aşan) detay kaybetmeden analiz edilmesi için şu algoritma uygulanır:
1. Segmentasyon (Chunking): Altyazı metni, her biri anlam bütünlüğüne sahip 2'şer dakikalık zaman bloklarına (segmentlere) bölünür.
2. Çoklu Çelişki Sorgusu (Batch Inference): Her bir segment, mDeBERTa-v3 modeline ayrı ayrı gönderilerek başlıkla kıyaslanır.
3. Maksimum Uyum Filtresi: Eğer en az bir segmentte çelişki oranı düşük (tutarlılık yüksek) çıkarsa, video "Clickbait Değildir" olarak kabul edilir. Kullanıcıya uyuşmanın gerçekleştiği zaman damgası (Örn: [04:15 - 06:20]) raporlanır. Tüm segmentlerde çelişki yüksek çıkarsa video kırmızı etiket alır.

### C. Özetleme ve Dürüst Başlık Üretimi
* Model: Yerelde hızlı çalışması için google/gemma-2-2b-it (Hugging Face pipeline aracılığıyla) veya OpenAI API standartlarında yerel hafif bir LLM kullanılır.
* Görevi: Başlık ve en uyumlu segmenti/yorumu okuyarak dürüst bir alternatif başlık üretmek ve uyuşmazlık sebebini 2 cümleyle özetlemek.

---

## 5. Veri Şeması ve API Protokolü (JSON)

### API İstek Yapısı (POST /api/analyze)
{
  "platform": "youtube",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "HAYATIMIN EN BÜYÜK KAZASINI YAPTIM! (ÖLÜMDEN DÖNDÜM)",
  "content": [
    {"text": "herkese selam arkadaşlar bugün yeni yarış oyununu oynuyoruz", "start": 0.0, "duration": 5.0},
    {"text": "aman tanrım bariyerlere çarptım araba darmadağın oldu", "start": 125.0, "duration": 10.0}
  ],
  "comments": [
    "Boşuna izlemeyin oyunda kaza yapıyor.",
    "Başlık tam bir clickbait olmuş ama video eğlenceli."
  ]
}

### API Yanıt Yapısı (Response)
{
  "clickbait_ratio": 0.88,
  "status_color": "red",
  "honest_title_suggestion": "Eren, Yeni Yarış Oyununda Eğlenceli Anlar Yaşadı",
  "contradiction_summary": "Video başlığında ölümcül bir kaza yapıldığı iddia edilmiş olsa da, video içeriği ve kullanıcı yorumları olayın tamamen bir bilgisayar oyunundan ibaret olduğunu (02:05 dakikasında) doğrulamaktadır.",
  "user_sentiment_feedback": "Kullanıcı yorumları yüksek oranda yanıltıcı başlık sitemi içeriyor.",
  "verified_timestamp": "02:05 - 02:15"
}

---

## 6. Geliştirme Adımları ve Kod Şablonları (Antigravity İçin Talimatlar)

Antigravity API, bu projeyi hayata geçirmek için aşağıdaki adımları sırasıyla tamamlamalı ve belirtilen kod şablonlarını üretmelidir:

### Adım 1: FastAPI Yerel Sunucu Altyapısını Yaz
FastAPI kullanarak istekleri karşılayacak, MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2cl ve google/gemma-2-2b-it modellerini yükleyip çalıştıracak olan main.py dosyasını oluştur.

### Adım 2: Zaman Damgalı Bölümleme (Timestamped Chunking) Fonksiyonunu Kodla
Gelen uzun altyazı verisini zaman damgası sınırlarına göre 2'şer dakikalık anlamlı parçalara bölen ve her birini sırayla NLI modeline sokarak en uyumlu zaman aralığını tespit eden backend algoritmasını yaz.

### Adım 3: Chrome Uzantısı (Frontend) Dosyalarını Üret
* manifest.json: Gerekli izinleri (activeTab, storage, host permissions) barındıran manifest dosyasını hazırla.
* content.js: YouTube video sayfalarında videoId'yi yakalayıp altyazıları çeken, haber sitelerinde h1 ve article etiketlerini ayıklayan ve sayfaya dinamik yeşil/sarı/kırmızı Anchor halkalarını ve hover bilgi kartını CSS ile enjekte eden betiği kodla.
* background.js: Sayfadan gelen verileri alıp yerel FastAPI sunucusuna (http://localhost:8000/api/analyze) post eden arka plan köprüsünü kur.