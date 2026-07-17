# ⚓ Anchor — Live Clickbait Detector

Anchor, dijital haber platformlarındaki yanıltıcı, manipülatif ve tıklama tuzağı (*clickbait*) içeren başlıkları, kullanıcının tarayıcısında **gerçek zamanlı (on-the-fly)** olarak analiz eden ve kanıt temelli çelişki raporu sunan gelişmiş bir Chrome uzantısıdır.

Proje, bulut API'lerine veya harici sunuculara bağımlılığı tamamen ortadan kaldırarak **%100 yerel (on-device CPU)** yapay zeka modelleriyle çalışacak şekilde optimize edilmiştir.

---

## 📸 Ekran Görüntüleri

### 1. Uzantı Kontrol Paneli (Popup)
<img src="popup.png" width="350" alt="Anchor Kontrol Paneli"/>

### 2. Gerçek Zamanlı Analiz Çıktıları
| 🔴 %98 Clickbait Yakalandı (Çelişki Raporu) | 🟢 %2 Dürüst İçerik Kontrolü |
|---|---|
| <img src="clickbait_report.png" width="400"/> | <img src="honest_report.png" width="400"/> |

---

## ⚙️ Teknik Mimari & Hibrit NLP Hattı

Sistem, minimum gecikme süresi (*latency*) ve maksimum veri gizliliği sağlamak amacıyla **iki aşamalı asenkron bir yapay zeka mimarisi** kullanır:

*   **Katman 1 — Doğal Dil Çıkarımı (NLI) ile Hız Hattı (`mDeBERTa-v3-base`):** Sayfa yüklendiği an haberin başlığı og ana metni yerel backend'e gönderilir. Türkçe dil yapısına adapte edilmiş NLI modeli, başlık ve içerik arasındaki mantıksal çelişkiyi **0.1 saniye** gibi bir sürede sınıflandırarak eklenti halkasının anında renk almasını ve skorun basılmasını sağlar.
*   **Katman 2 — Asenkron Metin Özetleme ile Rapor Hattı (`T5-Turkish`):** İlk katmanda çelişki skoru eşik değerin (%50) üzerinde çıktığında, ana istek akışını kilitlememek adına arka planda asenkron bir işlem (*background task*) tetiklenir. T5 modeli, haberin giriş segmentini işleyerek manipülasyonu ifşa eden tek cümlelik **Çelişki Raporu**'nu üretir ve arayüze dinamik olarak enjekte eder.

---

## ⚡ Uygulanan Mühendislik Optimizasyonları

*   **Asenkron Yapı (Lazy Loading):** Ağır dil modeli (LLM) üretim süreçleri tarayıcı istek hattını kiliklemez. Kullanıcı skoru anında görür, rapor arkadan beslenir. Bu sayede tarayıcı tarafında yaşanabilecek bağlantı kopma hataları kökten engellenmiştir.
*   **Token ve CPU Sünneti:** Yerel işlemcinin (CPU) boğulmasını önlemek adına üretici modele gönderilen metin sınırlandırılmış (`content[:200]`) ve üretim stratejisi `num_beams=1` (Greedy Search) olarak optimize edilerek hız 3 kat artırılmıştır.
*   **Akıllı Cümle Sınırlandırması:** Türkçe metin yapısındaki kısaltmalar (Örn: *Prof. Dr.*) veya zanlı isimleri (*S.K.*) gibi nokta içeren tuzaklar özel Regex filtreleriyle ayıklanarak cümle bütünlüğü korunmuştur.

---

## 🚀 Kurulum ve Çalıştırma

### 1. Yerel Sunucunun (Backend) Başlatılması
Projenin çalışabilmesi için yerel Python ortamında backend sunucusunun ayağa kaldırılması gerekir. Backend klasörünün içinde terminali açın ve sunucuyu başlatmak için "uvicorn main:app --reload" komutunu çalıştırın.

Sunucu ilk kez çalıştırıldığında gerekli NLP modellerini Hugging Face üzerinden yerel diskinize otomatik olarak indirecektir.

### 2. Chrome Uzantısının Yüklenmesi
1. Google Chrome tarayıcınızdan chrome://extensions/ sayfasına gidin.
2. Sağ üst köşede yer alan "Geliştirici Modu" (Developer Mode) seçeneğini aktif edin.
3. Sol üstteki "Paketlenmemiş uzantı yükle" (Load unpacked) butonuna tıklayın.
4. Proje klasörünüzün içindeki extension dizinini seçerek uzantıyı tarayıcınıza ekleyin.
