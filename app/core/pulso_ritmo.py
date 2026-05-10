import json
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, APP_VERSION


class GestorPulsoRitmo:
    """Entrenamiento de pulso y metrónomo."""

    def __init__(self, ruta_datos: Path | None = None, ruta_progreso: Path | None = None):
        self.ruta_datos = ruta_datos or (DATA_DIR / "pulso_ritmo.json")
        self.ruta_progreso = ruta_progreso or (DATA_DIR / "progreso_pulso_ritmo.json")

    def cargar_datos(self) -> dict:
        if not self.ruta_datos.exists():
            return {"ejercicios": []}
        try:
            return json.loads(self.ruta_datos.read_text(encoding="utf-8"))
        except Exception:
            return {"ejercicios": []}

    def cargar_progreso(self) -> dict:
        if not self.ruta_progreso.exists():
            return {
                "version": APP_VERSION,
                "ejercicios_completados": [],
                "historial": [],
                "ultimo_ejercicio": "",
            }
        try:
            return json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": APP_VERSION,
                "ejercicios_completados": [],
                "historial": [],
                "ultimo_ejercicio": "",
            }

    def guardar_progreso(self, progreso: dict):
        progreso["version"] = APP_VERSION
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def ejercicios(self) -> list[dict]:
        return list(self.cargar_datos().get("ejercicios", []))

    def ejercicio_por_id(self, ejercicio_id: str) -> dict:
        for ejercicio in self.ejercicios():
            if ejercicio.get("id") == ejercicio_id:
                return ejercicio
        return {}

    def siguiente_ejercicio(self, nivel_actual: str = "inicial") -> dict:
        progreso = self.cargar_progreso()
        hechos = set(progreso.get("ejercicios_completados", []))
        ejercicios = self.ejercicios()
        orden = ["nivel_0", "inicial", "basico", "intermedio", "avanzado"]
        if nivel_actual not in orden:
            nivel_actual = "inicial"
        permitidos = set(orden[:orden.index(nivel_actual) + 1])
        for ejercicio in ejercicios:
            if ejercicio.get("id") not in hechos and ejercicio.get("nivel") in permitidos:
                return ejercicio
        for ejercicio in ejercicios:
            if ejercicio.get("id") not in hechos:
                return ejercicio
        return ejercicios[-1] if ejercicios else {}

    def resumen(self, nivel_actual: str = "inicial") -> dict:
        datos = self.cargar_datos()
        progreso = self.cargar_progreso()
        hechos = set(progreso.get("ejercicios_completados", []))
        ejercicios = datos.get("ejercicios", [])
        total = len(ejercicios)
        completados = len([e for e in ejercicios if e.get("id") in hechos])
        porcentaje = int((completados / total) * 100) if total else 0
        siguiente = self.siguiente_ejercicio(nivel_actual)
        return {
            "titulo": datos.get("titulo", "Pulso y metrónomo"),
            "descripcion": datos.get("descripcion", ""),
            "total": total,
            "completados": completados,
            "porcentaje": porcentaje,
            "siguiente": siguiente,
            "nivel_actual": nivel_actual,
        }

    def marcar_completado(self, ejercicio_id: str, nivel_actual: str = "inicial") -> dict:
        ejercicio = self.ejercicio_por_id(ejercicio_id) or self.siguiente_ejercicio(nivel_actual)
        eid = ejercicio.get("id", ejercicio_id)
        progreso = self.cargar_progreso()
        completados = list(progreso.get("ejercicios_completados", []))
        if eid and eid not in completados:
            completados.append(eid)
        progreso["ejercicios_completados"] = completados
        progreso["ultimo_ejercicio"] = eid
        progreso.setdefault("historial", []).append({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "ejercicio_id": eid,
            "titulo": ejercicio.get("titulo", eid),
            "bpm": ejercicio.get("bpm", 60),
            "version": APP_VERSION,
        })
        progreso["historial"] = progreso["historial"][-100:]
        self.guardar_progreso(progreso)
        return self.resumen(nivel_actual)

    def reiniciar(self):
        self.guardar_progreso({
            "version": APP_VERSION,
            "ejercicios_completados": [],
            "historial": [],
            "ultimo_ejercicio": "",
        })
