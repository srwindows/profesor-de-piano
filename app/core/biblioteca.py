import json
from pathlib import Path
from app.config import LECCIONES_PATH, EXAMENES_PATH

class BibliotecaPedagogica:
    def __init__(self, lecciones_path: Path = LECCIONES_PATH, examenes_path: Path = EXAMENES_PATH):
        self.lecciones_path = lecciones_path
        self.examenes_path = examenes_path
        self.lecciones = self._leer(lecciones_path)
        self.examenes = self._leer(examenes_path)

    def _leer(self, ruta: Path):
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return []

    def lecciones_de_nivel(self, nivel: str):
        return [l for l in self.lecciones if l.get("nivel") == nivel]

    def examen_de_nivel(self, nivel: str):
        for examen in self.examenes:
            if examen.get("nivel") == nivel:
                return examen
        return None

    def resumen_nivel(self, nivel: str) -> str:
        lineas = []
        for lec in self.lecciones_de_nivel(nivel):
            objetivos = ", ".join(lec.get("objetivos", []))
            lineas.append(f"• {lec.get('titulo')}: {objetivos}")
        return "\n".join(lineas) if lineas else "Aún no hay lecciones para este nivel."
