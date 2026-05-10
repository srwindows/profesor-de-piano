from __future__ import annotations


class RelojMusical:
    """Reloj musical común para demo, pizarra, piano y metrónomo."""

    def __init__(self, bpm: int = 60, compas: str = "4/4"):
        self.bpm_base = max(20, int(bpm or 60))
        self.bpm = self.bpm_base
        self.compas = str(compas or "4/4")
        self.compas_num = self._compas_num(self.compas)
        self.posicion_ms = 0
        self.duracion_ms = 0
        self.activo = False
        self._beat_anterior = 0

    def configurar(self, bpm: int = 60, compas: str = "4/4", duracion_ms: int = 0):
        self.bpm_base = max(20, int(bpm or 60))
        self.bpm = self.bpm_base
        self.compas = str(compas or "4/4")
        self.compas_num = self._compas_num(self.compas)
        self.duracion_ms = max(0, int(duracion_ms or 0))
        self.stop()

    def _compas_num(self, compas: str) -> int:
        try:
            return max(1, int(str(compas).split("/", 1)[0]))
        except Exception:
            return 4

    def play(self):
        self.activo = True
        self._beat_anterior = self.beat_absoluto()

    def pause(self):
        self.activo = False

    def stop(self):
        self.activo = False
        self.posicion_ms = 0
        self._beat_anterior = 0

    def set_bpm(self, bpm: int):
        self.bpm = max(20, min(240, int(bpm or self.bpm)))

    def avanzar(self, delta_real_ms: int) -> dict:
        if self.activo:
            factor = self.bpm / max(1, self.bpm_base)
            self.posicion_ms += max(1, int(delta_real_ms or 1)) * factor
            if self.duracion_ms:
                self.posicion_ms = min(float(self.duracion_ms), self.posicion_ms)
        beat_abs = self.beat_absoluto()
        cambio_beat = beat_abs != self._beat_anterior
        self._beat_anterior = beat_abs
        return {
            "tiempo_ms": int(self.posicion_ms),
            "bpm": int(self.bpm),
            "beat": self.beat_compas(),
            "beat_absoluto": beat_abs,
            "compas": self.compas_actual(),
            "cambio_beat": cambio_beat,
            "primer_tiempo": self.beat_compas() == 1,
            "progreso": self.progreso(),
        }

    def beat_ms(self) -> float:
        return 60000.0 / max(1, self.bpm)

    def beat_absoluto(self) -> int:
        return int(float(self.posicion_ms) // self.beat_ms()) + 1

    def beat_compas(self) -> int:
        return ((self.beat_absoluto() - 1) % max(1, self.compas_num)) + 1

    def compas_actual(self) -> int:
        return ((self.beat_absoluto() - 1) // max(1, self.compas_num)) + 1

    def progreso(self) -> float:
        if not self.duracion_ms:
            return 0.0
        return max(0.0, min(1.0, float(self.posicion_ms) / max(1.0, float(self.duracion_ms))))
