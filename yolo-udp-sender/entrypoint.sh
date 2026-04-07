#!/bin/sh
set -eu

SHOW_FLAG=""
SHOW_VALUE="${SHOW:-0}"
if [ "$SHOW_VALUE" = "1" ] || [ "$SHOW_VALUE" = "true" ] || [ "$SHOW_VALUE" = "TRUE" ]; then
  SHOW_FLAG="--show"
fi

exec python /app/tonisateliot.py \
  --udp-ip "${UDP_IP:-127.0.0.1}" \
  --udp-port "${UDP_PORT:-20000}" \
  --model "${YOLO_MODEL:-yolov8n.pt}" \
  --source "${SOURCE:-0}" \
  --conf "${CONF:-0.45}" \
  --imgsz "${IMGSZ:-640}" \
  --cooldown "${COOLDOWN:-10.0}" \
  $SHOW_FLAG \
  "$@"
