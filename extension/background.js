/**
 * Anchor — Background Service Worker
 * Content script ile FastAPI backend arasındaki köprü.
 * Manifest V3 service worker olarak çalışır.
 */

const API_BASE = "http://localhost:8000";

// ── Content Script'ten Gelen Mesajları Dinle ─────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_REQUEST") {
    handleAnalyzeRequest(message.payload)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((err) =>
        sendResponse({ success: false, error: err.message || String(err) })
      );
    // async yanıt için true dön
    return true;
  }

  if (message.type === "HEALTH_CHECK") {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) =>
        sendResponse({ success: false, error: "Backend sunucusu çalışmıyor." })
      );
    return true;
  }

  if (message.type === "FETCH_TRANSCRIPT") {
    fetch(`${API_BASE}/api/transcript/${message.videoId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          sendResponse({ success: true, data: data.data });
        } else {
          sendResponse({ success: false, data: [], error: data.error });
        }
      })
      .catch((err) =>
        sendResponse({ success: false, data: [], error: err.message })
      );
    return true;
  }
});

// ── Analiz İsteğini Backend'e Gönder ─────────────────────────────
async function handleAnalyzeRequest(payload) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Backend hatası (${response.status}): ${errorText}`);
  }

  return await response.json();
}
