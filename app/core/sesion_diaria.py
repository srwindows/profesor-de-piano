import json
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, APP_VERSION


class GestorSesionDiaria:
    """Sesión de estudio completa.

    Une ruta, plan personalizado, técnica diaria, práctica y repaso en un
    flujo único. La sesión no sustituye a esos módulos: los orquesta.
    """

    def __init__(
        self,
        ruta_datos: Path | None = None,
        ruta_progreso: Path | None = None,
    ):
        self.ruta_datos = ruta_datos or (DATA_DIR / "sesion_diaria.json")
        self.ruta_progreso = ruta_progreso or (DATA_DIR / "progreso_sesion_diaria.json")

    def cargar_datos(self) -> dict:
        if not self.ruta_datos.exists():
            return {"pasos_base": []}
        try:
            return json.loads(self.ruta_datos.read_text(encoding="utf-8"))
        except Exception:
            return {"pasos_base": []}

    def cargar_progreso(self) -> dict:
        if not self.ruta_progreso.exists():
            return {
                "version": APP_VERSION,
                "sesiones_completadas": 0,
                "pasos_completados": [],
                "historial": [],
                "sesion_activa": "",
            }
        try:
            return json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": APP_VERSION,
                "sesiones_completadas": 0,
                "pasos_completados": [],
                "historial": [],
                "sesion_activa": "",
            }

    def guardar_progreso(self, progreso: dict):
        progreso["version"] = APP_VERSION
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def crear_sesion(self, nivel_actual: str, plan: dict | None = None, tecnica_resumen: dict | None = None, repasos_pendientes: int = 0) -> dict:
        datos = self.cargar_datos()
        plan = plan or {}
        tecnica_resumen = tecnica_resumen or {}
        pasos = []
        completados = set(self.cargar_progreso().get("pasos_completados", []))

        for paso in datos.get("pasos_base", []):
            p = dict(paso)
            p["estado"] = "completado" if p.get("id") in completados else "pendiente"
            p["nivel_actual"] = nivel_actual

            if p.get("tipo") == "tecnica":
                siguiente = tecnica_resumen.get("siguiente", {}) or {}
                if siguiente:
                    p["accion"] = f"Abrir Técnica diaria: {siguiente.get('titulo', 'siguiente rutina')}."
                    p["objetivo"] = siguiente.get("objetivo", p.get("objetivo", ""))

            if p.get("tipo") == "teoria":
                siguiente_plan = plan.get("siguiente_paso", "")
                if siguiente_plan:
                    p["accion"] = f"Abrir Plan alumno y revisar: {siguiente_plan}."

            if p.get("tipo") == "repaso":
                if repasos_pendientes > 0:
                    p["accion"] = f"Hay {repasos_pendientes} repaso(s) pendiente(s). Abrir Repaso IA."
                    p["prioridad"] = "alta"
                else:
                    p["accion"] = "No hay repasos pendientes. Usar este paso como repaso breve preventivo."
                    p["prioridad"] = "baja"

            pasos.append(p)

        total = len(pasos)
        hechos = len([p for p in pasos if p.get("estado") == "completado"])
        porcentaje = int((hechos / total) * 100) if total else 0
        siguiente = next((p for p in pasos if p.get("estado") != "completado"), {})

        return {
            "version": APP_VERSION,
            "titulo": datos.get("titulo", "Sesión diaria inteligente"),
            "descripcion": datos.get("descripcion", ""),
            "duracion_objetivo_min": datos.get("duracion_objetivo_min", 25),
            "nivel_actual": nivel_actual,
            "pasos": pasos,
            "progreso": {
                "total": total,
                "completados": hechos,
                "pendientes": max(0, total - hechos),
                "porcentaje": porcentaje,
            },
            "siguiente": siguiente,
            "resumen": self.texto_resumen(nivel_actual, pasos, porcentaje),
        }

    def texto_resumen(self, nivel_actual: str, pasos: list[dict], porcentaje: int) -> str:
        siguiente = next((p for p in pasos if p.get("estado") != "completado"), {})
        if siguiente:
            sig = siguiente.get("titulo", "siguiente paso")
        else:
            sig = "sesión completada"
        return (
            f"Sesión diaria para nivel {nivel_actual}. Progreso actual: {porcentaje}%.\n"
            f"Siguiente paso recomendado: {sig}.\n\n"
            "La idea es trabajar poco, pero bien: preparar cuerpo, técnica, concepto, práctica y repaso."
        )

    def marcar_siguiente_completado(self, sesion: dict) -> dict:
        progreso = self.cargar_progreso()
        hechos = list(progreso.get("pasos_completados", []))
        for paso in sesion.get("pasos", []):
            pid = paso.get("id", "")
            if pid and pid not in hechos:
                hechos.append(pid)
                progreso.setdefault("historial", []).append({
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                    "paso_id": pid,
                    "titulo": paso.get("titulo", pid),
                    "version": APP_VERSION,
                })
                break

        progreso["pasos_completados"] = hechos
        if len(hechos) >= len(sesion.get("pasos", [])) and sesion.get("pasos"):
            progreso["sesiones_completadas"] = int(progreso.get("sesiones_completadas", 0) or 0) + 1
        progreso["historial"] = progreso.get("historial", [])[-200:]
        self.guardar_progreso(progreso)
        return progreso

    def reiniciar_sesion(self):
        progreso = self.cargar_progreso()
        progreso["pasos_completados"] = []
        progreso["sesion_activa"] = datetime.now().isoformat(timespec="seconds")
        self.guardar_progreso(progreso)
        return progreso
