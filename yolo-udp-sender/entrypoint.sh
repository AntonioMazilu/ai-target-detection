#!/bin/sh
set -eu

SHOW_FLAG=""
SHOW_VALUE="${SHOW:-0}"
if [ "$SHOW_VALUE" = "1" ] || [ "$SHOW_VALUE" = "true" ] || [ "$SHOW_VALUE" = "TRUE" ]; then
  SHOW_FLAG="--show"
fi

PORTAL_HOST_VALUE="${PORTAL_HOST:-}"
RTSP_URL_DEFAULT="rtsp://127.0.0.1:8554/livecam"
UDP_IP_DEFAULT="127.0.0.1"

if [ -n "$PORTAL_HOST_VALUE" ]; then
  RTSP_URL_DEFAULT="rtsp://${PORTAL_HOST_VALUE}:8554/livecam"
  UDP_IP_DEFAULT="$PORTAL_HOST_VALUE"
fi

RTSP_URL_VALUE="${MEDIA_MTX_RTSP_URL:-$RTSP_URL_DEFAULT}"
UDP_IP_VALUE="${UDP_IP:-$UDP_IP_DEFAULT}"

# If UDP_IP is not explicitly set, keep it aligned with RTSP host to avoid split targets.
if [ -z "${UDP_IP:-}" ] && [ -n "$RTSP_URL_VALUE" ]; then
  RTSP_HOST=$(printf '%s' "$RTSP_URL_VALUE" | sed -E 's#^rtsp://([^/:]+).*#\1#')
  if [ -n "$RTSP_HOST" ] && [ "$RTSP_HOST" != "$RTSP_URL_VALUE" ]; then
    UDP_IP_VALUE="$RTSP_HOST"
  fi
fi

echo "Sender target configured: UDP=${UDP_IP_VALUE}:${UDP_PORT:-20000} RTSP=${RTSP_URL_VALUE}"

exec python /app/yolo_stream_sender.py \
  --udp-ip "${UDP_IP_VALUE}" \
  --udp-port "${UDP_PORT:-20000}" \
  --model "${YOLO_MODEL:-yolov8n.pt}" \
  --source "${SOURCE:-0}" \
  --conf "${CONF:-0.45}" \
  --imgsz "${IMGSZ:-640}" \
  --cooldown "${COOLDOWN:-10.0}" \
  --rtsp-url "${RTSP_URL_VALUE}" \
  --rtsp-transport "${RTSP_TRANSPORT:-tcp}" \
  --stream-fps "${STREAM_FPS:-20}" \
  --stream-width "${STREAM_WIDTH:-0}" \
  --stream-height "${STREAM_HEIGHT:-0}" \
  --log-csv "${LOG_CSV_PATH:-/app/yolo_stream_sender_log.csv}" \
  --health-port "${HEALTH_PORT:-8080}" \
  $SHOW_FLAG \
  "$@"
