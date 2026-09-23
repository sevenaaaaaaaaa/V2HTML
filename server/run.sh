#!/usr/bin/env bash
# V2HTML 服务端本地启动（默认 http://0.0.0.0:8400）
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m uvicorn server.app:app --host "${V2HTML_HOST:-0.0.0.0}" --port "${V2HTML_PORT:-8400}"
