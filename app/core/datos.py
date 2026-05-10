import json
from pathlib import Path
from app.config import NIVELES_PATH, EJERCICIOS_PATH


class RepositorioDatos:
    def __init__(self):
        self.niveles = self._leer_json(NIVELES_PATH, [])
        self.ejercicios = self._leer_json(EJERCICIOS_PATH, [])

    def _leer_json(self, ruta: Path, defecto):
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return defecto

    def obtener_niveles(self):
        return self.niveles

    def obtener_ejercicios_por_nivel(self, nivel_id: str):
        return [e for e in self.ejercicios if e.get("nivel") == nivel_id]

    def obtener_primer_ejercicio(self, nivel_id: str):
        ejercicios = self.obtener_ejercicios_por_nivel(nivel_id)
        return ejercicios[0] if ejercicios else None
