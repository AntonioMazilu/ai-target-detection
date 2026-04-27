#!/bin/sh
set -eu

SHOW_FLAG=""
SHOW_VALUE="${SHOW:-0}"
if [ "$SHOW_VALUE" = "1" ] || [ "$SHOW_VALUE" = "true" ] || [ "$SHOW_VALUE" = "TRUE" ]; then
  SHOW_FLAG="--show"
fi

PORTAL_HOST_VALUE="${PORTAL_HOST:-}"
RTSP_URL_DEFAULT="rtsp://127.0.0.1:8554/livecam"
RTMP_URL_DEFAULT="rtmp://127.0.0.1:1935/livecam"
UDP_IP_DEFAULT="127.0.0.1"

if [ -n "$PORTAL_HOST_VALUE" ]; then
  RTSP_URL_DEFAULT="rtsp://${PORTAL_HOST_VALUE}:8554/livecam"
  RTMP_URL_DEFAULT="rtmp://${PORTAL_HOST_VALUE}:1935/livecam"
  UDP_IP_DEFAULT="$PORTAL_HOST_VALUE"
fi

PUBLISH_PROTOCOL_VALUE="${MEDIA_MTX_PUBLISH_PROTOCOL:-${STREAM_PUBLISH_PROTOCOL:-rtmp}}"
PUBLISH_TRANSPORT_VALUE="${MEDIA_MTX_PUBLISH_TRANSPORT:-${STREAM_PUBLISH_TRANSPORT:-${RTSP_TRANSPORT:-tcp}}}"

RTSP_URL_VALUE="${MEDIA_MTX_RTSP_URL:-$RTSP_URL_DEFAULT}"
PUBLISH_URL_VALUE="${MEDIA_MTX_PUBLISH_URL:-${STREAM_PUBLISH_URL:-}}"

if [ -z "$PUBLISH_URL_VALUE" ]; then
  if [ "$PUBLISH_PROTOCOL_VALUE" = "rtmp" ]; then
    PUBLISH_URL_VALUE="$RTMP_URL_DEFAULT"
  else
    PUBLISH_URL_VALUE="$RTSP_URL_VALUE"
  fi
fi

# Infer protocol from explicit publish URL when available.
case "$PUBLISH_URL_VALUE" in
  rtmp://*) PUBLISH_PROTOCOL_VALUE="rtmp" ;;
  rtsp://*) PUBLISH_PROTOCOL_VALUE="rtsp" ;;
esac

UDP_IP_VALUE="${UDP_IP:-$UDP_IP_DEFAULT}"

# If UDP_IP is not explicitly set, keep it aligned with publish host to avoid split targets.
if [ -z "${UDP_IP:-}" ] && [ -n "$PUBLISH_URL_VALUE" ]; then
  PUBLISH_HOST=$(printf '%s' "$PUBLISH_URL_VALUE" | sed -E 's#^[a-z]+://([^/:]+).*#\1#')
  if [ -n "$PUBLISH_HOST" ] && [ "$PUBLISH_HOST" != "$PUBLISH_URL_VALUE" ]; then
    UDP_IP_VALUE="$PUBLISH_HOST"
  fi
fi

echo "Sender target configured: UDP=${UDP_IP_VALUE}:${UDP_PORT:-20000} PUBLISH=${PUBLISH_URL_VALUE} (${PUBLISH_PROTOCOL_VALUE})"

exec python /app/yolo_stream_sender.py \
  --udp-ip "${UDP_IP_VALUE}" \
  --udp-port "${UDP_PORT:-20000}" \
  --model "${YOLO_MODEL:-yolov8n.pt}" \
  --source "${SOURCE:-0}" \
  --conf "${CONF:-0.45}" \
  --imgsz "${IMGSZ:-640}" \
  --cooldown "${COOLDOWN:-10.0}" \
  --publish-url "${PUBLISH_URL_VALUE}" \
  --publish-transport "${PUBLISH_TRANSPORT_VALUE}" \
  --rtsp-url "${RTSP_URL_VALUE}" \
  --rtsp-transport "${RTSP_TRANSPORT:-tcp}" \
  --stream-fps "${STREAM_FPS:-20}" \
  --stream-width "${STREAM_WIDTH:-0}" \
  --stream-height "${STREAM_HEIGHT:-0}" \
  --log-csv "${LOG_CSV_PATH:-/app/yolo_stream_sender_log.csv}" \
  --health-port "${HEALTH_PORT:-8080}" \
  $SHOW_FLAG \
  "$@"
