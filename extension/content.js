/**
 * Anchor — Content Script
 * YouTube sayfalarında çalışır:
 *  1. Video başlığını ve ID'sini yakalar
 *  2. Background script üzerinden backend'e analiz isteği gönderir
 *  3. Sayfaya Anchor halkası ve hover kartı enjekte eder
 */

(() => {
  "use strict";

  // ── Sabitler ───────────────────────────────────────────────────
  const ANCHOR_ATTR = "data-anchor-processed";
  const DEBOUNCE_MS = 2000;
  const OBSERVER_THROTTLE_MS = 3000;

  // ── Durum ──────────────────────────────────────────────────────
  let lastProcessedUrl = "";
  let processingQueue = new Set();
  let observerTimer = null;

  // ══════════════════════════════════════════════════════════════
  //  YOUTUBE MODÜLÜ
  // ══════════════════════════════════════════════════════════════

  /**
   * YouTube video sayfasından videoId'yi çıkarır.
   */
  function getYouTubeVideoId(url) {
    const urlObj = new URL(url || window.location.href);
    return urlObj.searchParams.get("v");
  }

  /**
   * Video izleme sayfasında başlığı yakalar.
   */
  function getVideoTitle() {
    // Birincil seçici (izleme sayfası)
    const titleEl =
      document.querySelector(
        "h1.ytd-watch-metadata yt-formatted-string"
      ) ||
      document.querySelector("h1.ytd-video-primary-info-renderer") ||
      document.querySelector("#title h1 yt-formatted-string") ||
      document.querySelector("h1.style-scope.ytd-watch-metadata");

    return titleEl ? titleEl.textContent.trim() : null;
  }

  // ══════════════════════════════════════════════════════════════
  //  ANALİZ İSTEĞİ
  // ══════════════════════════════════════════════════════════════

  /**
   * Background script'e analiz isteği gönderir.
   */
  function sendAnalyzeRequest(payload) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: "ANALYZE_REQUEST", payload },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          if (response && response.success) {
            resolve(response.data);
          } else {
            reject(new Error(response?.error || "Bilinmeyen hata"));
          }
        }
      );
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  UI ENJEKSİYONU — Anchor Halkası
  // ══════════════════════════════════════════════════════════════

  /**
   * Bir DOM elementine Anchor halkası ekler.
   */
  function injectAnchorRing(targetEl, status = "loading") {
    // Zaten eklenmiş mi?
    if (targetEl.querySelector(".anchor-ring-container")) return null;

    const container = document.createElement("div");
    container.className = "anchor-ring-container";
    container.setAttribute("data-status", status);

    // SVG Halka
    container.innerHTML = `
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

    // Tıklanabilir hedef alanı güçlendir
    targetEl.style.position = targetEl.style.position || "relative";
    targetEl.appendChild(container);

    return container;
  }

  /**
   * Anchor halkasını günceller (renk + doluluk oranı).
   */
  function updateAnchorRing(container, data) {
    if (!container) return;

    const { clickbait_ratio, status_color } = data;
    container.setAttribute("data-status", status_color);

    // SVG ilerleme çemberini güncelle
    const progressCircle = container.querySelector(".anchor-ring-progress");
    if (progressCircle) {
      const circumference = 2 * Math.PI * 16; // r=16
      const offset = circumference * (1 - clickbait_ratio);
      progressCircle.style.strokeDashoffset = offset;
    }
  }

  // ══════════════════════════════════════════════════════════════
  //  UI ENJEKSİYONU — Hover Kartı
  // ══════════════════════════════════════════════════════════════

  /**
   * Anchor halkasına hover kartı ekler.
   */
  function attachHoverCard(container, data) {
    if (!container || container.querySelector(".anchor-hover-card")) return;

    const {
      clickbait_ratio,
      status_color,
      honest_title_suggestion,
      contradiction_summary,
      user_sentiment_feedback,
      verified_timestamp,
    } = data;

    const percentText = Math.round(clickbait_ratio * 100);

    const colorLabels = {
      green: "Dürüst İçerik",
      yellow: "Hafif Abartı",
      orange: "Yanıltıcı",
      red: "Clickbait",
    };

    const card = document.createElement("div");
    card.className = "anchor-hover-card";
    card.setAttribute("data-color", status_color);

    card.innerHTML = `
      <div class="anchor-card-header">
        <div class="anchor-card-score" data-color="${status_color}">
          <span class="anchor-score-number">%${percentText}</span>
          <span class="anchor-score-label">${colorLabels[status_color] || "Analiz"}</span>
        </div>
        <div class="anchor-card-badge">⚓ Anchor</div>
      </div>

      <div class="anchor-card-body">
        <div class="anchor-card-section">
          <div class="anchor-card-section-title">💡 Dürüst Başlık Önerisi</div>
          <p class="anchor-card-text anchor-honest-title">"${escapeHtml(honest_title_suggestion)}"</p>
        </div>

        <div class="anchor-card-section">
          <div class="anchor-card-section-title">📋 Çelişki Raporu</div>
          <p class="anchor-card-text">${escapeHtml(contradiction_summary)}</p>
        </div>

        ${
          verified_timestamp
            ? `<div class="anchor-card-section">
                <div class="anchor-card-section-title">⏱️ Doğrulanan Zaman</div>
                <p class="anchor-card-text anchor-timestamp">[${escapeHtml(verified_timestamp)}]</p>
              </div>`
            : ""
        }

        ${
          user_sentiment_feedback
            ? `<div class="anchor-card-section">
                <div class="anchor-card-section-title">💬 Yorum Analizi</div>
                <p class="anchor-card-text">${escapeHtml(user_sentiment_feedback)}</p>
              </div>`
            : ""
        }
      </div>
    `;

    container.appendChild(card);
  }

  /**
   * HTML'de güvenli metin gösterimi.
   */
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  // ══════════════════════════════════════════════════════════════
  //  ANA YOUTUBE İŞ AKIŞI
  // ══════════════════════════════════════════════════════════════

  /**
   * YouTube video sayfasını analiz eder.
   */
  async function processYouTubeWatchPage() {
    const videoId = getYouTubeVideoId();
    if (!videoId) return;

    const currentUrl = window.location.href;
    if (currentUrl === lastProcessedUrl) return;
    if (processingQueue.has(videoId)) return;

    lastProcessedUrl = currentUrl;
    processingQueue.add(videoId);

    const title = getVideoTitle();
    if (!title) {
      processingQueue.delete(videoId);
      return;
    }

    // Halka enjeksiyonu için hedef element
    const titleContainer =
      document.querySelector("#above-the-fold #title") ||
      document.querySelector("h1.ytd-watch-metadata");

    let ringContainer = null;
    if (titleContainer) {
      ringContainer = injectAnchorRing(titleContainer, "loading");
    }

    try {
      // Backend'e analiz isteği gönder
      const payload = {
        platform: "youtube",
        url: `https://www.youtube.com/watch?v=${videoId}`,
        title: title,
        content: [], // Altyazı backend tarafında çekilecek veya content script'ten
        comments: [],
      };

      // Altyazıyı backend'den çekmek yerine, burada boş gönderiyoruz
      // Backend altyazı çekme özelliği ayrıca eklenecek
      // Şimdilik sayfadan altyazı çekmeyi deneyelim
      const transcriptData = await extractYouTubeTranscript(videoId);
      if (transcriptData && transcriptData.length > 0) {
        payload.content = transcriptData;
      }

      // Yorumları çekmeyi dene
      const comments = extractYouTubeComments();
      if (comments.length > 0) {
        payload.comments = comments;
      }

      const result = await sendAnalyzeRequest(payload);

      // UI'ı güncelle
      if (ringContainer) {
        updateAnchorRing(ringContainer, result);
        attachHoverCard(ringContainer, result);
      }
    } catch (err) {
      console.error("[Anchor] Analiz hatası:", err);
      if (ringContainer) {
        ringContainer.setAttribute("data-status", "error");
      }
    } finally {
      processingQueue.delete(videoId);
    }
  }

  /**
   * YouTube altyazı verilerini sayfadan çıkarmaya çalışır.
   * Not: Bu yöntem her zaman çalışmayabilir, backend'de de
   * youtube-transcript-api ile yedek çekim yapılabilir.
   */
  async function extractYouTubeTranscript(videoId) {
    try {
      // Backend'den altyazı çek (youtube-transcript-api kullanarak)
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
          {
            type: "FETCH_TRANSCRIPT",
            videoId: videoId,
          },
          (resp) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
              return;
            }
            resolve(resp);
          }
        );
      });

      if (response && response.success && response.data) {
        return response.data;
      }
    } catch (e) {
      console.warn("[Anchor] Altyazı çekme başarısız:", e);
    }
    return [];
  }

  /**
   * Sayfadaki YouTube yorumlarını çıkarır.
   */
  function extractYouTubeComments() {
    const commentEls = document.querySelectorAll(
      "#content-text.ytd-comment-renderer"
    );
    const comments = [];
    commentEls.forEach((el, i) => {
      if (i < 10) {
        const text = el.textContent.trim();
        if (text) comments.push(text);
      }
    });
    return comments;
  }

  // ══════════════════════════════════════════════════════════════
  //  THUMBNAIL HALKALARI (Ana Sayfa / Arama Sonuçları)
  // ══════════════════════════════════════════════════════════════

  /**
   * YouTube ana sayfasındaki video kartlarına halka ekler.
   * Not: Ana sayfa analizleri daha sınırlıdır (altyazı yok).
   */
  function processYouTubeThumbnails() {
    const thumbnails = document.querySelectorAll(
      "ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer"
    );

    thumbnails.forEach((item) => {
      if (item.hasAttribute(ANCHOR_ATTR)) return;
      item.setAttribute(ANCHOR_ATTR, "true");

      const thumbnailEl = item.querySelector("#thumbnail");
      if (!thumbnailEl) return;

      // Küçük bir halka ekle (henüz analiz edilmemiş durumda)
      const ring = injectAnchorRing(thumbnailEl, "idle");
      if (ring) {
        ring.classList.add("anchor-ring-thumbnail");
      }
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  SAYFA GÖZLEMCİSİ (MutationObserver)
  // ══════════════════════════════════════════════════════════════

  function initObserver() {
    const observer = new MutationObserver(() => {
      // Throttle
      if (observerTimer) return;
      observerTimer = setTimeout(() => {
        observerTimer = null;

        // Sayfa türüne göre işlem
        if (window.location.pathname === "/watch") {
          processYouTubeWatchPage();
        }
        // Ana sayfada thumbnail halkalarını ekle
        processYouTubeThumbnails();
      }, OBSERVER_THROTTLE_MS);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  // ══════════════════════════════════════════════════════════════
  //  BAŞLATMA
  // ══════════════════════════════════════════════════════════════

  function init() {
    console.log("[Anchor] ⚓ Content script yüklendi.");

    // YouTube SPA navigasyonunu dinle
    let currentPath = window.location.href;

    // İlk yükleme
    setTimeout(() => {
      if (window.location.pathname === "/watch") {
        processYouTubeWatchPage();
      }
      processYouTubeThumbnails();
    }, DEBOUNCE_MS);

    // SPA navigasyonu (YouTube History API kullanır)
    const originalPushState = history.pushState;
    history.pushState = function (...args) {
      originalPushState.apply(this, args);
      handleNavigation();
    };

    window.addEventListener("popstate", handleNavigation);

    function handleNavigation() {
      const newUrl = window.location.href;
      if (newUrl !== currentPath) {
        currentPath = newUrl;
        setTimeout(() => {
          if (window.location.pathname === "/watch") {
            processYouTubeWatchPage();
          }
          processYouTubeThumbnails();
        }, DEBOUNCE_MS);
      }
    }

    // DOM değişikliklerini izle
    initObserver();
  }

  // Sayfa hazır olduğunda başlat
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
