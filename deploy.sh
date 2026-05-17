#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ai-backend"
IMAGE_NAME="ai-backend"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
DB_FILE="$BACKEND_DIR/history.db"
BACKUP_DIR="$PROJECT_DIR/db_backups"
ENV_FILE="$PROJECT_DIR/.env"

cd "$PROJECT_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env file not found."
  echo "Create .env first."
  exit 1
fi

BACKEND_PORT="$(grep -E '^BACKEND_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
BACKEND_PORT="${BACKEND_PORT:-8000}"

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then
  cp "$DB_FILE" "$BACKUP_DIR/history_$(date +%Y%m%d_%H%M%S).db"
  echo "DB backup created."
else
  mkdir -p "$BACKEND_DIR"
  touch "$DB_FILE"
  echo "New empty DB file created."
fi

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" "$BACKEND_DIR"

if docker ps -a --format '{{.Names}}' | grep -qx "$APP_NAME"; then
  echo "Stopping old container..."
  docker stop "$APP_NAME" >/dev/null 2>&1 || true
  docker rm "$APP_NAME" >/dev/null 2>&1 || true
fi

echo "Starting new container..."
docker run -d \
  --name "$APP_NAME" \
  --restart unless-stopped \
  -p "$BACKEND_PORT:8000" \
  -v "$DB_FILE:/app/history.db" \
  --env-file "$ENV_FILE" \
  "$IMAGE_NAME"

sleep 2

echo "Health check..."
curl -fsS "http://127.0.0.1:$BACKEND_PORT/health"
echo

echo "Chat API check..."
curl -fsS "http://127.0.0.1:$BACKEND_PORT/openapi.json" | grep -o '"/chat[^"]*"' | sort -u
echo

echo "Recent logs..."
docker logs --tail 20 "$APP_NAME"
