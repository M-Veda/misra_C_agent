#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "Bootstrapping MISRA Compliance Platform..."

if ! command -v docker &>/dev/null; then
    echo "Docker is required but not installed."
    exit 1
fi

docker compose build
docker compose up -d

echo "Waiting for services to become healthy..."
timeout 120 bash -c 'until docker compose ps --format json | grep -q healthy; do sleep 2; done' || true

docker compose ps
echo "Bootstrap complete."
