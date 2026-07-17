/**
 * Anchor — Content Script (News Only)
 *
 * Sadece haber sitelerinde çalışır. Başlık ve içeriği analiz edip
 * sağ alt köşeye Anchor analiz butonunu enjekte eder.
 */

(() => {
  "use strict";

  const DEBOUNCE_MS = 1500;
  let observerTimer = null;

  // ══════════════════════════════════════════════════════════════
  //  PLATFORM ALGILAMA
  // ══════════════════════════════════════════════════════════════

  function detectPlatform() {
    const hostname = window.location.hostname.toLowerCase();
    if (
      hostname.startsWith("chrome") ||
      hostname.startsWith("about") ||
      hostname.startsWith("extension") ||
      hostname === "newtab" ||
      window.location.protocol === "chrome-extension:" ||
      window.location.protocol === "chrome:"
    ) {
      return null;
    }
    
    // Hata 2: Anasayfada çalışmasını engelle (Sadece detay/alt sayfalarda çalışsın)
    const path = window.location.pathname;
    if (path === "/" || path === "/index.html" || path.length <= 5) {
      return null;
    }

    // YouTube dahil her yeri artık detay sayfasıysa haber sitesi gibi varsayıyoruz
    return "news";
  }

  // ══════════════════════════════════════════════════════════════
  //  HABER İÇERİĞİ ÇIKARMA
  // ══════════════════════════════════════════════════════════════

  function extractNewsContent() {
    let title = "";
    const titleEl = document.querySelector("h1, .news-title, .article-title, .news-detail-title, .entry-title");
    if (titleEl) title = titleEl.textContent.trim();
    if (!title) title = document.title;
    if (!title || title.length < 10) return null;

    const selectors = [
      "article p", ".news-content p", ".article-body p", ".article-detail p",
      "[role='main'] p", "main p", ".post-content p",
      ".article-content p", ".entry-content p",
      ".story-body p", ".content-body p",
      ".text-content p", ".article__body p", ".article-text p",
    ];
    
    // Hata 1: Çöp içerikleri temizlemek için yardımcı fonksiyon
    function isBadElement(el) {
      if (!el) return false;
      const badSelectors = [
        "iframe", ".video-js", ".modal", ".ad-container", ".reklam", 
        "script", "style", "#cookie-consent", ".ad", ".advertisement"
      ];
      try {
        return badSelectors.some(sel => el.closest(sel) !== null);
      } catch(e) { return false; }
    }

    let body = "";
    const art = document.querySelector("article");
    if (art) {
      art.querySelectorAll("p").forEach((p) => {
        if (isBadElement(p)) return;
        const t = p.textContent.trim();
        if (t.length > 20) body += t + " ";
      });
    }
    
    if (body.length < 100) {
      for (const s of selectors) {
        document.querySelectorAll(s).forEach((el) => {
          if (isBadElement(el)) return;
          const t = el.textContent.trim();
          if (t.length > 20) body += t + " ";
        });
        if (body.length >= 100) break;
      }
    }
    
    if (body.length < 100) {
      document.querySelectorAll("p").forEach((p) => {
        if (isBadElement(p)) return;
        const t = p.textContent.trim();
        if (t.length > 30) body += t + " ";
      });
    }
    
    body = body.trim();
    if (body.length < 200) return null;
    
    return { title, content: body.slice(0, 5000) };
  }

  // ══════════════════════════════════════════════════════════════
  //  ANALİZ İSTEĞİ (BACKGROUND.JS'E İLETİR)
  // ══════════════════════════════════════════════════════════════

  function sendAnalyzeRequest(payload) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: "ANALYZE_REQUEST", payload },
        (response) => {
          if (chrome.runtime.lastError) {
            reject({ message: chrome.runtime.lastError.message, offline: true });
            return;
          }
          if (response && response.success) {
            resolve(response.data);
          } else {
            reject({
              message: response?.error || "Bilinmeyen hata",
              offline: response?.offline || false,
            });
          }
        }
      );
    });
  }

  function sendGenerateReportRequest(payload) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: "GENERATE_REPORT_REQUEST", payload },
        (response) => {
          if (chrome.runtime.lastError) {
            reject({ message: chrome.runtime.lastError.message, offline: true });
            return;
          }
          if (response && response.success) {
            resolve(response.data);
          } else {
            reject({
              message: response?.error || "Bilinmeyen hata",
              offline: response?.offline || false,
            });
          }
        }
      );
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  UI ENJEKSİYONU
  // ══════════════════════════════════════════════════════════════

  function createRingSVG() {
    return `
      <svg class="anchor-ring-svg" viewBox="0 0 40 40">
        <circle class="anchor-ring-bg" cx="20" cy="20" r="16"
                fill="none" stroke-width="3" />
        <circle class="anchor-ring-progress" cx="20" cy="20" r="16"
                fill="none" stroke-width="3"
                stroke-dasharray="100.53"
                stroke-dashoffset="100.53" />
      </svg>
      <div class="anchor-ring-icon">⚓</div>
    `;
  }

  function injectFixedRing(status = "loading") {
    const existing = document.querySelector(".anchor-fixed-ring");
    if (existing) return existing;
    const container = document.createElement("div");
    container.className = "anchor-ring-container anchor-fixed-ring";
    container.setAttribute("data-status", status);
    container.innerHTML = createRingSVG();
    document.body.appendChild(container);
    return container;
  }

  function updateAnchorRing(container, data) {
    if (!container) return;
    const clickbait_ratio = data?.clickbait_ratio || 0;
    const status_color = data?.status_color || "green";
    
    container.setAttribute("data-status", status_color);
    const p = container.querySelector(".anchor-ring-progress");
    if (p) {
      const c = 2 * Math.PI * 16;
      p.style.strokeDasharray = `${c}`;
      p.style.strokeDashoffset = `${c * (1 - clickbait_ratio)}`;
    }
  }

  function attachHoverCard(container, data) {
    if (!container || container.querySelector(".anchor-hover-card")) return;
    
    const clickbait_ratio = data?.clickbait_ratio || 0;
    const status_color = data?.status_color || "green";
    const contradiction_summary = data?.contradiction_summary || "Veri bulunamadı.";

    const pct = Math.round(clickbait_ratio * 100);
    const labels = {
      green: "Dürüst İçerik", yellow: "Hafif Abartı",
      orange: "Yanıltıcı", red: "Clickbait",
    };
    
    let reportClass = data?.needs_report ? "skeleton-text" : "";
    let reportText = data?.needs_report ? "Yapay zeka analiz ediyor..." : esc(contradiction_summary);
    
    const card = document.createElement("div");
    card.className = "anchor-hover-card";
    card.setAttribute("data-color", status_color);
    
    card.innerHTML = `
      <div class="anchor-card-header">
        <div class="anchor-card-score" data-color="${status_color}">
          <span class="anchor-score-number">%${pct}</span>
          <span class="anchor-score-label">${labels[status_color] || "Analiz"}</span>
        </div>
        <div class="anchor-card-badge">⚓ Anchor</div>
      </div>
      <div class="anchor-card-body">
        <div class="anchor-card-section">
          <div class="anchor-card-section-title">📋 Çelişki Raporu</div>
          <p class="anchor-card-text anchor-report-text ${reportClass}">${reportText}</p>
        </div>
      </div>
    `;
    container.appendChild(card);
  }

  function attachOfflineCard(container, errorObj) {
    if (!container || container.querySelector(".anchor-hover-card")) return;
    container.setAttribute("data-status", "offline");
    
    const errorMsg = errorObj ? (typeof errorObj === "string" ? errorObj : JSON.stringify(errorObj)) : "Bilinmeyen Hata";
    
    const card = document.createElement("div");
    card.className = "anchor-hover-card";
    card.setAttribute("data-color", "offline");
    card.innerHTML = `
      <div class="anchor-card-header">
        <div class="anchor-card-score" data-color="offline">
          <span class="anchor-score-number">—</span>
          <span class="anchor-score-label">Çevrimdışı</span>
        </div>
        <div class="anchor-card-badge">⚓ Anchor</div>
      </div>
      <div class="anchor-card-body">
        <div class="anchor-card-section">
          <p class="anchor-offline-warning">
            ⚠️ Yerel sunucu aktif değil. Analiz yapılamadı.<br><br>
            <span style="font-size:10px; color:#999; word-wrap: break-word;">Detay: ${esc(errorMsg)}</span>
          </p>
        </div>
      </div>
    `;
    container.appendChild(card);
  }

  function updateHoverCardWithReport(container, reportResult) {
    if (!container) return;
    
    const reportEl = container.querySelector(".anchor-report-text");
    if (reportEl) {
      reportEl.classList.remove("skeleton-text");
      reportEl.classList.add("fade-in-text");
      reportEl.innerHTML = esc(reportResult.contradiction_summary);
    }
  }

  function esc(text) {
    const d = document.createElement("div");
    d.textContent = text || "";
    return d.innerHTML;
  }

  // ══════════════════════════════════════════════════════════════
  //  HABER SİTESİ ANA İŞ AKIŞI
  // ══════════════════════════════════════════════════════════════

  async function processNewsPage() {
    const data = extractNewsContent();
    if (!data) return;

    // Anchor halkasını ekrana sabitle
    const ring = injectFixedRing("loading");

    try {
      const payload = {
        platform: "news",
        url: window.location.href,
        title: data.title,
        content: data.content,
      };

      const result = await sendAnalyzeRequest(payload);
      
      updateAnchorRing(ring, result);
      attachHoverCard(ring, result);
      
      // Aşama 2: T5'i tetikle ve Skeleton'ı doldur
      if (result.needs_report) {
        sendGenerateReportRequest({ title: payload.title, content: payload.content })
          .then((reportResult) => {
            updateHoverCardWithReport(ring, reportResult);
          })
          .catch((err) => {
            console.error("[Anchor UI Error] T5 Lazy Loading hatası:", err);
            updateHoverCardWithReport(ring, {
              contradiction_summary: "Arka plan analizi başarısız oldu."
            });
          });
      }
      
    } catch (err) {
      console.error("[Anchor UI Error] Haber analizi hatası:", JSON.stringify(err));
      if (err.offline && !String(err.message).includes("JSON")) {
        attachOfflineCard(ring, err);
      } else {
        ring.setAttribute("data-status", "error");
      }
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  INIT & MUTATION OBSERVER
  // ══════════════════════════════════════════════════════════════

  function run() {
    const p = detectPlatform();
    if (!p) return;

    // Herhangi bir DOM değişiminde haberi tekrar tara
    const observer = new MutationObserver(() => {
      clearTimeout(observerTimer);
      observerTimer = setTimeout(() => {
        if (!document.querySelector(".anchor-fixed-ring")) {
          processNewsPage();
        }
      }, DEBOUNCE_MS);
    });

    observer.observe(document.body, { childList: true, subtree: true });
    
    // İlk tarama
    setTimeout(processNewsPage, 1000);
  }

  // Sadece tam yüklendiğinde çalış
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }

})();
