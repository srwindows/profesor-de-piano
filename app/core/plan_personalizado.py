import json
from dataclasses import dataclass, asdict
from pathlib import Path

from app.config import DATA_DIR, APP_VERSION


@dataclass
class PasoPlan:
    orden: int
    tipo: str
    titulo: str
    motivo: str
    accion: str
    prioridad: str = "media"
    estado: str = "pendiente"


class GestorPlanPersonalizado:
    """Crea y mantiene un plan de estudio a partir de la evaluación inicial.

    v2.0.3 añade seguimiento real:
    - pasos pendientes/completados;
    - porcentaje de progreso;
    - siguiente paso recomendado;
    - guardado persistente en data/plan_personalizado.json.
    """

    def __init__(self, ruta_evaluacion: Path | None = None, ruta_plan: Path | None = None):
        self.ruta_evaluacion = ruta_evaluacion or (DATA_DIR / "evaluacion_inicial.json")
        self.ruta_plan = ruta_plan or (DATA_DIR / "plan_personalizado.json")

    def cargar_evaluacion(self) -> dict:
        if not self.ruta_evaluacion.exists():
            return {}
        try:
            return json.loads(self.ruta_evaluacion.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def cargar_plan(self) -> dict:
        if not self.ruta_plan.exists():
            return {}
        try:
            plan = json.loads(self.ruta_plan.read_text(encoding="utf-8"))
            return self._normalizar_plan(plan)
        except Exception:
            return {}

    def guardar_plan(self, plan: dict):
        plan = self._normalizar_plan(plan or {})
        self.ruta_plan.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_plan.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    def _normalizar_plan(self, plan: dict) -> dict:
        if not plan:
            return {}
        pasos = list(plan.get("pasos", []))
        for i, paso in enumerate(pasos, start=1):
            paso.setdefault("orden", i)
            paso.setdefault("tipo", "repaso")
            paso.setdefault("titulo", "Paso")
            paso.setdefault("motivo", "")
            paso.setdefault("accion", "")
            paso.setdefault("prioridad", "media")
            paso.setdefault("estado", "pendiente")
        plan["pasos"] = pasos
        plan["total_pasos"] = len(pasos)
        plan["progreso"] = self.progreso(plan)
        siguiente = self.siguiente_paso(plan)
        plan["siguiente_paso"] = siguiente.get("titulo", "Plan completado") if siguiente else "Plan completado"
        return plan

    def progreso(self, plan: dict) -> dict:
        pasos = list((plan or {}).get("pasos", []))
        total = len(pasos)
        completados = len([p for p in pasos if p.get("estado") == "completado"])
        porcentaje = int((completados / total) * 100) if total else 0
        return {
            "total": total,
            "completados": completados,
            "pendientes": max(0, total - completados),
            "porcentaje": porcentaje,
        }

    def siguiente_paso(self, plan: dict) -> dict:
        for paso in list((plan or {}).get("pasos", [])):
            if paso.get("estado", "pendiente") != "completado":
                return paso
        return {}

    def marcar_siguiente_completado(self) -> dict:
        plan = self.plan_o_generar()
        pasos = list(plan.get("pasos", []))
        for paso in pasos:
            if paso.get("estado", "pendiente") != "completado":
                paso["estado"] = "completado"
                paso["completado_en_version"] = APP_VERSION
                break
        plan["pasos"] = pasos
        self.guardar_plan(plan)
        return self.cargar_plan()

    def reiniciar_seguimiento(self) -> dict:
        plan = self.plan_o_generar()
        for paso in plan.get("pasos", []):
            paso["estado"] = "pendiente"
            paso.pop("completado_en_version", None)
        self.guardar_plan(plan)
        return self.cargar_plan()

    def _paso_para_categoria(self, categoria: str, motivo: str, orden: int) -> PasoPlan:
        cat = (categoria or "Concepto general").strip()
        mapa = {
            "Postura": ("Teoría visual: postura al piano", "Abrir teoría desde cero y revisar postura corporal."),
            "Posición de manos": ("Teoría visual: manos relajadas", "Abrir imagen de postura de manos y practicar dedos curvados."),
            "Digitación": ("Teoría visual: digitación 1–5", "Repasar numeración de dedos antes de tocar ejercicios."),
            "Localización de DO": ("Teoría visual: localizar DO", "Revisar patrón de 2 teclas negras y buscar DO en varias octavas."),
            "Mapa del teclado": ("Teoría visual: patrón del teclado", "Repasar grupos de 2 y 3 teclas negras."),
            "Teclas blancas": ("Teoría visual: DO RE MI FA SOL LA SI", "Repasar secuencia de teclas blancas y decirla en voz alta."),
            "Acordes": ("Preacordes: notas juntas", "Antes de acordes mayores, entender que un acorde son varias notas simultáneas."),
            "Lectura musical": ("Lectura inicial", "Relacionar nota escrita, nombre y tecla sin velocidad."),
        }
        titulo, accion = mapa.get(cat, ("Repaso general guiado", "Repetir explicación y ejemplo con el profesor."))
        prioridad = "alta" if cat in {"Postura", "Posición de manos", "Localización de DO", "Mapa del teclado"} else "media"
        return PasoPlan(
            orden=orden,
            tipo="repaso",
            titulo=titulo,
            motivo=motivo or f"Refuerzo recomendado en {cat}.",
            accion=accion,
            prioridad=prioridad,
            estado="pendiente",
        )

    def generar_desde_evaluacion(self) -> dict:
        evaluacion = self.cargar_evaluacion()
        alumno = evaluacion.get("alumno", "alumno")
        nivel = evaluacion.get("nivel_recomendado", "inicial")
        detalle = list(evaluacion.get("detalle", []))
        fallos = [d for d in detalle if not d.get("correcto")]

        pasos: list[PasoPlan] = []
        categorias_vistas = []
        orden = 1

        if fallos:
            for item in fallos:
                categoria = item.get("categoria", "Concepto general")
                if categoria in categorias_vistas:
                    continue
                categorias_vistas.append(categoria)
                motivo = (
                    f"En la evaluación falló o no dominó: {item.get('pregunta', '')} "
                    f"Respuesta correcta: {item.get('respuesta_correcta', '')}"
                )
                pasos.append(self._paso_para_categoria(categoria, motivo, orden))
                orden += 1
        else:
            pasos.append(PasoPlan(
                orden=orden,
                tipo="consolidacion",
                titulo="Confirmación de técnica base",
                motivo="La evaluación no detectó fallos importantes.",
                accion="Hacer una práctica corta de postura, digitación y primeras notas antes de subir dificultad.",
                prioridad="media",
                estado="pendiente",
            ))
            orden += 1

        pasos.append(PasoPlan(
            orden=orden,
            tipo="practica",
            titulo="Práctica interactiva del nivel recomendado",
            motivo=f"Nivel recomendado por la evaluación: {nivel}.",
            accion="Entrar en práctica, empezar por ejercicios cortos y usar Repaso IA si aparece un fallo.",
            prioridad="alta" if fallos else "media",
            estado="pendiente",
        ))

        plan = {
            "version": APP_VERSION,
            "alumno": alumno,
            "nivel_recomendado": nivel,
            "total_pasos": len(pasos),
            "origen": "evaluacion_inicial",
            "resumen": self._resumen_texto(evaluacion, pasos),
            "pasos": [asdict(p) for p in pasos],
        }
        plan = self._normalizar_plan(plan)
        self.guardar_plan(plan)
        return plan

    def _resumen_texto(self, evaluacion: dict, pasos: list[PasoPlan]) -> str:
        alumno = evaluacion.get("alumno", "alumno")
        aciertos = evaluacion.get("aciertos", 0)
        total = evaluacion.get("total", 0)
        nivel = evaluacion.get("nivel_recomendado", "inicial")
        if pasos and any(p.tipo == "repaso" for p in pasos):
            foco = "Primero reforzaremos los conceptos fallados; después pasaremos a práctica."
        else:
            foco = "La base parece suficiente; haremos una consolidación corta y pasaremos a práctica."
        return (
            f"{alumno}, tu evaluación inicial ha dado {aciertos}/{total} aciertos. "
            f"El nivel recomendado es {nivel}. {foco}"
        )

    def plan_o_generar(self) -> dict:
        plan = self.cargar_plan()
        if plan:
            return plan
        return self.generar_desde_evaluacion()
