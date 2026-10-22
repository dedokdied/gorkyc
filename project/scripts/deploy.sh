#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.yml"

cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
    echo "Нет .env. Скопируй infra/deploy/env.example в .env и заполни секреты."
    exit 1
fi

docker compose -f "$COMPOSE_FILE" up -d --build
docker compose -f "$COMPOSE_FILE" ps
