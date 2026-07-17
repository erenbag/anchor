"""
Anchor — NLI (Natural Language Inference) Motoru
mDeBERTa-v3-base modeli ile Başlık–İçerik çelişki analizi.
"""
import logging
from transformers import pipeline

from config import NLI_MODEL_NAME

logger = logging.getLogger(__name__)


class NLIEngine:
    """
    Hugging Face zero-shot NLI pipeline wrapper.
    Başlık (hypothesis) ile içerik (premise) arasındaki
    entailment / contradiction / neutral oranlarını döndürür.
    """

    def __init__(self):
        self._pipe = None

    # ── Lazy Loading ──────────────────────────────────────────────
    def load(self):
        """Modeli ilk istek geldiğinde yükler (lazy init)."""
        if self._pipe is not None:
            return
        logger.info("NLI modeli yükleniyor: %s …", NLI_MODEL_NAME)
        self._pipe = pipeline(
            "zero-shot-classification",
            model=NLI_MODEL_NAME,
            device=-1,  # CPU (-1); GPU varsa 0
        )
        logger.info("NLI modeli hazır.")

    # ── Tekil Analiz ──────────────────────────────────────────────
    def analyze(self, premise: str, hypothesis: str) -> dict:
        """
        Tek bir premise–hypothesis çifti için NLI skoru döndürür.

        Returns:
            {
                "entailment": float,   # Uyumluluk olasılığı
                "contradiction": float, # Çelişki olasılığı
                "neutral": float        # Nötr olasılık
            }
        """
        self.load()

        # zero-shot-classification pipeline'ı candidate_labels kullanır.
        # Biz NLI skorlarını almak için hypothesis'i label olarak verip
        # premise'i sequence olarak besliyoruz.
        result = self._pipe(
            sequences=premise,
            candidate_labels=["entailment", "contradiction", "neutral"],
            hypothesis_template=hypothesis + " {}",
            multi_label=True,
        )

        scores = {}
        for label, score in zip(result["labels"], result["scores"]):
            scores[label] = round(score, 4)

        return scores

    # ── Doğrudan NLI (Premise ↔ Hypothesis) ──────────────────────
    def analyze_nli(self, premise: str, hypothesis: str) -> dict:
        """
        Gerçek NLI analizi: premise (içerik) ve hypothesis (başlık)
        arasındaki çelişki oranını hesaplar.

        Bu metod, zero-shot-classification yerine doğrudan NLI mantığı
        kullanarak daha doğru sonuç verir.

        Returns:
            {
                "contradiction_score": float,  # 0.0 – 1.0
                "entailment_score": float,
                "neutral_score": float
            }
        """
        self.load()

        # Pipeline'ı NLI tarzında kullanıyoruz:
        # candidate_labels olarak başlığı veriyoruz,
        # bu sayede model başlık ile içerik arasındaki ilişkiyi değerlendirir.
        result = self._pipe(
            sequences=premise[:500],  # Modelin çok hızlı (0.1s) dönmesi için 2048 yerine ilk 500 karakterle sınırla
            candidate_labels=[hypothesis],
            multi_label=False,
        )

        # zero-shot-classification skoru → entailment oranı
        entailment_score = result["scores"][0]
        contradiction_score = 1.0 - entailment_score

        return {
            "contradiction_score": round(contradiction_score, 4),
            "entailment_score": round(entailment_score, 4),
        }

    # ── Batch Analiz (Segmentler İçin) ────────────────────────────
    def analyze_batch(
        self, segments: list[dict], hypothesis: str
    ) -> list[dict]:
        """
        Birden fazla segment'i başlıkla karşılaştırır.

        Args:
            segments: [{"text": str, "start": float, "end": float}, ...]
            hypothesis: Videonun/haberin başlığı

        Returns:
            [
                {
                    "start": float,
                    "end": float,
                    "contradiction_score": float,
                    "entailment_score": float,
                },
                ...
            ]
        """
        self.load()
        results = []

        for seg in segments:
            nli_result = self.analyze_nli(
                premise=seg["text"],
                hypothesis=hypothesis,
            )
            results.append(
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "contradiction_score": nli_result["contradiction_score"],
                    "entailment_score": nli_result["entailment_score"],
                }
            )

        return results

    def calculate_clickbait_score(self, title: str, content: str) -> dict:
        """
        Sadece haberler için: Başlık ve içerik arasındaki çelişkiyi (clickbait oranı) hesaplar.
        """
        nli_result = self.analyze_nli(premise=content, hypothesis=title)
        ratio = nli_result["contradiction_score"]
        
        # Basit özet
        if ratio > 0.6:
            summary = "Haberin başlığı ile içeriği büyük ölçüde çelişiyor. (Clickbait ihtimali çok yüksek)"
        elif ratio > 0.3:
            summary = "Haberin başlığında içerikte bulunmayan abartılı ifadeler olabilir."
        else:
            summary = "Başlık içerikle uyumlu, yanıltıcı bir durum tespit edilmedi."
            
        return {
            "clickbait_ratio": ratio,
            "contradiction_summary": summary
        }


# Singleton instance
nli_engine = NLIEngine()
