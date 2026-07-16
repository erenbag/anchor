"""
Anchor — Zaman Damgalı Bölümleme (Timestamped Chunking)
Uzun altyazı verilerini 2 dakikalık anlamlı segmentlere böler.
"""
from config import SEGMENT_DURATION_SECONDS


def chunk_transcript(transcript: list[dict]) -> list[dict]:
    """
    YouTube altyazı verilerini zaman damgasına göre segmentlere böler.

    Args:
        transcript: [
            {"text": "merhaba arkadaşlar", "start": 0.0, "duration": 5.0},
            {"text": "bugün yeni bir video ile", "start": 5.0, "duration": 3.5},
            ...
        ]

    Returns:
        [
            {
                "text": "merhaba arkadaşlar bugün yeni bir video ile ...",
                "start": 0.0,
                "end": 120.0,
            },
            {
                "text": "...",
                "start": 120.0,
                "end": 240.0,
            },
            ...
        ]
    """
    if not transcript:
        return []

    segments = []
    current_texts: list[str] = []
    segment_start = 0.0
    segment_end = SEGMENT_DURATION_SECONDS

    for entry in transcript:
        entry_start = entry.get("start", 0.0)
        entry_text = entry.get("text", "").strip()

        if not entry_text:
            continue

        # Eğer bu altyazı parçası mevcut segmentin dışına çıktıysa,
        # mevcut segmenti kaydet ve yenisine başla
        if entry_start >= segment_end and current_texts:
            segments.append(
                {
                    "text": " ".join(current_texts),
                    "start": segment_start,
                    "end": segment_end,
                }
            )
            current_texts = []
            segment_start = segment_end
            segment_end = segment_start + SEGMENT_DURATION_SECONDS

        current_texts.append(entry_text)

    # Son kalan segmenti ekle
    if current_texts:
        last_entry = transcript[-1]
        final_end = last_entry.get("start", 0.0) + last_entry.get("duration", 0.0)
        segments.append(
            {
                "text": " ".join(current_texts),
                "start": segment_start,
                "end": round(final_end, 2),
            }
        )

    return segments


def format_timestamp(seconds: float) -> str:
    """Saniyeyi MM:SS formatına çevirir."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_time_range(start: float, end: float) -> str:
    """Zaman aralığını [MM:SS - MM:SS] formatına çevirir."""
    return f"{format_timestamp(start)} - {format_timestamp(end)}"
