/**
 * Anchor — Popup Script
 * Uzantı popup'ının logic'i: backend durumu, aktif sayfa bilgisi.
 */

document.addEventListener("DOMContentLoaded", async () => {
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const pageUrl = document.getElementById("pageUrl");
  const popupVersion = document.getElementById("popupVersion");

  // Dinamik Versiyon Numarası
  if (popupVersion && chrome.runtime.getManifest) {
    const manifest = chrome.runtime.getManifest();
    if (manifest && manifest.version) {
      popupVersion.textContent = "v" + manifest.version;
    }
  }

  // ── Backend Sağlık Kontrolü ────────────────────────────────────
  try {
    const response = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: "HEALTH_CHECK" }, (resp) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(resp);
      });
    });

    if (response && response.success) {
      statusDot.classList.add("online");
      statusText.textContent = "Backend sunucusu aktif ✓";
    } else {
      statusDot.classList.add("offline");
      statusText.textContent = "Backend sunucusu yanıt vermiyor";
    }
  } catch (err) {
    console.error("[Anchor UI Error] Popup backend kontrolü:", err);
    statusDot.classList.add("offline");
    statusText.textContent = "Backend'e bağlanılamadı";
  }

  // ── Aktif Sekme Bilgisi ────────────────────────────────────────
  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    if (tab && tab.url) {
      const url = new URL(tab.url);
      pageUrl.textContent = url.hostname + url.pathname.slice(0, 40);

      if (url.hostname.includes("youtube.com")) {
        pageUrl.textContent = "▶ YouTube" + (url.searchParams.get("v") ? " — Video Sayfası" : "");
      }
    }
  } catch (err) {
    pageUrl.textContent = "Sayfa bilgisi alınamadı";
  }
});
