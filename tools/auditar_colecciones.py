from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
catalog = json.loads((ROOT / "data/colecciones_curso.json").read_text(encoding="utf-8"))

errores = []
for nivel in catalog["niveles"]:
    ruta = ROOT / nivel["archivo_clases"]
    if not ruta.exists():
        errores.append(f"No existe {ruta}")
        continue
    data = json.loads(ruta.read_text(encoding="utf-8"))
    clases = data.get("clases", data.get("lecciones", []))
    total = data.get("total_clases") or len(clases)
    if len(clases) != total:
        errores.append(f"{nivel['id']}: total_clases={total} pero clases={len(clases)}")

if errores:
    print("AUDITORÍA CON ERRORES")
    for e in errores:
        print("-", e)
    raise SystemExit(1)

print("AUDITORÍA OK")
print("Niveles:", len(catalog["niveles"]))
for n in catalog["niveles"]:
    ruta = ROOT / n["archivo_clases"]
    data = json.loads(ruta.read_text(encoding="utf-8"))
    clases = data.get("clases", data.get("lecciones", []))
    print(f"- {n['id']}: {len(clases)} clases · {n['estado']}")
