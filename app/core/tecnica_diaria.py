import json
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, APP_VERSION


class GestorTecnicaDiaria:
    """Rutina de técnica diaria.

    v2.1.1 introduce una sección transversal tipo Hanon/preparatoria.
    Guarda el progreso en `data/progreso_tecnica_diaria.json`.
    """

    def __init__(
        self,
        ruta_datos: Path | None = None,
        ruta_progreso: Path | None = None,
    ):
        self.ruta_datos = ruta_datos or (DATA_DIR / "tecnica_diaria.json")
        self.ruta_progreso = ruta_progreso or (DATA_DIR / "progreso_tecnica_diaria.json")

    def cargar_datos(self) -> dict:
        if not self.ruta_datos.exists():
            return {"rutinas": []}
        try:
            return json.loads(self.ruta_datos.read_text(encoding="utf-8"))
        except Exception:
            return {"rutinas": []}

    def cargar_progreso(self) -> dict:
        if not self.ruta_progreso.exists():
            return {
                "version": APP_VERSION,
                "rutinas_completadas": [],
                "historial": [],
                "racha_dias": 0,
                "ultima_rutina": "",
            }
        try:
            return json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": APP_VERSION,
                "rutinas_completadas": [],
                "historial": [],
                "racha_dias": 0,
                "ultima_rutina": "",
            }

    def guardar_progreso(self, progreso: dict):
        progreso["version"] = APP_VERSION
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def rutinas(self) -> list[dict]:
        return list(self.cargar_datos().get("rutinas", []))

    def rutina_por_id(self, rutina_id: str) -> dict:
        for rutina in self.rutinas():
            if rutina.get("id") == rutina_id:
                return rutina
        return {}

    def resumen(self) -> dict:
        datos = self.cargar_datos()
        progreso = self.cargar_progreso()
        total = len(datos.get("rutinas", []))
        completadas = len(set(progreso.get("rutinas_completadas", [])))
        porcentaje = int((completadas / total) * 100) if total else 0
        siguiente = self.siguiente_rutina()
        return {
            "titulo": datos.get("titulo", "Técnica diaria"),
            "descripcion": datos.get("descripcion", ""),
            "total": total,
            "completadas": completadas,
            "porcentaje": porcentaje,
            "siguiente": siguiente,
            "racha_dias": int(progreso.get("racha_dias", 0) or 0),
        }

    def siguiente_rutina(self) -> dict:
        progreso = self.cargar_progreso()
        hechas = set(progreso.get("rutinas_completadas", []))
        for rutina in self.rutinas():
            if rutina.get("id") not in hechas:
                return rutina
        rutinas = self.rutinas()
        return rutinas[-1] if rutinas else {}

    def marcar_completada(self, rutina_id: str) -> dict:
        rutina = self.rutina_por_id(rutina_id) or self.siguiente_rutina()
        rid = rutina.get("id", rutina_id)
        progreso = self.cargar_progreso()
        completadas = list(progreso.get("rutinas_completadas", []))
        if rid and rid not in completadas:
            completadas.append(rid)
        progreso["rutinas_completadas"] = completadas
        progreso["ultima_rutina"] = rid
        progreso.setdefault("historial", []).append({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "rutina_id": rid,
            "titulo": rutina.get("titulo", rid),
            "version": APP_VERSION,
        })
        progreso["historial"] = progreso["historial"][-100:]
        progreso["racha_dias"] = int(progreso.get("racha_dias", 0) or 0) + 1
        self.guardar_progreso(progreso)
        return self.resumen()

    def reiniciar(self):
        self.guardar_progreso({
            "version": APP_VERSION,
            "rutinas_completadas": [],
            "historial": [],
            "racha_dias": 0,
            "ultima_rutina": "",
        })
        return self.resumen()

    def texto_profesor(self) -> str:
        resumen = self.resumen()
        siguiente = resumen.get("siguiente", {}) or {}
        return (
            f"{resumen.get('titulo', 'Técnica diaria')}.\n\n"
            f"Progreso: {resumen.get('completadas', 0)}/{resumen.get('total', 0)} rutinas "
            f"({resumen.get('porcentaje', 0)}%).\n"
            f"Siguiente rutina: {siguiente.get('titulo', 'Sin rutina')}.\n\n"
            f"Objetivo: {siguiente.get('objetivo', '')}\n"
            f"Patrón: {siguiente.get('patron', '')}\n"
            f"Notas de referencia: {siguiente.get('notas_referencia', '')}\n\n"
            "Hazlo lento. La técnica solo sirve si no crea tensión."
        )
