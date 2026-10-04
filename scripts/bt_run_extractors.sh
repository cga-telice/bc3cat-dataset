#!/usr/bin/env bash
# Corre los extractores de un script de la BT por fases, uno tras otro, y
# descarga cada modelo de la GPU antes de cargar el siguiente (nunca dos a la vez).
# Uso: scripts/bt_run_extractors.sh scripts/calibrate_characterization.py [args...]
set -euo pipefail
script="$1"; shift
url="${OLLAMA_URL:-http://localhost:11434}"
for model in phi4:latest qwen2.5:14b; do
  echo "== $model"
  PYTHONPATH=src python -X utf8 "$script" --extract "$model" "$@"
  curl -s "$url/api/generate" -d "{\"model\": \"$model\", \"keep_alive\": 0}" > /dev/null
done
