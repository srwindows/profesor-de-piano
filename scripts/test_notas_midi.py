import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.notas import normalizar_nota


CASOS = [
    ("Do4", 60),
    ("Re4", 62),
    ("Mi4", 64),
    ("Fa4", 65),
    ("Sol4", 67),
    ("La4", 69),
    ("Si4", 71),
    ("Do5", 72),
]


def main():
    errores = []
    for nombre, midi in CASOS:
        desde_nombre = normalizar_nota(nombre)
        desde_midi = normalizar_nota(midi)
        ok = (
            desde_nombre["midi"] == midi
            and desde_midi["midi"] == midi
            and desde_nombre["nota"] == desde_midi["nota"]
            and desde_nombre["nombre_completo"] == desde_midi["nombre_completo"]
        )
        print(
            f"{nombre} -> midi={desde_nombre['midi']} nota={desde_nombre['nota']} "
            f"visible={desde_nombre['nombre_completo']} esperado={desde_midi['nombre_completo']} "
            f"validacion={'OK' if ok else 'ERROR'}"
        )
        if not ok:
            errores.append((nombre, midi, desde_nombre, desde_midi))
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
