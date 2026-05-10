import json
from pathlib import Path

from app.config import DATA_DIR


class GestorRutaCurso:
    """Mapa curricular general del curso.

    Une teoría, práctica, evaluación, plan personalizado y progreso en una
    sola vista para que el alumno sepa dónde está y qué viene después.
    """

    def __init__(self, ruta: Path | None = None):
        self.ruta = ruta or (DATA_DIR / "ruta_curso.json")

    def cargar(self) -> dict:
        if not self.ruta.exists():
            return {"niveles": []}
        try:
            return json.loads(self.ruta.read_text(encoding="utf-8"))
        except Exception:
            return {"niveles": []}

    def estado_ruta(self, progreso, plan: dict | None = None, nivel0_superado: bool = False) -> dict:
        datos = self.cargar()
        niveles = list(datos.get("niveles", []))
        nivel_actual = getattr(progreso, "nivel_actual", "sin_evaluar")
        examenes_aprobados = int(getattr(progreso, "examenes_aprobados", 0) or 0)
        plan = plan or {}
        plan_progreso = plan.get("progreso", {})
        plan_porcentaje = int(plan_progreso.get("porcentaje", 0) or 0)

        completados = set()
        if nivel0_superado:
            completados.add("nivel_0")
        if examenes_aprobados >= 1:
            completados.add("inicial")
        if examenes_aprobados >= 2:
            completados.add("basico")
        if examenes_aprobados >= 3:
            completados.add("intermedio")

        salida = []
        desbloqueado_anterior = True
        for item in niveles:
            item = dict(item)
            rid = item.get("id", "")
            practica = item.get("nivel_practica", rid)

            if rid in completados:
                estado = "completado"
            elif rid == "nivel_0" and not nivel0_superado:
                estado = "actual"
            elif nivel_actual == practica and desbloqueado_anterior:
                estado = "actual"
            elif item.get("estado_inicial") == "disponible" and rid in {"nivel_0", "inicial"}:
                estado = "disponible"
            elif desbloqueado_anterior and rid not in completados:
                estado = "bloqueado" if rid not in {"nivel_0", "inicial"} else "disponible"
            else:
                estado = "bloqueado"

            item["estado"] = estado
            item["plan_porcentaje"] = plan_porcentaje if estado == "actual" else 0
            salida.append(item)

            # Solo desbloquea el siguiente si este está completado.
            desbloqueado_anterior = estado == "completado"

        siguiente = next((n for n in salida if n.get("estado") in {"actual", "disponible"}), salida[0] if salida else {})
        return {
            "titulo": datos.get("titulo", "Ruta curricular"),
            "descripcion": datos.get("descripcion", ""),
            "nivel_actual": nivel_actual,
            "niveles": salida,
            "siguiente": siguiente,
            "plan_porcentaje": plan_porcentaje,
        }

    def nivel_para_continuar(self, estado: dict) -> str:
        sig = (estado or {}).get("siguiente", {}) or {}
        nivel = sig.get("nivel_practica") or sig.get("id") or "inicial"
        if nivel == "nivel_0":
            return "inicial"
        return nivel
