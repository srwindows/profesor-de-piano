import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from app.config import PROGRESO_PATH

@dataclass
class EstadoProgreso:
    nivel_actual: str = "sin_evaluar"
    lecciones_superadas: int = 0
    ejercicios_superados: int = 0
    ejercicios_fallados: int = 0
    ultimo_ejercicio_id: str = ""
    indice_ejercicio: int = 0
    racha: int = 0
    modo_inicio: str = "nuevo"
    examenes_aprobados: int = 0
    examenes_fallados: int = 0
    modo_examen: bool = False
    historial: list[dict] = field(default_factory=list)
    lecciones_guiadas_superadas: list[str] = field(default_factory=list)
    leccion_guiada_actual: str = ""
    ultima_pantalla: str = "inicio"

    # v1.9.7: memoria pedagógica para repaso inteligente.
    repasos_pendientes: list[str] = field(default_factory=list)
    mapa_fallos: dict = field(default_factory=dict)
    mapa_aciertos: dict = field(default_factory=dict)
    ultima_recomendacion: str = ""

class GestorProgreso:
    def __init__(self, ruta: Path = PROGRESO_PATH):
        self.ruta = ruta
        self.estado = EstadoProgreso()
        self.cargar()

    def cargar(self):
        if not self.ruta.exists():
            self.guardar()
            return
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            base = asdict(EstadoProgreso())
            base.update(datos)
            self.estado = EstadoProgreso(**base)
            self._normalizar_campos_nuevos()
        except Exception:
            self.estado = EstadoProgreso()
            self.guardar()

    def _normalizar_campos_nuevos(self):
        if self.estado.repasos_pendientes is None:
            self.estado.repasos_pendientes = []
        if self.estado.mapa_fallos is None:
            self.estado.mapa_fallos = {}
        if self.estado.mapa_aciertos is None:
            self.estado.mapa_aciertos = {}
        if self.estado.ultima_recomendacion is None:
            self.estado.ultima_recomendacion = ""
        self.estado.repasos_pendientes = list(dict.fromkeys([x for x in self.estado.repasos_pendientes if x]))[-50:]
        self.guardar()

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps(asdict(self.estado), indent=2, ensure_ascii=False), encoding="utf-8")

    def establecer_nivel(self, nivel: str, modo_inicio: str, reiniciar_indice: bool = False):
        self.estado.nivel_actual = nivel
        self.estado.modo_inicio = modo_inicio
        self.estado.modo_examen = False
        if reiniciar_indice:
            self.estado.indice_ejercicio = 0
            self.estado.racha = 0
        self.guardar()

    def registrar_resultado(self, ejercicio_id: str, superado: bool):
        ejercicio_id = str(ejercicio_id or "").strip()
        self.estado.ultimo_ejercicio_id = ejercicio_id
        self.estado.historial.append({"id": ejercicio_id, "superado": bool(superado)})
        self.estado.historial = self.estado.historial[-300:]

        if superado:
            self.estado.ejercicios_superados += 1
            self.estado.lecciones_superadas += 1
            self.estado.racha += 1
            self.estado.indice_ejercicio += 1
            if ejercicio_id:
                self.estado.mapa_aciertos[ejercicio_id] = int(self.estado.mapa_aciertos.get(ejercicio_id, 0)) + 1
                self.estado.repasos_pendientes = [x for x in self.estado.repasos_pendientes if x != ejercicio_id]
                self.estado.ultima_recomendacion = "Ejercicio superado. Si estaba en repaso, queda retirado de la cola."
        else:
            self.estado.ejercicios_fallados += 1
            self.estado.racha = 0
            if ejercicio_id:
                self.estado.mapa_fallos[ejercicio_id] = int(self.estado.mapa_fallos.get(ejercicio_id, 0)) + 1
                cola = [x for x in self.estado.repasos_pendientes if x != ejercicio_id]
                cola.insert(0, ejercicio_id)
                self.estado.repasos_pendientes = cola[:50]
                self.estado.ultima_recomendacion = "Ejercicio añadido al repaso inteligente para repetirlo con explicación."
        self.guardar()

    def retroceder_para_repaso(self):
        self.estado.indice_ejercicio = max(0, self.estado.indice_ejercicio - 1)
        self.guardar()

    def iniciar_examen(self):
        self.estado.modo_examen = True
        self.estado.indice_ejercicio = 0
        self.estado.racha = 0
        self.guardar()

    def finalizar_examen(self, aprobado: bool):
        self.estado.modo_examen = False
        if aprobado:
            self.estado.examenes_aprobados += 1
        else:
            self.estado.examenes_fallados += 1
        self.guardar()

    def registrar_leccion_guiada(self, leccion_id: str):
        if leccion_id and leccion_id not in self.estado.lecciones_guiadas_superadas:
            self.estado.lecciones_guiadas_superadas.append(leccion_id)
        self.estado.leccion_guiada_actual = leccion_id
        self.estado.ultima_pantalla = "teoria_nivel_0"
        self.guardar()

    def establecer_leccion_guiada_actual(self, leccion_id: str):
        self.estado.leccion_guiada_actual = leccion_id
        self.estado.ultima_pantalla = "teoria_nivel_0"
        self.guardar()

    def limpiar_repasos_superados(self):
        """Elimina de la cola los ejercicios con al menos un acierto posterior."""
        if not self.estado.repasos_pendientes:
            return
        self.estado.repasos_pendientes = [
            eid for eid in self.estado.repasos_pendientes
            if int(self.estado.mapa_fallos.get(eid, 0)) > int(self.estado.mapa_aciertos.get(eid, 0))
        ][:50]
        self.guardar()

    def estadisticas(self) -> dict:
        total = self.estado.ejercicios_superados + self.estado.ejercicios_fallados
        tasa = int((self.estado.ejercicios_superados / total) * 100) if total else 0
        return {
            "total": total,
            "tasa": tasa,
            "racha": self.estado.racha,
            "examenes_aprobados": self.estado.examenes_aprobados,
            "repasos_pendientes": len(self.estado.repasos_pendientes),
        }
