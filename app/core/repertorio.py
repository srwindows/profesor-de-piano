import json
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, APP_VERSION


class GestorRepertorio:
    """Repertorio progresivo guiado.

    Cada pieza se estudia por fases: escuchar, manos separadas, unir,
    evaluar y marcar como trabajada.
    """

    def __init__(self, ruta_datos: Path | None = None, ruta_progreso: Path | None = None):
        self.ruta_datos = ruta_datos or (DATA_DIR / "repertorio.json")
        self.ruta_progreso = ruta_progreso or (DATA_DIR / "progreso_repertorio.json")

    def cargar_datos(self) -> dict:
        if not self.ruta_datos.exists():
            return {"piezas": []}
        try:
            return json.loads(self.ruta_datos.read_text(encoding="utf-8"))
        except Exception:
            return {"piezas": []}

    def cargar_progreso(self) -> dict:
        if not self.ruta_progreso.exists():
            return {
                "version": APP_VERSION,
                "piezas_trabajadas": [],
                "historial": [],
                "ultima_pieza": "",
            }
        try:
            return json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
        except Exception:
            return {
                "version": APP_VERSION,
                "piezas_trabajadas": [],
                "historial": [],
                "ultima_pieza": "",
            }

    def guardar_progreso(self, progreso: dict):
        progreso["version"] = APP_VERSION
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def piezas(self) -> list[dict]:
        return list(self.cargar_datos().get("piezas", []))

    def pieza_por_id(self, pieza_id: str) -> dict:
        for pieza in self.piezas():
            if pieza.get("id") == pieza_id:
                return pieza
        return {}

    def resumen(self, nivel_actual: str = "inicial") -> dict:
        datos = self.cargar_datos()
        progreso = self.cargar_progreso()
        hechas = set(progreso.get("piezas_trabajadas", []))
        piezas = datos.get("piezas", [])
        total = len(piezas)
        trabajadas = len([p for p in piezas if p.get("id") in hechas])
        porcentaje = int((trabajadas / total) * 100) if total else 0
        siguiente = self.siguiente_pieza(nivel_actual)
        return {
            "titulo": datos.get("titulo", "Repertorio progresivo"),
            "descripcion": datos.get("descripcion", ""),
            "total": total,
            "trabajadas": trabajadas,
            "porcentaje": porcentaje,
            "siguiente": siguiente,
            "nivel_actual": nivel_actual,
        }

    def siguiente_pieza(self, nivel_actual: str = "inicial") -> dict:
        progreso = self.cargar_progreso()
        hechas = set(progreso.get("piezas_trabajadas", []))
        piezas = self.piezas()

        orden_niveles = ["nivel_0", "inicial", "basico", "intermedio", "avanzado"]
        if nivel_actual not in orden_niveles:
            nivel_actual = "inicial"
        niveles_permitidos = set(orden_niveles[:orden_niveles.index(nivel_actual) + 1])

        for pieza in piezas:
            if pieza.get("id") not in hechas and pieza.get("nivel") in niveles_permitidos:
                return pieza
        for pieza in piezas:
            if pieza.get("id") not in hechas:
                return pieza
        return piezas[-1] if piezas else {}

    def marcar_trabajada(self, pieza_id: str) -> dict:
        pieza = self.pieza_por_id(pieza_id) or self.siguiente_pieza()
        pid = pieza.get("id", pieza_id)
        progreso = self.cargar_progreso()
        trabajadas = list(progreso.get("piezas_trabajadas", []))
        if pid and pid not in trabajadas:
            trabajadas.append(pid)
        progreso["piezas_trabajadas"] = trabajadas
        progreso["ultima_pieza"] = pid
        progreso.setdefault("historial", []).append({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "pieza_id": pid,
            "titulo": pieza.get("titulo", pid),
            "version": APP_VERSION,
        })
        progreso["historial"] = progreso["historial"][-100:]
        self.guardar_progreso(progreso)
        return self.resumen(pieza.get("nivel", "inicial"))

    def reiniciar(self):
        self.guardar_progreso({
            "version": APP_VERSION,
            "piezas_trabajadas": [],
            "historial": [],
            "ultima_pieza": "",
        })

    def texto_profesor(self, nivel_actual: str = "inicial") -> str:
        resumen = self.resumen(nivel_actual)
        pieza = resumen.get("siguiente", {}) or {}
        fases = pieza.get("fases", [])
        return (
            f"{resumen.get('titulo', 'Repertorio progresivo')}.\n\n"
            f"Progreso: {resumen.get('trabajadas', 0)}/{resumen.get('total', 0)} piezas.\n"
            f"Siguiente pieza: {pieza.get('titulo', 'Sin pieza')}.\n"
            f"Tempo recomendado: {pieza.get('tempo', '—')} bpm. Compás: {pieza.get('compas', '—')}.\n\n"
            f"Objetivo: {pieza.get('objetivo', '')}\n\n"
            "Fases de estudio:\n- " + "\n- ".join(fases) if fases else "Sin fases configuradas."
        )
