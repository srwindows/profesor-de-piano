import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import signal
import wave
import hashlib
import queue
from pathlib import Path
from typing import Callable, Optional

from app.config import BASE_DIR


class VozAvatar:
    """Voz del avatar usando exclusivamente Piper TTS.

    Cambios integrados:
    - No usa voz robótica de respaldo.
    - Cancela la locución anterior antes de iniciar otra.
    - Evita que voces antiguas se reproduzcan después de un doble clic.
    - Detiene generación/reproducción al cerrar el programa.
    - Usa --length-scale para que la velocidad sea real.
    - Permite pausas configurables tras comas y puntos.
    """

    def __init__(self):
        self.proceso = None
        self._proceso_generacion = None
        self._proceso_reproduccion = None
        self.lock = threading.RLock()
        self.ultimo_error = ""
        self.ultimo_motor = ""
        self.ultimo_reproductor = ""
        self.ultimo_modelo = ""
        self._cancelado = False
        self._pausado = False
        self._token_voz = 0
        self._cache_dir = BASE_DIR / "data" / "cache_voz"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._precalentando = False
        self._precache_activa = set()
        self._procesos_fondo = set()
        # Cola única de precaché: evita lanzar muchos procesos Piper en paralelo
        # cuando la interfaz cambia de punto/clase con rapidez. Varios Piper a
        # la vez saturaban CPU/disco y Qt acababa apareciendo como "ocupado".
        self._precache_queue = queue.Queue(maxsize=2)
        self._precache_worker_thread = None
        self._precache_worker_lock = threading.RLock()
        self._precache_ultimo_global = ""
        self._cache_version = "v413-pronunciacion-musical-do-central-pizarra"
        self._limpiar_cache_voz_obsoleta()
        # Estado de reproducción interna con sounddevice. Se usa para que
        # Pausa, Stop y la barra de progreso interactiva respondan al instante,
        # sin depender del búfer de aplay/paplay.
        self._sd_stream = None
        self._sd_state = None
        self._sd_done_event = None

    def _limpiar_cache_voz_obsoleta(self):
        """Evita reutilizar audios antiguos con pronunciaciones defectuosas.

        Las versiones previas pudieron cachear bloques como "Nivel." de forma
        aislada. Al cambiar la lógica de narración conviene invalidar la caché
        sin tocar ninguna carpeta de voces.
        """
        try:
            marcador = self._cache_dir / f".{self._cache_version}.ok"
            if marcador.exists():
                return
            for wav in self._cache_dir.glob("*.wav"):
                try:
                    wav.unlink()
                except Exception:
                    pass
            marcador.write_text("ok", encoding="utf-8")
        except Exception:
            pass

    def disponible(self, motor="piper", modelo_chica="", modelo_chico="") -> bool:
        return self._resolver_backend(motor, "chica", modelo_chica, modelo_chico)[0] is not None

    def diagnostico(self, motor="piper", avatar_tipo="chico", modelo_chica="", modelo_chico="") -> dict:
        backend, ejecutable, modelo = self._resolver_backend(motor, avatar_tipo, modelo_chica, modelo_chico)
        reproductor = self._resolver_reproductor()
        config = self._ruta_config_modelo(modelo) if modelo else ""
        return {
            "backend": backend or "",
            "motor": ejecutable or "",
            "modelo": modelo or "",
            "config": config or "",
            "reproductor": reproductor or "sounddevice",
            "piper": self._resolver_piper() or "",
            "paplay": shutil.which("paplay") or "",
            "pw_play": shutil.which("pw-play") or "",
            "aplay": shutil.which("aplay") or "",
            "ultimo_error": self.ultimo_error,
        }

    def detener(self):
        """Cancela cualquier generación Piper y cualquier reproducción activa.

        v1.8.3: además aborta la salida sounddevice inmediatamente. Esto evita
        que queden milisegundos o segundos en cola después de pulsar Stop.
        """
        with self.lock:
            self._cancelado = True
            self._pausado = False
            self._token_voz += 1
            procesos = [self.proceso, self._proceso_generacion, self._proceso_reproduccion]
            try:
                procesos.extend(list(self._procesos_fondo))
                self._procesos_fondo.clear()
            except Exception:
                pass
            try:
                while True:
                    self._precache_queue.get_nowait()
            except Exception:
                pass
            self.proceso = None
            self._proceso_generacion = None
            self._proceso_reproduccion = None
            sd_stream = self._sd_stream
            sd_done = self._sd_done_event
            self._sd_stream = None
            self._sd_state = None
            self._sd_done_event = None

        # Corta sounddevice antes de matar reproductores externos: es la ruta
        # principal de reproducción y debe responder de forma instantánea.
        if sd_done is not None:
            try:
                sd_done.set()
            except Exception:
                pass
        if sd_stream is not None:
            for metodo in ("abort", "stop", "close"):
                try:
                    getattr(sd_stream, metodo)()
                except Exception:
                    pass

        for proceso in procesos:
            if proceso is None:
                continue
            try:
                if proceso.poll() is None:
                    proceso.terminate()
                    try:
                        proceso.wait(timeout=0.12)
                    except Exception:
                        proceso.kill()
            except Exception:
                pass

        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass


    def pausar(self) -> bool:
        """Pausa inmediata de la voz.

        Con sounddevice la pausa se aplica en el siguiente bloque de audio
        (bloques muy pequeños). Con reproductores externos se usa SIGSTOP como
        respaldo.
        """
        with self.lock:
            self._pausado = True
            proceso = self._proceso_reproduccion
        if proceso is not None and proceso.poll() is None:
            try:
                if hasattr(signal, "SIGSTOP"):
                    os.kill(proceso.pid, signal.SIGSTOP)
            except Exception:
                pass
        return True

    def reanudar(self) -> bool:
        """Reanuda la voz pausada sin regenerar audio."""
        with self.lock:
            self._pausado = False
            proceso = self._proceso_reproduccion
        if proceso is not None and proceso.poll() is None:
            try:
                if hasattr(signal, "SIGCONT"):
                    os.kill(proceso.pid, signal.SIGCONT)
            except Exception:
                pass
        return True

    def alternar_pausa(self) -> bool:
        """Alterna pausa/reanudación. Devuelve True si queda en pausa."""
        with self.lock:
            pausado = self._pausado
        if pausado:
            self.reanudar()
            return False
        self.pausar()
        return True

    def esta_pausado(self) -> bool:
        with self.lock:
            return bool(self._pausado)

    def esta_reproduciendo(self) -> bool:
        with self.lock:
            if self._sd_state is not None and not self._cancelado:
                return True
            proceso = self._proceso_reproduccion
            return bool(proceso is not None and proceso.poll() is None)

    def saltar_a_porcentaje(self, ratio: float) -> bool:
        """Mueve la reproducción actual al punto indicado por la barra.

        Funciona de forma precisa cuando la voz se está reproduciendo por
        sounddevice, que es la ruta principal desde v1.8.3.
        """
        try:
            ratio = float(ratio)
        except Exception:
            return False
        ratio = max(0.0, min(1.0, ratio))
        with self.lock:
            estado = self._sd_state
            if not estado:
                return False
            total = int(estado.get("total", 0))
            if total <= 0:
                return False
            estado["pos"] = max(0, min(total - 1, int(total * ratio)))
            return True


    def hablar(
        self,
        texto: str,
        avatar_tipo="chico",
        velocidad=100,
        volumen=95,
        motor="piper",
        modelo_chica="",
        modelo_chico="",
        pausa_coma_ms=450,
        pausa_punto_ms=850,
        on_start: Optional[Callable[[], None]] = None,
        on_end: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        texto = self._limpiar_texto(texto)
        if not texto:
            self.ultimo_error = "Texto vacío."
            return False

        backend, ejecutable, modelo = self._resolver_backend("piper", avatar_tipo, modelo_chica, modelo_chico)
        if backend is None:
            self.ultimo_error = (
                "Voz Piper no disponible. Instala piper-tts y configura un modelo .onnx "
                "para el avatar seleccionado. No se usará voz robótica de respaldo."
            )
            if on_error:
                try:
                    on_error(self.ultimo_error)
                except Exception:
                    pass
            return False

        self.detener()
        with self.lock:
            self._cancelado = False
            self._pausado = False
            self._token_voz += 1
            token = self._token_voz

        hilo = threading.Thread(
            target=self._hablar_thread,
            args=(
                token,
                backend,
                ejecutable,
                modelo,
                texto,
                velocidad,
                volumen,
                pausa_coma_ms,
                pausa_punto_ms,
                on_start,
                on_end,
                on_error,
            ),
            daemon=True,
        )
        hilo.start()
        return True

    def _hablar_thread(
        self,
        token,
        backend,
        ejecutable,
        modelo,
        texto,
        velocidad,
        volumen,
        pausa_coma_ms,
        pausa_punto_ms,
        on_start,
        on_end,
        on_error,
    ):
        """Genera y reproduce la voz con arranque rápido.

        Versión v1.8.1:
        - Ya no genera toda la explicación completa antes de empezar a sonar.
        - Divide el texto en bloques grandes y naturales.
        - Genera el primer bloque y lo reproduce enseguida.
        - Mientras suena el primer bloque, prepara los siguientes en segundo plano.
        - Guarda una caché WAV por bloque para que repetir la explicación sea casi inmediato.
        """
        try:
            self.ultimo_error = ""
            self.ultimo_motor = ejecutable
            self.ultimo_modelo = modelo or ""
            self._hablar_streaming_bloques(
                token=token,
                ejecutable=ejecutable,
                modelo=modelo,
                texto=texto,
                velocidad=velocidad,
                volumen=volumen,
                pausa_coma_ms=pausa_coma_ms,
                pausa_punto_ms=pausa_punto_ms,
                on_start=on_start,
                on_error=on_error,
            )
        except Exception as exc:
            if not self._token_cancelado(token):
                self.ultimo_error = str(exc)
                if on_error:
                    try:
                        on_error(self.ultimo_error)
                    except Exception:
                        pass
        finally:
            with self.lock:
                if token == self._token_voz:
                    self.proceso = None
                    self._proceso_generacion = None
                    self._proceso_reproduccion = None
            if on_end and not self._token_cancelado(token):
                try:
                    on_end()
                except Exception:
                    pass

    def _hablar_streaming_bloques(
        self,
        token,
        ejecutable,
        modelo,
        texto,
        velocidad,
        volumen,
        pausa_coma_ms,
        pausa_punto_ms,
        on_start=None,
        on_error=None,
    ):
        # Si la explicación completa ya está cacheada, se reproduce como un
        # único WAV. Así la barra interactiva puede buscar cualquier punto de la
        # narración de forma real.
        wav_completo = self._obtener_wav_completo_cacheado(
            ejecutable=ejecutable,
            modelo=modelo,
            texto=texto,
            velocidad=velocidad,
            volumen=volumen,
            pausa_coma_ms=pausa_coma_ms,
            pausa_punto_ms=pausa_punto_ms,
            token=token,
            crear=False,
        )
        if wav_completo and os.path.exists(wav_completo):
            self._reproducir_wav(wav_completo, token=token, on_start=on_start)
            return

        # Arranque rápido: si aún no está listo el WAV completo, se reproduce por
        # segmentos cortos. Cada coma, dos puntos o punto genera una pausa real;
        # no dependemos de cómo Piper interprete la puntuación.
        bloques = self._dividir_texto_para_streaming(texto, pausa_coma_ms, pausa_punto_ms)
        if not bloques:
            return

        cola = queue.Queue(maxsize=32)
        centinela = object()

        def productor():
            def poner_en_cola(item):
                # No usar timeout corto: si Piper genera más rápido que la
                # reproducción, una Queue.Full cortaba la narración por el
                # tercer o cuarto bloque. Aquí espera de forma cancelable.
                while not self._token_cancelado(token):
                    try:
                        cola.put(item, timeout=0.10)
                        return True
                    except queue.Full:
                        continue
                    except Exception:
                        return False
                return False

            try:
                for indice, (bloque, pausa_ms) in enumerate(bloques):
                    if self._token_cancelado(token):
                        break
                    try:
                        wav_path = self._obtener_wav_cacheado(
                            ejecutable=ejecutable,
                            modelo=modelo,
                            texto=bloque,
                            velocidad=velocidad,
                            volumen=volumen,
                            pausa_ms=pausa_ms,
                            token=token,
                        )
                    except Exception as exc:
                        # Un bloque problemático no debe cortar toda la clase.
                        # Se registra el error y se continúa con el siguiente.
                        self.ultimo_error = str(exc)
                        continue
                    if self._token_cancelado(token):
                        if wav_path and str(wav_path).startswith(tempfile.gettempdir()):
                            try:
                                os.remove(wav_path)
                            except Exception:
                                pass
                        break
                    if wav_path and not poner_en_cola((indice, wav_path)):
                        break
            except Exception as exc:
                if not self._token_cancelado(token):
                    self.ultimo_error = str(exc)
            finally:
                poner_en_cola(centinela)

        threading.Thread(target=productor, daemon=True).start()

        arrancado = False
        while not self._token_cancelado(token):
            try:
                item = cola.get(timeout=0.05)
            except queue.Empty:
                continue
            if item is centinela:
                break
            if isinstance(item, tuple) and item[0] == "error":
                raise RuntimeError(item[1])
            _indice, wav_path = item
            if not wav_path or not os.path.exists(wav_path):
                continue
            self._reproducir_wav(wav_path, token=token, on_start=(on_start if not arrancado else None))
            arrancado = True

        if self._token_cancelado(token):
            return


    def _obtener_wav_completo_cacheado(
        self,
        ejecutable,
        modelo,
        texto,
        velocidad,
        volumen,
        pausa_coma_ms,
        pausa_punto_ms,
        token=None,
        crear=True,
    ):
        """Devuelve/genera un WAV completo con pausas reales por puntuación.

        Este WAV completo es el que permite que la barra de progreso sea
        interactiva de verdad. La generación se hace en segundo plano desde la
        UI cuando aparece el texto, por eso Play puede arrancar desde caché.
        """
        modelo_path = self._normalizar_modelo(modelo)
        if not modelo_path or not modelo_path.exists():
            return ""
        texto_limpio = self._limpiar_texto(texto)
        if not texto_limpio:
            return ""
        try:
            stat = modelo_path.stat()
            modelo_id = f"{modelo_path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"
        except Exception:
            modelo_id = str(modelo_path)
        raw = "|".join([
            modelo_id,
            texto_limpio,
            str(self._normalizar_velocidad(velocidad)),
            str(int(float(volumen))) if str(volumen).replace('.', '', 1).isdigit() else str(volumen),
            str(int(pausa_coma_ms or 0)),
            str(int(pausa_punto_ms or 0)),
            self._cache_version + "-full",
        ])
        clave = hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()
        cache_path = self._cache_dir / f"full_{clave}.wav"
        if cache_path.exists() and cache_path.stat().st_size > 128:
            return str(cache_path)
        if not crear:
            return ""

        fd, tmp = tempfile.mkstemp(prefix="profesor_avatar_full_", suffix=".wav")
        os.close(fd)
        try:
            ok = self._generar_piper(
                ejecutable=ejecutable,
                modelo=str(modelo_path),
                texto=texto_limpio,
                wav_path=tmp,
                velocidad=velocidad,
                pausa_coma_ms=pausa_coma_ms,
                pausa_punto_ms=pausa_punto_ms,
                token=token,
            )
            if not ok or self._token_cancelado(token):
                return ""
            self._aplicar_volumen_wav(tmp, volumen)
            tmp_cache = cache_path.with_suffix(".tmp.wav")
            shutil.copyfile(tmp, tmp_cache)
            os.replace(tmp_cache, cache_path)
            return str(cache_path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def _obtener_wav_cacheado(self, ejecutable, modelo, texto, velocidad, volumen, pausa_ms, token=None):
        modelo_path = self._normalizar_modelo(modelo)
        if not modelo_path or not modelo_path.exists():
            raise RuntimeError("No hay modelo Piper .onnx válido configurado para este avatar.")

        texto_piper = self._preparar_texto_rapido_piper(texto)
        clave = self._clave_cache_voz(modelo_path, texto_piper, velocidad, volumen, pausa_ms)
        cache_path = self._cache_dir / f"{clave}.wav"
        if cache_path.exists() and cache_path.stat().st_size > 128:
            return str(cache_path)

        fd, tmp = tempfile.mkstemp(prefix="profesor_avatar_stream_", suffix=".wav")
        os.close(fd)
        try:
            if not self._generar_piper_bloque(ejecutable, modelo_path, texto_piper, tmp, velocidad, token):
                if self._token_cancelado(token):
                    return ""
                raise RuntimeError(self.ultimo_error or "No se pudo generar voz Piper.")
            if self._token_cancelado(token):
                return ""
            self._aplicar_volumen_wav(tmp, volumen)
            if pausa_ms > 0:
                self._anadir_silencio_wav(tmp, pausa_ms)
            try:
                # Escritura atómica: evita que una reproducción lea una caché a medio crear.
                tmp_cache = cache_path.with_suffix(".tmp.wav")
                shutil.copyfile(tmp, tmp_cache)
                os.replace(tmp_cache, cache_path)
                return str(cache_path)
            except Exception:
                return tmp
        finally:
            try:
                if os.path.exists(tmp) and str(cache_path) != tmp:
                    os.remove(tmp)
            except Exception:
                pass

    def _clave_cache_voz(self, modelo_path: Path, texto: str, velocidad, volumen, pausa_ms) -> str:
        try:
            stat = modelo_path.stat()
            modelo_id = f"{modelo_path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"
        except Exception:
            modelo_id = str(modelo_path)
        raw = "|".join([
            modelo_id,
            str(texto),
            str(self._normalizar_velocidad(velocidad)),
            str(int(float(volumen))) if str(volumen).replace('.', '', 1).isdigit() else str(volumen),
            str(int(pausa_ms or 0)),
            self._cache_version + "-stream",
        ])
        return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()

    def _preparar_texto_rapido_piper(self, texto: str) -> str:
        """Prepara una pieza corta para Piper sin añadir finales artificiales.

        En v1.8.4 no se manda a Piper cada fragmento con punto final
        obligatorio, porque con algunas voces españolas eso provocaba lecturas
        como "inicialo" o "virtualo" cuando la palabra quedaba aislada. La
        pausa se añade como silencio WAV, no como puntuación forzada.
        """
        return self._texto_piper_seguro(texto)

    def _dividir_texto_para_streaming(self, texto, pausa_coma_ms, pausa_punto_ms):
        """Divide la narración en frases con pausas reales y respetando líneas.

        v1.8.4 corrige dos fallos importantes:
        - Los saltos de línea y líneas vacías cuentan como pausas didácticas,
          aunque el texto visible no tenga coma o punto.
        - La puntuación se usa para decidir la pausa, pero no se fuerza dentro
          del fragmento enviado a Piper. Así evitamos "nivel inicialo" y
          "piano virtualo".
        """
        try:
            pausa_coma_ms = max(0, min(3000, int(pausa_coma_ms)))
        except Exception:
            pausa_coma_ms = 850
        try:
            pausa_punto_ms = max(0, min(4000, int(pausa_punto_ms)))
        except Exception:
            pausa_punto_ms = 1250

        pausa_linea_ms = max(1000, int(pausa_coma_ms))
        pausa_parrafo_ms = max(1250, int(pausa_punto_ms))
        texto = self._limpiar_texto(texto)
        if not texto:
            return []

        bloques = []

        def reforzar_pausa_anterior(ms):
            if not bloques:
                return
            frase, pausa = bloques[-1]
            bloques[-1] = (frase, max(int(pausa or 0), int(ms or 0)))

        for linea in texto.split("\n"):
            linea = re.sub(r"\s+", " ", linea).strip()
            if not linea:
                reforzar_pausa_anterior(pausa_parrafo_ms)
                continue

            m_nivel = re.match(r"^(Nivel)\s*[:：]\s*(.+)$", linea, flags=re.I)
            if m_nivel:
                # Protección final: si llega una línea con formato Nivel: X,
                # se habla como frase completa. No se separa en "Nivel" + "X".
                valor = m_nivel.group(2).strip().strip(". ")
                valor = valor[0].upper() + valor[1:] if valor else "actual"
                bloques.append((f"El nivel actual es {valor}.", pausa_parrafo_ms))
                continue

            encontrados = list(re.finditer(r"([^,.;:!?]+)([,.;:!?]?)", linea))
            if not encontrados:
                limpio = self._texto_piper_seguro(linea)
                if limpio:
                    bloques.append((limpio, pausa_linea_ms))
                continue

            habia_signo_final = False
            for m in encontrados:
                cuerpo = re.sub(r"\s+", " ", m.group(1)).strip()
                signo = m.group(2)
                if not cuerpo:
                    continue
                habia_signo_final = bool(signo)
                texto_piper = self._texto_piper_seguro(cuerpo + signo)
                if not texto_piper:
                    continue
                if signo in {",", ";", ":"}:
                    pausa = pausa_coma_ms
                elif signo in {".", "!", "?"}:
                    pausa = pausa_punto_ms
                else:
                    pausa = pausa_linea_ms
                bloques.append((texto_piper, pausa))

            if not habia_signo_final:
                reforzar_pausa_anterior(pausa_linea_ms)

        if bloques:
            ultimo, _ = bloques[-1]
            bloques[-1] = (ultimo, 0)
        return bloques

    def _anadir_silencio_wav(self, wav_path, pausa_ms):
        try:
            pausa_ms = max(0, min(5000, int(pausa_ms)))
        except Exception:
            pausa_ms = 0
        if pausa_ms <= 0:
            return
        try:
            with wave.open(wav_path, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())
            n_frames = int(params.framerate * (pausa_ms / 1000.0))
            silencio = b"\x00" * n_frames * params.nchannels * params.sampwidth
            with wave.open(wav_path, "wb") as wf:
                wf.setparams(params)
                wf.writeframes(frames + silencio)
        except Exception as exc:
            self.ultimo_error = f"No se pudo añadir silencio de pausa: {exc}"

    def preparar_texto_async(
        self,
        texto: str,
        avatar_tipo="chico",
        modelo_chica="",
        modelo_chico="",
        velocidad=100,
        volumen=95,
        pausa_coma_ms=650,
        pausa_punto_ms=1200,
    ):
        """Pre-genera en caché la explicación visible sin reproducirla.

        Versión estable: no crea un hilo/proceso Piper por cada cambio de
        pantalla. Encola como máximo los últimos trabajos y los ejecuta en un
        único worker. Esto evita bloqueos aparentes de Qt por saturación de CPU,
        disco o PortAudio cuando se avanza rápido por la pizarra.
        """
        texto = self._limpiar_texto(texto)
        if not texto:
            return
        backend, ejecutable, modelo = self._resolver_backend("piper", avatar_tipo, modelo_chica, modelo_chico)
        if not ejecutable or not modelo:
            return
        modelo_path = self._normalizar_modelo(modelo)
        if not modelo_path or not modelo_path.exists():
            return

        bloques = self._dividir_texto_para_streaming(texto, pausa_coma_ms, pausa_punto_ms)
        if not bloques:
            return

        try:
            clave_global = hashlib.sha1((
                str(modelo_path.resolve()) + "|" + texto + "|" + str(velocidad) + "|" +
                str(volumen) + "|" + str(pausa_coma_ms) + "|" + str(pausa_punto_ms)
            ).encode("utf-8", "ignore")).hexdigest()
        except Exception:
            clave_global = hashlib.sha1((texto + str(time.time())).encode("utf-8", "ignore")).hexdigest()

        with self.lock:
            if clave_global == getattr(self, "_precache_ultimo_global", ""):
                return
            self._precache_ultimo_global = clave_global

        tarea = {
            "clave_global": clave_global,
            "ejecutable": ejecutable,
            "modelo_path": str(modelo_path),
            "texto": texto,
            "bloques": bloques,
            "velocidad": velocidad,
            "volumen": volumen,
            "pausa_coma_ms": pausa_coma_ms,
            "pausa_punto_ms": pausa_punto_ms,
        }

        # Mantiene solo las tareas más recientes. Si el alumno cambia de panel,
        # no interesa terminar de sintetizar explicaciones antiguas.
        try:
            while self._precache_queue.full():
                self._precache_queue.get_nowait()
        except Exception:
            pass
        try:
            self._precache_queue.put_nowait(tarea)
        except Exception:
            return
        self._asegurar_worker_precache()

    def _asegurar_worker_precache(self):
        with self._precache_worker_lock:
            if self._precache_worker_thread is not None and self._precache_worker_thread.is_alive():
                return
            self._precache_worker_thread = threading.Thread(target=self._precache_worker_loop, daemon=True)
            self._precache_worker_thread.start()

    def _precache_worker_loop(self):
        while True:
            try:
                tarea = self._precache_queue.get(timeout=12.0)
            except queue.Empty:
                return
            except Exception:
                return
            try:
                bloques = tarea.get("bloques") or []
                ejecutable = tarea.get("ejecutable")
                modelo_path = tarea.get("modelo_path")
                velocidad = tarea.get("velocidad", 100)
                volumen = tarea.get("volumen", 95)

                # Prepara solo los primeros segmentos de inmediato. Es suficiente
                # para que Play arranque rápido, sin lanzar una generación enorme
                # por cada texto visible. El WAV completo se crea solo para textos
                # razonables y cuando la cola no está esperando otro trabajo.
                for bloque, pausa_ms in bloques[:6]:
                    self._obtener_wav_cacheado(
                        ejecutable=ejecutable,
                        modelo=modelo_path,
                        texto=bloque,
                        velocidad=velocidad,
                        volumen=volumen,
                        pausa_ms=pausa_ms,
                        token=None,
                    )
                    if not self._precache_queue.empty():
                        break

                if self._precache_queue.empty() and len(str(tarea.get("texto") or "")) <= 1600:
                    self._obtener_wav_completo_cacheado(
                        ejecutable=ejecutable,
                        modelo=modelo_path,
                        texto=tarea.get("texto", ""),
                        velocidad=velocidad,
                        volumen=volumen,
                        pausa_coma_ms=tarea.get("pausa_coma_ms", 650),
                        pausa_punto_ms=tarea.get("pausa_punto_ms", 1200),
                        token=None,
                        crear=True,
                    )
            except Exception as exc:
                self.ultimo_error = str(exc)
            finally:
                try:
                    self._precache_queue.task_done()
                except Exception:
                    pass

    def precalentar_async(self, avatar_tipo="chico", modelo_chica="", modelo_chico="", velocidad=100):
        """Calienta Piper en segundo plano para reducir el primer clic.

        No reproduce sonido. Solo genera una frase mínima y la descarta para que
        el binario, el modelo y las páginas de disco queden en caché del sistema.
        """
        with self.lock:
            if self._precalentando:
                return
            self._precalentando = True

        def run():
            try:
                backend, ejecutable, modelo = self._resolver_backend("piper", avatar_tipo, modelo_chica, modelo_chico)
                if not ejecutable or not modelo:
                    return
                fd, tmp = tempfile.mkstemp(prefix="profesor_piper_warmup_", suffix=".wav")
                os.close(fd)
                try:
                    # Usa token None: no debe cortar la voz real ni cambiar el estado visible.
                    self._generar_piper_bloque(ejecutable, modelo, "Preparado.", tmp, velocidad, token=None)
                finally:
                    try:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                    except Exception:
                        pass
            finally:
                with self.lock:
                    self._precalentando = False
        threading.Thread(target=run, daemon=True).start()

    def _token_cancelado(self, token) -> bool:
        if token is None:
            return False
        with self.lock:
            return self._cancelado or token != self._token_voz

    def _generar_piper(
        self,
        ejecutable,
        modelo,
        texto,
        wav_path,
        velocidad=100,
        pausa_coma_ms=450,
        pausa_punto_ms=850,
        token=None,
    ) -> bool:
        if not ejecutable:
            self.ultimo_error = "Piper no está instalado. Instala: python3 -m pip install --user piper-tts --break-system-packages"
            return False
        modelo = self._normalizar_modelo(modelo)
        if not modelo or not modelo.exists():
            self.ultimo_error = "No hay modelo Piper .onnx válido configurado para este avatar."
            return False

        bloques = self._dividir_texto_en_bloques(texto, pausa_coma_ms, pausa_punto_ms)
        if not bloques:
            self.ultimo_error = "No hay texto narrable."
            return False
        if len(bloques) <= 1 and not bloques[0][1]:
            return self._generar_piper_bloque(ejecutable, modelo, bloques[0][0], wav_path, velocidad, token)

        tmp_paths = []
        try:
            for indice, (bloque, _pausa) in enumerate(bloques):
                if self._token_cancelado(token):
                    return False
                fd, tmp = tempfile.mkstemp(prefix=f"profesor_piper_bloque_{indice}_", suffix=".wav")
                os.close(fd)
                tmp_paths.append(tmp)
                if not self._generar_piper_bloque(ejecutable, modelo, bloque, tmp, velocidad, token):
                    return False
            if self._token_cancelado(token):
                return False
            return self._concatenar_wavs_con_pausas(tmp_paths, bloques, wav_path)
        finally:
            for p in tmp_paths:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    def _generar_piper_bloque(self, ejecutable, modelo, texto, wav_path, velocidad=100, token=None) -> bool:
        velocidad = self._normalizar_velocidad(velocidad)
        length_scale = self._velocidad_a_length_scale(velocidad)

        # Piper no usa una opción llamada "speed". Su control real de duración
        # es --length-scale: valores mayores hablan más lento y valores menores
        # hablan más rápido.
        cmd = [ejecutable, "--model", str(modelo), "--length-scale", f"{length_scale:.3f}"]
        config = self._ruta_config_modelo(modelo)
        if config:
            cmd.extend(["--config", str(config)])
        cmd.extend(["--output_file", wav_path])

        proceso = None
        try:
            proceso = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            with self.lock:
                if self._token_cancelado(token):
                    try:
                        proceso.kill()
                    except Exception:
                        pass
                    return False
                if token is None:
                    try:
                        self._procesos_fondo.add(proceso)
                    except Exception:
                        pass
                else:
                    self.proceso = proceso
                    self._proceso_generacion = proceso
            stdout, stderr = proceso.communicate(input=texto, timeout=90)
        except Exception as exc:
            self.ultimo_error = f"Piper falló: {exc}"
            try:
                if proceso is not None:
                    proceso.kill()
            except Exception:
                pass
            return False
        finally:
            with self.lock:
                try:
                    self._procesos_fondo.discard(locals().get("proceso"))
                except Exception:
                    pass
                if self._proceso_generacion is locals().get("proceso"):
                    self._proceso_generacion = None
                if self.proceso is locals().get("proceso"):
                    self.proceso = None

        if self._token_cancelado(token):
            return False
        if proceso.returncode != 0 or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 128:
            self.ultimo_error = (stderr or stdout or "Piper no generó audio.").strip()
            return False
        return True

    def _dividir_texto_en_bloques(self, texto, pausa_coma_ms, pausa_punto_ms):
        """Versión completa para caché/WAV final. Usa la misma segmentación
        humanizada que el streaming, para que la barra interactiva y la lectura
        por bloques suenen igual.
        """
        return self._dividir_texto_para_streaming(texto, pausa_coma_ms, pausa_punto_ms)

    def _concatenar_wavs_con_pausas(self, tmp_paths, bloques, salida) -> bool:
        params_base = None
        frames_salida = bytearray()
        try:
            for ruta, (_bloque, pausa_ms) in zip(tmp_paths, bloques):
                with wave.open(ruta, "rb") as wf:
                    params = wf.getparams()
                    frames = wf.readframes(wf.getnframes())
                if params_base is None:
                    params_base = params
                elif (
                    params.nchannels != params_base.nchannels
                    or params.sampwidth != params_base.sampwidth
                    or params.framerate != params_base.framerate
                ):
                    self.ultimo_error = "Los bloques de voz Piper no tienen el mismo formato WAV."
                    return False
                frames_salida.extend(frames)
                if pausa_ms > 0:
                    n_frames = int(params_base.framerate * (pausa_ms / 1000.0))
                    frames_salida.extend(b"\x00" * n_frames * params_base.nchannels * params_base.sampwidth)

            if params_base is None:
                self.ultimo_error = "No se generaron bloques de voz."
                return False
            with wave.open(salida, "wb") as wf:
                wf.setnchannels(params_base.nchannels)
                wf.setsampwidth(params_base.sampwidth)
                wf.setframerate(params_base.framerate)
                wf.writeframes(bytes(frames_salida))
            return os.path.exists(salida) and os.path.getsize(salida) > 128
        except Exception as exc:
            self.ultimo_error = f"No se pudieron unir las pausas de voz: {exc}"
            return False

    def _normalizar_velocidad(self, velocidad) -> int:
        try:
            valor = int(velocidad)
        except Exception:
            valor = 100
        return max(50, min(220, valor))

    def _velocidad_a_length_scale(self, velocidad) -> float:
        # UI: 50 = muy lento, 100 = natural, 220 = rápido.
        # Piper: length_scale 2.0 = lento, 1.0 = natural, 0.455 = rápido.
        velocidad = self._normalizar_velocidad(velocidad)
        return max(0.35, min(2.20, 100.0 / float(velocidad)))

    def _aplicar_volumen_wav(self, wav_path, volumen):
        """Aplica volumen al WAV generado por Piper antes de reproducirlo."""
        try:
            vol = max(0.0, min(2.0, float(volumen) / 100.0))
        except Exception:
            vol = 1.0
        if abs(vol - 1.0) < 0.01:
            return
        try:
            import numpy as np
            with wave.open(wav_path, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())

            if params.sampwidth != 2:
                return

            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            audio = np.clip(audio * vol, -32768, 32767).astype(np.int16)
            with wave.open(wav_path, "wb") as wf:
                wf.setparams(params)
                wf.writeframes(audio.tobytes())
        except Exception as exc:
            self.ultimo_error = f"No se pudo aplicar volumen a la voz: {exc}"

    def _reproducir_wav(self, wav_path, token=None, on_start=None):
        # Ruta estable por defecto: reproductor externo de PipeWire/Pulse/ALSA.
        # Evita abrir un segundo OutputStream de PortAudio mientras el motor del
        # piano ya usa sounddevice. En varios Debian eso podía dejar la ventana
        # "ocupada" sin traceback. Para depurar con sounddevice: export
        # PROFESOR_VOZ_SOUNDDEVICE=1 antes de ejecutar main.py.
        if self._token_cancelado(token):
            return

        if on_start:
            try:
                on_start()
            except Exception:
                pass

        usar_sd = str(os.environ.get("PROFESOR_VOZ_SOUNDDEVICE", "0")).strip().lower() in {"1", "true", "yes", "si", "sí"}
        if usar_sd:
            self.ultimo_reproductor = "sounddevice"
            ok = self._reproducir_wav_sounddevice(wav_path, token=token)
            if ok or self._token_cancelado(token):
                return

        reproductor = self._resolver_reproductor()
        self.ultimo_reproductor = reproductor or "ninguno"
        if not reproductor:
            # Último respaldo: solo usa sounddevice si no hay paplay/pw-play/aplay.
            if not usar_sd:
                self.ultimo_reproductor = "sounddevice-fallback"
                self._reproducir_wav_sounddevice(wav_path, token=token)
            return
        if os.path.basename(reproductor) == "aplay":
            cmd = [reproductor, "-q", "--buffer-time=20000", "--period-time=5000", wav_path]
        elif os.path.basename(reproductor) == "paplay":
            cmd = [reproductor, "--latency-msec=20", wav_path]
        else:
            cmd = [reproductor, wav_path]
        try:
            with self.lock:
                if self._token_cancelado(token):
                    return
                proceso = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self.proceso = proceso
                self._proceso_reproduccion = proceso
                if self._pausado and hasattr(signal, "SIGSTOP"):
                    try:
                        os.kill(proceso.pid, signal.SIGSTOP)
                    except Exception:
                        pass
            _, err = proceso.communicate()
            with self.lock:
                if self._proceso_reproduccion is proceso:
                    self._proceso_reproduccion = None
                if self.proceso is proceso:
                    self.proceso = None
            if proceso.returncode != 0 and not self._token_cancelado(token):
                self.ultimo_error = (err.decode("utf-8", "ignore") if err else "Error reproduciendo WAV.").strip()
        except Exception as exc:
            if not self._token_cancelado(token):
                self.ultimo_error = f"No se pudo reproducir la voz: {exc}"

    def _reproducir_wav_sounddevice(self, wav_path, token=None) -> bool:
        try:
            import numpy as np
            import sounddevice as sd

            with wave.open(wav_path, "rb") as wf:
                sr = wf.getframerate()
                canales = wf.getnchannels()
                ancho = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())

            if ancho == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif ancho == 1:
                audio = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            else:
                self.ultimo_error = f"Formato WAV no soportado: {ancho * 8} bits."
                return False

            if canales > 1:
                audio = audio.reshape(-1, canales)
            else:
                audio = audio.reshape(-1, 1)
            if self._token_cancelado(token):
                return True

            done = threading.Event()
            estado = {"pos": 0, "total": int(len(audio))}

            def callback(outdata, frames_solicitados, _time_info, _status):
                if self._token_cancelado(token):
                    outdata.fill(0)
                    done.set()
                    raise sd.CallbackStop

                with self.lock:
                    pausado = bool(self._pausado)
                    pos = int(estado.get("pos", 0))
                    total = int(estado.get("total", len(audio)))

                if pausado:
                    outdata.fill(0)
                    return

                if pos >= total:
                    outdata.fill(0)
                    done.set()
                    raise sd.CallbackStop

                fin = min(total, pos + frames_solicitados)
                tramo = audio[pos:fin]
                outdata[:len(tramo), :] = tramo
                if len(tramo) < frames_solicitados:
                    outdata[len(tramo):, :].fill(0)
                    done.set()
                    with self.lock:
                        estado["pos"] = total
                    raise sd.CallbackStop

                with self.lock:
                    estado["pos"] = fin

            stream = sd.OutputStream(
                samplerate=sr,
                channels=audio.shape[1],
                dtype="float32",
                blocksize=64,
                latency=0.005,
                callback=callback,
            )
            with self.lock:
                self._sd_stream = stream
                self._sd_state = estado
                self._sd_done_event = done
            stream.start()
            while not done.is_set() and not self._token_cancelado(token):
                time.sleep(0.006)
            if self._token_cancelado(token):
                try:
                    stream.abort()
                except Exception:
                    pass
            else:
                try:
                    stream.stop()
                except Exception:
                    pass
            try:
                stream.close()
            except Exception:
                pass
            with self.lock:
                if self._sd_stream is stream:
                    self._sd_stream = None
                if self._sd_state is estado:
                    self._sd_state = None
                if self._sd_done_event is done:
                    self._sd_done_event = None
            return True
        except Exception as exc:
            with self.lock:
                self._sd_stream = None
                self._sd_state = None
                self._sd_done_event = None
            if not self._token_cancelado(token):
                self.ultimo_error = f"No se pudo reproducir la voz con sounddevice: {exc}"
            return False


    def texto_narrado_limpio(self, texto: str) -> str:
        """Devuelve el texto real que recibirá el narrador, separado del texto visual."""
        return self._limpiar_texto(texto)

    def diagnostico_texto_narrado(self, texto: str, pausa_coma_ms=650, pausa_punto_ms=1200) -> str:
        """Muestra unidades de voz y pausas para auditar la lectura del profesor."""
        limpio = self._limpiar_texto(texto)
        bloques = self._dividir_texto_para_streaming(limpio, pausa_coma_ms, pausa_punto_ms)
        lineas = ["TEXTO LIMPIO PARA EL NARRADOR:", limpio or "(vacío)", "", "BLOQUES QUE SE MANDAN A PIPER:"]
        for i, (bloque, pausa) in enumerate(bloques, 1):
            lineas.append(f"{i:02d}. {bloque}    [pausa después: {int(pausa)} ms]")
        return "\n".join(lineas)

    def _texto_piper_seguro(self, texto: str) -> str:
        """Texto corto seguro para Piper.

        v1.8.5: se mantiene puntuación final real. La versión anterior
        eliminaba puntos y comas, y algunos modelos Piper españoles pronunciaban
        fragmentos aislados como "nivelo" o "inicialo". Para una lectura
        natural, cada unidad breve llega a Piper como frase completa:
        "Nivel."; pausa real; "Inicial.".

        v4.1.13: antes de mandar cada bloque a Piper, se normaliza la notación
        musical para que no deletree DO como "de o" ni convierta "central"
        en una palabra con vocal añadida al final.
        """
        texto = str(texto or "").strip()
        if not texto:
            return ""
        texto = re.sub(r"\s+", " ", texto)
        texto = self._corregir_frase_voz(texto)
        texto = self._normalizar_notacion_musical_para_voz(texto)
        # Algunas voces Piper españolas tienden a añadir una vocal de apoyo
        # cuando una palabra terminada en L queda completamente aislada. Para
        # cabeceras cortas usamos dos puntos, que mantienen la entonación de
        # etiqueta sin convertirlo en "nivelo" o "virtualo".
        # Nunca enviar palabras aisladas problemáticas a Piper. Algunas voces
        # españolas añaden una vocal de apoyo cuando reciben palabras sueltas
        # terminadas en L: "nivel" -> "nivelo", "inicial" -> "inicialo".
        # Por eso se convierten en frases naturales completas.
        if re.fullmatch(r"(?i)nivel", texto):
            return "El nivel de la clase."
        if re.fullmatch(r"(?i)inicial", texto):
            return "La fase inicial."
        if re.fullmatch(r"(?i)piano virtual", texto):
            return "El piano de la pantalla."
        texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)
        texto = re.sub(r"([,.;:!?]){2,}", r"\1", texto).strip()

        # Mantener signos de apertura si existen; solo asegura un cierre
        # gramatical cuando el bloque no trae puntuación. Esto evita que Piper
        # intente alargar palabras sueltas terminadas en consonante.
        if texto and texto[-1] not in ".,;:!?":
            texto += "."
        return texto

    def _corregir_frase_voz(self, texto: str) -> str:
        texto = str(texto or "")
        reemplazos = {
            "Toca Do": "Toca el Do",
            "Toca Re": "Toca el Re",
            "Toca Mi": "Toca el Mi",
            "Toca Fa": "Toca el Fa",
            "Toca Sol": "Toca el Sol",
            "Toca La": "Toca el La",
            "Toca Si": "Toca el Si",
            "Localizar Do, en tu teclado": "Localizar el Do en tu teclado",
            "Localizar Do en tu teclado": "Localizar el Do en tu teclado",
            "Piano Virtual": "Piano virtual",
            "piano Virtual": "piano virtual",
            "o el piano virtual.": "o usando el piano de la pantalla.",
            "o el piano virtual": "o usando el piano de la pantalla",
            "MODO CLASE": "Modo clase",
            "EJEMPLO GUIADO": "Ejemplo guiado",
            "PRÁCTICA GUIADA": "Práctica guiada",
            "EJERCICIO EVALUABLE": "Ejercicio evaluable",
            # Evita que Piper una "pizarra:" con la palabra siguiente y
            # produzca lecturas torpes como "pizarraba".
            "Ahora en la pizarra:": "Ahora, la pizarra muestra:",
            "Ahora en la pizarra": "Ahora, la pizarra muestra",
        }
        for origen, destino in reemplazos.items():
            texto = texto.replace(origen, destino)
        return texto

    def _normalizar_notacion_musical_para_voz(self, texto: str) -> str:
        """Convierte texto musical visual en texto amable para Piper.

        La interfaz puede mostrar DO, RE, C4 o DO central, pero el narrador no
        debe leerlo como acrónimos. Esta función solo afecta a la voz; no cambia
        lo que aparece escrito en la pantalla.
        """
        texto = str(texto or "")
        if not texto:
            return ""

        mapa_alturas = {
            "C4": "do central del piano",
            "D4": "re de la zona central",
            "E4": "mi de la zona central",
            "F4": "fa de la zona central",
            "G4": "sol de la zona central",
            "A4": "la de la zona central",
            "B4": "si de la zona central",
            "C3": "do grave",
            "F3": "fa grave",
            "G3": "sol grave",
            "C5": "do agudo",
            "G5": "sol agudo",
        }
        for origen, destino in mapa_alturas.items():
            texto = re.sub(rf"(?<![A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9#]){re.escape(origen)}(?![A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9#])", destino, texto)

        texto = re.sub(
            r"\b(?:DO|Do|do)\s+central\b(?!\s+del\s+piano)",
            "do central del piano",
            texto,
            flags=re.I,
        )

        notas = {
            "DO": "do", "RE": "re", "MI": "mi", "FA": "fa",
            "SOL": "sol", "LA": "la", "SI": "si",
            "Do": "do", "Re": "re", "Mi": "mi", "Fa": "fa",
            "Sol": "sol", "La": "la", "Si": "si",
        }
        patron = r"(?<![A-Za-zÁÉÍÓÚÜÑáéíóúüñ])(?:DO|RE|MI|FA|SOL|LA|SI|Do|Re|Mi|Fa|Sol|La|Si)(?![A-Za-zÁÉÍÓÚÜÑáéíóúüñ])"
        texto = re.sub(patron, lambda m: notas.get(m.group(0), m.group(0).lower()), texto)

        texto = re.sub(
            r"\b(do)\s+central\s*([.;:!?]?)$",
            lambda m: f"{m.group(1)} central del piano{m.group(2) or ''}",
            texto,
            flags=re.I,
        )
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    def _resolver_backend(self, motor, avatar_tipo, modelo_chica, modelo_chico):
        avatar_tipo = avatar_tipo if avatar_tipo in {"chica", "chico"} else "chico"
        modelo = str(modelo_chica or "") if avatar_tipo == "chica" else str(modelo_chico or "")
        modelo_path = self._normalizar_modelo(modelo)
        piper = self._resolver_piper()

        if piper and modelo_path and modelo_path.exists():
            return "piper", piper, str(modelo_path)
        return None, None, None

    def _resolver_piper(self):
        candidatos = [
            shutil.which("piper"),
            shutil.which("piper-tts"),
            str(Path.home() / ".local" / "bin" / "piper"),
            str(Path.home() / ".local" / "bin" / "piper-tts"),
            "/usr/local/bin/piper",
            "/usr/bin/piper",
        ]
        for c in candidatos:
            if c and Path(c).exists():
                return c
        return None

    def _normalizar_modelo(self, modelo):
        if not modelo:
            return None
        ruta = Path(str(modelo).strip()).expanduser()
        if ruta.is_absolute():
            return ruta
        candidatos = [
            BASE_DIR / ruta,
            Path.cwd() / ruta,
        ]
        for c in candidatos:
            if c.exists():
                return c.resolve()
        return (BASE_DIR / ruta).resolve()

    def _ruta_config_modelo(self, modelo):
        if not modelo:
            return ""
        ruta = self._normalizar_modelo(modelo)
        if not ruta:
            return ""
        candidatos = [
            Path(str(ruta) + ".json"),
            ruta.with_suffix(ruta.suffix + ".json"),
            ruta.with_suffix(".onnx.json"),
            ruta.with_suffix(".json"),
        ]
        for c in candidatos:
            if c.exists():
                return str(c)
        return ""

    def _resolver_reproductor(self):
        for nombre in ("paplay", "pw-play", "aplay"):
            ruta = shutil.which(nombre)
            if ruta:
                return ruta
        return None

    def _limpiar_texto(self, texto: str) -> str:
        """Prepara texto para Piper respetando pausas didácticas.

        v1.8.4: no destruye saltos de línea. Cada línea es una unidad de habla
        y las líneas vacías generan pausa larga. También corrige cabeceras como
        "MODO CLASE — Toca Do" para que se lea: "Modo clase"; pausa;
        "Toca el Do".
        """
        texto = str(texto or "").replace("\r\n", "\n").replace("\r", "\n")
        texto = re.sub(r"[*_#`>]+", "", texto)
        texto = texto.replace("—", "\n").replace("–", "\n")

        lineas = []
        titulos = {
            "MODO CLASE",
            "EJEMPLO GUIADO",
            "PRÁCTICA GUIADA",
            "EJERCICIO EVALUABLE",
            "Qué vamos a aprender",
            "Explicación del profesor",
            "Cómo debes pensarlo",
            "Qué haremos después",
            "Ejercicio que haremos al final",
            "Sin nota de evaluación",
            "MODO",
            "PLAN DEL NIVEL",
            "LECCIÓN",
        }
        titulos_upper = {t.upper() for t in titulos}

        for raw in texto.split("\n"):
            linea = re.sub(r"\s+", " ", raw).strip()
            if not linea:
                if lineas and lineas[-1] != "":
                    lineas.append("")
                continue

            # No leer "uno punto", "dos punto", etc.
            linea = re.sub(r"^\d+\.\s*", "", linea).strip()
            linea = self._corregir_frase_voz(linea)

            # Texto visual tipo "Nivel: inicial" -> texto hablado estable.
            # No se manda "Nivel" ni "Inicial" como bloques aislados, porque
            # algunas voces Piper los pronuncian como "nivelo" e "inicialo".
            m_nivel = re.match(r"^(Nivel)\s*[:：]\s*(.+)$", linea, flags=re.I)
            if m_nivel:
                valor = m_nivel.group(2).strip().strip(". ")
                if valor:
                    valor = valor[0].upper() + valor[1:]
                    lineas.append(f"El nivel actual es {valor}.")
                else:
                    lineas.append("Estamos en el nivel actual.")
                lineas.append("")
                continue

            if linea.upper() in titulos_upper:
                if linea.lower() == "qué vamos a aprender":
                    linea = "¿Qué vamos a aprender?"
                lineas.append(linea)
                continue

            linea = re.sub(r"\s+([:;,.!?])", r"\1", linea)
            linea = re.sub(r"([:;,.!?])\1+", r"\1", linea)
            lineas.append(linea)

        # Une la pareja visual "Nivel" + "Inicial" como una frase natural.
        # La prioridad es que Piper no reciba nunca "Nivel" ni "Inicial" como
        # bloques autónomos.
        compactadas = []
        i = 0
        while i < len(lineas):
            actual = lineas[i]
            siguiente = lineas[i + 1] if i + 1 < len(lineas) else None
            if actual.strip().lower() == "nivel" and siguiente and siguiente.strip():
                valor = siguiente.strip().strip(". ")
                valor = valor[0].upper() + valor[1:] if valor else valor
                compactadas.append(f"El nivel actual es {valor}.")
                compactadas.append("")
                i += 2
                continue
            compactadas.append(actual)
            i += 1
        lineas = compactadas

        salida = "\n".join(lineas).strip()
        salida = self._normalizar_notacion_musical_para_voz(salida)
        if len(salida) > 2200:
            salida = salida[:2200].rsplit("\n", 1)[0].strip() or salida[:2200].rsplit(" ", 1)[0].strip()
        return salida
