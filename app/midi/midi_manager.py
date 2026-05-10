import re
import threading
import time
from typing import Callable, Optional

NOTAS_ES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
_SEMITONOS_EN = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_SEMITONOS_ES = {"DO": 0, "RE": 2, "MI": 4, "FA": 5, "SOL": 7, "LA": 9, "SI": 11}


def midi_numero_a_nombre(numero: int) -> str:
    nota = NOTAS_ES[int(numero) % 12]
    octava = (int(numero) // 12) - 1
    return f"{nota}{octava}"


def nota_nombre_a_midi(nota: str) -> Optional[int]:
    """Convierte C4/Do4/Do#4/Reb4 a número MIDI.

    La aplicación usa nombres españoles al recibir MIDI y nombres ingleses en el
    motor de audio. Esta función acepta ambos formatos para poder enviar MIDI OUT
    desde cualquier parte del programa.
    """
    texto = str(nota or "").strip()
    if not texto:
        return None
    texto = texto.replace("♯", "#").replace("♭", "b")
    texto = texto.replace("ó", "o").replace("Ó", "O")

    # Permite octavas negativas por compatibilidad MIDI, aunque el piano visual
    # normalmente trabaja de A0 a C8.
    m = re.match(r"^([A-Ga-g]|Do|DO|do|Re|RE|re|Mi|MI|mi|Fa|FA|fa|Sol|SOL|sol|La|LA|la|Si|SI|si)([#b]?)(-?\d+)$", texto)
    if not m:
        return None

    base, alteracion, octava_txt = m.groups()
    base_norm = base.upper().replace("Ó", "O")
    if base_norm in _SEMITONOS_EN:
        semitono = _SEMITONOS_EN[base_norm]
    else:
        semitono = _SEMITONOS_ES.get(base_norm)
    if semitono is None:
        return None

    if alteracion == "#":
        semitono += 1
    elif alteracion == "b":
        semitono -= 1

    try:
        octava = int(octava_txt)
    except Exception:
        return None
    numero = (octava + 1) * 12 + semitono
    return max(0, min(127, int(numero)))


class MidiManager:
    """Entrada y salida MIDI real mediante mido/python-rtmidi.

    v4.1.11 MIDI real:
    - Mantiene abierto MIDI IN y MIDI OUT por separado.
    - Lee la entrada con un hilo de polling no bloqueante para evitar puertos que
      aparecen en la lista, pero no disparan callback de mido en ALSA/PipeWire.
    - Envía note_on/note_off reales al puerto MIDI OUT seleccionado.
    """

    def __init__(self):
        self.error = ""
        self._input = None
        self._output = None
        self._lock = threading.RLock()
        self._poll_stop = threading.Event()
        self._poll_thread = None
        self.on_note_on: Optional[Callable[[str, int, int], None]] = None
        self.on_note_off: Optional[Callable[[str, int, int], None]] = None
        self.on_raw: Optional[Callable[[str], None]] = None
        self.nombre_entrada_abierta = ""
        self.nombre_salida_abierta = ""
        self._ultimo_raw_ts = 0.0

    def entradas(self):
        try:
            import mido
            return mido.get_input_names()
        except Exception as exc:
            self.error = str(exc)
            return []

    def salidas(self):
        try:
            import mido
            return mido.get_output_names()
        except Exception as exc:
            self.error = str(exc)
            return []

    def abrir_entrada(self, nombre: str) -> bool:
        self.cerrar_entrada()
        if not nombre:
            self.error = "Sin entrada MIDI seleccionada"
            return False
        try:
            import mido
            # Sin callback: se usa polling propio. Es más estable en Linux con
            # ALSA/PipeWire y evita que el dispositivo se vea pero no entregue notas.
            entrada = mido.open_input(nombre)
            with self._lock:
                self._input = entrada
                self.nombre_entrada_abierta = nombre
                self._poll_stop.clear()
                self._poll_thread = threading.Thread(target=self._bucle_lectura_entrada, daemon=True)
                self._poll_thread.start()
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            with self._lock:
                self._input = None
                self.nombre_entrada_abierta = ""
            return False

    def cerrar_entrada(self):
        self._poll_stop.set()
        hilo = None
        with self._lock:
            hilo = self._poll_thread
            self._poll_thread = None
        if hilo is not None and hilo.is_alive() and hilo is not threading.current_thread():
            try:
                hilo.join(timeout=0.35)
            except Exception:
                pass
        with self._lock:
            if self._input is not None:
                try:
                    self._input.close()
                except Exception:
                    pass
            self._input = None
            self.nombre_entrada_abierta = ""

    def abrir_salida(self, nombre: str) -> bool:
        self.cerrar_salida()
        if not nombre:
            self.error = "Sin salida MIDI seleccionada"
            return False
        try:
            import mido
            with self._lock:
                self._output = mido.open_output(nombre)
                self.nombre_salida_abierta = nombre
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            with self._lock:
                self._output = None
                self.nombre_salida_abierta = ""
            return False

    def cerrar_salida(self):
        with self._lock:
            if self._output is not None:
                try:
                    self.all_notes_off()
                except Exception:
                    pass
                try:
                    self._output.close()
                except Exception:
                    pass
            self._output = None
            self.nombre_salida_abierta = ""

    def _bucle_lectura_entrada(self):
        while not self._poll_stop.is_set():
            entrada = None
            with self._lock:
                entrada = self._input
            if entrada is None:
                break
            try:
                for msg in entrada.iter_pending():
                    self._procesar_mensaje(msg)
            except Exception as exc:
                self.error = str(exc)
            time.sleep(0.003)

    def _procesar_mensaje(self, msg):
        try:
            tipo = getattr(msg, "type", "")
            nota_num = getattr(msg, "note", None)
            vel = int(getattr(msg, "velocity", 0) or 0)
            canal = int(getattr(msg, "channel", 0) or 0) + 1
            if self.on_raw:
                # Evita inundar la UI con mensajes de reloj/active_sensing.
                # Las notas siempre se notifican; el resto se limita.
                ahora = time.monotonic()
                if tipo in {"note_on", "note_off"} or ahora - self._ultimo_raw_ts >= 0.25:
                    self._ultimo_raw_ts = ahora
                    self.on_raw(str(msg))
            if nota_num is None:
                return
            nombre = midi_numero_a_nombre(int(nota_num))
            if tipo == "note_on" and vel > 0:
                if self.on_note_on:
                    self.on_note_on(nombre, vel, canal)
            elif tipo in ("note_off", "note_on"):
                if self.on_note_off:
                    self.on_note_off(nombre, vel, canal)
        except Exception as exc:
            self.error = str(exc)

    def salida_abierta(self) -> bool:
        with self._lock:
            return self._output is not None

    def entrada_abierta(self) -> bool:
        with self._lock:
            return self._input is not None

    def enviar_note_on(self, nota: str, velocity: int = 96, canal: int = 1) -> bool:
        return self._enviar_nota("note_on", nota, velocity, canal)

    def enviar_note_off(self, nota: str, velocity: int = 0, canal: int = 1) -> bool:
        return self._enviar_nota("note_off", nota, velocity, canal)

    def _enviar_nota(self, tipo: str, nota: str, velocity: int = 96, canal: int = 1) -> bool:
        numero = nota_nombre_a_midi(nota)
        if numero is None:
            self.error = f"Nota MIDI no válida: {nota}"
            return False
        try:
            import mido
            with self._lock:
                salida = self._output
                nombre_salida = self.nombre_salida_abierta
            if salida is None:
                self.error = "No hay salida MIDI abierta"
                return False
            canal_midi = max(0, min(15, int(canal or 1) - 1))
            vel = max(0, min(127, int(velocity or 0)))
            salida.send(mido.Message(tipo, note=int(numero), velocity=vel, channel=canal_midi))
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def all_notes_off(self):
        try:
            import mido
            with self._lock:
                salida = self._output
            if salida is None:
                return False
            for canal in range(16):
                salida.send(mido.Message("control_change", control=123, value=0, channel=canal))
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def cerrar(self):
        self.cerrar_entrada()
        self.cerrar_salida()
