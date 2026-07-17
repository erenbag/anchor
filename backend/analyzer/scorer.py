"""
Anchor — Clickbait Skor Hesaplama Motoru (News Only)
"""
from config import COLOR_THRESHOLDS

def determine_color(ratio: float) -> str:
    """Clickbait oranına göre renk kodu döndürür."""
    for color, (low, high) in COLOR_THRESHOLDS.items():
        if low <= ratio <= high:
            return color
    return "red"
