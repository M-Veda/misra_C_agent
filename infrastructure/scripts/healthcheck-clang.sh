#!/usr/bin/env bash
set -euo pipefail

if command -v grpc_health_probe &>/dev/null; then
    grpc_health_probe -addr=localhost:50051
    exit 0
fi

/app/misra_clang_worker --health-check --address localhost:50051
