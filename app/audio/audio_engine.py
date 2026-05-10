import math, threading, time, os
from dataclasses import dataclass
try:
    import numpy as np
    import sounddevice as sd
except Exception:
    np = None
    sd = None

NOTAS = {"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}

def nota_a_midi(nombre: str) -> int:
    nombre = nombre.strip().upper()
    if len(nombre) >= 3 and nombre[1] == "#":
        nota, octava = nombre[:2], int(nombre[2:])
    else:
        nota, octava = nombre[0], int(nombre[1:])
    return 12 * (octava + 1) + NOTAS.get(nota, 0)

def midi_a_freq(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))

@dataclass
class Voz:
    nota: str
    freq: float
    velocity: int = 96
    amplitud: float = 1.0
    fase1: float = 0.0
    fase2: float = 0.0
    fase3: float = 0.0
    inicio: float = 0.0
    release_inicio: float | None = None
    nivel_release: float = 1.0
    release_duracion: float | None = None

@dataclass
class SonidoFeedback:
    muestras: object
    posicion: int = 0

class AudioEngine:
    def __init__(self, sample_rate=44100, block_size=256):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.volumen = 0.55
        self.forma_onda = "piano suave"
        self.activo = True
        self.reverb = 0.22
        self.delay = 0.08
        self.brillo = 0.55
        self.sustain = 0.35
        self.voces = {}
        self.feedback_sounds = []
        self.lock = threading.RLock()
        self.stream = None
        self._cerrando_stream = False
        self._arrancando_stream = False
        self._ultimo_intento_inicio = 0.0
        self.error = ""
        self.delay_buffer = None
        self.delay_pos = 0
        self.reverb_mem_l = 0.0
        self.reverb_mem_r = 0.0
        self.attack = 0.008
        self.decay = 0.55
        self.release = 0.45

    def disponible(self):
        return sd is not None and np is not None

    def iniciar(self):
        if getattr(self, "_cerrando_stream", False):
            return False
        if not self.activo:
            self.error = "Audio desactivado."
            return False
        if not self.disponible():
            self.error = "Faltan numpy/sounddevice. Instala requirements.txt."
            return False
        if self.stream is not None:
            return True
        try:
            # Evita configuraciones agresivas de PortAudio que en algunos Debian/Xfce
            # pueden terminar en violación de segmento al arrancar la aplicación.
            block = int(os.environ.get("PROFESOR_AUDIO_BLOCK", self.block_size or 512))
            block = max(256, min(2048, block))
            latency = os.environ.get("PROFESOR_AUDIO_LATENCY", "high")
            self.delay_buffer = np.zeros((int(self.sample_rate * 0.35), 2), dtype=np.float32)
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=block,
                channels=2,
                dtype="float32",
                callback=self._callback,
                latency=latency,
            )
            self.stream.start()
            self.error = ""
            return True
        except Exception as exc:
            try:
                if self.stream is not None:
                    self.stream.close()
            except Exception:
                pass
            self.stream = None
            self.error = str(exc)
            return False

    def iniciar_async(self):
        """Arranca PortAudio en segundo plano para no bloquear la interfaz.

        En algunos equipos Linux/PipeWire/ALSA la apertura de un OutputStream
        puede tardar o quedarse esperando al dispositivo. Si eso ocurre desde
        el hilo gráfico, Qt muestra "la ventana no responde" aunque no haya
        traceback en consola. Esta ruta deja preparada la nota/feedback y abre
        el stream en un hilo auxiliar.
        """
        if not self.activo:
            self.error = "Audio desactivado."
            return False
        if not self.disponible():
            self.error = "Faltan numpy/sounddevice. Instala requirements.txt."
            return False
        if self.stream is not None:
            return True
        ahora = time.monotonic()
        with self.lock:
            if self.stream is not None:
                return True
            if self._arrancando_stream:
                return False
            # Evita crear hilos de arranque en cascada si el backend no responde.
            if ahora - float(getattr(self, "_ultimo_intento_inicio", 0.0) or 0.0) < 0.85:
                return False
            self._arrancando_stream = True
            self._ultimo_intento_inicio = ahora

        def _worker():
            try:
                self.iniciar()
            finally:
                with self.lock:
                    self._arrancando_stream = False

        threading.Thread(target=_worker, daemon=True).start()
        return False

    def _cerrar_stream_seguro(self, abortar: bool = True):
        """Cierra PortAudio de forma defensiva para Debian/ALSA."""
        stream = self.stream
        self.stream = None
        if stream is None:
            return
        try:
            if abortar and hasattr(stream, "abort"):
                stream.abort()
            else:
                try:
                    if getattr(stream, "active", False):
                        stream.stop()
                except Exception:
                    try:
                        stream.stop()
                    except Exception:
                        pass
        except Exception as exc:
            self.error = str(exc)
        try:
            stream.close()
        except Exception as exc:
            self.error = str(exc)

    def parar(self):
        self._cerrando_stream = True
        with self.lock:
            self.voces.clear()
            self.feedback_sounds.clear()
        self._cerrar_stream_seguro(abortar=True)
        self._cerrando_stream = False

    def configurar(self, volumen=None, forma_onda=None, activo=None, reverb=None, delay=None, brillo=None, sustain=None):
        if volumen is not None: self.volumen = max(0.0, min(1.0, float(volumen)))
        if forma_onda is not None: self.forma_onda = str(forma_onda)
        if activo is not None: self.activo = bool(activo)
        if reverb is not None: self.reverb = max(0.0, min(1.0, float(reverb)))
        if delay is not None: self.delay = max(0.0, min(0.75, float(delay)))
        if brillo is not None: self.brillo = max(0.0, min(1.0, float(brillo)))
        if sustain is not None: self.sustain = max(0.05, min(0.95, float(sustain)))

    def _normalizar_velocity(self, velocity) -> int:
        try:
            return max(1, min(127, int(velocity)))
        except Exception:
            return 96

    def _velocity_a_amplitud(self, velocity: int) -> float:
        """Convierte MIDI velocity a amplitud perceptual para teclados contrapesados."""
        v = max(1, min(127, int(velocity))) / 127.0
        return 0.015 + (v ** 2.15) * 1.55

    def note_on(self, nota, velocity=96):
        if not self.activo:
            return
        if self.stream is None:
            self.iniciar_async()
        vel = self._normalizar_velocity(velocity)
        with self.lock:
            self.voces[nota] = Voz(
                nota=nota,
                freq=midi_a_freq(nota_a_midi(nota)),
                velocity=vel,
                amplitud=self._velocity_a_amplitud(vel),
                inicio=time.time(),
            )

    def note_off(self, nota, release_segundos=None):
        """Libera una nota sin volver a dispararla.

        Importante para el piano virtual: si release_segundos es 0 o menor,
        la nota se corta de forma inmediata. Eso evita el falso "segundo ataque"
        que se percibía al soltar el ratón sobre una tecla.
        """
        with self.lock:
            if release_segundos is not None:
                try:
                    if float(release_segundos) <= 0.0:
                        self.voces.pop(nota, None)
                        return
                except Exception:
                    pass
            voz = self.voces.get(nota)
            if voz and voz.release_inicio is None:
                ahora = time.time()
                voz.release_inicio = ahora
                try:
                    if release_segundos is not None:
                        voz.release_duracion = max(0.001, min(1.5, float(release_segundos)))
                except Exception:
                    voz.release_duracion = None
                voz.nivel_release = self._env(voz, ahora)

    def cortar_nota(self, nota, limpiar_cola=False):
        """Corta una nota inmediatamente sin envolvente de release.

        Se usa en el piano virtual educativo: al levantar el botón del ratón
        debe cesar la nota, no sonar otra cola que el alumno interprete como
        una segunda pulsación.
        """
        with self.lock:
            self.voces.pop(nota, None)
            if limpiar_cola:
                try:
                    if self.delay_buffer is not None:
                        self.delay_buffer[:] = 0
                    self.reverb_mem_l = 0.0
                    self.reverb_mem_r = 0.0
                except Exception:
                    pass

    def sonido_acierto(self):
        """Campana ascendente agradable al superar un ejercicio."""
        self._crear_feedback("acierto")

    def sonido_error(self):
        """Aviso descendente corto al fallar un ejercicio."""
        self._crear_feedback("error")


    def sonido_celebracion(self, tipo="leccion"):
        """Pequeña música de celebración para lecciones, retos y niveles.

        No depende de archivos externos: se sintetiza en memoria para mantener
        el ZIP ligero y evitar añadir carpetas pesadas de audio.
        """
        self._crear_celebracion(tipo)

    def _crear_celebracion(self, tipo="leccion"):
        if not self.activo or np is None:
            return
        if self.stream is None:
            self.iniciar_async()
        sr = self.sample_rate
        tipo = str(tipo or "leccion")
        if tipo == "nivel":
            notas = [523.25, 659.25, 783.99, 1046.50, 1318.51, 1567.98]
            dur_nota = 0.18
            cola = 0.95
            base_amp = 0.38
        elif tipo == "reto":
            notas = [523.25, 659.25, 783.99, 1174.66]
            dur_nota = 0.16
            cola = 0.70
            base_amp = 0.34
        else:
            notas = [523.25, 659.25, 783.99]
            dur_nota = 0.15
            cola = 0.55
            base_amp = 0.32
        total = int(sr * (dur_nota * len(notas) + cola))
        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)
        for i, freq in enumerate(notas):
            start = int(i * dur_nota * sr)
            dur = int((dur_nota + cola * 0.55) * sr)
            end = min(total, start + dur)
            t = np.arange(end - start, dtype=np.float32) / sr
            ataque = np.minimum(1.0, t / 0.012)
            env = ataque * np.exp(-3.2 * t)
            tono = (
                np.sin(2 * math.pi * freq * t)
                + 0.35 * np.sin(2 * math.pi * freq * 2.0 * t)
                + 0.18 * np.sin(2 * math.pi * freq * 3.0 * t)
            ) * env * base_amp
            pan = -0.35 + (0.70 * (i / max(1, len(notas)-1)))
            out_l[start:end] += tono * (0.75 - pan * 0.25)
            out_r[start:end] += tono * (0.75 + pan * 0.25)
        # Acorde final suave para nivel/reto.
        if tipo in {"reto", "nivel"}:
            chord_freqs = [523.25, 659.25, 783.99]
            if tipo == "nivel":
                chord_freqs += [1046.50]
            start = int((dur_nota * len(notas) + 0.08) * sr)
            dur = min(total - start, int(sr * (0.80 if tipo == "nivel" else 0.55)))
            if dur > 0:
                t = np.arange(dur, dtype=np.float32) / sr
                env = np.minimum(1.0, t / 0.018) * np.exp(-2.2 * t)
                chord = np.zeros(dur, dtype=np.float32)
                for freq in chord_freqs:
                    chord += np.sin(2 * math.pi * freq * t)
                chord = (chord / max(1, len(chord_freqs))) * env * 0.38
                out_l[start:start+dur] += chord * 0.90
                out_r[start:start+dur] += chord * 1.00
        stereo = np.column_stack((out_l, out_r)).astype(np.float32)
        stereo = np.clip(stereo, -0.85, 0.85)
        with self.lock:
            self.feedback_sounds = self.feedback_sounds[-8:]
            self.feedback_sounds.append(SonidoFeedback(stereo))


    def sonido_metronomo(self, acento=False):
        """Click corto de metrónomo sintetizado en el motor de audio.

        Devuelve True si ha podido programar el sonido. Es más fiable que
        QApplication.beep(), que en muchos escritorios Linux puede estar silenciado.
        """
        if not self.activo or np is None:
            return False
        try:
            if self.stream is None:
                self.iniciar_async()
            sr = self.sample_rate
            dur = 0.075 if acento else 0.052
            t = np.linspace(0.0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
            freq = 1760.0 if acento else 1120.0
            env = np.exp(-52.0 * t) * np.minimum(1.0, t / 0.003)
            click = (np.sin(2 * math.pi * freq * t) + 0.22 * np.sin(2 * math.pi * freq * 2.01 * t)) * env
            amp = 0.42 if acento else 0.30
            mono = np.clip(click * amp, -0.8, 0.8).astype(np.float32)
            stereo = np.column_stack((mono, mono)).astype(np.float32)
            with self.lock:
                self.feedback_sounds = self.feedback_sounds[-8:]
                self.feedback_sounds.append(SonidoFeedback(stereo))
            return True
        except Exception as exc:
            try:
                self.error = f"Error metrónomo: {exc}"
            except Exception:
                pass
            return False

    def _crear_feedback(self, tipo):
        if not self.activo or np is None:
            return
        if self.stream is None:
            self.iniciar_async()
        sr = self.sample_rate
        if tipo == "acierto":
            dur = 0.62
            t = np.linspace(0.0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
            env1 = np.exp(-3.8 * t) * np.minimum(1.0, t / 0.018)
            campana1 = np.sin(2 * math.pi * 523.25 * t) + 0.35 * np.sin(2 * math.pi * 1046.5 * t)
            t2 = np.maximum(0, t - 0.16)
            env2 = (t >= 0.16).astype(np.float32) * np.exp(-4.2 * t2)
            campana2 = np.sin(2 * math.pi * 783.99 * t2) * env2
            mono = (campana1 * env1 * 0.45) + (campana2 * 0.38)
            pan_l = mono * 0.88
            pan_r = mono * 1.00
        else:
            dur = 0.34
            t = np.linspace(0.0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
            env = np.exp(-7.0 * t) * np.minimum(1.0, t / 0.01)
            f_desc = 260.0 - 90.0 * (t / dur)
            fase = 2 * math.pi * np.cumsum(f_desc) / sr
            mono = (np.sin(fase) + 0.28 * np.sin(2.01 * fase)) * env * 0.55
            pan_l = mono * 1.00
            pan_r = mono * 0.82
        stereo = np.column_stack((pan_l, pan_r)).astype(np.float32)
        stereo = np.clip(stereo, -0.85, 0.85)
        with self.lock:
            self.feedback_sounds = self.feedback_sounds[-8:]
            self.feedback_sounds.append(SonidoFeedback(stereo))

    def _forma_base(self, fases, mult=1.0):
        if self.forma_onda == "órgano":
            return np.sin(fases)
        if self.forma_onda == "pad cálido":
            return np.sin(fases) * 0.75 + np.sin(fases * 0.5) * 0.20
        if self.forma_onda == "sierra":
            return 2.0 * ((fases / (2 * math.pi)) % 1.0) - 1.0
        if self.forma_onda == "cuadrada":
            return np.sign(np.sin(fases))
        return np.sin(fases)

    def _env(self, voz, ahora):
        edad = max(0.0, ahora - voz.inicio)
        if edad < self.attack:
            env = edad / self.attack
        else:
            env = self.sustain + (1.0 - self.sustain) * math.exp(-(edad - self.attack) / max(0.05, self.decay))
        if voz.release_inicio is not None:
            r = ahora - voz.release_inicio
            dur_rel = voz.release_duracion if voz.release_duracion is not None else self.release
            env = voz.nivel_release * max(0.0, 1.0 - r / max(0.015, dur_rel)) ** 1.6
        return env

    def _render_voz(self, voz, frames, ahora):
        t = np.arange(frames)
        inc1 = 2 * math.pi * voz.freq / self.sample_rate
        inc2 = 2 * math.pi * (voz.freq * 2.01) / self.sample_rate
        inc3 = 2 * math.pi * (voz.freq * 3.0) / self.sample_rate
        f1 = voz.fase1 + inc1 * t
        f2 = voz.fase2 + inc2 * t
        f3 = voz.fase3 + inc3 * t
        dinamica = max(0.0, min(1.0, voz.velocity / 127.0))
        b = max(0.0, min(1.0, self.brillo * 0.72 + dinamica * 0.34))
        if self.forma_onda == "piano suave":
            señal = np.sin(f1) * 0.88 + np.sin(f2) * (0.16 + b*0.22) + np.sin(f3) * (0.06 + b*0.10)
            señal *= np.exp(-t / (self.sample_rate * (1.2 + self.sustain)))
        elif self.forma_onda == "pad cálido":
            señal = np.sin(f1) * 0.65 + np.sin(f1 * 0.997) * 0.28 + np.sin(f2) * (0.08 + b*0.12)
        elif self.forma_onda == "órgano":
            señal = np.sin(f1) * 0.70 + np.sin(f2) * 0.26 + np.sin(f3) * 0.16
        else:
            señal = self._forma_base(f1)
        voz.fase1 = float((f1[-1] + inc1) % (2 * math.pi))
        voz.fase2 = float((f2[-1] + inc2) % (2 * math.pi))
        voz.fase3 = float((f3[-1] + inc3) % (2 * math.pi))
        env = self._env(voz, ahora)
        return señal.astype(np.float32) * env * voz.amplitud

    def _callback(self, outdata, frames, time_info, status):
        if np is None:
            return
        mezcla = np.zeros(frames, dtype=np.float32)
        feedback_stereo = np.zeros((frames, 2), dtype=np.float32)
        ahora = time.time()
        quitar = []
        with self.lock:
            total = max(1, len(self.voces))
            for nota, voz in list(self.voces.items()):
                mezcla += self._render_voz(voz, frames, ahora) / math.sqrt(total)
                dur_rel = voz.release_duracion if voz.release_duracion is not None else self.release
                if voz.release_inicio is not None and ahora - voz.release_inicio >= max(0.015, dur_rel):
                    quitar.append(nota)
            for nota in quitar:
                self.voces.pop(nota, None)
            feedback_restante = []
            for fb in self.feedback_sounds:
                fin = min(fb.posicion + frames, len(fb.muestras))
                tramo = fb.muestras[fb.posicion:fin]
                if len(tramo):
                    feedback_stereo[:len(tramo), :] += tramo
                fb.posicion = fin
                if fb.posicion < len(fb.muestras):
                    feedback_restante.append(fb)
            self.feedback_sounds = feedback_restante
        mezcla *= self.volumen * 0.75
        stereo = np.column_stack((mezcla, mezcla)).astype(np.float32)
        stereo += feedback_stereo * self.volumen
        if self.delay_buffer is not None and self.delay > 0:
            db = self.delay_buffer
            for i in range(frames):
                old = db[self.delay_pos].copy()
                stereo[i, 0] += old[1] * self.delay * 0.45
                stereo[i, 1] += old[0] * self.delay * 0.45
                db[self.delay_pos] = stereo[i] + old * 0.28
                self.delay_pos = (self.delay_pos + 1) % len(db)
        if self.reverb > 0:
            for i in range(frames):
                self.reverb_mem_l = self.reverb_mem_l * 0.985 + stereo[i, 0] * 0.015
                self.reverb_mem_r = self.reverb_mem_r * 0.982 + stereo[i, 1] * 0.018
                stereo[i, 0] += self.reverb_mem_r * self.reverb * 1.7
                stereo[i, 1] += self.reverb_mem_l * self.reverb * 1.7
        outdata[:] = np.clip(stereo, -0.95, 0.95)
