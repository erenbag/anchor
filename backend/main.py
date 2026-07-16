"""
Anchor — FastAPI Ana Sunucu
Tüm analiz pipeline'ını birleştiren ana endpoint.
"""
import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import HOST, PORT
from analyzer.nli_engine import nli_engine
from analyzer.chunker import chunk_transcript
from analyzer.scorer import calculate_score
from analyzer.sentiment import analyze_comments
from analyzer.summarizer import generate_honest_title

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("anchor")

# ── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title="Anchor — Clickbait Analiz API",
    description="Başlık-İçerik Uyuşmazlığı Tespit Sistemi",
    version="1.0.0",
)

# CORS — Chrome uzantısının localhost'a istek atabilmesi için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Modelleri ───────────────────────────────────────────
class TranscriptEntry(BaseModel):
    text: str
    start: float = 0.0
    duration: float = 0.0


class AnalyzeRequest(BaseModel):
    platform: str  # "youtube" veya "news"
    url: str = ""
    title: str
    content: list[TranscriptEntry] | str  # YouTube: list, Haber: str
    comments: list[str] = []


class AnalyzeResponse(BaseModel):
    clickbait_ratio: float
    status_color: str
    honest_title_suggestion: str
    contradiction_summary: str
    user_sentiment_feedback: str
    verified_timestamp: str | None = None


# ── Startup Event ────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Sunucu başladığında NLI modelini önceden yükle."""
    logger.info("Anchor sunucusu başlatılıyor…")
    logger.info("NLI modeli ön-yükleniyor (ilk istek hızlı olsun diye)…")
    nli_engine.load()
    logger.info("✅ Anchor sunucusu hazır!")


# ── Ana Analiz Endpoint'i ────────────────────────────────────────
@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Başlık-İçerik çelişki analizi yapar.

    YouTube: Zaman damgalı altyazı segmentasyonu + yorum analizi
    Haber: Başlık vs makale gövdesi NLI analizi
    """
    logger.info(
        "Analiz isteği alındı — Platform: %s | Başlık: %s",
        request.platform,
        request.title[:80],
    )

    try:
        title = request.title
        platform = request.platform.lower()

        # ── 1. İçerik İşleme ─────────────────────────────────────
        if platform == "youtube":
            # YouTube: transcript verisini segmentlere böl
            transcript_data = [
                {"text": entry.text, "start": entry.start, "duration": entry.duration}
                for entry in request.content
            ]
            segments = chunk_transcript(transcript_data)

            if not segments:
                raise HTTPException(
                    status_code=400,
                    detail="Altyazı verisi boş veya geçersiz.",
                )

            # Her segmenti NLI ile analiz et
            nli_results = nli_engine.analyze_batch(segments, title)
            # En iyi segmentin metnini özetleme için sakla
            best_idx = min(
                range(len(nli_results)),
                key=lambda i: nli_results[i]["contradiction_score"],
            )
            content_for_summary = segments[best_idx]["text"]

        elif platform == "news":
            # Haber: tek bir metin bloğu
            if isinstance(request.content, list):
                content_text = " ".join(entry.text for entry in request.content)
            else:
                content_text = request.content

            if not content_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Haber içeriği boş.",
                )

            # Tek segment olarak NLI analizi
            nli_result = nli_engine.analyze_nli(
                premise=content_text, hypothesis=title
            )
            nli_results = [
                {
                    "start": 0,
                    "end": 0,
                    "contradiction_score": nli_result["contradiction_score"],
                    "entailment_score": nli_result["entailment_score"],
                }
            ]
            content_for_summary = content_text[:2000]
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz platform: {platform}. 'youtube' veya 'news' olmalı.",
            )

        # ── 2. Yorum Duygu Analizi ───────────────────────────────
        comment_sentiment = analyze_comments(request.comments)

        # ── 3. Skor Hesaplama ────────────────────────────────────
        score_result = calculate_score(
            nli_results=nli_results,
            comment_sentiment=comment_sentiment,
            platform=platform,
        )

        # ── 4. Gemini ile Dürüst Başlık Üretimi ─────────────────
        summary_result = generate_honest_title(
            original_title=title,
            content_summary=content_for_summary,
            platform=platform,
            comments=request.comments if request.comments else None,
            verified_timestamp=score_result.get("verified_timestamp"),
        )

        # ── 5. Yanıt ────────────────────────────────────────────
        response = AnalyzeResponse(
            clickbait_ratio=score_result["clickbait_ratio"],
            status_color=score_result["status_color"],
            honest_title_suggestion=summary_result["honest_title_suggestion"],
            contradiction_summary=summary_result["contradiction_summary"],
            user_sentiment_feedback=score_result["user_sentiment_feedback"],
            verified_timestamp=score_result.get("verified_timestamp"),
        )

        logger.info(
            "✅ Analiz tamamlandı — Skor: %.2f | Renk: %s",
            response.clickbait_ratio,
            response.status_color,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analiz hatası: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analiz sırasında hata: {str(e)}")


# ── YouTube Altyazı Çekme Endpoint'i ─────────────────────────────
@app.get("/api/transcript/{video_id}")
async def get_transcript(video_id: str):
    """YouTube video altyazısını çeker (youtube-transcript-api)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id, languages=["tr", "en"])

        entries = []
        for snippet in transcript_list:
            entries.append(
                {
                    "text": snippet.text,
                    "start": snippet.start,
                    "duration": snippet.duration,
                }
            )

        logger.info(
            "Altyazı çekildi — Video: %s | %d parça", video_id, len(entries)
        )
        return {"success": True, "data": entries}

    except Exception as e:
        logger.warning("Altyazı çekme hatası (video: %s): %s", video_id, e)
        return {"success": False, "data": [], "error": str(e)}


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "anchor"}


# ── Doğrudan Çalıştırma ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
