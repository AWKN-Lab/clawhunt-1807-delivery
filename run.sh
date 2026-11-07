#!/usr/bin/env bash
# run.sh：一条命令启动 mock（8001）+ H5（5173）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [ -x "$ROOT/.venv/bin/python" ]; then
  export CH1807_PYTHON="$ROOT/.venv/bin/python"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  export CH1807_PYTHON="$ROOT/.venv/Scripts/python.exe"
else
  echo "[run] 未找到 .venv，使用系统 python（建议先按 README 第 2 步安装依赖）"
fi
exec node "$ROOT/scripts/dev.mjs" "$@"
