"""
Anchor — Yapılandırma Sabitleri
"""
import os
from dotenv import load_dotenv

# .env dosyasını yükle (backend/ değil, projenin kök dizinindeki .env)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# ─── Model Ayarları ───────────────────────────────────────────────
NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
GENERATIVE_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

# ─── Zaman Damgalı Bölümleme ─────────────────────────────────────
SEGMENT_DURATION_SECONDS = 120  # 2 dakikalık bloklar

# ─── Clickbait Skor Eşikleri ─────────────────────────────────────
# Renk skalası (çelişki oranına göre)
COLOR_THRESHOLDS = {
    "green":  (0.0, 0.20),   # Dürüst — başlık ve içerik tutarlı
    "yellow": (0.21, 0.50),  # Hafif abartı
    "orange": (0.51, 0.80),  # Yanıltıcı
    "red":    (0.81, 1.00),  # Tam clickbait
}

# ─── Yorum Analizi Ağırlığı ──────────────────────────────────────
# Nihai skorda yorum analizinin ağırlığı (0.0 - 1.0)
COMMENT_WEIGHT = 0.20  # %20 yorumlar, %80 NLI
NLI_WEIGHT = 0.80

# ─── Sunucu Ayarları ─────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8000
