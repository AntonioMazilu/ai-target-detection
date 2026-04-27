#!/usr/bin/env python3
"""Run YOLO inference, push annotated frames to MediaMTX RTSP, and send UDP labels."""

from __future__ import annotations

import argparse
import csv
import http.server
import json
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YOLO sender: RTSP stream publisher + UDP text detections"
    )
    parser.add_argument("--udp-ip", default="127.0.0.1", help="Destination UDP IP")
    parser.add_argument("--udp-port", type=int, default=20000, help="Destination UDP port")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model path or name")
    parser.add_argument(
        "--source",
        default="0",
        help="Video source: camera index, file path, or RTSP/HTTP URL",
    )
    parser.add_argument("--conf", type=float, default=0.45, help="Detection confidence threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    parser.add_argument(
        "--cooldown",
        type=float,
        default=10.0,
        help="Minimum seconds between UDP messages",
    )
    parser.add_argument(
        "--rtsp-url",
        default="rtsp://127.0.0.1:8554/livecam",
        help="MediaMTX RTSP publish URL",
    )
    parser.add_argument(
        "--rtsp-transport",
        default="tcp",
        choices=["tcp", "udp"],
        help="RTSP transport for publishing",
    )
    parser.add_argument(
        "--stream-fps",
        type=float,
        default=20.0,
        help="Outgoing stream frame rate",
    )
    parser.add_argument(
        "--stream-width",
        type=int,
        default=0,
        help="Outgoing stream width (0 keeps source width)",
    )
    parser.add_argument(
        "--stream-height",
        type=int,
        default=0,
        help="Outgoing stream height (0 keeps source height)",
    )
    parser.add_argument(
        "--log-csv",
        default="/app/yolo_stream_sender_log.csv",
        help="CSV path for sent detection messages",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show local preview window (requires a GUI)",
    )
    parser.add_argument(
        "--health-port",
        type=int,
        default=8080,
        help="HTTP health endpoint port (0 disables)",
    )
    return parser.parse_args()


def parse_source(source_value: str):
    if source_value.isdigit():
        return int(source_value)
    return source_value


def append_csv_row(csv_path: Path, timestamp: str, label: str, udp_ip: str, udp_port: int) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(["timestamp", "label", "udp_ip", "udp_port"])
        writer.writerow([timestamp, label, udp_ip, udp_port])


def best_detection(result, names) -> Optional[Tuple[str, float, int]]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return None

    confidences = boxes.conf.tolist()
    top_idx = max(range(len(confidences)), key=lambda idx: confidences[idx])
    class_id = int(boxes.cls[top_idx].item())
    class_name = names[class_id] if isinstance(names, dict) else names[class_id]
    return str(class_name), float(confidences[top_idx]), len(confidences)


def build_detection_payload(
    *,
    label: str,
    confidence: float,
    count: int,
    source: str,
    rtsp_url: str,
    udp_ip: str,
    udp_port: int,
    timestamp: float,
) -> str:
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
        "label": label,
        "confidence": round(confidence, 4),
        "count": int(count),
        "source": source,
        "rtsp_url": rtsp_url,
        "udp_target": f"{udp_ip}:{udp_port}",
    }
    return json.dumps(payload, separators=(",", ":"))


class RtspPublisher:
    def __init__(self, rtsp_url: str, transport: str, fps: float) -> None:
        self.rtsp_url = rtsp_url
        self.transport = transport
        self.fps = max(fps, 1.0)
        self._proc: Optional[subprocess.Popen] = None
        self._size: Optional[Tuple[int, int]] = None

    def _start(self, width: int, height: int) -> None:
        self.stop()
        command = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            f"{self.fps}",
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "rtsp",
            "-rtsp_transport",
            self.transport,
            self.rtsp_url,
        ]

        self._proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._size = (width, height)

    def publish(self, frame) -> None:
        height, width = frame.shape[:2]
        current_size = (width, height)

        if self._proc is None or self._proc.poll() is not None or self._size != current_size:
            self._start(width=width, height=height)

        assert self._proc is not None and self._proc.stdin is not None

        try:
            self._proc.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError):
            self._start(width=width, height=height)
            if self._proc is not None and self._proc.stdin is not None:
                self._proc.stdin.write(frame.tobytes())

    def stop(self) -> None:
        if self._proc is None:
            return

        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except Exception:
            pass

        try:
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass

        self._proc = None
        self._size = None


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/health", "/api/health"):
            self.send_response(404)
            self.end_headers()
            return

        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        return


def start_health_server(port: int) -> Optional[socketserver.TCPServer]:
    if port <= 0:
        return None

    server = socketserver.TCPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    args = parse_args()
    csv_path = Path(args.log_csv)

    model = YOLO(args.model)
    names = model.names

    cap = cv2.VideoCapture(parse_source(args.source))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    publisher = RtspPublisher(rtsp_url=args.rtsp_url, transport=args.rtsp_transport, fps=args.stream_fps)
    health_server = start_health_server(args.health_port)

    stream_width = args.stream_width
    stream_height = args.stream_height
    last_sent_at = 0.0
    consecutive_read_errors = 0

    print(
        "Starting sender with "
        f"model={args.model}, source={args.source}, rtsp={args.rtsp_url}, "
        f"udp={args.udp_ip}:{args.udp_port}"
    )

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                consecutive_read_errors += 1
                if consecutive_read_errors > 120:
                    print("Video source read failed repeatedly, stopping.")
                    break
                time.sleep(0.05)
                continue

            consecutive_read_errors = 0

            results = model.predict(frame, imgsz=args.imgsz, conf=args.conf, verbose=False)
            result = results[0]
            annotated = result.plot()

            detection = best_detection(result=result, names=names)
            if detection is not None:
                label, confidence, count = detection
                now = time.time()
                if now - last_sent_at >= args.cooldown:
                    message_text = build_detection_payload(
                        label=label,
                        confidence=confidence,
                        count=count,
                        source=str(args.source),
                        rtsp_url=args.rtsp_url,
                        udp_ip=args.udp_ip,
                        udp_port=args.udp_port,
                        timestamp=now,
                    )
                    udp_socket.sendto(message_text.encode("utf-8"), (args.udp_ip, args.udp_port))

                    log_label = f"{label} conf={confidence:.2f} count={count}"

                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
                    append_csv_row(
                        csv_path=csv_path,
                        timestamp=timestamp,
                        label=log_label,
                        udp_ip=args.udp_ip,
                        udp_port=args.udp_port,
                    )
                    print(f"[{timestamp}] Sent detection payload: {message_text}")
                    last_sent_at = now

            out_frame = annotated
            if stream_width > 0 and stream_height > 0:
                out_frame = cv2.resize(annotated, (stream_width, stream_height))

            publisher.publish(out_frame)

            if args.show:
                cv2.imshow("YOLO Stream Sender", out_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        udp_socket.close()
        publisher.stop()
        if health_server is not None:
            health_server.shutdown()
            health_server.server_close()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)