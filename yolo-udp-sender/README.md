# YOLO Stream + UDP Sender

Standalone container image for Jetson or other edge nodes.

## What It Does

- Captures frames from a camera or stream source.
- Runs YOLOv8 inference.
- Publishes annotated video to MediaMTX over RTSP.
- Sends detection payloads over UDP as JSON.

## UDP Payload Example

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

## Build

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

## Run (Linux Host Network)

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

When `PORTAL_HOST` is set, the entrypoint auto-targets both:

- RTSP publish: `rtsp://PORTAL_HOST:8554/livecam`
- UDP labels: `PORTAL_HOST:20000`

## Environment Variables

- `PORTAL_HOST` (optional, preferred when using Tailscale)
- `UDP_IP` (optional override)
- `UDP_PORT` (default: `20000`)
- `MEDIA_MTX_RTSP_URL` (optional override)
- `RTSP_TRANSPORT` (default: `tcp`)
- `YOLO_MODEL` (default: `yolov8n.pt`)
- `SOURCE` (default: `0`)
- `CONF` (default: `0.45`)
- `IMGSZ` (default: `640`)
- `COOLDOWN` (default: `10.0`)
- `STREAM_FPS` (default: `20`)
- `STREAM_WIDTH` / `STREAM_HEIGHT` (default: source size)
- `LOG_CSV_PATH` (default: `/app/yolo_stream_sender_log.csv`)
- `HEALTH_PORT` (default: `8080`, set `0` to disable)
- `SHOW` (default: `0`)
