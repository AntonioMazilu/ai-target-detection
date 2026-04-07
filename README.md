# Video and UDP Labels Dashboard

A production-style, responsive Flask web application that:

- Shows camera video coming from a MediaMTX server.
- Listens for UDP label messages and logs them to CSV.
- Displays incoming labels live in the web UI.
- Runs the app with Docker Compose (MediaMTX can run separately via Docker command).

## Stack

- Backend: Flask
- Frontend: HTML/CSS/JS (responsive dashboard)
- Video: MediaMTX (RTSP ingest, HLS playback)
- Runtime: Docker + Docker Compose

## Project Structure

```
.
├── app
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   ├── udp_label_listener.py
│   ├── static
│   │   ├── css
│   │   │   └── style.css
│   │   └── js
│   │       └── dashboard.js
│   └── templates
│       └── index.html
├── docker-compose.yml
└── .env.example
```

## Quick Start

1. Create your env file:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build
```

3. Run MediaMTX separately (if not already running):

```bash
docker run --rm -it --network=host bluenviron/mediamtx:1
```

4. Open the dashboard:

- App: http://localhost:8000
- HLS stream URL default: http://localhost:8888/livecam/index.m3u8

## Publishing Video to MediaMTX

MediaMTX path is `livecam` by default.

Example publish command (from host):

```bash
ffmpeg -re -stream_loop -1 -i sample.mp4 -c:v libx264 -preset veryfast -tune zerolatency -c:a aac -f rtsp rtsp://localhost:8554/livecam
```

If your camera already outputs RTSP, publish/relay it into the `livecam` path and the web app will display it.

## API Endpoints

- `GET /api/health`
- `GET /api/labels/recent?limit=20`

## Build Images Separately

Build only the web app image:

```bash
docker build -t vision-dashboard:local ./app
```

Build only the YOLO UDP sender image:

```bash
docker build -t yolo-udp-sender:local ./yolo-udp-sender
```

These are independent images; building one does not build the other.

## YOLO UDP Sender Container

An additional sender project is included in [yolo-udp-sender/README.md](yolo-udp-sender/README.md).

It packages your `tonisateliot.py` script as a Docker image and includes a GitHub Actions workflow to publish a free public image on GitHub Container Registry.

## GHCR Publish Workflows

- Web app image workflow: `.github/workflows/publish-web-app.yml`
	- Image: `ghcr.io/<your-github-username>/vision-dashboard`
	- Tag trigger: `app-v*` (example: `app-v1.0.0`)
- YOLO sender image workflow: `.github/workflows/publish-yolo-udp-sender.yml`
	- Image: `ghcr.io/<your-github-username>/yolo-udp-sender`
	- Tag trigger: `yolo-v*` (example: `yolo-v1.0.0`)

## UDP Label Listener

The app includes your UDP listener behavior on:

- IP: `0.0.0.0`
- Port: `20000`

Incoming labels are shown live in the dashboard and appended to CSV at:

- `/app/udp_listener_log.csv` inside the web container.

Example test packet from host:

```bash
echo "target-detected" | nc -u -w1 localhost 20000
```

## Notes

- The UI is mobile-first and scales cleanly to phones, tablets, and laptops/desktops.
- Dashboard refresh interval is configurable with `DASHBOARD_REFRESH_MS`.
- Video playback uses HLS.js with Safari native HLS fallback.
