from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import sys
import asyncio
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor

from analyzer.nli_engine import nli_engine

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("anchor")

# ── Global Model Değişkeni ───────────────────────────────────────
t5_summarizer = None
executor = ThreadPoolExecutor(max_workers=1)

# ── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title="Anchor — Clickbait Analiz API (Sade ve Hızlı)",
    description="Sadece Clickbait Skoru ve Dinamik Rapor.",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    platform: str
    url: str = ""
    title: str
    content: str = ""

class AnalyzeResponse(BaseModel):
    clickbait_ratio: float
    status_color: str
    contradiction_summary: str
    needs_report: bool = False

class GenerateReportRequest(BaseModel):
    title: str
    content: str

class GenerateReportResponse(BaseModel):
    contradiction_summary: str

@app.on_event("startup")
async def startup_event():
    global t5_summarizer
    logger.info("Anchor sunucusu baslatiliyor (v3.0.0)...")
    try:
        logger.info("mDeBERTa NLI modeli yukleniyor...")
        nli_engine.load()
        logger.info("T5 Ozetleme modeli yukleniyor...")
        t5_summarizer = pipeline("summarization", model="webis/t5-turkish-summarization", device=-1)
        logger.info("Tum modeller hazir!")
    except Exception as e:
        logger.error(f"Model yukleme sirasinda hata: {e}")

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    logger.info("Aşama 1: Analiz istegi alindi - Haber: %s", request.title)
    
    if not request.title or not request.content:
        return AnalyzeResponse(
            clickbait_ratio=0.0,
            status_color="green",
            contradiction_summary="Başlık veya içerik eksik olduğu için analiz yapılamadı."
        )
        
    try:
        from analyzer.scorer import determine_color
        
        # 1. Sadece NLI Skoru Hesapla
        score_result = nli_engine.calculate_clickbait_score(
            title=request.title,
            content=request.content
        )
        
        ratio = score_result["clickbait_ratio"]
        color = determine_color(ratio)
        
        # 2. Hızlı Yanıt
        if ratio < 0.5:
            return AnalyzeResponse(
                clickbait_ratio=ratio,
                status_color=color,
                contradiction_summary="Başlık içerikle uyumludur.",
                needs_report=False
            )
        else:
            return AnalyzeResponse(
                clickbait_ratio=ratio,
                status_color=color,
                contradiction_summary="Detaylar arka planda analiz ediliyor...",
                needs_report=True
            )
            
    except Exception as e:
        logger.error(f"Analiz sirasinda beklenmeyen hata: {e}")
        return AnalyzeResponse(
            clickbait_ratio=0.0,
            status_color="error",
            contradiction_summary=f"Analiz sırasında bir hata oluştu: {str(e)}"
        )

@app.post("/api/generate_report", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest):
    logger.info("Aşama 2: Rapor üretimi basliyor...")
    
    import re
    def get_alternative_sentence(text: str) -> str:
        sentences = [s.strip() for s in re.split(r'(?<=[a-zğüşöçı])\.\s+', text) if len(s.strip()) > 30]
        if len(sentences) > 1:
            keywords = ["neden", "sebep", "işte", "açıkladı", "göre", "iddia", "gerçek", "detay", "olay", "halde"]
            for s in sentences[1:5]:
                if any(k in s.lower() for k in keywords):
                    return s + "."
            return sentences[1] + "."
        elif len(sentences) == 1:
            return sentences[0] + "."
        return text[:100] + "..."

    fallback_text = get_alternative_sentence(request.content)
    final_text = fallback_text
    
    try:
        if t5_summarizer is not None:
            # 1. İçeriği kes (Max 200 karakter)
            text_to_summarize = request.content[:200]
            
            loop = asyncio.get_running_loop()
            
            # 2. Asenkron Timeout YOK - Güvenli Arka Plan İşlemi
            summary_output = await loop.run_in_executor(
                executor, 
                lambda: t5_summarizer(
                    text_to_summarize, 
                    max_length=12, 
                    min_length=4, 
                    num_beams=1, 
                    early_stopping=True, 
                    do_sample=False
                )
            )
            
            if summary_output and len(summary_output) > 0:
                gen_text = summary_output[0]['summary_text'].strip()
                
                # Aynılık Kontrolü
                w_gen = set(re.findall(r'\w+', gen_text.lower()))
                w_orig = set(re.findall(r'\w+', request.title.lower()))
                
                if w_gen and w_orig:
                    overlap = len(w_gen.intersection(w_orig))
                    similarity = max(overlap / len(w_gen), overlap / len(w_orig))
                    if similarity <= 0.60 and gen_text != request.title:
                        final_text = gen_text
                        
    except Exception as e:
        print(f"--- T5 MODEL HATASI: {str(e)} ---")
        
    summary = f"Başlık abartılı; içerikte aslında şu belirtiliyor: {final_text}"
    
    return GenerateReportResponse(
        contradiction_summary=summary
    )
