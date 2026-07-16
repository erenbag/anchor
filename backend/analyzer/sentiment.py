"""
Anchor — Yorum Duygu Analizi (Sentiment Analysis)
Kullanıcı yorumlarından clickbait sitemini tespit eder.
"""
import logging
from analyzer.nli_engine import nli_engine

logger = logging.getLogger(__name__)

# Clickbait sitemini tespit etmek için kullanılan anahtar hipotezler
CLICKBAIT_HYPOTHESES = [
    "Bu video clickbait, başlık yanıltıcı",
    "This is clickbait, the title is misleading",
    "Başlık ile içerik uyuşmuyor",
]


def analyze_comments(comments: list[str]) -> dict:
    """
    Yorum listesini analiz ederek kullanıcı duygu skoru döndürür.

    Args:
        comments: ["Boşuna izlemeyin...", "Güzel video ama başlık abartı"]

    Returns:
        {
            "avg_clickbait_sentiment": float,  # 0.0 – 1.0 (yüksek = clickbait sitemi)
            "feedback_text": str,               # Kullanıcıya gösterilecek metin
            "analyzed_count": int,
        }
    """
    if not comments:
        return {
            "avg_clickbait_sentiment": 0.0,
            "feedback_text": "Yorum analizi yapılamadı (yorum bulunamadı).",
            "analyzed_count": 0,
        }

    clickbait_scores = []

    for comment in comments[:10]:  # En fazla 10 yorum analiz et
        if len(comment.strip()) < 5:
            continue

        try:
            # Her yorumu "clickbait" hipotezi ile karşılaştır
            result = nli_engine.analyze_nli(
                premise=comment,
                hypothesis="Bu içerik clickbait ve yanıltıcı",
            )
            clickbait_scores.append(result["entailment_score"])
        except Exception as e:
            logger.warning("Yorum analiz hatası: %s", e)
            continue

    if not clickbait_scores:
        return {
            "avg_clickbait_sentiment": 0.0,
            "feedback_text": "Yorumlar analiz edilemedi.",
            "analyzed_count": 0,
        }

    avg_score = sum(clickbait_scores) / len(clickbait_scores)

    # Duygu metnini oluştur
    if avg_score >= 0.7:
        feedback = "Kullanıcı yorumları yüksek oranda yanıltıcı başlık sitemi içeriyor."
    elif avg_score >= 0.4:
        feedback = "Kullanıcı yorumlarında kısmi başlık eleştirisi mevcut."
    else:
        feedback = "Kullanıcı yorumları genel olarak içerikle uyumlu görünüyor."

    return {
        "avg_clickbait_sentiment": round(avg_score, 4),
        "feedback_text": feedback,
        "analyzed_count": len(clickbait_scores),
    }
