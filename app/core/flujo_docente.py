import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from app.config import DATA_DIR


FLUJO_NIVEL_0_PATH = DATA_DIR / "flujo_docente_nivel_0.json"
PROGRESO_FLUJO_PATH = DATA_DIR / "progreso_flujo_docente.json"


def normalizar_nivel_id(nivel: str | int | None) -> str:
    texto = str(nivel if nivel is not None else "nivel_0").strip().lower()
    alias = {
        "0": "nivel_0",
        "n0": "nivel_0",
        "inicial": "nivel_0",
        "1": "nivel_1",
        "n1": "nivel_1",
        "2": "nivel_2",
        "n2": "nivel_2",
    }
    return alias.get(texto, texto if texto.startswith("nivel_") else "nivel_0")


def numero_nivel(nivel: str | int | None) -> int:
    nivel_id = normalizar_nivel_id(nivel)
    try:
        return int(nivel_id.rsplit("_", 1)[1])
    except Exception:
        return 0


def ruta_flujo_por_nivel(nivel: str | int | None) -> Path:
    n = numero_nivel(nivel)
    return DATA_DIR / f"flujo_docente_nivel_{n}.json"


def ruta_progreso_flujo_por_nivel(nivel: str | int | None) -> Path:
    n = numero_nivel(nivel)
    if n == 0:
        return PROGRESO_FLUJO_PATH
    return DATA_DIR / f"progreso_flujo_docente_nivel_{n}.json"


@dataclass
class ResultadoFase:
    correcto: bool
    mensaje: str
    desbloquea: str = ""


class MotorFlujoDocente:
    """Controla el flujo real de cada clase.

    Regla:
    teoría -> ejercicios asociados -> examen final de clase -> siguiente clase.
    La última clase desbloquea el examen global del nivel.
    """

    def __init__(
        self,
        ruta_flujo: Path | None = None,
        ruta_progreso: Path | None = None,
        nivel: str | int | None = "nivel_0",
    ):
        self.nivel_id = normalizar_nivel_id(nivel)
        self.nivel_numero = numero_nivel(self.nivel_id)
        self.ruta_flujo = Path(ruta_flujo) if ruta_flujo else ruta_flujo_por_nivel(self.nivel_id)
        self.ruta_progreso = Path(ruta_progreso) if ruta_progreso else ruta_progreso_flujo_por_nivel(self.nivel_id)
        self.datos = {}
        self.progreso = {}
        self.cargar()

    def cargar(self):
        try:
            self.datos = json.loads(self.ruta_flujo.read_text(encoding="utf-8"))
        except Exception:
            self.datos = {"nivel": self.nivel_numero, "clases": [], "examen_global": {}}
        self._cargar_progreso()

    def _cargar_progreso(self):
        base = {
            "version": "4.0.5",
            "nivel_actual": self.nivel_numero,
            "clase_actual_id": self.primera_clase_id(),
            "fase_actual": "teoria",
            "teoria_superada": [],
            "ejercicios_superados": {},
            "examenes_clase_superados": [],
            "examen_global_superado": False,
            "eventos": []
        }
        if self.ruta_progreso.exists():
            try:
                datos = json.loads(self.ruta_progreso.read_text(encoding="utf-8"))
                if isinstance(datos, dict):
                    base.update(datos)
            except Exception:
                pass
        if not base.get("clase_actual_id"):
            base["clase_actual_id"] = self.primera_clase_id()
        self.progreso = base
        self.guardar()

    def guardar(self):
        self.ruta_progreso.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_progreso.write_text(json.dumps(self.progreso, indent=2, ensure_ascii=False), encoding="utf-8")

    def _evento(self, tipo: str, clase_id: str, detalle: dict | None = None):
        self.progreso.setdefault("eventos", []).append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tipo": tipo,
            "clase_id": clase_id,
            "detalle": detalle or {}
        })
        self.progreso["eventos"] = self.progreso["eventos"][-500:]
        self.guardar()

    def clases(self) -> list[dict]:
        return sorted(self.datos.get("clases", []), key=lambda x: x.get("orden", 0))

    def primera_clase_id(self) -> str:
        clases = self.clases()
        return clases[0].get("id", "") if clases else ""

    def clase_por_id(self, clase_id: str) -> dict | None:
        for clase in self.clases():
            if clase.get("id") == clase_id:
                return clase
        return None

    def clase_actual(self) -> dict | None:
        return self.clase_por_id(self.progreso.get("clase_actual_id", ""))

    def fase_actual(self) -> str:
        return self.progreso.get("fase_actual", "teoria")

    def estado_clase(self, clase_id: str) -> dict:
        clase = self.clase_por_id(clase_id) or {}
        ejercicios = clase.get("ejercicios_asociados", [])
        superados = set(self.progreso.get("ejercicios_superados", {}).get(clase_id, []))
        return {
            "clase_id": clase_id,
            "teoria_superada": clase_id in set(self.progreso.get("teoria_superada", [])),
            "ejercicios_total": len(ejercicios),
            "ejercicios_superados": len(superados),
            "examen_clase_superado": clase_id in set(self.progreso.get("examenes_clase_superados", [])),
            "puede_examen": len(ejercicios) == len(superados) and clase_id in set(self.progreso.get("teoria_superada", [])),
            "puede_avanzar": clase_id in set(self.progreso.get("examenes_clase_superados", [])),
        }

    def marcar_teoria_superada(self, clase_id: str) -> ResultadoFase:
        lista = list(self.progreso.get("teoria_superada", []))
        if clase_id not in lista:
            lista.append(clase_id)
        self.progreso["teoria_superada"] = lista
        self.progreso["fase_actual"] = "ejercicios"
        self._evento("teoria_superada", clase_id)
        return ResultadoFase(True, "Teoría superada. Ahora toca realizar los ejercicios asociados.", "ejercicios")

    def marcar_ejercicio_superado(self, clase_id: str, ejercicio_id: str) -> ResultadoFase:
        mapa = dict(self.progreso.get("ejercicios_superados", {}))
        lista = list(mapa.get(clase_id, []))
        if ejercicio_id and ejercicio_id not in lista:
            lista.append(ejercicio_id)
        mapa[clase_id] = lista
        self.progreso["ejercicios_superados"] = mapa

        estado = self.estado_clase(clase_id)
        if estado["ejercicios_total"] > 0 and estado["ejercicios_superados"] >= estado["ejercicios_total"]:
            self.progreso["fase_actual"] = "examen_clase"
            msg = "Ejercicios asociados superados. Se desbloquea el examen final de la clase."
            desbloquea = "examen_clase"
        else:
            msg = f"Ejercicio superado. Progreso: {estado['ejercicios_superados']}/{estado['ejercicios_total']}."
            desbloquea = "ejercicios"
        self._evento("ejercicio_superado", clase_id, {"ejercicio_id": ejercicio_id})
        return ResultadoFase(True, msg, desbloquea)

    def comprobar_examen_clase(self, clase_id: str, respuesta_indice: int) -> ResultadoFase:
        clase = self.clase_por_id(clase_id)
        if not clase:
            return ResultadoFase(False, "No encuentro esta clase.")
        examen = clase.get("examen_clase", {})
        correcto = int(respuesta_indice) == int(examen.get("respuesta_correcta", -1))
        if not correcto:
            self._evento("examen_clase_error", clase_id, {"respuesta": respuesta_indice})
            return ResultadoFase(False, examen.get("feedback_error", "Respuesta incorrecta. Repasa la teoría y los ejercicios."))

        lista = list(self.progreso.get("examenes_clase_superados", []))
        if clase_id not in lista:
            lista.append(clase_id)
        self.progreso["examenes_clase_superados"] = lista
        desbloquea = examen.get("desbloquea_si_aprueba", "")
        self.progreso["fase_actual"] = "teoria"
        if desbloquea and not str(desbloquea).startswith("examen_global_"):
            self.progreso["clase_actual_id"] = desbloquea
        self._evento("examen_clase_superado", clase_id, {"desbloquea": desbloquea})
        msg = examen.get("feedback_correcto", "Examen de clase superado.")
        if str(desbloquea).startswith("examen_global_"):
            msg += f" Has superado la última clase. Se desbloquea el examen global del Nivel {self.nivel_numero}."
        else:
            msg += " Se desbloquea la siguiente clase."
        self.guardar()
        return ResultadoFase(True, msg, desbloquea)

    def examen_global_desbloqueado(self) -> bool:
        ids = {c.get("id") for c in self.clases()}
        superados = set(self.progreso.get("examenes_clase_superados", []))
        return bool(ids) and ids.issubset(superados)

    def resumen(self) -> str:
        total = len(self.clases())
        examenes = len(set(self.progreso.get("examenes_clase_superados", [])))
        clase = self.clase_actual() or {}
        return f"Flujo docente: clase {clase.get('orden', '-')}/{total} · fase {self.fase_actual()} · exámenes de clase {examenes}/{total}"
