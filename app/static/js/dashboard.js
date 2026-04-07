function byId(id) {
  return document.getElementById(id);
}

let hlsInstance = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setListenerPill(listener) {
  const pill = byId("listener-pill");
  pill.classList.remove("ok", "warn", "error");

  if (!listener) {
    pill.textContent = "Listener: Unknown";
    pill.classList.add("warn");
    return;
  }

  if (listener.last_error) {
    pill.textContent = "Listener: Error";
    pill.classList.add("error");
    return;
  }

  if (listener.listening) {
    pill.textContent = "Listener: Active";
    pill.classList.add("ok");
    return;
  }

  pill.textContent = "Listener: Stopped";
  pill.classList.add("warn");
}

function renderLabels(payload) {
  const listener = payload.listener || {};
  const messages = Array.isArray(payload.messages) ? payload.messages : [];

  setListenerPill(listener);
  byId("label-bind").textContent = `${listener.bind_ip || "-"}:${listener.bind_port || "-"}`;
  byId("label-csv-path").textContent = listener.csv_path || "-";

  const tbody = byId("labels-body");
  if (messages.length === 0) {
    tbody.innerHTML = '<tr><td>-</td><td>-</td><td>No labels received</td></tr>';
  } else {
    tbody.innerHTML = messages
      .map((item) => {
        const time = escapeHtml(item.timestamp || "-");
        const sender = `${escapeHtml(item.sender_ip || "-")}:${escapeHtml(item.sender_port || "-")}`;
        const label = escapeHtml(item.label || "");
        return `<tr><td>${time}</td><td>${sender}</td><td>${label || "-"}</td></tr>`;
      })
      .join("");
  }

  byId("labels-meta").textContent = `Received: ${listener.received_count || 0}`;
  byId("labels-updated").textContent = `Last update: ${payload.updated_at || "-"}`;
  byId("labels-error").textContent = listener.last_error || "";
}

async function fetchLabels() {
  try {
    const response = await fetch("/api/labels/recent?limit=20", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    renderLabels(payload);
  } catch (error) {
    setListenerPill(null);
    byId("labels-error").textContent = `Failed to fetch labels: ${error}`;
  }
}

function setVideoSource(url) {
  const videoEl = byId("live-video");
  const sourceUrl = (url || "").trim();

  byId("video-source-input").value = sourceUrl;
  byId("video-url").textContent = sourceUrl || "-";
  byId("video-open-link").href = sourceUrl || "#";

  if (!sourceUrl) {
    byId("video-error").textContent = "Video source URL is empty.";
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    videoEl.removeAttribute("src");
    videoEl.load();
    return;
  }

  localStorage.setItem("dashboard_video_hls_url", sourceUrl);
  byId("video-error").textContent = "";

  if (hlsInstance) {
    hlsInstance.destroy();
    hlsInstance = null;
  }

  if (window.Hls && window.Hls.isSupported()) {
    hlsInstance = new Hls({
      maxBufferLength: 8,
      liveSyncDurationCount: 3,
    });
    hlsInstance.loadSource(sourceUrl);
    hlsInstance.attachMedia(videoEl);
    return;
  }

  if (videoEl.canPlayType("application/vnd.apple.mpegurl")) {
    videoEl.src = sourceUrl;
    return;
  }

  byId("video-error").textContent = "Your browser does not support HLS playback.";
}

function initVideo() {
  const defaultSource = document.body.dataset.videoHlsUrl;
  const savedSource = localStorage.getItem("dashboard_video_hls_url");
  setVideoSource(savedSource || defaultSource);
}

function bootstrap() {
  byId("btn-load-video").addEventListener("click", () => setVideoSource(byId("video-source-input").value));
  initVideo();
  fetchLabels();
  const refreshMs = Number(document.body.dataset.refreshMs || "2000");
  window.setInterval(fetchLabels, Math.max(refreshMs, 1000));
}

window.addEventListener("DOMContentLoaded", bootstrap);
