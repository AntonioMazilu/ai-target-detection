# YOLO Stream + UDP Sender

Standalone container image for Jetson/Raspberry Pi nodes.

The sender does two things at the same time:

- Runs YOLOv8 detection.
- Sends text detections over UDP (for the dashboard labels table).
- Publishes annotated video as RTSP to MediaMTX.

## Build Locally

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

## Run Locally (Host Network)

Use host networking so camera, UDP and RTSP routing are straightforward on Linux.

```bash
docker run --rm -it --network host \
  -e PORTAL_HOST=127.0.0.1 \
  -e UDP_PORT=20000 \
  -e SOURCE=0 \
  -e YOLO_MODEL=yolov8n.pt \
  -e CONF=0.45 \
  -e IMGSZ=640 \
  -e COOLDOWN=2 \
  -e STREAM_FPS=20 \
  yolo-udp-sender:local
```

For a remote portal host, set `PORTAL_HOST`.
Example: `PORTAL_HOST=100.104.203.108`

When `PORTAL_HOST` is set, the entrypoint auto-configures both targets:

- RTSP video target: `rtsp://PORTAL_HOST:8554/livecam`
- UDP text target: `PORTAL_HOST:20000`

You can still override either target explicitly with `MEDIA_MTX_RTSP_URL` and `UDP_IP`.

## Environment Variables

- `PORTAL_HOST` (optional; default source host for both UDP and RTSP targets)
- `UDP_IP` (default: `127.0.0.1`)
- `UDP_PORT` (default: `20000`)
- `MEDIA_MTX_RTSP_URL` (default: `rtsp://127.0.0.1:8554/livecam`)
- `RTSP_TRANSPORT` (default: `tcp`, values: `tcp|udp`)
- `YOLO_MODEL` (default: `yolov8n.pt`)
- `SOURCE` (default: `0`)
- `CONF` (default: `0.45`)
- `IMGSZ` (default: `640`)
- `COOLDOWN` (default: `10.0`)
- `STREAM_FPS` (default: `20`)
- `STREAM_WIDTH` (default: `0`, keep source width)
- `STREAM_HEIGHT` (default: `0`, keep source height)
- `LOG_CSV_PATH` (default: `/app/yolo_stream_sender_log.csv`)
- `HEALTH_PORT` (default: `8080`, set `0` to disable)
- `SHOW` (default: `0`)

## Publish Public Image to GitHub Container Registry

This repository includes a GitHub Actions workflow that publishes:

- `ghcr.io/<your-github-username>/yolo-udp-sender:latest`
- `ghcr.io/<your-github-username>/yolo-udp-sender:<git-tag>`

Published images support:

- `linux/amd64`
- `linux/arm64`
