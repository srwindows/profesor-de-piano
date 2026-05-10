#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/voices/piper/laura"

echo "[1/2] Reconstruyendo voz chico..."
if ls "$DIR"/voz_chico_es_ES_carlfm.part* >/dev/null 2>&1; then
  cat "$DIR"/voz_chico_es_ES_carlfm.part* > "$DIR/voices/piper/es_ES-carlfm-high.onnx"
elif [ -f "$DIR/es_ES-carlfm-high.onnx" ]; then
  cp -f "$DIR/es_ES-carlfm-high.onnx" "$DIR/voices/piper/es_ES-carlfm-high.onnx"
else
  echo "No encuentro las partes voz_chico_es_ES_carlfm.part* ni es_ES-carlfm-high.onnx"
fi

echo "[2/2] Reconstruyendo voz Laura..."
if ls "$DIR"/voz_laura_es_MX_laura.part* >/dev/null 2>&1; then
  cat "$DIR"/voz_laura_es_MX_laura.part* > "$DIR/voices/piper/laura/es_MX-laura-high.onnx"
elif [ -f "$DIR/es_MX-laura-high.onnx" ]; then
  cp -f "$DIR/es_MX-laura-high.onnx" "$DIR/voices/piper/laura/es_MX-laura-high.onnx"
else
  echo "No encuentro las partes voz_laura_es_MX_laura.part* ni es_MX-laura-high.onnx"
fi

echo "Listo. Modelos disponibles:"
ls -lh "$DIR/voices/piper"/*.onnx 2>/dev/null || true
ls -lh "$DIR/voices/piper/laura"/*.onnx 2>/dev/null || true
