#!/usr/bin/env python3
"""Configura automáticamente las rutas de modelos Piper en data/ajustes_usuario.json.

Busca modelos ya descargados en la carpeta del proyecto y en ~/Escritorio/profesor_de_piano.
No descarga nada; solo guarda rutas existentes.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AJUSTES = BASE_DIR / "data" / "ajustes_usuario.json"

NOMBRES_CHICA = [
    "es_MX-laura-high.onnx",
    "laura-high.onnx",
]
NOMBRES_CHICO = [
    "es_ES-carlfm-high.onnx",
    "carlfm-high.onnx",
]


def buscar(nombre):
    carpetas = [
        BASE_DIR,
        BASE_DIR / "voices",
        Path.home() / "Escritorio" / "profesor_de_piano",
        Path.home() / "Desktop" / "profesor_de_piano",
        Path.home(),
    ]
    vistos = set()
    for carpeta in carpetas:
        carpeta = carpeta.expanduser()
        if not carpeta.exists() or carpeta in vistos:
            continue
        vistos.add(carpeta)
        try:
            for ruta in carpeta.rglob(nombre):
                if ruta.is_file() and ruta.stat().st_size > 1024:
                    return ruta.resolve()
        except PermissionError:
            continue
    return None


def buscar_primero(nombres):
    for nombre in nombres:
        encontrado = buscar(nombre)
        if encontrado:
            return encontrado
    return None


def main():
    if AJUSTES.exists():
        datos = json.loads(AJUSTES.read_text(encoding="utf-8"))
    else:
        datos = {}

    chica = buscar_primero(NOMBRES_CHICA)
    chico = buscar_primero(NOMBRES_CHICO)

    datos["voz_motor"] = "piper"
    if chica:
        datos["voz_piper_modelo_chica"] = str(chica)
    else:
        datos.setdefault("voz_piper_modelo_chica", "voices/piper/laura/es_MX-laura-high.onnx")
    if chico:
        datos["voz_piper_modelo_chico"] = str(chico)
    else:
        datos.setdefault("voz_piper_modelo_chico", "voices/piper/es_ES-carlfm-high.onnx")

    AJUSTES.parent.mkdir(parents=True, exist_ok=True)
    AJUSTES.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Configuración Piper guardada en:", AJUSTES)
    print("Voz chica:", datos.get("voz_piper_modelo_chica", ""))
    print("Voz chico:", datos.get("voz_piper_modelo_chico", ""))
    if not chica:
        print("AVISO: no he encontrado la voz chica es_MX-laura-high.onnx.")
    if not chico:
        print("AVISO: no he encontrado la voz chico es_ES-carlfm-high.onnx.")


if __name__ == "__main__":
    main()
