#!/usr/bin/env bash
# verify.sh：一条命令验收（mock 单测 + 前端构建 + Playwright E2E）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$ROOT/.venv/Scripts/python.exe"
if [ ! -x "$PY" ]; then
  echo "[verify] 未找到 .venv，使用系统 python（依赖可能未安装，见 README 第 2 步）"
  PY="$(command -v python3 || command -v python)"
fi
exec "$PY" "$ROOT/scripts/verify.py"
