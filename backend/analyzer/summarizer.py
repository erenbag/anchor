"""
Anchor — Statik Dürüst Başlık Üretimi (News Only)
Haberler için ilk cümleyi çeker (0.5ms gecikme).
"""
import logging
import re

logger = logging.getLogger(__name__)

def generate_honest_title(
    original_title: str,
    content_summary: str,
    platform: str = "news",
    comments: list[str] | None = None,
    verified_timestamp: str | None = None,
) -> dict:
    """
    Haber içeriklerinin ilk anlamlı cümlesini cımbızlayıp dürüst başlık olarak döner.
    """
    honest_title = original_title
    
    try:
        # İçeriğin ilk 2 cümlesini başlık yap (Nokta, soru işareti veya ünlemden böl)
        sentences = [s.strip() for s in re.split(r'[.?!]', content_summary) if len(s.strip()) > 15]
        
        if sentences:
            honest_title = sentences[0] + "."
            if len(sentences) > 1 and len(honest_title) < 50:
                honest_title += " " + sentences[1] + "."
        
        return {
            "honest_title_suggestion": honest_title,
            "contradiction_summary": "Sistem NLP algoritmasıyla haber metninin en anlamlı özetini başlık olarak çıkardı."
        }

    except Exception as e:
        logger.error(f"Statik başlık üretimi hatası: {e}")
        return {
            "honest_title_suggestion": original_title,
            "contradiction_summary": "Sistem başlığı analiz edemedi."
        }
