# AI Target Detection (Sender Only)

This repository now contains only the YOLO sender workload that runs on the Jetson node.

The sender container does all of the following:

- Reads camera/video input.
- Runs YOLO object detection.
- Publishes annotated stream to MediaMTX (RTSP).
- Sends detection messages over UDP as JSON payloads.

The web dashboard is intentionally separated into another repository/folder and is not part of this codebase.

## Folder Layout

- `yolo-udp-sender/`: Sender source, Dockerfile, entrypoint.
- `.github/workflows/publish-yolo-udp-sender.yml`: GHCR publishing workflow.
- `docker-compose.yml`: Local sender-only compose definition.

## Detection Payload Format (UDP)

Each UDP message is JSON and includes metadata required for downstream dashboards:

```json
{
  "timestamp": "2026-04-27T18:31:11Z",
  "label": "person",
  "confidence": 0.8723,
  "count": 2,
  "source": "/dev/video0",
  "rtsp_url": "rtsp://100.117.91.117:8554/livecam",
  "udp_target": "100.117.91.117:20000"
}
```

## Build and Run (Jetson)

### Docker build

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

### Docker run

```bash
docker run --rm -it --network host --privileged \
  --device /dev:/dev \
  -e PORTAL_HOST=100.117.91.117 \
  -e UDP_PORT=20000 \
  -e SOURCE=/dev/video0 \
  -e YOLO_MODEL=yolov8n.pt \
  -e CONF=0.45 \
  -e IMGSZ=640 \
  -e COOLDOWN=1.5 \
  -e STREAM_FPS=20 \
  -e HEALTH_PORT=8080 \
  yolo-udp-sender:local
```

## Sender-only Compose

```bash
cp .env.example .env
docker compose up -d --build
```

## GHCR Publishing

Tag and push using the sender workflow trigger pattern:

```bash
git tag yolo-v1.0.0
git push origin yolo-v1.0.0
```

Published image target:

- `ghcr.io/<github-owner>/yolo-udp-sender:latest`

## Runtime Notes

- Use Tailscale IPs for `PORTAL_HOST` so sender traffic goes over the tailnet.
- Default RTSP path is `livecam`.
- MediaMTX should run on the portal machine hosting AMS.
