#!/usr/bin/env python3
"""Run lightweight YOLO detection and send results via UDP.

Example:
  python3 tonisateliot.py --udp-ip 127.0.0.1 --udp-port 20000 --source 0

Dependencies:
  pip install ultralytics opencv-python-headless
"""

from __future__ import annotations

import argparse
import csv
import socket
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


CSV_PATH = Path(__file__).with_name("yolo_udp_sender_log.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YOLO detection to UDP sender (Raspberry Pi friendly defaults)"
    )
    parser.add_argument("--udp-ip", default="127.0.0.1", help="Destination UDP IP")
    parser.add_argument("--udp-port", type=int, default=20000, help="Destination UDP port")
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLO model path/name (yolov8n.pt is lightweight)",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Video source (0 for camera, RTSP URL, or file path)",
    )
    parser.add_argument("--conf", type=float, default=0.45, help="Confidence threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    parser.add_argument(
        "--cooldown",
        type=float,
        default=10.0,
        help="Minimum seconds between UDP sends",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show preview window with detections (requires GUI)",
    )
    return parser.parse_args()


def open_source(source_value: str) -> cv2.VideoCapture:
    source: int | str
    if source_value.isdigit():
        source = int(source_value)
    else:
        source = source_value
    return cv2.VideoCapture(source)


def build_payload(label: str) -> bytes:
    return label.encode("utf-8")


def append_csv_row(timestamp: str, label: str, udp_ip: str, udp_port: int) -> None:
    file_exists = CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(["timestamp", "label", "udp_ip", "udp_port"])
        writer.writerow([timestamp, label, udp_ip, udp_port])


def main() -> None:
    args = parse_args()

    model = YOLO(args.model)
    names = model.names

    cap = open_source(args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {args.source}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_send_ts = 0.0

    print(
        f"Running detection with model={args.model}, source={args.source}, "
        f"udp={args.udp_ip}:{args.udp_port}"
    )

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Frame read failed, stopping.")
                break

            results = model.predict(frame, imgsz=args.imgsz, conf=args.conf, verbose=False)
            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                confs = boxes.conf.tolist()
                top_idx = max(range(len(confs)), key=lambda i: confs[i])
                class_id = int(boxes.cls[top_idx].item())
                label = names[class_id] if isinstance(names, dict) else names[class_id]

                now = time.time()
                # Rate limit sends so a persistent object does not spam UDP packets.
                if now - last_send_ts >= args.cooldown:
                    message = build_payload(label=label)
                    sock.sendto(message, (args.udp_ip, args.udp_port))
                    last_send_ts = now
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
                    print(f"[{timestamp}] Sent UDP label: {message.decode('utf-8')}")
                    append_csv_row(
                        timestamp=timestamp,
                        label=label,
                        udp_ip=args.udp_ip,
                        udp_port=args.udp_port,
                    )

            if args.show:
                annotated = result.plot()
                cv2.imshow("Pi YOLO UDP Sender", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        cap.release()
        sock.close()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
