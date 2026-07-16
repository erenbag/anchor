"""
Anchor — Özetleme ve Dürüst Başlık Üretimi (Gemini API)
Google Gemini 2.0 Flash ile hızlı, çok dilli başlık alternatifi üretir.
"""
import logging
from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)

# Gemini istemcisi
_client = None


def _get_client() -> genai.Client:
    """Gemini istemcisini lazy-load eder."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY ayarlanmamış. .env dosyasını kontrol edin.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini API istemcisi hazır.")
    return _client


def generate_honest_title(
    original_title: str,
    content_summary: str,
    platform: str,
    comments: list[str] | None = None,
    verified_timestamp: str | None = None,
) -> dict:
    """
    Gemini API ile dürüst başlık önerisi ve çelişki özeti üretir.

    Args:
        original_title: Orijinal başlık
        content_summary: En uyumlu segmentin / makale gövdesinin metni
        platform: "youtube" veya "news"
        comments: Kullanıcı yorumları (opsiyonel)
        verified_timestamp: Doğrulanan zaman aralığı (opsiyonel)

    Returns:
        {
            "honest_title_suggestion": str,
            "contradiction_summary": str,
        }
    """
    client = _get_client()

    # Yorum bölümünü oluştur
    comments_section = ""
    if comments:
        top_comments = comments[:5]
        comments_text = "\n".join(f"- {c}" for c in top_comments)
        comments_section = f"\n\nKullanıcı Yorumları:\n{comments_text}"

    # Zaman damgası bilgisi
    timestamp_info = ""
    if verified_timestamp:
        timestamp_info = f"\nDoğrulanan Zaman Aralığı: [{verified_timestamp}]"

    prompt = f"""Sen bir medya dürüstlüğü analistisin. Aşağıdaki bilgilere dayanarak iki görev yapacaksın:

1. **Dürüst Başlık Önerisi**: Orijinal başlığın yerine, içeriği gerçekçi yansıtan dürüst bir başlık öner. Başlık Türkçe olsun, dikkat çekici ama dürüst olsun.

2. **Çelişki Özeti**: Orijinal başlık ile gerçek içerik arasındaki uyum veya çelişkiyi 2 cümleyle özetle. Eğer bir çelişki varsa neyin yanıltıcı olduğunu belirt. Eğer uyumluysa bunu da belirt.{timestamp_info}

Platform: {platform.upper()}
Orijinal Başlık: "{original_title}"

İçerik Özeti:
{content_summary[:3000]}{comments_section}

YANITINI TAM OLARAK ŞÖYLE VER (bu formatı bozma):
DÜRÜST_BAŞLIK: <önerilen başlık>
ÇELİŞKİ_ÖZETİ: <2 cümlelik özet>"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
        )

        text = response.text.strip()

        # Yanıtı parse et
        honest_title = ""
        contradiction_summary = ""

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("DÜRÜST_BAŞLIK:"):
                honest_title = line.replace("DÜRÜST_BAŞLIK:", "").strip()
            elif line.startswith("ÇELİŞKİ_ÖZETİ:"):
                contradiction_summary = line.replace("ÇELİŞKİ_ÖZETİ:", "").strip()

        # Eğer parse başarısız olursa, ham metni kullan
        if not honest_title:
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            honest_title = lines[0] if lines else "Başlık üretilemedi."
        if not contradiction_summary:
            contradiction_summary = text[:300] if text else "Özet üretilemedi."

        return {
            "honest_title_suggestion": honest_title,
            "contradiction_summary": contradiction_summary,
        }

    except Exception as e:
        logger.error("Gemini API hatası: %s", e)
        return {
            "honest_title_suggestion": "Başlık önerisi üretilemedi (API hatası).",
            "contradiction_summary": f"Özet üretilemedi: {str(e)}",
        }
