# AI Target Detection Stack

Dockerized pipeline for:

- YOLOv8 detection on a Jetson node.
- Annotated video stream publishing to MediaMTX (RTSP -> HLS).
- UDP text detection messages to a dashboard.
- Web dashboard that displays both video and detection text.

## Components

- `app/`: Flask dashboard (video + detection text table).
- `yolo-udp-sender/`: Jetson-side YOLO sender image.
- `docker-compose.yml`: Dashboard container for the portal machine.

## Architecture

1. Jetson sender container reads camera/video input.
2. Sender runs YOLO and publishes annotated stream to MediaMTX:
   - `rtsp://<portal-host>:8554/livecam`
3. MediaMTX exposes HLS playback:
   - `http://<portal-host>:8888/livecam/index.m3u8`
4. Sender also sends text labels over UDP to dashboard listener:
   - `<portal-host>:20000/udp`
5. Dashboard shows live HLS video and received labels.

## Dashboard Quick Start (Portal Machine)

1. Create env file:

```bash
cp .env.example .env
```

2. Start dashboard container:

```bash
docker compose up -d --build
```

3. Open:

- Dashboard: `http://localhost:200`

## MediaMTX (Portal Machine)

Run MediaMTX as Docker:

```bash
docker run -d --name mediamtx --restart unless-stopped \
  -p 1935:1935 -p 8554:8554 -p 8888:8888 -p 8889:8889 -p 8890:8890/udp \
  bluenviron/mediamtx:latest
```

## Jetson Sender Container

Build locally:

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

Run on Jetson:

```bash
docker run --rm -it --network host \
  -e PORTAL_HOST=<portal-tailscale-ip> \
  -e UDP_PORT=20000 \
  -e SOURCE=0 \
  -e YOLO_MODEL=yolov8n.pt \
  -e CONF=0.45 \
  -e IMGSZ=640 \
  -e COOLDOWN=2 \
  -e STREAM_FPS=20 \
  -e HEALTH_PORT=8080 \
  yolo-udp-sender:local
```

If using Tailscale, set `PORTAL_HOST` to the portal Tailscale IP.
The sender then auto-targets both endpoints on that host:

- RTSP publish: `rtsp://PORTAL_HOST:8554/livecam`
- UDP labels: `PORTAL_HOST:20000`

### AMS App Fields (Jetson Sender)

When creating the sender application in AMS, use:

- Docker image: your pushed sender image.
- Service/container port: `8080` (health endpoint).
- Environment variables: `PORTAL_HOST`, `UDP_PORT`, `SOURCE`, `YOLO_MODEL`, `CONF`, `IMGSZ`, `COOLDOWN`, `STREAM_FPS`, optionally `STREAM_WIDTH`, `STREAM_HEIGHT`, `UDP_IP`, `MEDIA_MTX_RTSP_URL`.

## Dashboard Environment Variables

- `VIDEO_HLS_URL` default is auto-derived from the request host (or can be set explicitly)
- `DASHBOARD_REFRESH_MS` default `2000`
- `UDP_LABEL_BIND_IP` default `0.0.0.0`
- `UDP_LABEL_BIND_PORT` default `20000`
- `UDP_LABEL_BUFFER_SIZE` default `4096`
- `UDP_LABEL_MAX_RECENT` default `120`
- `UDP_LABEL_CSV_PATH` default `/app/udp_listener_log.csv`

## APIs

- `GET /api/health`
- `GET /api/labels/recent?limit=20`

## Image Publishing Workflows

- `.github/workflows/publish-web-app.yml`
  - `ghcr.io/<your-github-username>/vision-dashboard`
- `.github/workflows/publish-yolo-udp-sender.yml`
  - `ghcr.io/<your-github-username>/yolo-udp-sender`
