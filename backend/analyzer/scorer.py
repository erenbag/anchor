"""
Anchor — Clickbait Skor Hesaplama Motoru
NLI sonuçları + Yorum Duygusu → Nihai Clickbait Skoru
"""
from analyzer.chunker import format_time_range
from config import COLOR_THRESHOLDS, NLI_WEIGHT, COMMENT_WEIGHT


def determine_color(ratio: float) -> str:
    """Clickbait oranına göre renk kodu döndürür."""
    for color, (low, high) in COLOR_THRESHOLDS.items():
        if low <= ratio <= high:
            return color
    return "red"


def calculate_score(
    nli_results: list[dict],
    comment_sentiment: dict,
    platform: str,
) -> dict:
    """
    Nihai clickbait skorunu ve detaylarını hesaplar.

    Args:
        nli_results: Segment bazlı NLI çıktıları
            [{"start": 0, "end": 120, "contradiction_score": 0.85, "entailment_score": 0.15}, ...]
        comment_sentiment: Yorum analiz çıktısı
            {"avg_clickbait_sentiment": 0.7, "feedback_text": "...", "analyzed_count": 5}
        platform: "youtube" veya "news"

    Returns:
        {
            "clickbait_ratio": float,
            "status_color": str,
            "verified_timestamp": str | None,
            "best_segment": dict | None,
            "worst_segment": dict | None,
            "user_sentiment_feedback": str,
        }
    """
    if not nli_results:
        return {
            "clickbait_ratio": 0.0,
            "status_color": "green",
            "verified_timestamp": None,
            "best_segment": None,
            "worst_segment": None,
            "user_sentiment_feedback": comment_sentiment.get("feedback_text", ""),
        }

    # ── Maksimum Uyum Filtresi ────────────────────────────────────
    # En düşük çelişki (= en yüksek uyum) olan segmenti bul
    best_segment = min(nli_results, key=lambda s: s["contradiction_score"])
    worst_segment = max(nli_results, key=lambda s: s["contradiction_score"])

    # NLI bazlı clickbait oranı:
    # Şartname: "Eğer en az bir segmentte çelişki düşükse → clickbait değildir"
    # Bu yüzden EN İYİ segmentin skorunu temel alıyoruz
    nli_ratio = best_segment["contradiction_score"]

    # ── Yorum Ağırlığı Uygula ────────────────────────────────────
    comment_score = comment_sentiment.get("avg_clickbait_sentiment", 0.0)

    if comment_sentiment.get("analyzed_count", 0) > 0:
        # Yorumlar varsa: hibrit skor
        final_ratio = (NLI_WEIGHT * nli_ratio) + (COMMENT_WEIGHT * comment_score)
    else:
        # Yorum yoksa: sadece NLI
        final_ratio = nli_ratio

    final_ratio = round(min(max(final_ratio, 0.0), 1.0), 4)

    # ── Zaman Damgası ─────────────────────────────────────────────
    verified_timestamp = None
    if platform == "youtube":
        if best_segment["entailment_score"] > 0.5:
            verified_timestamp = format_time_range(
                best_segment["start"], best_segment["end"]
            )

    return {
        "clickbait_ratio": final_ratio,
        "status_color": determine_color(final_ratio),
        "verified_timestamp": verified_timestamp,
        "best_segment": best_segment,
        "worst_segment": worst_segment,
        "user_sentiment_feedback": comment_sentiment.get("feedback_text", ""),
    }
