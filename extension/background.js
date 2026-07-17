/**
 * Anchor — Background Service Worker (News Only)
 * Frontend (content.js) ile Backend arasındaki köprü.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "ANALYZE_REQUEST") {
    fetch("http://127.0.0.1:8000/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
    .then(response => response.json())
    .then(data => sendResponse({ success: true, data: data }))
    .catch(err => sendResponse({ success: false, error: err.toString(), offline: true }));
    return true; // Asenkron fetch için zorunlu
  } 
  
  else if (request.type === "GENERATE_REPORT_REQUEST") {
    fetch("http://127.0.0.1:8000/api/generate_report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
    .then(response => response.json())
    .then(data => sendResponse({ success: true, data: data }))
    .catch(err => sendResponse({ success: false, error: err.toString(), offline: true }));
    return true;
  }
  
  // Popup'tan gelebilecek diğer sağlık kontrolü veya durum istekleri için fallback
  else {
    sendResponse({ success: true, status: "ready", message: "Background service worker aktif." });
    return false;
  }
});
