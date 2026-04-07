# YOLO UDP Sender

Standalone container image for running YOLO detection and sending detected labels over UDP.

This is designed to send labels to the dashboard UDP listener at port `20000`.

## Build Locally

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

## Run Locally (Host Network)

Use host networking so camera and UDP access are simple on Linux.

```bash
docker run --rm -it --network host \
  -e UDP_IP=127.0.0.1 \
  -e UDP_PORT=20000 \
  -e SOURCE=0 \
  -e YOLO_MODEL=yolov8n.pt \
  -e CONF=0.45 \
  -e IMGSZ=640 \
  -e COOLDOWN=10 \
  yolo-udp-sender:local
```

If your source is RTSP, set `SOURCE` to the RTSP URL.

## Environment Variables

- `UDP_IP` (default: `127.0.0.1`)
- `UDP_PORT` (default: `20000`)
- `YOLO_MODEL` (default: `yolov8n.pt`)
- `SOURCE` (default: `0`)
- `CONF` (default: `0.45`)
- `IMGSZ` (default: `640`)
- `COOLDOWN` (default: `10.0`)
- `SHOW` (default: `0`)

## Publish Public Image to GitHub Container Registry (Free)

This repository includes a GitHub Actions workflow that publishes:

- `ghcr.io/<your-github-username>/yolo-udp-sender:latest`
- `ghcr.io/<your-github-username>/yolo-udp-sender:<git-tag>`

Published images support:

- `linux/amd64`
- `linux/arm64` (Raspberry Pi 64-bit OS)

Steps:

1. Push this repository to your GitHub account.
2. In GitHub, make the repository public.
3. Create a tag and push it:

```bash
git tag yolo-v1.0.0
git push origin yolo-v1.0.0
```

After workflow success, the image can be pulled by anyone:

```bash
docker pull ghcr.io/<your-github-username>/yolo-udp-sender:latest
```
