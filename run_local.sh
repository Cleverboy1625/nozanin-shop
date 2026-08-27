#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON="$BACKEND_DIR/.venv/bin/python"
PORT="${PORT:-8010}"
LOG_FILE="${TMPDIR:-/tmp}/nozanin-cloudflared-${PORT}.log"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python virtualenv topilmadi: $PYTHON" >&2
  exit 1
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared o'rnatilmagan" >&2
  exit 1
fi

pkill -f 'uvicorn.*app.main' 2>/dev/null || true
pkill -f 'bot.bot' 2>/dev/null || true
pkill -f 'cloudflared tunnel --url' 2>/dev/null || true
rm -f "$LOG_FILE"

cloudflared tunnel --no-autoupdate --protocol http2 --url "http://127.0.0.1:${PORT}" --logfile "$LOG_FILE" &
TUNNEL_PID=$!

cleanup() {
  kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

PUBLIC_URL=""
for _ in {1..60}; do
  PUBLIC_URL="$(sed -nE 's#.*(https://[[:alnum:]-]+\.trycloudflare\.com).*#\1#p' "$LOG_FILE" 2>/dev/null | tail -n 1 || true)"
  [[ -n "$PUBLIC_URL" ]] && break
  sleep 1
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "Cloudflare Quick Tunnel public URL bermadi." >&2
  echo "Log: $LOG_FILE" >&2
  exit 1
fi

export WEBAPP_URL="$PUBLIC_URL"
export USE_WEBHOOK=true
export PYTHONPATH="$BACKEND_DIR"

ENV_FILE="$BACKEND_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  sed -i "s#^WEBAPP_URL=.*#WEBAPP_URL=$PUBLIC_URL#" "$ENV_FILE"
  sed -i "s#^CORS_ORIGINS=.*#CORS_ORIGINS=$PUBLIC_URL#" "$ENV_FILE"
  sed -i "s#^USE_WEBHOOK=.*#USE_WEBHOOK=true#" "$ENV_FILE"
fi

echo "Mini App URL: $WEBAPP_URL"
echo "Webhook URL: $WEBAPP_URL/telegram/webhook"
echo "Backend: http://127.0.0.1:${PORT}"
exec "$PYTHON" -m uvicorn app.main:app --app-dir "$BACKEND_DIR" --host 127.0.0.1 --port "$PORT"
