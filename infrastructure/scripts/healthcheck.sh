#!/usr/bin/env bash
set -euo pipefail

curl -sf http://localhost:8000/api/v1/health >/dev/null
