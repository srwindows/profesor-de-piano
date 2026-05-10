import json
from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR
from app.core.flujo_docente import MotorFlujoDocente, normalizar_nivel_id, numero_nivel
from app.core.historial_alumno import HistorialAlumno


LECCIONES_NIVEL_0_PATH = DATA_DIR / "lecciones_nivel_0.json"
PROGRESO_ALUMNO_PATH = DATA_DIR / "progreso_alumno.json"


def ruta_lecciones_por_nivel(nivel: str | int | None) -> Path:
    return DATA_DIR / f"lecciones_nivel_{numero_nivel(nivel)}.json"


def ruta_progreso_alumno_por_nivel(nivel: str | int | None) -> Path:
    n = numero_nivel(nivel)
    if n == 0:
        return PROGRESO_ALUMNO_PATH
    return DATA_DIR / f"progreso_alumno_nivel_{n}.json"


@dataclass
class ResultadoRespuesta:
    correcto: bool
    mensaje: str


class GestorLeccionesGuiadas:
    """Carga lecciones desde JSON y guarda progreso pedagógico del alumno.

    Esta capa evita que el contenido del curso quede incrustado en la interfaz.
    Las próximas versiones podrán añadir niveles y lecciones editando JSON.
    """

    def __init__(
        self,
        ruta_lecciones: Path | None = None,
        ruta_progreso: Path | None = None,
        nivel: str | int | None = "nivel_0",
    ):
        self.nivel_id = normalizar_nivel_id(nivel)
        self.nivel_numero = numero_nivel(self.nivel_id)
        self.ruta_lecciones = Path(ruta_lecciones) if ruta_lecciones else ruta_lecciones_por_nivel(self.nivel_id)
        self.ruta_progreso = Path(ruta_progreso) if ruta_progreso else ruta_progreso_alumno_por_nivel(self.nivel_id)
        self.datos = {"nivel": self.nivel_id, "lecciones": []}
        self.progreso = {}
        self.flujo_docente = MotorFlujoDocente(nivel=self.nivel_id)
        self.historial_alumno = HistorialAlumno()
        self.cargar()

    def configurar_nivel(self, nivel: str | int | None):
        nivel_id = normalizar_nivel_id(nivel)
        if nivel_id == self.nivel_id:
            return
        self.nivel_id = nivel_id
        self.nivel_numero = numero_nivel(nivel_id)
        self.ruta_lecciones = ruta_lecciones_por_nivel(nivel_id)
        self.ruta_progreso = ruta_progreso_alumno_por_nivel(nivel_id)
        self.flujo_docente = MotorFlujoDocente(nivel=nivel_id)
        self.cargar()

    def cargar(self):
        try:
            self.datos = json.loads(self.ruta_lecciones.read_text(encoding="utf-8"))
        except Exception:
            self.datos = {"nivel": self.nivel_id, "lecciones": []}
        if isinstance(self.datos, dict):
            self.datos.setdefault("nivel", self.nivel_id)
        self._cargar_progreso()

    def _cargar_progreso(self):
        base = {
            "version": "4.0.6",
            "nivel_actual": self.nivel_numero,
            "leccion_actual_id": self.primera_leccion_id(),
            "lecciones_superadas": [],
            "respuestas": [],
            "ultima_pantalla": "teoria_nivel_0",
            f"mini_evaluacion_nivel_{self.nivel_numero}_superada": False,
        }
        if self.ruta_progreso.exists():
            try:
                datos = json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
                base.update(datos if isinstance(datos, dict) else {})
            except Exception:
                pass
        if not base.get("leccion_actual_id"):
            base["leccion_actual_id"] = self.primera_leccion_id()
        self.progreso = base
        self.guardar()

    def guardar(self):
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(self.progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def lecciones(self) -> list[dict]:
        return sorted(self.datos.get("lecciones", []), key=lambda x: x.get("orden", 0))

    def primera_leccion_id(self) -> str:
        lecciones = self.lecciones()
        return lecciones[0]["id"] if lecciones else ""

    def leccion_por_id(self, leccion_id: str) -> dict | None:
        for leccion in self.lecciones():
            if leccion.get("id") == leccion_id:
                return leccion
        return None

    def leccion_actual(self) -> dict | None:
        leccion = self.leccion_por_id(self.progreso.get("leccion_actual_id", ""))
        if leccion is None and self.lecciones():
            leccion = self.lecciones()[0]
            self.progreso["leccion_actual_id"] = leccion["id"]
            self.guardar()
        return leccion

    def indice_actual(self) -> int:
        actual = self.progreso.get("leccion_actual_id", "")
        for i, leccion in enumerate(self.lecciones()):
            if leccion.get("id") == actual:
                return i
        return 0

    def esta_superada(self, leccion_id: str) -> bool:
        return leccion_id in set(self.progreso.get("lecciones_superadas", []))

    def porcentaje(self) -> int:
        total = len(self.lecciones())
        if total <= 0:
            return 0
        return int((len(set(self.progreso.get("lecciones_superadas", []))) / total) * 100)

    def titulo_nivel(self) -> str:
        return str(self.datos.get("titulo") or f"Nivel {self.nivel_numero}")

    def etiqueta_nivel(self) -> str:
        return f"Nivel {self.nivel_numero}"

    def clave_mini_evaluacion_superada(self) -> str:
        return f"mini_evaluacion_nivel_{self.nivel_numero}_superada"

    def clave_nivel_superado(self) -> str:
        return f"nivel_{self.nivel_numero}_superado"

    def marcar_superada(self, leccion_id: str, origen: str = "manual"):
        lista = list(self.progreso.get("lecciones_superadas", []))
        if leccion_id and leccion_id not in lista:
            lista.append(leccion_id)
        self.progreso["lecciones_superadas"] = lista
        self.progreso["ultimo_origen_superacion"] = origen
        try:
            leccion = self.leccion_por_id(leccion_id) or {}
            evento = "examen_clase_superado" if origen == "examen_clase" else "clase_superada"
            self.historial_alumno.registrar_clase(
                clase_id=leccion_id,
                titulo=leccion.get("titulo", ""),
                evento=evento,
                correcto=True,
                detalle={"origen": origen}
            )
        except Exception:
            pass
        self.guardar()

    def hay_siguiente(self) -> bool:
        """Indica si existe una lección posterior a la actual."""
        return self.indice_actual() < max(len(self.lecciones()) - 1, 0)

    def avanzar(self) -> dict | None:
        """Avanza a la siguiente lección de forma segura.

        En la v1.9.2 original, al estar ya en una lección superada el usuario
        podía quedar con la sensación de bloqueo si la interfaz no refrescaba
        claramente. Este método mantiene el avance por índice real y devuelve
        la nueva lección o la última si ya no hay más.
        """
        lecciones = self.lecciones()
        if not lecciones:
            return None
        idx_actual = self.indice_actual()
        idx_nuevo = min(idx_actual + 1, len(lecciones) - 1)
        self.progreso["leccion_actual_id"] = lecciones[idx_nuevo]["id"]
        self.guardar()
        return lecciones[idx_nuevo]

    def avanzar_desde(self, leccion_id: str) -> dict | None:
        """Avanza desde una lección concreta, evitando estados internos obsoletos."""
        return self.siguiente_por_indice(leccion_id)

    def retroceder(self) -> dict | None:
        lecciones = self.lecciones()
        if not lecciones:
            return None
        idx = max(0, self.indice_actual() - 1)
        self.progreso["leccion_actual_id"] = lecciones[idx]["id"]
        self.guardar()
        return lecciones[idx]


    def indice_de(self, leccion_id: str) -> int:
        """Devuelve el índice real de una lección por id; -1 si no existe."""
        for i, leccion in enumerate(self.lecciones()):
            if leccion.get("id") == leccion_id:
                return i
        return -1

    def fijar_leccion_actual(self, leccion_id: str) -> dict | None:
        """Fija la lección actual por id y guarda el progreso."""
        leccion = self.leccion_por_id(leccion_id)
        if leccion:
            self.progreso["leccion_actual_id"] = leccion_id
            self.guardar()
        return leccion

    def siguiente_por_indice(self, leccion_id: str | None = None) -> dict | None:
        """Avanza estrictamente a la lección siguiente por índice, sin depender de estados obsoletos."""
        lecciones = self.lecciones()
        if not lecciones:
            return None
        actual_id = leccion_id or self.progreso.get("leccion_actual_id", "")
        idx = self.indice_de(actual_id)
        if idx < 0:
            idx = self.indice_actual()
        if idx >= len(lecciones) - 1:
            self.progreso["leccion_actual_id"] = lecciones[-1]["id"]
            self.guardar()
            return lecciones[-1]
        nueva = lecciones[idx + 1]
        self.progreso["leccion_actual_id"] = nueva["id"]
        self.guardar()
        return nueva

    def primera_pendiente_desde_actual(self) -> dict | None:
        """Si la lección actual ya está superada, salta a la primera pendiente posterior.

        Esto repara progresos guardados inconsistentes, por ejemplo:
        lecciones_superadas contiene la primera lección, pero leccion_actual_id sigue
        apuntando a esa primera lección.
        """
        lecciones = self.lecciones()
        if not lecciones:
            return None
        superadas = set(self.progreso.get("lecciones_superadas", []))
        actual_id = self.progreso.get("leccion_actual_id", "")
        idx = self.indice_de(actual_id)
        if idx < 0:
            idx = 0
        # Si la actual no está superada, no se toca: el alumno debe trabajarla.
        if lecciones[idx].get("id") not in superadas:
            return lecciones[idx]
        # Si está superada, intenta avanzar a la primera no superada posterior.
        for j in range(idx + 1, len(lecciones)):
            if lecciones[j].get("id") not in superadas:
                self.progreso["leccion_actual_id"] = lecciones[j]["id"]
                self.guardar()
                return lecciones[j]
        # Si todo está superado, deja la última lección como referencia.
        self.progreso["leccion_actual_id"] = lecciones[-1]["id"]
        self.guardar()
        return lecciones[-1]

    def seleccionar(self, leccion_id: str) -> dict | None:
        leccion = self.leccion_por_id(leccion_id)
        if leccion:
            self.progreso["leccion_actual_id"] = leccion_id
            self.guardar()
        return leccion

    def comprobar_respuesta(self, leccion_id: str, indice: int) -> ResultadoRespuesta:
        leccion = self.leccion_por_id(leccion_id)
        if not leccion:
            return ResultadoRespuesta(False, "No encuentro la lección actual.")

        # v4.0.5: la pregunta del desplegable se considera examen final de clase.
        resultado_flujo = self.flujo_docente.comprobar_examen_clase(leccion_id, int(indice))
        correcto = bool(resultado_flujo.correcto)
        mensaje = resultado_flujo.mensaje or leccion.get("feedback_correcto" if correcto else "feedback_error", "")

        self.progreso.setdefault("respuestas", []).append({
            "leccion_id": leccion_id,
            "respuesta": int(indice),
            "correcto": correcto,
            "tipo": "examen_clase",
            "desbloquea": resultado_flujo.desbloquea,
        })
        self.progreso["respuestas"] = self.progreso["respuestas"][-300:]
        if correcto:
            self.marcar_superada(leccion_id, origen="examen_clase")
        else:
            try:
                self.historial_alumno.registrar_clase(
                    clase_id=leccion_id,
                    titulo=leccion.get("titulo", ""),
                    evento="examen_clase_fallado",
                    correcto=False,
                    detalle={"respuesta": int(indice), "mensaje": mensaje}
                )
            except Exception:
                pass
            self.guardar()
        return ResultadoRespuesta(correcto, mensaje)

    def texto_resumen_progreso(self) -> str:
        total = len(self.lecciones())
        superadas = len(set(self.progreso.get("lecciones_superadas", [])))
        actual = self.leccion_actual()
        titulo = actual.get("titulo", "—") if actual else "—"
        return f"Lección {self.indice_actual() + 1}/{max(total, 1)} · Superadas: {superadas}/{total} · Actual: {titulo} · {self.flujo_docente.resumen()}"
