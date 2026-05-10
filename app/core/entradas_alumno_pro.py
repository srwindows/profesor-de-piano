from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import time


@dataclass
class EstadoEntradaAlumno:
    nombre: str
    activo: bool = False
    disponible: bool = True
    permanente: bool = False
    solicitado_por_profesor: bool = False
    motivo: str = ""
    ultima_activacion: str = ""
    ultima_observacion: str = ""


class GestorEntradasAlumnoPro:
    """Gobierna las cuatro entradas del alumno en modo Pro.

    Regla del proyecto:
    - MIDI siempre activo y continuo.
    - Historial siempre activo.
    - Cámara bajo petición voluntaria.
    - Sonido/micrófono bajo petición voluntaria.
    """

    def __init__(self):
        self.entradas: dict[str, EstadoEntradaAlumno] = {
            "midi": EstadoEntradaAlumno("MIDI", activo=True, permanente=True, motivo="Entrada permanente de bajo consumo."),
            "camara": EstadoEntradaAlumno("Cámara", activo=False, permanente=False, motivo="Solo bajo petición docente."),
            "sonido": EstadoEntradaAlumno("Sonido / micrófono", activo=False, permanente=False, motivo="Solo bajo petición docente."),
            "historial": EstadoEntradaAlumno("Historial pedagógico", activo=True, permanente=True, motivo="Memoria didáctica local."),
        }
        self.eventos: list[dict] = []
        self._ultimo_pedido: dict[str, float] = {}

    def estado(self, clave: str) -> EstadoEntradaAlumno:
        return self.entradas[clave]

    def resumen(self) -> str:
        midi = "activo continuo" if self.entradas["midi"].activo else "inactivo"
        cam = "activa" if self.entradas["camara"].activo else ("solicitada" if self.entradas["camara"].solicitado_por_profesor else "en espera")
        son = "activa" if self.entradas["sonido"].activo else ("solicitada" if self.entradas["sonido"].solicitado_por_profesor else "en espera")
        hist = "activo" if self.entradas["historial"].activo else "inactivo"
        return f"MIDI: {midi} · Cámara: {cam} · Sonido: {son} · Historial: {hist}"

    def como_dict(self) -> dict:
        return {k: asdict(v) for k, v in self.entradas.items()}

    def _evento(self, tipo: str, entrada: str, motivo: str = "", detalle: dict | None = None):
        self.eventos.append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tipo": tipo,
            "entrada": entrada,
            "motivo": motivo,
            "detalle": detalle or {},
        })
        self.eventos = self.eventos[-300:]

    def registrar_midi_continuo(self, detalle: dict | None = None):
        self._evento("midi_continuo", "midi", "MIDI activo permanente.", detalle or {})

    def solicitar_camara(self, motivo: str) -> bool:
        return self._solicitar("camara", motivo)

    def solicitar_sonido(self, motivo: str) -> bool:
        return self._solicitar("sonido", motivo)

    def _solicitar(self, entrada: str, motivo: str) -> bool:
        # Evita repetir la misma petición cada pocos segundos.
        ahora = time.monotonic()
        ultimo = self._ultimo_pedido.get(entrada, 0.0)
        if ahora - ultimo < 8.0:
            return False
        self._ultimo_pedido[entrada] = ahora

        e = self.entradas[entrada]
        e.solicitado_por_profesor = True
        e.motivo = motivo
        e.ultima_observacion = f"Profesor solicita activar {e.nombre}: {motivo}"
        self._evento("solicitud_profesor", entrada, motivo)
        return True

    def activar(self, entrada: str, motivo: str = ""):
        e = self.entradas[entrada]
        e.activo = True
        e.solicitado_por_profesor = False
        if motivo:
            e.motivo = motivo
        e.ultima_activacion = datetime.now().isoformat(timespec="seconds")
        e.ultima_observacion = f"{e.nombre} activa."
        self._evento("activada", entrada, motivo)

    def desactivar(self, entrada: str, motivo: str = ""):
        e = self.entradas[entrada]
        if e.permanente:
            e.activo = True
            e.ultima_observacion = f"{e.nombre} es permanente y no se desactiva."
            self._evento("no_desactivada_permanente", entrada, motivo)
            return
        e.activo = False
        e.solicitado_por_profesor = False
        if motivo:
            e.motivo = motivo
        e.ultima_observacion = f"{e.nombre} detenida."
        self._evento("desactivada", entrada, motivo)

    def registrar_observacion(self, entrada: str, observacion: str, detalle: dict | None = None):
        if entrada not in self.entradas:
            return
        self.entradas[entrada].ultima_observacion = observacion
        self._evento("observacion", entrada, observacion, detalle or {})

    def decidir_por_diagnostico_midi(self, diagnostico) -> list[dict]:
        """Sugiere activar cámara o sonido según lo que MIDI no puede explicar solo."""
        decisiones = []
        if diagnostico is None:
            return decisiones

        velocity_clase = getattr(diagnostico, "velocity_clase", "")
        correcto = getattr(diagnostico, "correcto", None)
        pulso = getattr(diagnostico, "pulso_clase", "")
        notas_sobrantes = getattr(diagnostico, "notas_sobrantes", []) or []
        notas_faltantes = getattr(diagnostico, "notas_faltantes", []) or []
        simultaneidad_ms = getattr(diagnostico, "simultaneidad_ms", None)

        if velocity_clase in {"demasiado_fuerte", "muy_suave"}:
            motivo = "El MIDI detecta una pulsación irregular. Conviene ver mano, muñeca y tensión."
            if self.solicitar_camara(motivo):
                decisiones.append({"entrada": "camara", "motivo": motivo})

        if pulso == "fuera_de_pulso" and correcto is not False:
            motivo = "El MIDI detecta problema de pulso. De momento basta MIDI y metrónomo; no hace falta cámara."
            self.registrar_observacion("midi", motivo, {"pulso": pulso})
            decisiones.append({"entrada": "midi", "motivo": motivo})

        if notas_sobrantes or notas_faltantes:
            motivo = "Hay notas sobrantes o faltantes. Conviene ver la mano para comprobar colocación."
            if self.solicitar_camara(motivo):
                decisiones.append({"entrada": "camara", "motivo": motivo})

        if simultaneidad_ms is not None and simultaneidad_ms > 120:
            motivo = "El acorde no baja suficientemente junto. Conviene escuchar y/o ver el ataque."
            if self.solicitar_sonido(motivo):
                decisiones.append({"entrada": "sonido", "motivo": motivo})

        return decisiones
