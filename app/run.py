import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from udp_label_listener import UdpLabelListener


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app() -> Flask:
    app = Flask(__name__)

    label_listener = UdpLabelListener(
        bind_ip=os.getenv("UDP_LABEL_BIND_IP", "0.0.0.0"),
        bind_port=int(os.getenv("UDP_LABEL_BIND_PORT", "20000")),
        buffer_size=int(os.getenv("UDP_LABEL_BUFFER_SIZE", "4096")),
        csv_path=os.getenv("UDP_LABEL_CSV_PATH", "/app/udp_listener_log.csv"),
        max_recent=int(os.getenv("UDP_LABEL_MAX_RECENT", "120")),
    )

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            video_hls_url=os.getenv("VIDEO_HLS_URL", "http://localhost:8888/livecam/index.m3u8"),
            refresh_ms=int(os.getenv("DASHBOARD_REFRESH_MS", "2000")),
        )

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/labels/recent")
    def labels_recent():
        limit = request.args.get("limit", default=25, type=int)
        status = label_listener.get_status()
        messages = label_listener.get_recent(limit=limit)
        return jsonify(
            {
                "updated_at": utc_now_iso(),
                "listener": status,
                "messages": messages,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
