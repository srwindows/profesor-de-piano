from __future__ import annotations

import math
import time


class AudioInputManager:
    """Entrada de sonido bajo demanda.

    No graba audio en disco. Solo calcula métricas ligeras de nivel:
    RMS, pico y estado aproximado de señal. Se activa únicamente cuando el alumno
    lo permite o cuando el profesor lo solicita para una comprobación.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        self.sample_rate = int(sample_rate)
        self.block_size = int(block_size)
        self.stream = None
        self.error = ""
        self.activo = False
        self.ultimo_rms = 0.0
        self.ultimo_pico = 0.0
        self.ultimo_ts = 0.0

    def disponible(self) -> bool:
        try:
            import sounddevice  # noqa
            import numpy  # noqa
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def iniciar(self, dispositivo=None) -> bool:
        if self.activo:
            return True
        if not self.disponible():
            return False
        try:
            import sounddevice as sd
            import numpy as np

            def callback(indata, frames, time_info, status):
                try:
                    if indata is None:
                        return
                    arr = np.asarray(indata, dtype=np.float32)
                    if arr.size == 0:
                        return
                    self.ultimo_rms = float(np.sqrt(np.mean(np.square(arr))))
                    self.ultimo_pico = float(np.max(np.abs(arr)))
                    self.ultimo_ts = time.time()
                except Exception:
                    pass

            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=1,
                dtype="float32",
                callback=callback,
                device=dispositivo,
                latency="high",
            )
            self.stream.start()
            self.activo = True
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            self.activo = False
            try:
                if self.stream is not None:
                    self.stream.close()
            except Exception:
                pass
            self.stream = None
            return False

    def detener(self):
        stream = self.stream
        self.stream = None
        self.activo = False
        if stream is not None:
            try:
                if hasattr(stream, "abort"):
                    stream.abort()
                else:
                    stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

    def observacion(self) -> dict:
        rms = float(self.ultimo_rms or 0.0)
        pico = float(self.ultimo_pico or 0.0)
        if not self.activo:
            estado = "inactivo"
            texto = "Escucha desactivada."
        elif rms < 0.003:
            estado = "muy_bajo"
            texto = "La entrada de sonido es muy baja o no hay señal suficiente."
        elif pico > 0.95:
            estado = "saturacion"
            texto = "La entrada de sonido parece saturar. Baja ganancia o aléjate del micrófono."
        elif rms > 0.18:
            estado = "fuerte"
            texto = "El sonido entra con bastante nivel. Útil para detectar golpes o ataques bruscos."
        else:
            estado = "correcto"
            texto = "Entrada de sonido activa con nivel utilizable."

        return {
            "activo": self.activo,
            "rms": round(rms, 5),
            "pico": round(pico, 5),
            "estado": estado,
            "texto": texto,
            "ts": self.ultimo_ts,
            "graba_audio": False,
        }
