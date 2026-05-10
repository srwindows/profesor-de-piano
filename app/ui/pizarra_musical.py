import math
import re
import time
import unicodedata

from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QAction, QPainterPath, QPolygonF, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QCheckBox, QToolButton, QMenu, QSizePolicy
)

from app.config import ASSETS_DIR
from app.core.notas import midi_a_info, nombre_a_midi, normalizar_nota


class PizarraMusicalCanvas(QFrame):
    """Lienzo ligero para explicar partitura como pizarra de clase.

    Hotfix v4.1.9:
    - El lienzo ya no es solo decorativo: admite clic izquierdo, doble clic,
      rueda/teclado y menú contextual.
    - Los símbolos musicales importantes se dibujan con QPainterPath/primitivas,
      no dependen de que el sistema tenga una fuente musical instalada.
    """

    paso_siguiente_solicitado = Signal()
    paso_anterior_solicitado = Signal()
    simbolo_pulsado = Signal(str, str, list)
    practica_simbolo_solicitada = Signal(list, str)


    def __init__(self, parent=None):
        super().__init__(parent)
        self.texto = ""
        self.titulo = "Pizarra musical"
        self.modo = "general"
        self.paso = 0
        self.pasos = []
        self.capas = {
            "claves": True,
            "notas": True,
            "do_central": True,
            "manos": True,
            "figuras": True,
            "pulso": True,
            "digitacion": True,
            "puntero": True,
            "flechas": True,
        }
        # v4.1.5: pentagrama vivo para MIDI Didáctico / ND.
        self.midi_vivo_activo = False
        self.midi_vivo_notas = []
        self.midi_vivo_actual = {}
        self.midi_vivo_siguiente = {}
        self.midi_vivo_activas = []
        self.midi_vivo_tiempo_ms = 0
        self.midi_vivo_progreso = 0.0
        self.midi_vivo_modo = "clase"
        self.midi_vivo_bpm = 60
        self.midi_vivo_beat = 1
        self.midi_vivo_compas_num = 4
        # Digitación Hanon: se alimenta con los campos `mano` y `dedo` de cada
        # nota. La pizarra no inventa la técnica en pantalla: dibuja las dos
        # manos y resalta el dedo concreto que debe tocar la nota activa.
        self.hanon_digitacion_activas = []
        self.hanon_digitacion_actual = {}
        self.hanon_digitacion_siguiente = {}
        self._pixmap_manos_digitacion = {}
        self.piano_interactivo_visible = False
        self.piano_interactivo_notas = set()

        # Entrada MIDI externa en directo. No sustituye a la partitura: se dibuja
        # encima del pentagrama para que el alumno vea inmediatamente qué tecla ha
        # tocado en su piano físico.
        self.midi_entrada_nota = ""
        self.midi_entrada_activa = False
        self.midi_entrada_velocity = 0
        self.midi_entrada_canal = 0
        self.midi_entrada_origen = ""

        # Capa temporal de marcas docentes. El pentagrama base se dibuja siempre
        # limpio; halos, flechas, etiquetas y ayudas visuales viven aquí.
        self.marcas_docentes = []
        self._timer_marcas_docentes = QTimer(self)
        self._timer_marcas_docentes.setInterval(40)
        self._timer_marcas_docentes.timeout.connect(self._tick_marcas_docentes)
        self._secuencia_docente = []
        self._secuencia_docente_indice = 0
        self._secuencia_docente_inicio = None
        self._secuencia_docente_ms_acumulados = 0
        self._secuencia_docente_pausada = False
        self._secuencia_docente_texto = ""
        self._secuencia_docente_duracion_ms = 0
        self._timer_secuencia_docente = QTimer(self)
        self._timer_secuencia_docente.setInterval(80)
        self._timer_secuencia_docente.timeout.connect(self._tick_secuencia_docente)

        self._hotspots = []
        self._hover_hotspot = None
        self._ultimo_click_vacio_avanza = True
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            "Pizarra interactiva: clic en símbolos para explicarlos, clic en zona vacía para avanzar, "
            "doble clic para retroceder, rueda/cursores para cambiar de paso."
        )
        self.setMinimumHeight(280)
        self.setMaximumHeight(560)
        self.setObjectName("PizarraMusicalCanvas")
        self.setStyleSheet("""
            #PizarraMusicalCanvas {
                background: #fffdf7;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
        """)

    def preparar(self, texto: str, titulo: str = "Pizarra musical"):
        self.texto = str(texto or "")
        self.titulo = str(titulo or "Pizarra musical")
        self.modo = self._detectar_modo(self.texto)
        self.pasos = self._crear_pasos(self.texto, self.modo)
        self.paso = 0
        self.update()

    def preparar_midi_didactico(self, notas: list[dict], titulo: str = "MIDI Didáctico · Pentagrama vivo"):
        """Activa la partitura viva del MIDI Didáctico.

        `notas` debe ser una lista de dicts con nota, compás, pulso, mano, inicio_ms y duracion_ms.
        """
        self.midi_vivo_activo = True
        self.modo = "midi_didactico"
        self.titulo = str(titulo or "MIDI Didáctico · Pentagrama vivo")
        self.midi_vivo_notas = sorted(list(notas or []), key=lambda n: (int(n.get("inicio_ms", 0) or 0), int(n.get("midi", 0) or 0)))
        self.midi_vivo_actual = {}
        self.midi_vivo_siguiente = self.midi_vivo_notas[0] if self.midi_vivo_notas else {}
        self.midi_vivo_activas = []
        self.hanon_digitacion_actual = {}
        self.hanon_digitacion_siguiente = dict(self.midi_vivo_siguiente or {})
        self.hanon_digitacion_activas = []
        self.midi_vivo_tiempo_ms = 0
        self.midi_vivo_progreso = 0.0
        self.midi_vivo_modo = "clase"
        self.piano_interactivo_notas = set()
        self.pasos = [
            "El pentagrama sigue el MIDI Didáctico nota por nota.",
            "La nota activa se resalta fuerte; la siguiente queda preparada.",
            "El profesor, el piano virtual y el Motor MIDI Pro trabajan sobre la misma nota.",
        ]
        self.paso = 0
        self.update()

    def actualizar_midi_didactico(self, actual: dict | None = None, siguiente: dict | None = None,
                                  activas: list[dict] | None = None, tiempo_ms: int = 0,
                                  progreso: float = 0.0, modo: str = "clase",
                                  bpm: int | None = None, beat: int | None = None,
                                  compas_num: int | None = None):
        """Actualiza el resaltado vivo siguiendo el archivo MIDI."""
        self.midi_vivo_activo = True
        self.modo = "midi_didactico"
        self.midi_vivo_actual = dict(actual or {})
        self.midi_vivo_siguiente = dict(siguiente or {})
        self.midi_vivo_activas = [dict(x) for x in (activas or [])]
        self.hanon_digitacion_actual = dict(actual or {})
        self.hanon_digitacion_siguiente = dict(siguiente or {})
        self.hanon_digitacion_activas = [dict(x) for x in (activas or [])]
        try:
            self.midi_vivo_tiempo_ms = int(tiempo_ms)
        except Exception:
            self.midi_vivo_tiempo_ms = 0
        try:
            self.midi_vivo_progreso = max(0.0, min(1.0, float(progreso)))
        except Exception:
            self.midi_vivo_progreso = 0.0
        self.midi_vivo_modo = str(modo or "clase")
        if bpm is not None:
            self.midi_vivo_bpm = int(bpm or 60)
        if beat is not None:
            self.midi_vivo_beat = max(1, int(beat or 1))
        if compas_num is not None:
            self.midi_vivo_compas_num = max(1, int(compas_num or 4))
        self.piano_interactivo_notas = {str(n.get("nota", "")) for n in self.midi_vivo_activas if n.get("nota")}
        self.update()

    def limpiar_midi_didactico(self):
        self.midi_vivo_activo = False
        self.midi_vivo_actual = {}
        self.midi_vivo_siguiente = {}
        self.midi_vivo_activas = []
        self.hanon_digitacion_actual = {}
        self.hanon_digitacion_siguiente = {}
        self.hanon_digitacion_activas = []
        self.piano_interactivo_notas = set()
        self.update()

    def alternar_piano_interactivo(self, visible: bool | None = None):
        self.piano_interactivo_visible = (not self.piano_interactivo_visible) if visible is None else bool(visible)
        self.update()
        return self.piano_interactivo_visible

    def mostrar_nota_midi_externa(self, nota: str, velocity: int = 0, canal: int = 0, origen: str = "midi_in"):
        """Muestra en el pentagrama la última nota tocada desde un teclado MIDI externo."""
        self.midi_entrada_nota = str(nota or "").strip()
        self.midi_entrada_activa = bool(self.midi_entrada_nota)
        try:
            self.midi_entrada_velocity = int(velocity or 0)
        except Exception:
            self.midi_entrada_velocity = 0
        try:
            self.midi_entrada_canal = int(canal or 0)
        except Exception:
            self.midi_entrada_canal = 0
        self.midi_entrada_origen = str(origen or "midi_in")
        self.update()

    def limpiar_nota_midi_externa(self, nota: str | None = None):
        nota = str(nota or "").strip()
        if nota and nota.upper() != str(self.midi_entrada_nota or "").upper():
            return
        self.midi_entrada_activa = False
        self.update()

    def limpiar_marcas_docentes(self):
        """Borra solo la capa temporal de explicación del profesor."""
        self.marcas_docentes = []
        self._timer_marcas_docentes.stop()
        self.update()

    def borrar_pizarra(self):
        """Limpia marcas temporales sin borrar el pentagrama base ni la clase."""
        self.marcas_docentes = []
        self._timer_marcas_docentes.stop()
        self.midi_entrada_nota = ""
        self.midi_entrada_activa = False
        self.midi_entrada_velocity = 0
        self.midi_entrada_canal = 0
        self.midi_entrada_origen = ""
        self.update()

    def clear_highlights(self):
        self.limpiar_marcas_docentes()

    def iniciar_animacion_marca(self, tipo: str, duracion_ms: int = 2500, etiqueta: str = ""):
        marca = self._crear_marca_docente(tipo, etiqueta, duracion_ms)
        if marca:
            self._establecer_marcas_docentes(marca)

    def _crear_marca_docente(self, tipo: str, etiqueta: str = "", duracion_ms: int = 2500) -> dict:
        tipo = str(tipo or "").strip()
        if not tipo:
            return {}
        etiquetas = {
            "clave_sol": "Clave de Sol",
            "clave_fa": "Clave de Fa",
            "mano_derecha": "Mano derecha",
            "mano_izquierda": "Mano izquierda",
            "lineas_pentagrama": "Cinco líneas",
            "do_central": "DO central",
            "notas": "Notas",
            "compases": "Compases",
            "espacios_pentagrama": "Espacios",
            "claves": "Claves",
        }
        try:
            duracion = max(800, min(6000, int(duracion_ms or 2500)))
        except Exception:
            duracion = 2500
        return {
            "tipo": tipo,
            "etiqueta": etiqueta or etiquetas.get(tipo, tipo),
            "inicio": time.monotonic(),
            "duracion_ms": duracion,
            "fade_ms": 1100,
            "intensidad": 1.0,
        }

    def _establecer_marcas_docentes(self, *marcas):
        ahora = time.monotonic()
        normalizadas = []
        for marca in marcas:
            if not isinstance(marca, dict):
                continue
            m = dict(marca)
            m.setdefault("inicio", ahora)
            m.setdefault("duracion_ms", 2500)
            m.setdefault("fade_ms", 1100)
            m.setdefault("intensidad", 1.0)
            normalizadas.append(m)
        self.marcas_docentes = normalizadas
        if self.marcas_docentes and not self._timer_marcas_docentes.isActive():
            self._timer_marcas_docentes.start()
        self.update()

    def _tick_marcas_docentes(self):
        ahora = time.monotonic()
        vivas = []
        for marca in list(getattr(self, "marcas_docentes", []) or []):
            try:
                edad_ms = (ahora - float(marca.get("inicio", ahora))) * 1000.0
                duracion = float(marca.get("duracion_ms", 2500) or 2500)
                fade = float(marca.get("fade_ms", 1100) or 1100)
            except Exception:
                continue
            if edad_ms <= duracion + fade:
                vivas.append(marca)
        self.marcas_docentes = vivas
        if not self.marcas_docentes:
            self._timer_marcas_docentes.stop()
        self.update()

    def resaltar_lineas_pentagrama(self):
        self.iniciar_animacion_marca("lineas_pentagrama", 2600, "Cinco líneas")

    def highlight_staff(self):
        self.resaltar_lineas_pentagrama()

    def highlight_notes(self):
        self.iniciar_animacion_marca("notas", 2500, "Notas")

    def highlight_measures(self):
        self.iniciar_animacion_marca("compases", 2500, "Compases")

    def highlight_spaces(self):
        self.iniciar_animacion_marca("espacios_pentagrama", 2500, "Espacios")

    def highlight_clefs(self):
        self.iniciar_animacion_marca("claves", 2500, "Claves")

    def senalar_clave_sol(self):
        self.animar_clave_sol()

    def senalar_clave_fa(self):
        self.animar_clave_fa()

    def mostrar_mano_derecha(self):
        self.animar_mano_derecha()

    def mostrar_mano_izquierda(self):
        self.animar_mano_izquierda()

    def resaltar_do_central(self):
        self.iniciar_animacion_marca("do_central", 2700, "DO central")

    def animar_clave_sol(self):
        self.iniciar_animacion_marca("clave_sol", 2800, "Clave de Sol")

    def highlight_treble_clef(self):
        self.animar_clave_sol()

    def animar_clave_fa(self):
        self.iniciar_animacion_marca("clave_fa", 2800, "Clave de Fa")

    def highlight_bass_clef(self):
        self.animar_clave_fa()

    def animar_mano_derecha(self):
        self.iniciar_animacion_marca("mano_derecha", 2600, "Mano derecha")

    def highlight_right_hand(self):
        self.animar_mano_derecha()

    def animar_mano_izquierda(self):
        self.iniciar_animacion_marca("mano_izquierda", 2600, "Mano izquierda")

    def highlight_left_hand(self):
        self.animar_mano_izquierda()

    def _texto_normalizado_docente(self, texto: str) -> str:
        t = str(texto or "").lower()
        t = "".join(
            ch for ch in unicodedata.normalize("NFD", t)
            if unicodedata.category(ch) != "Mn"
        )
        return " ".join(t.split())

    def _estimar_duracion_secuencia_docente_ms(self, texto: str) -> int:
        palabras = max(1, len(str(texto or "").split()))
        ms = int((palabras / 145.0) * 60_000)
        texto = str(texto or "")
        ms += texto.count(",") * 450
        ms += (texto.count(".") + texto.count(";") + texto.count(":") + texto.count("!") + texto.count("?")) * 850
        return max(2200, min(12 * 60_000, ms))

    def _fragmentos_temporales_docentes(self, texto_normalizado: str, duracion_ms: int) -> list[dict]:
        """Divide el texto en bloques temporales parecidos a la narración TTS."""
        texto_normalizado = str(texto_normalizado or "").strip()
        if not texto_normalizado:
            return []

        fragmentos = []
        for m in re.finditer(r"([^,.;:!?]+)([,.;:!?]?)", texto_normalizado):
            cuerpo = re.sub(r"\s+", " ", m.group(1)).strip()
            if not cuerpo:
                continue
            signo = m.group(2) or ""
            inicio = m.start(1)
            fin = m.end(1)
            palabras = max(1, len(cuerpo.split()))
            pausa_equiv = 0.0
            if signo in {",", ";", ":"}:
                pausa_equiv = 1.6
            elif signo in {".", "!", "?"}:
                pausa_equiv = 2.8
            fragmentos.append({
                "texto": cuerpo,
                "inicio": inicio,
                "fin": fin,
                "peso": palabras + pausa_equiv,
            })

        if not fragmentos:
            return [{"texto": texto_normalizado, "inicio": 0, "fin": len(texto_normalizado), "ms": 0, "dur_ms": duracion_ms}]

        total_peso = max(1.0, sum(float(f["peso"]) for f in fragmentos))
        acumulado = 0.0
        total_ms = max(1200, int(duracion_ms or self._estimar_duracion_secuencia_docente_ms(texto_normalizado)))
        for frag in fragmentos:
            frag_ms = int((float(frag["peso"]) / total_peso) * total_ms)
            frag["ms"] = int(acumulado)
            frag["dur_ms"] = max(450, frag_ms)
            acumulado += frag_ms
        return fragmentos

    def _buscar_eventos_docentes(self, texto: str, duracion_ms: int | None = None) -> list[dict]:
        t = self._texto_normalizado_docente(texto)
        if not t:
            return []

        patrones = [
            ("clave de sol", "clave_sol", "Clave de Sol", 2800),
            ("clave sol", "clave_sol", "Clave de Sol", 2800),
            ("clave de fa", "clave_fa", "Clave de Fa", 2800),
            ("clave fa", "clave_fa", "Clave de Fa", 2800),
            ("mano derecha", "mano_derecha", "Mano derecha", 2600),
            ("mano izquierda", "mano_izquierda", "Mano izquierda", 2600),
            ("do central", "do_central", "DO central", 2700),
            ("cinco lineas", "lineas_pentagrama", "Cinco líneas", 2600),
            ("5 lineas", "lineas_pentagrama", "Cinco líneas", 2600),
            ("lineas del pentagrama", "lineas_pentagrama", "Cinco líneas", 2600),
            ("lineas", "lineas_pentagrama", "Líneas", 2400),
            ("pentagrama", "lineas_pentagrama", "Pentagrama", 2600),
            ("espacios", "espacios_pentagrama", "Espacios", 2400),
            ("compases", "compases", "Compases", 2400),
            ("compas", "compases", "Compás", 2400),
            ("notas", "notas", "Notas", 2400),
            ("nota", "notas", "Nota", 2200),
            ("claves", "claves", "Claves", 2400),
        ]
        total_ms = int(duracion_ms or self._estimar_duracion_secuencia_docente_ms(texto))
        total_ms = max(1200, total_ms)
        fragmentos = self._fragmentos_temporales_docentes(t, total_ms)
        eventos = []
        ocupados = []
        for frag in fragmentos:
            frag_texto = frag.get("texto", "")
            frag_inicio = int(frag.get("inicio", 0) or 0)
            frag_ms = int(frag.get("ms", 0) or 0)
            frag_dur = int(frag.get("dur_ms", 900) or 900)
            frag_len = max(1, len(frag_texto))
            for patron, tipo, etiqueta, duracion_marca in patrones:
                inicio = 0
                while True:
                    pos_local = frag_texto.find(patron, inicio)
                    if pos_local < 0:
                        break
                    pos = frag_inicio + pos_local
                    fin = pos + len(patron)
                    if not any(pos < ocupado_fin and fin > ocupado_ini for ocupado_ini, ocupado_fin in ocupados):
                        ratio_local = max(0.0, min(1.0, pos_local / frag_len))
                        eventos.append({
                            "pos": pos,
                            "ms": frag_ms + int(ratio_local * max(350, frag_dur - 350)),
                            "tipo": tipo,
                            "etiqueta": etiqueta,
                            "duracion_marca": duracion_marca,
                        })
                        ocupados.append((pos, fin))
                    inicio = pos_local + len(patron)

        eventos.sort(key=lambda e: e["pos"])
        if not eventos:
            return []

        ultimo_ms = -900
        secuencia = []
        for evento in eventos:
            ms = int(evento.get("ms", 0) or 0)
            ms = max(0, min(total_ms - 700, ms))
            if ms - ultimo_ms < 900:
                ms = ultimo_ms + 900
            ultimo_ms = ms
            evento["ms"] = min(ms, max(0, total_ms - 500))
            secuencia.append(evento)
        return secuencia

    def preparar_secuencia_docente(self, texto: str, duracion_ms: int | None = None) -> bool:
        self._secuencia_docente_texto = str(texto or "")
        self._secuencia_docente_duracion_ms = int(duracion_ms or self._estimar_duracion_secuencia_docente_ms(texto))
        self._secuencia_docente = self._buscar_eventos_docentes(self._secuencia_docente_texto, self._secuencia_docente_duracion_ms)
        self._secuencia_docente_indice = 0
        self._secuencia_docente_inicio = None
        self._secuencia_docente_ms_acumulados = 0
        self._secuencia_docente_pausada = False
        self._timer_secuencia_docente.stop()
        if self._secuencia_docente:
            self._disparar_evento_docente(self._secuencia_docente[0], reiniciar_tiempo=True)
            self._secuencia_docente_indice = 1
            return True
        self.limpiar_marcas_docentes()
        return False

    def iniciar_secuencia_docente(self, texto: str | None = None, duracion_ms: int | None = None) -> bool:
        if texto is not None:
            self._secuencia_docente_texto = str(texto or "")
        if duracion_ms is not None:
            self._secuencia_docente_duracion_ms = int(duracion_ms or 0)
        if not self._secuencia_docente:
            self._secuencia_docente = self._buscar_eventos_docentes(
                self._secuencia_docente_texto,
                self._secuencia_docente_duracion_ms,
            )
        if not self._secuencia_docente:
            self.limpiar_marcas_docentes()
            return False
        self._secuencia_docente_indice = 0
        self._secuencia_docente_ms_acumulados = 0
        self._secuencia_docente_inicio = time.monotonic()
        self._secuencia_docente_pausada = False
        self.limpiar_marcas_docentes()
        self._timer_secuencia_docente.start()
        self._tick_secuencia_docente()
        return True

    def pausar_secuencia_docente(self):
        if self._secuencia_docente_inicio is not None and not self._secuencia_docente_pausada:
            self._secuencia_docente_ms_acumulados += int((time.monotonic() - self._secuencia_docente_inicio) * 1000)
        self._secuencia_docente_inicio = None
        self._secuencia_docente_pausada = True
        self._timer_secuencia_docente.stop()

    def reanudar_secuencia_docente(self):
        if not self._secuencia_docente:
            return
        self._secuencia_docente_inicio = time.monotonic()
        self._secuencia_docente_pausada = False
        self._timer_secuencia_docente.start()

    def detener_secuencia_docente(self, limpiar: bool = True):
        self._timer_secuencia_docente.stop()
        self._secuencia_docente_indice = 0
        self._secuencia_docente_inicio = None
        self._secuencia_docente_ms_acumulados = 0
        self._secuencia_docente_pausada = False
        if limpiar:
            self.limpiar_marcas_docentes()

    def _ms_actual_secuencia_docente(self) -> int:
        elapsed = int(getattr(self, "_secuencia_docente_ms_acumulados", 0) or 0)
        inicio = getattr(self, "_secuencia_docente_inicio", None)
        if inicio is not None and not getattr(self, "_secuencia_docente_pausada", False):
            elapsed += int((time.monotonic() - inicio) * 1000)
        return max(0, elapsed)

    def _tick_secuencia_docente(self):
        if not self._secuencia_docente:
            self._timer_secuencia_docente.stop()
            return
        elapsed = self._ms_actual_secuencia_docente()
        while self._secuencia_docente_indice < len(self._secuencia_docente):
            evento = self._secuencia_docente[self._secuencia_docente_indice]
            if elapsed < int(evento.get("ms", 0) or 0):
                break
            self._disparar_evento_docente(evento, reiniciar_tiempo=True)
            self._secuencia_docente_indice += 1
        duracion = int(getattr(self, "_secuencia_docente_duracion_ms", 0) or 0)
        if self._secuencia_docente_indice >= len(self._secuencia_docente) and elapsed > duracion + 1500:
            self._timer_secuencia_docente.stop()

    def _disparar_evento_docente(self, evento: dict, reiniciar_tiempo: bool = True):
        marca = self._crear_marca_docente(
            evento.get("tipo", ""),
            evento.get("etiqueta", ""),
            evento.get("duracion_marca", 2500),
        )
        if marca:
            self._establecer_marcas_docentes(marca)

    def aplicar_marca_docente_por_texto(self, texto: str) -> bool:
        """Sincroniza ayudas visuales con el texto que ya lee el profesor."""
        return self.preparar_secuencia_docente(texto)

    def enfocar_concepto_desde_texto(self, texto: str):
        """Sitúa la pizarra en el paso visual más útil para el texto que el profesor va a explicar."""
        t = str(texto or "").lower()
        if not self.pasos:
            return
        if self.modo == "partitura":
            if any(x in t for x in ["do central", "localizar do", "grupo de dos"]):
                self.paso = min(3, len(self.pasos) - 1)
            elif "clave de fa" in t:
                self.paso = min(2, len(self.pasos) - 1)
            elif "clave de sol" in t:
                self.paso = min(1, len(self.pasos) - 1)
            else:
                # Para clases generales de pentagrama conviene enseñar todos los
                # elementos: claves, Do central, nota aguda y nota grave.
                self.paso = min(4, len(self.pasos) - 1)
        elif self.modo in {"ritmo", "pulso", "digitacion"}:
            self.paso = len(self.pasos) - 1
        else:
            self.paso = min(1, len(self.pasos) - 1)
        self.update()

    def set_capa(self, nombre: str, activo: bool):
        if nombre in self.capas:
            self.capas[nombre] = bool(activo)
            self.update()

    def paso_siguiente(self):
        if self.pasos:
            self.paso = min(len(self.pasos) - 1, self.paso + 1)
            self.update()

    def paso_anterior(self):
        if self.pasos:
            self.paso = max(0, self.paso - 1)
            self.update()

    def paso_actual_texto(self) -> str:
        if not self.pasos:
            return ""
        return self.pasos[max(0, min(self.paso, len(self.pasos) - 1))]

    def notas_docente_actuales(self) -> list[str]:
        if self.modo == "midi_didactico":
            candidatos = []
            try:
                candidatos.extend(list(getattr(self, "midi_vivo_activas", []) or []))
                candidatos.append(dict(getattr(self, "midi_vivo_actual", {}) or {}))
                candidatos.append(dict(getattr(self, "midi_vivo_siguiente", {}) or {}))
                candidatos.extend(list(getattr(self, "midi_vivo_notas", []) or [])[:1])
            except Exception:
                candidatos = []
            salida = []
            for item in candidatos:
                try:
                    nota = str((item or {}).get("nota", "") or "").strip()
                except Exception:
                    nota = ""
                if nota and nota not in salida:
                    salida.append(nota)
            return salida[:4]

        if self.modo == "partitura":
            if self.paso == 1:
                return ["G4"]  # Sol de referencia
            if self.paso == 2:
                return ["F3"]  # Fa de referencia
            if self.paso == 3:
                return ["C4"]  # Do central
            if self.paso >= 4:
                return ["C4", "G4", "F3"]
        if self.modo == "digitacion":
            return ["C4", "D4", "E4", "F4", "G4"]
        return []

    def secuencia_docente_actual(self) -> list[str]:
        """Secuencia breve que la pizarra puede pedir al alumno."""
        if self.modo == "midi_didactico":
            salida = []
            try:
                origen = list(getattr(self, "midi_vivo_notas", []) or [])
            except Exception:
                origen = []
            for item in origen:
                try:
                    nota = str((item or {}).get("nota", "") or "").strip()
                except Exception:
                    nota = ""
                if nota:
                    salida.append(nota)
            return salida[:32] if salida else (self.notas_docente_actuales() or ["C4"])

        if self.modo == "digitacion":
            return ["C4", "D4", "E4", "F4", "G4"]

        if self.modo == "partitura":
            if self.paso == 1:
                return ["G4"]
            if self.paso == 2:
                return ["F3"]
            if self.paso == 3:
                return ["C4"]
            if self.paso >= 4:
                return ["C4", "G4", "F3"]
            return ["C4"]

        if self.modo == "ritmo":
            # Cuatro negras sobre DO central: útil para preparar metrónomo.
            return ["C4", "C4", "C4", "C4"]

        if self.modo == "pulso":
            # DO en el tiempo 1 y silencio interno después. En esta fase validamos la nota.
            return ["C4"]

        return self.notas_docente_actuales() or ["C4"]

    def _detectar_modo(self, texto: str) -> str:
        t = texto.lower()
        if any(x in t for x in ["pentagrama", "clave de sol", "clave de fa", "partitura", "do central"]):
            return "partitura"
        if any(x in t for x in ["negra", "blanca", "redonda", "silencio", "figura"]):
            return "ritmo"
        if any(x in t for x in ["pulso", "metrónomo", "metronomo", "compás", "compas"]):
            return "pulso"
        if any(x in t for x in ["digitación", "digitacion", "dedo", "mano derecha", "mano izquierda"]):
            return "digitacion"
        return "general"

    def _crear_pasos(self, texto: str, modo: str) -> list[str]:
        if modo == "partitura":
            return [
                "Primero vemos dos pentagramas: arriba suele leer la mano derecha y abajo la mano izquierda.",
                "La clave de Sol no es un adorno: señala dónde vive SOL y desde ahí nombramos las demás notas.",
                "La clave de Fa tampoco es un adorno: sus dos puntos señalan la línea de FA.",
                "El DO central queda entre los dos pentagramas y sirve como puente entre teclado y partitura.",
                "La altura de la nota dice si el sonido sube o baja; la figura dice cuánto dura.",
            ]
        if modo == "ritmo":
            return [
                "Las figuras musicales indican duración.",
                "Negra: normalmente un pulso. Blanca: dos pulsos. Redonda: cuatro pulsos.",
                "El silencio también se cuenta: no se toca, pero el pulso sigue.",
            ]
        if modo == "pulso":
            return [
                "El pulso es el latido regular de la música.",
                "El compás agrupa pulsos; por ejemplo, en 4/4 contamos 1, 2, 3, 4.",
                "El metrónomo ayuda a comprobar si te adelantas o te retrasas.",
            ]
        if modo == "digitacion":
            return [
                "La digitación organiza qué dedo toca cada nota.",
                "Mano derecha e izquierda pueden tener tareas distintas; no basta con mirar notas.",
                "El objetivo es tocar con control y sin tensión.",
            ]
        return [
            "El profesor convierte este punto en una explicación visual.",
            "Primero identifica el concepto principal.",
            "Después lo conecta con el piano, la partitura o el ejercicio.",
        ]

    def texto_narracion_visual_actual(self) -> str:
        paso = int(getattr(self, "paso", 0) or 0)
        base = self.paso_actual_texto()

        if self.modo == "partitura":
            detalles = [
                "Ahora dibujo los dos pentagramas del piano: el superior, que normalmente usamos para la mano derecha, y el inferior, que normalmente usamos para la mano izquierda.",
                "Ahora activo la capa de claves y señalo la clave de Sol. Se llama así porque marca la línea donde vive la nota Sol. También resalto Sol en el piano virtual.",
                "Ahora señalo la clave de Fa. Se llama así porque sus dos puntos señalan la línea donde vive la nota Fa. También resalto Fa en el piano virtual.",
                "Ahora activo el Do central: aparece entre los dos pentagramas y queda resaltado también en el piano virtual.",
                "Ahora añado notas más agudas y más graves para que veas que la altura en el pentagrama indica si el sonido sube o baja.",
            ]
        elif self.modo == "ritmo":
            detalles = [
                "Ahora activo la capa de figuras y dibujo la negra. En esta explicación básica, la negra representa un pulso.",
                "Ahora comparo la blanca con la negra. La blanca dura dos pulsos si la negra vale uno.",
                "Ahora muestro la redonda. En cuatro por cuatro, la redonda ocupa cuatro pulsos.",
                "Ahora aparece el silencio. El silencio no se toca, pero se cuenta por dentro.",
            ]
        elif self.modo == "pulso":
            detalles = [
                "Ahora activo la capa de pulso y marco el primer tiempo. Este es el punto de referencia para empezar a contar.",
                "Ahora añado el segundo pulso. La separación entre uno y dos debe ser regular.",
                "Ahora añado el tercer pulso. No hay que correr ni frenar.",
                "Ahora completo el cuarto pulso. En cuatro por cuatro volvemos después al uno.",
            ]
        elif self.modo == "digitacion":
            detalles = [
                "Ahora activo la capa de digitación y dibujo la posición de cinco dedos sobre Do, Re, Mi, Fa y Sol. También resalto esas teclas en el piano.",
                "Ahora destaco los primeros dedos para que veas la relación entre nota y dedo.",
                "Ahora se entiende que la digitación sirve para tocar con continuidad y sin tensión.",
            ]
        else:
            detalles = [
                "Ahora convierto el punto actual en una explicación visual.",
                "Ahora separo la idea principal del ejemplo.",
                "Ahora preparo la comprobación antes de avanzar.",
            ]

        detalle = detalles[max(0, min(paso, len(detalles) - 1))] if detalles else ""
        partes = []
        if detalle:
            partes.append(detalle)
        if base and base not in detalle:
            partes.append("Paso docente: " + base)
        return " ".join(partes).strip()

    # ------------------------------------------------------------------
    # Interactividad del lienzo
    # ------------------------------------------------------------------
    def _reset_hotspots(self):
        self._hotspots = []

    def _add_hotspot(self, rect, titulo: str, descripcion: str, notas=None, accion: str = "explicar"):
        """Registra una zona pulsable del lienzo."""
        try:
            if not isinstance(rect, QRectF):
                rect = QRectF(rect)
            item = {
                "rect": rect,
                "titulo": str(titulo or "Símbolo"),
                "descripcion": str(descripcion or titulo or "Símbolo musical"),
                "notas": list(notas or []),
                "accion": str(accion or "explicar"),
            }
            self._hotspots.append(item)
            return item
        except Exception:
            return None

    def _hotspot_en_pos(self, pos):
        try:
            p = QPointF(pos)
            for item in reversed(getattr(self, "_hotspots", []) or []):
                if item.get("rect") and item["rect"].contains(p):
                    return item
        except Exception:
            pass
        return None

    def _emitir_hotspot(self, item):
        if not item:
            return False
        titulo = str(item.get("titulo", "Símbolo"))
        descripcion = str(item.get("descripcion", titulo))
        notas = list(item.get("notas", []) or [])
        self.simbolo_pulsado.emit(titulo, descripcion, notas)
        if item.get("accion") == "practicar" and notas:
            self.practica_simbolo_solicitada.emit(notas, descripcion)
        return True

    def mousePressEvent(self, event):
        try:
            self.setFocus(Qt.MouseFocusReason)
            if event.button() == Qt.LeftButton:
                item = self._hotspot_en_pos(event.position().toPoint() if hasattr(event, "position") else event.pos())
                if item is not None:
                    self._emitir_hotspot(item)
                    event.accept()
                    return
                if getattr(self, "_ultimo_click_vacio_avanza", True):
                    self.paso_siguiente_solicitado.emit()
                    event.accept()
                    return
            elif event.button() == Qt.RightButton:
                self._abrir_menu_contextual(event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos())
                event.accept()
                return
        except Exception:
            pass
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.paso_anterior_solicitado.emit()
                event.accept()
                return
        except Exception:
            pass
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        try:
            item = self._hotspot_en_pos(event.position().toPoint() if hasattr(event, "position") else event.pos())
            if item != getattr(self, "_hover_hotspot", None):
                self._hover_hotspot = item
                if item:
                    self.setToolTip(f"{item.get('titulo','Símbolo')}: {item.get('descripcion','')}")
                else:
                    self.setToolTip("Clic en símbolos para explicarlos. Clic en zona vacía para avanzar de paso.")
                self.update()
        except Exception:
            pass
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_hotspot = None
        self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        try:
            if event.angleDelta().y() < 0:
                self.paso_siguiente_solicitado.emit()
            else:
                self.paso_anterior_solicitado.emit()
            event.accept()
            return
        except Exception:
            pass
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        try:
            if event.key() in (Qt.Key_Right, Qt.Key_Down, Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
                self.paso_siguiente_solicitado.emit()
                event.accept()
                return
            if event.key() in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Backspace):
                self.paso_anterior_solicitado.emit()
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)

    def _abrir_menu_contextual(self, global_pos):
        menu = QMenu(self)
        act_prev = menu.addAction("Paso anterior")
        act_next = menu.addAction("Paso siguiente")
        menu.addSeparator()
        act_practica = menu.addAction("Practicar lo señalado")
        act_practica.setEnabled(bool(self.notas_docente_actuales()))
        elegido = menu.exec(global_pos)
        if elegido is act_prev:
            self.paso_anterior_solicitado.emit()
        elif elegido is act_next:
            self.paso_siguiente_solicitado.emit()
        elif elegido is act_practica:
            notas = self.notas_docente_actuales()
            self.practica_simbolo_solicitada.emit(notas, "Practica en el piano lo que está señalando la pizarra.")

    def _dibujar_hover_hotspot(self, p: QPainter):
        item = getattr(self, "_hover_hotspot", None)
        if not item:
            return
        rect = item.get("rect")
        if not rect:
            return
        p.save()
        p.setPen(QPen(QColor("#f59e0b"), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 8, 8)
        p.restore()

    def _dibujar_ayuda_interactiva(self, p: QPainter, r):
        p.save()
        p.setPen(QColor("#64748b"))
        f = QFont(); f.setPointSize(8); f.setItalic(True); p.setFont(f)
        p.drawText(
            QRectF(r.left() + 10, r.top() + 28, r.width() - 20, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            "Clic: explicar símbolo · zona vacía: siguiente paso · doble clic: paso anterior"
        )
        p.restore()

    # ------------------------------------------------------------------
    # Símbolos musicales dibujados sin depender de fuentes externas
    # ------------------------------------------------------------------
    def _dibujar_clave_sol(self, p: QPainter, x: float, y: float, escala: float = 1.0, color="#0f172a"):
        """Clave de Sol vectorial legible y vertical.

        Se dibuja con trazos simples para que no dependa de ninguna fuente musical
        instalada y para evitar la sensación de que la clave está "levantada".
        """
        s = float(escala or 1.0)
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(color), max(2.0, 3.0 * s), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)

        # Trazo principal vertical: baja atravesando el pentagrama.
        path = QPainterPath(QPointF(x + 26*s, y - 2*s))
        path.cubicTo(x + 12*s, y + 10*s, x + 15*s, y + 27*s, x + 29*s, y + 22*s)
        path.cubicTo(x + 46*s, y + 16*s, x + 49*s, y + 38*s, x + 32*s, y + 48*s)
        path.cubicTo(x + 12*s, y + 60*s, x + 3*s, y + 39*s, x + 20*s, y + 31*s)
        path.cubicTo(x + 38*s, y + 22*s, x + 51*s, y + 40*s, x + 36*s, y + 56*s)
        path.cubicTo(x + 22*s, y + 71*s, x + 12*s, y + 64*s, x + 14*s, y + 80*s)
        path.cubicTo(x + 19*s, y + 105*s, x + 47*s, y + 96*s, x + 39*s, y + 73*s)
        p.drawPath(path)

        p.drawLine(QPointF(x + 27*s, y + 2*s), QPointF(x + 25*s, y + 91*s))
        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(x + 22*s, y + 41*s, 8*s, 8*s))
        p.restore()

    def _dibujar_clave_fa(self, p: QPainter, x: float, y: float, escala: float = 1.0, color="#0f172a"):
        """Clave de Fa vectorial limpia: arco proporcionado y dos puntos en la línea de FA."""
        s = float(escala or 1.0)
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(color), max(2.0, 3.0 * s), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)

        path = QPainterPath(QPointF(x + 16*s, y + 16*s))
        path.cubicTo(x + 39*s, y + 2*s, x + 66*s, y + 17*s, x + 56*s, y + 39*s)
        path.cubicTo(x + 48*s, y + 56*s, x + 25*s, y + 61*s, x + 9*s, y + 71*s)
        p.drawPath(path)

        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(x + 5*s, y + 11*s, 12*s, 12*s))
        p.drawEllipse(QRectF(x + 57*s, y + 26*s, 8*s, 8*s))
        p.drawEllipse(QRectF(x + 57*s, y + 43*s, 8*s, 8*s))
        p.restore()

    def _dibujar_silencio_negra(self, p: QPainter, x: float, y: float, escala: float = 1.0, color="#1e293b"):
        """Silencio de negra aproximado mediante trazos vectoriales."""
        p.save()
        p.setPen(QPen(QColor(color), max(2.0, 3.0 * escala), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath(QPointF(x + 8*escala, y - 38*escala))
        path.lineTo(x - 4*escala, y - 18*escala)
        path.lineTo(x + 12*escala, y - 4*escala)
        path.lineTo(x - 6*escala, y + 16*escala)
        path.cubicTo(x + 6*escala, y + 8*escala, x + 18*escala, y + 16*escala, x + 10*escala, y + 30*escala)
        p.drawPath(path)
        p.restore()

    def _dibujar_corchea_simple(self, p: QPainter, x: float, y: float, escala: float = 1.0, color="#2563eb"):
        p.save()
        p.setPen(QPen(QColor(color), max(1.5, 2.0 * escala)))
        p.setBrush(QColor(color))
        p.drawEllipse(QRectF(x - 8*escala, y - 5*escala, 16*escala, 10*escala))
        p.drawLine(QPointF(x + 8*escala, y - 2*escala), QPointF(x + 8*escala, y - 42*escala))
        path = QPainterPath(QPointF(x + 8*escala, y - 42*escala))
        path.cubicTo(x + 30*escala, y - 35*escala, x + 32*escala, y - 18*escala, x + 12*escala, y - 12*escala)
        p.drawPath(path)
        p.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        self._reset_hotspots()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = self.rect().adjusted(12, 10, -12, -10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#fffdf7"))
        p.drawRoundedRect(r, 12, 12)

        self._dibujar_titulo(p, r)
        self._dibujar_ayuda_interactiva(p, r)

        if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico":
            self._dibujar_midi_didactico_vivo(p, r)
            self._dibujar_marcas_docentes(p, r)
            self._dibujar_midi_entrada_externa(p, r)
            self._dibujar_paso(p, r)
            self._dibujar_hover_hotspot(p)
            return

        if self.modo == "partitura":
            self._dibujar_partitura(p, r)
        elif self.modo == "ritmo":
            self._dibujar_ritmo(p, r)
        elif self.modo == "pulso":
            self._dibujar_pulso(p, r)
        elif self.modo == "digitacion":
            self._dibujar_digitacion(p, r)
        else:
            self._dibujar_general(p, r)

        self._dibujar_marcas_docentes(p, r)
        self._dibujar_midi_entrada_externa(p, r)
        self._dibujar_paso(p, r)
        self._dibujar_hover_hotspot(p)

    def _dibujar_titulo(self, p: QPainter, r):
        p.setPen(QColor("#0f3768"))
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(r.left()+8, r.top()+4, r.width()-16, 28), Qt.AlignCenter, self.titulo)

    def _dibujar_staff(self, p: QPainter, x: int, y: int, w: int, label: str, color="#0f172a", separacion: int = 10):
        p.setPen(QPen(QColor("#111827"), 1.4))
        for i in range(5):
            yy = y + i * int(separacion)
            p.drawLine(x, yy, x + w, yy)

        p.setPen(QColor(color))
        f = QFont()
        f.setPointSize(10 if separacion > 10 else 9)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(x, y - 28, w, 22), Qt.AlignLeft | Qt.AlignVCenter, label)

    def _dibujar_nota(self, p: QPainter, cx: int, cy: int, color="#2563eb", relleno=True, escala: float = 1.0):
        escala = max(0.8, min(1.8, float(escala or 1.0)))
        p.setPen(QPen(QColor(color), 2))
        p.setBrush(QBrush(QColor(color) if relleno else QColor("#fffdf7")))
        p.drawEllipse(QRectF(cx - 9 * escala, cy - 6 * escala, 18 * escala, 12 * escala))
        p.drawLine(int(cx + 8 * escala), int(cy - 3 * escala), int(cx + 8 * escala), int(cy - 45 * escala))

    def _puntero(self, p: QPainter, x: int, y: int, texto: str = ""):
        if not self.capas.get("puntero", True):
            return
        p.setPen(QPen(QColor("#f59e0b"), 3))
        p.setBrush(QColor("#fef3c7"))
        p.drawEllipse(QRectF(x-11, y-11, 22, 22))
        p.drawLine(x+12, y, x+52, y-20)
        if texto:
            p.setPen(QColor("#92400e"))
            f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
            p.drawText(QRectF(x+56, y-34, 210, 28), Qt.AlignLeft | Qt.AlignVCenter, texto)

    def _rect_label_docente(self, x: float, y: float, texto: str, color="#0f3768"):
        w = max(92, min(210, 18 + len(str(texto or "")) * 8))
        return QRectF(x, y, w, 28), QColor(color)

    def _dibujar_etiqueta_docente(self, p: QPainter, x: float, y: float, texto: str, color="#0f3768", intensidad: float = 1.0):
        rect, qcolor = self._rect_label_docente(x, y, texto, color)
        p.save()
        alpha = max(45, min(255, int(255 * max(0.0, min(1.0, intensidad)))))
        qcolor.setAlpha(alpha)
        fondo = QColor("#ffffff")
        fondo.setAlpha(max(160, min(245, int(235 * max(0.0, min(1.0, intensidad))))))
        p.setPen(QPen(qcolor, 1.4))
        p.setBrush(fondo)
        p.drawRoundedRect(rect, 8, 8)
        p.setPen(qcolor)
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, texto)
        p.restore()

    def _dibujar_mano_docente(self, p: QPainter, cx: float, cy: float, lado: str, color="#2563eb", intensidad: float = 1.0):
        size = 42
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)
        if lado == "derecha":
            self.dibujar_icono_mano_derecha(p, rect, intensidad, color)
        else:
            self.dibujar_icono_mano_izquierda(p, rect, intensidad, color)

    def dibujar_icono_mano_derecha(self, painter: QPainter, rect: QRectF, intensidad: float = 1.0, color="#2563eb"):
        self._dibujar_icono_mano(painter, rect, "derecha", intensidad, color)

    def dibujar_icono_mano_izquierda(self, painter: QPainter, rect: QRectF, intensidad: float = 1.0, color="#16a34a"):
        self._dibujar_icono_mano(painter, rect, "izquierda", intensidad, color)

    def _dibujar_icono_mano(self, p: QPainter, rect: QRectF, lado: str, intensidad: float, color="#2563eb"):
        p.save()
        qcolor = QColor(color)
        qcolor.setAlpha(max(70, min(255, int(255 * intensidad))))
        relleno = QColor("#dbeafe" if lado == "derecha" else "#dcfce7")
        relleno.setAlpha(max(80, min(230, int(220 * intensidad))))
        brillo = QColor(color)
        brillo.setAlpha(max(0, min(72, int(58 * intensidad))))

        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(brillo)
        p.drawEllipse(rect.adjusted(-5, -5, 5, 5))

        p.setPen(QPen(qcolor, 1.7))
        p.setBrush(relleno)
        cx = rect.center().x()
        cy = rect.center().y()
        escala = rect.width() / 42.0

        palma = QRectF(cx - 12 * escala, cy - 2 * escala, 24 * escala, 20 * escala)
        p.drawRoundedRect(palma, 9 * escala, 9 * escala)

        dedos = [
            (-12, -18, 6, 20),
            (-5, -23, 6, 25),
            (2, -25, 6, 27),
            (9, -21, 6, 23),
        ]
        for dx, dy, ancho, alto in dedos:
            p.drawRoundedRect(
                QRectF(cx + dx * escala, cy + dy * escala, ancho * escala, alto * escala),
                3.2 * escala,
                3.2 * escala,
            )

        if lado == "derecha":
            pulgar = QRectF(cx + 11 * escala, cy + 2 * escala, 14 * escala, 8 * escala)
        else:
            pulgar = QRectF(cx - 25 * escala, cy + 2 * escala, 14 * escala, 8 * escala)
        p.drawRoundedRect(pulgar, 4 * escala, 4 * escala)

        p.setPen(QPen(qcolor, 1.2))
        p.drawLine(QPointF(cx - 8 * escala, cy + 18 * escala), QPointF(cx + 8 * escala, cy + 18 * escala))
        p.restore()

    def _dibujar_flecha_docente(self, p: QPainter, x1: float, y1: float, x2: float, y2: float, color="#f59e0b", intensidad: float = 1.0):
        p.save()
        qcolor = QColor(color)
        qcolor.setAlpha(max(45, min(255, int(235 * intensidad))))
        p.setPen(QPen(qcolor, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        ang = 0.55
        direction = QPointF(x2 - x1, y2 - y1)
        length = max(1.0, (direction.x() ** 2 + direction.y() ** 2) ** 0.5)
        ux, uy = direction.x() / length, direction.y() / length
        left = QPointF(x2 - 16 * (ux * 0.85 - uy * ang), y2 - 16 * (uy * 0.85 + ux * ang))
        right = QPointF(x2 - 16 * (ux * 0.85 + uy * ang), y2 - 16 * (uy * 0.85 - ux * ang))
        p.setBrush(qcolor)
        p.drawPolygon(QPolygonF([QPointF(x2, y2), left, right]))
        p.restore()

    def _fase_marca_docente(self, marca: dict) -> tuple[float, float]:
        ahora = time.monotonic()
        try:
            edad_ms = (ahora - float(marca.get("inicio", ahora))) * 1000.0
            duracion = float(marca.get("duracion_ms", 2500) or 2500)
            fade = float(marca.get("fade_ms", 1100) or 1100)
        except Exception:
            return 1.0, 0.0
        if edad_ms <= duracion:
            fade_factor = 1.0
        else:
            fade_factor = max(0.0, 1.0 - ((edad_ms - duracion) / max(1.0, fade)))
        pulso = 0.64 + 0.36 * (0.5 + 0.5 * math.sin((edad_ms / 1000.0) * math.tau * 1.35))
        intensidad = max(0.0, min(1.0, pulso * fade_factor))
        return intensidad, edad_ms

    def _dibujar_marcas_docentes(self, p: QPainter, r):
        marcas = list(getattr(self, "marcas_docentes", []) or [])
        if not marcas:
            return

        x = r.left() + (58 if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico" else 55)
        w = r.width() - (116 if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico" else 110)
        y1 = r.top() + (62 if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico" else 58)
        y2 = r.top() + (150 if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico" else 138)
        cx_do = x + int(w * 0.50)
        cy_do = y1 + 58

        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        for marca in marcas:
            tipo = marca.get("tipo", "")
            etiqueta = marca.get("etiqueta", "")
            intensidad, edad_ms = self._fase_marca_docente(marca)
            if intensidad <= 0:
                continue
            halo_extra = 5 + 10 * intensidad
            if tipo == "lineas_pentagrama":
                color = QColor("#f59e0b")
                color.setAlpha(max(45, min(210, int(190 * intensidad))))
                p.setPen(QPen(color, 2.2 + 2.0 * intensidad, Qt.SolidLine, Qt.RoundCap))
                for i in range(5):
                    yy = y1 + i * 10
                    p.drawLine(QPointF(x + 3, yy), QPointF(x + w - 3, yy))
                self._dibujar_etiqueta_docente(p, x + w - 180, y1 - 34, etiqueta or "Cinco líneas", "#92400e", intensidad)
            elif tipo == "clave_sol":
                halo = QRectF(x - halo_extra * 0.45, y1 - 30 - halo_extra * 0.5, 70 + halo_extra, 96 + halo_extra)
                pen = QColor("#2563eb"); pen.setAlpha(max(55, min(255, int(225 * intensidad))))
                brush = QColor(37, 99, 235, max(18, min(74, int(54 * intensidad))))
                p.setPen(QPen(pen, 2.0 + 2.2 * intensidad))
                p.setBrush(brush)
                p.drawEllipse(halo)
                self._dibujar_flecha_docente(p, x + 138 + 4 * intensidad, y1 - 26, x + 48, y1 + 18, "#2563eb", intensidad)
                self._dibujar_etiqueta_docente(p, x + 146, y1 - 42, etiqueta or "Clave de Sol", "#1d4ed8", intensidad)
            elif tipo == "clave_fa":
                halo = QRectF(x - 2 - halo_extra * 0.45, y2 - 23 - halo_extra * 0.5, 74 + halo_extra, 84 + halo_extra)
                pen = QColor("#16a34a"); pen.setAlpha(max(55, min(255, int(225 * intensidad))))
                brush = QColor(22, 163, 74, max(18, min(74, int(54 * intensidad))))
                p.setPen(QPen(pen, 2.0 + 2.2 * intensidad))
                p.setBrush(brush)
                p.drawEllipse(halo)
                self._dibujar_flecha_docente(p, x + 138 + 4 * intensidad, y2 - 14, x + 50, y2 + 18, "#16a34a", intensidad)
                self._dibujar_etiqueta_docente(p, x + 146, y2 - 32, etiqueta or "Clave de Fa", "#15803d", intensidad)
            elif tipo == "mano_derecha":
                mx, my = x + w - 74, y1 + 22
                self._dibujar_mano_docente(p, mx, my, "derecha", "#2563eb", intensidad)
                self._dibujar_etiqueta_docente(p, mx - 58, my + 27, etiqueta or "Mano derecha", "#1d4ed8", intensidad)
            elif tipo == "mano_izquierda":
                mx, my = x + w - 74, y2 + 22
                self._dibujar_mano_docente(p, mx, my, "izquierda", "#16a34a", intensidad)
                self._dibujar_etiqueta_docente(p, mx - 62, my + 27, etiqueta or "Mano izquierda", "#15803d", intensidad)
            elif tipo == "do_central":
                pen = QColor("#dc2626"); pen.setAlpha(max(60, min(255, int(235 * intensidad))))
                brush = QColor(220, 38, 38, max(18, min(70, int(52 * intensidad))))
                p.setPen(QPen(pen, 2.0 + 2.0 * intensidad))
                p.setBrush(brush)
                p.drawEllipse(QRectF(cx_do - 28 - halo_extra * 0.4, cy_do - 22 - halo_extra * 0.25, 56 + halo_extra * 0.8, 44 + halo_extra * 0.5))
                p.drawLine(cx_do - 28, cy_do, cx_do + 28, cy_do)
                self._dibujar_flecha_docente(p, cx_do - 120, cy_do + 42 + 3 * intensidad, cx_do - 22, cy_do + 6, "#dc2626", intensidad)
                self._dibujar_etiqueta_docente(p, cx_do - 205, cy_do + 32, etiqueta or "DO central", "#b91c1c", intensidad)
            elif tipo == "espacios_pentagrama":
                color = QColor("#8b5cf6")
                color.setAlpha(max(26, min(110, int(80 * intensidad))))
                p.setPen(Qt.NoPen)
                p.setBrush(color)
                for y_base in (y1, y2):
                    for i in range(4):
                        yy = y_base + i * 10 + 2
                        p.drawRoundedRect(QRectF(x + 75, yy, w - 125, 6), 3, 3)
                self._dibujar_etiqueta_docente(p, x + w - 180, y1 + 72, etiqueta or "Espacios", "#6d28d9", intensidad)
            elif tipo == "compases":
                color = QColor("#0f766e")
                color.setAlpha(max(50, min(230, int(210 * intensidad))))
                p.setPen(QPen(color, 2.0 + 1.5 * intensidad, Qt.SolidLine, Qt.RoundCap))
                for frac in (0.34, 0.55, 0.76):
                    xx = x + w * frac
                    p.drawLine(QPointF(xx, y1), QPointF(xx, y1 + 40))
                    p.drawLine(QPointF(xx, y2), QPointF(xx, y2 + 40))
                self._dibujar_flecha_docente(p, x + w * 0.55, y1 - 38, x + w * 0.55, y1 + 5, "#0f766e", intensidad)
                self._dibujar_etiqueta_docente(p, x + w * 0.55 + 14, y1 - 48, etiqueta or "Compases", "#0f766e", intensidad)
            elif tipo == "notas":
                color = QColor("#db2777")
                color.setAlpha(max(55, min(245, int(220 * intensidad))))
                brush = QColor(219, 39, 119, max(18, min(72, int(54 * intensidad))))
                p.setPen(QPen(color, 2.0 + 1.8 * intensidad))
                p.setBrush(brush)
                puntos = [
                    QPointF(x + int(w * 0.43), y1 + 10),
                    QPointF(x + int(w * 0.50), y1 + 58),
                    QPointF(x + int(w * 0.30), y2 + 30),
                ]
                for punto in puntos:
                    p.drawEllipse(QRectF(punto.x() - 18 - halo_extra * 0.25, punto.y() - 14 - halo_extra * 0.25, 36 + halo_extra * 0.5, 28 + halo_extra * 0.5))
                self._dibujar_etiqueta_docente(p, x + w * 0.58, y1 + 72, etiqueta or "Notas", "#be185d", intensidad)
            elif tipo == "claves":
                for yy, color_txt, etiqueta_txt in (
                    (y1, "#2563eb", "Clave de Sol"),
                    (y2, "#16a34a", "Clave de Fa"),
                ):
                    halo = QRectF(x - halo_extra * 0.45, yy - 28 - halo_extra * 0.5, 72 + halo_extra, 88 + halo_extra)
                    pen = QColor(color_txt); pen.setAlpha(max(55, min(255, int(215 * intensidad))))
                    brush = QColor(color_txt); brush.setAlpha(max(16, min(64, int(48 * intensidad))))
                    p.setPen(QPen(pen, 1.8 + 1.8 * intensidad))
                    p.setBrush(brush)
                    p.drawEllipse(halo)
                self._dibujar_etiqueta_docente(p, x + 112, y1 + 52, etiqueta or "Claves", "#334155", intensidad)
        p.restore()

    def _dibujar_partitura(self, p: QPainter, r):
        x = r.left() + 55
        w = r.width() - 110
        # v4.0.1: subimos el sistema para que el pentagrama inferior no quede cortado.
        y1 = r.top() + 58
        y2 = r.top() + 138

        if self.capas.get("manos", True):
            label1 = "Pentagrama superior = normalmente mano derecha"
            label2 = "Pentagrama inferior = normalmente mano izquierda"
        else:
            label1 = "Pentagrama superior"
            label2 = "Pentagrama inferior"

        self._dibujar_staff(p, x, y1, w, label1, "#2563eb")
        self._dibujar_staff(p, x, y2, w, label2, "#16a34a")

        p.setPen(QPen(QColor("#64748b"), 3))
        p.drawArc(x - 30, y1 - 5, 24, (y2-y1)+45, 90*16, 180*16)

        if self.capas.get("claves", True):
            self._dibujar_clave_sol(p, x + 9, y1 - 18, 0.72, "#0f172a")
            self._dibujar_clave_fa(p, x + 5, y2 - 10, 0.58, "#0f172a")
            self._add_hotspot(
                QRectF(x + 4, y1 - 25, 56, 86),
                "Clave de Sol",
                "La clave de Sol marca la línea de SOL y ayuda a leer el pentagrama superior.",
                ["G4"],
            )
            self._add_hotspot(
                QRectF(x + 4, y2 - 18, 62, 78),
                "Clave de Fa",
                "La clave de Fa señala la línea de FA y orienta la lectura del pentagrama inferior.",
                ["F3"],
            )

        if self.paso >= 1 and self.capas.get("claves", True):
            sol_y = y1 + 10
            p.setPen(QPen(QColor("#2563eb"), 3))
            p.drawLine(x + 42, sol_y, x + 145, sol_y)
            self._dibujar_nota(p, x + 160, sol_y, "#2563eb", True)
            self._add_hotspot(
                QRectF(x + 140, sol_y - 24, 82, 56),
                "Nota SOL",
                "SOL es la nota de referencia de la clave de Sol. Si la pulsas, el piano debe resaltar SOL.",
                ["G4"],
            )
            p.setPen(QColor("#2563eb"))
            f_sol = QFont(); f_sol.setPointSize(9); f_sol.setBold(True); p.setFont(f_sol)
            p.drawText(QRectF(x + 185, sol_y - 13, 310, 24), Qt.AlignLeft | Qt.AlignVCenter, "Clave de Sol: línea de SOL")
            self._puntero(p, x + 160, sol_y, "SOL")

        if self.paso >= 2 and self.capas.get("claves", True):
            fa_y = y2 + 20
            p.setPen(QPen(QColor("#16a34a"), 3))
            p.drawLine(x + 42, fa_y, x + 145, fa_y)
            self._dibujar_nota(p, x + 160, fa_y, "#16a34a", True)
            self._add_hotspot(
                QRectF(x + 140, fa_y - 24, 86, 56),
                "Nota FA",
                "FA es la referencia de la clave de Fa. Sirve para leer el pentagrama inferior.",
                ["F3"],
            )
            p.setPen(QColor("#16a34a"))
            f_fa = QFont(); f_fa.setPointSize(9); f_fa.setBold(True); p.setFont(f_fa)
            p.drawText(QRectF(x + 185, fa_y - 13, 310, 24), Qt.AlignLeft | Qt.AlignVCenter, "Clave de Fa: puntos en FA")
            self._puntero(p, x + 160, fa_y, "FA")

        cx = x + int(w * 0.50)
        cy = y1 + 58
        if self.paso >= 3 and self.capas.get("do_central", True):
            p.setPen(QPen(QColor("#dc2626"), 2))
            p.drawLine(cx - 20, cy, cx + 20, cy)
            self._dibujar_nota(p, cx, cy, "#dc2626", relleno=False)
            self._add_hotspot(
                QRectF(cx - 30, cy - 26, 92, 64),
                "DO central",
                "El DO central es el puente entre el pentagrama superior, el inferior y el centro del teclado.",
                ["C4"],
            )
            p.setPen(QColor("#dc2626"))
            f2 = QFont(); f2.setPointSize(10); f2.setBold(True); p.setFont(f2)
            p.drawText(QRectF(cx - 80, cy + 8, 160, 22), Qt.AlignCenter, "DO central")
            self._puntero(p, cx, cy, "DO central")

        if self.paso >= 4 and self.capas.get("notas", True):
            agudo_x = x + int(w*0.72)
            grave_x = x + int(w*0.30)
            self._dibujar_nota(p, agudo_x, y1 + 10, "#2563eb", True)
            self._dibujar_nota(p, grave_x, y2 + 30, "#16a34a", True)
            self._add_hotspot(QRectF(agudo_x - 24, y1 - 18, 96, 58), "Nota aguda", "Esta nota está más arriba en el pentagrama: su sonido es más agudo.", ["G4"])
            self._add_hotspot(QRectF(grave_x - 24, y2 + 2, 96, 58), "Nota grave", "Esta nota está más abajo en el pentagrama: su sonido es más grave.", ["F3"])
            p.setPen(QColor("#475569"))
            f3 = QFont(); f3.setPointSize(9); p.setFont(f3)
            p.drawText(QRectF(x + int(w*0.65), y1 - 4, 150, 20), Qt.AlignCenter, "más agudo")
            p.drawText(QRectF(x + int(w*0.22), y2 + 38, 170, 20), Qt.AlignCenter, "más grave")

    def _nota_a_y_treble(self, nota: str, y_staff: int, separacion: int = 10) -> int:
        """Mapa didáctico suficiente para Nivel 1: C4-G4 en clave de Sol."""
        base = str(nota or "").upper().strip()
        base = base.replace("DO", "C").replace("RE", "D").replace("MI", "E").replace("FA", "F").replace("SOL", "G")
        paso = max(4, float(separacion) / 2.0)
        mapa = {
            "C4": y_staff + paso * 10,
            "D4": y_staff + paso * 9,
            "E4": y_staff + paso * 8,
            "F4": y_staff + paso * 7,
            "G4": y_staff + paso * 6,
            "A4": y_staff + paso * 5,
            "B4": y_staff + paso * 4,
            "C5": y_staff + paso * 3,
        }
        return int(mapa.get(base, y_staff + paso * 8))

    def _nota_dict_a_posicion_midi_vivo(self, item: dict, y_treble: int, y_bass: int, separacion: int = 14):
        """Posiciona una nota usando su MIDI real. MIDI 60 = C4/Do central."""
        nota = self._normalizar_nota_midi(str((item or {}).get("nota", "")))
        try:
            midi = int((item or {}).get("midi", 0) or 0)
        except Exception:
            midi = 0
        if midi <= 0:
            midi = self._nota_nombre_a_midi(nota)
        if midi <= 0:
            return self._nota_a_y_treble(nota, y_treble, separacion), "superior", nota.startswith("C4")

        octava = (midi // 12) - 1
        pc = midi % 12
        base_por_pc = {0: "C", 1: "C", 2: "D", 3: "D", 4: "E", 5: "F", 6: "F", 7: "G", 8: "G", 9: "A", 10: "A", 11: "B"}
        base = base_por_pc.get(pc, "C")
        orden = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
        idx = octava * 7 + orden.get(base, 0)
        paso = max(4.0, float(separacion) / 2.0)

        if midi >= 60:
            # Clave de Sol: línea inferior = E4. Cada grado diatónico cambia medio espacio.
            ref = 4 * 7 + orden["E"]
            y = y_treble + 4 * separacion - (idx - ref) * paso
            return int(y), "superior", midi == 60

        # Clave de Fa: línea superior = A3. C3 queda visualmente en el pentagrama inferior.
        ref = 3 * 7 + orden["A"]
        y = y_bass - (idx - ref) * paso
        return int(y), "inferior", False

    def _nota_nombre_a_midi(self, nota: str) -> int:
        return int(nombre_a_midi(nota) or 0)

    def _nota_legible_es(self, nota: str) -> str:
        info = normalizar_nota(nota)
        if info.get("midi") is not None:
            return str(info.get("nombre_completo", nota))
        return str(nota or "")

    def _accidental_midi_vivo(self, item: dict | None) -> str:
        """Devuelve el accidental que debe verse en el pentagrama.

        Importante para Hanon/MIDI didáctico: una nota como G#4/Sol#4 se
        coloca en la misma línea/espacio que Sol, pero debe llevar el símbolo
        de sostenido. Sin este símbolo la pizarra parece pedir Sol natural
        mientras el piano resalta Sol sostenido.
        """
        item = item or {}
        texto_original = str(
            item.get("nota")
            or item.get("note_name")
            or item.get("nombre_completo")
            or ""
        ).strip()
        texto = texto_original.replace("♯", "#").replace("＃", "#").replace("♭", "b")
        # Si el origen trae un bemol explícito, se conserva como bemol visual.
        if "b" in texto and not texto.upper().startswith("B"):
            return "♭"
        try:
            midi = int(item.get("midi", item.get("midi_number", 0)) or 0)
        except Exception:
            midi = 0
        try:
            info = normalizar_nota(texto_original, midi=midi if midi else None)
            note_name = str(info.get("note_name", "") or "")
        except Exception:
            note_name = texto
        if "#" in note_name or "#" in texto:
            return "♯"
        return ""

    def _dibujar_accidental_midi_vivo(self, p: QPainter, cx: int, cy: int, item: dict | None, color: str):
        accidental = self._accidental_midi_vivo(item)
        if not accidental:
            return
        p.save()
        p.setPen(QColor(color))
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        p.setFont(f)
        # El símbolo va a la izquierda de la cabeza de nota, como en notación real.
        p.drawText(QRectF(cx - 42, cy - 22, 26, 42), Qt.AlignCenter, accidental)
        p.restore()

    def _clave_evento_midi_vivo(self, item: dict) -> tuple:
        return (
            str(item.get("nota", "")),
            int(item.get("inicio_ms", -1) or -1),
            int(item.get("duracion_ms", -1) or -1),
            int(item.get("compas", 0) or 0),
            int(item.get("pulso", 0) or 0),
        )

    def _normalizar_nota_midi(self, nota: str) -> str:
        n = str(nota or "").strip().upper()
        for es, ang in (("DO", "C"), ("RE", "D"), ("MI", "E"), ("FA", "F"), ("SOL", "G"), ("LA", "A"), ("SI", "B")):
            n = n.replace(es, ang)
        return n

    def _nota_midi_a_posicion_staff(self, nota: str, y_treble: int, y_bass: int, separacion: int = 14):
        """Devuelve posición didáctica aproximada para mostrar la nota MIDI entrante."""
        n = self._normalizar_nota_midi(nota).replace("♯", "#").replace("♭", "B")
        if not n:
            return y_treble + 40, "superior", False
        return self._nota_dict_a_posicion_midi_vivo(normalizar_nota(n), y_treble, y_bass, separacion)

    def _dibujar_midi_entrada_externa(self, p: QPainter, r):
        if not getattr(self, "midi_entrada_nota", ""):
            return

        x = r.left() + 55
        w = r.width() - 110
        y1 = r.top() + 58
        y2 = r.top() + 138
        nota = str(getattr(self, "midi_entrada_nota", "") or "")
        activa = bool(getattr(self, "midi_entrada_activa", False))
        velocity = int(getattr(self, "midi_entrada_velocity", 0) or 0)
        canal = int(getattr(self, "midi_entrada_canal", 0) or 0)
        origen = str(getattr(self, "midi_entrada_origen", "") or "")

        # En modo MIDI didáctico las líneas están algo más abajo.
        if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico":
            y1 = r.top() + 82
            y2 = r.top() + 210

        cx = x + int(w * 0.83)
        cy, pentagrama, ledger_do = self._nota_midi_a_posicion_staff(nota, y1, y2, 14)
        if "hanon_correcta" in origen or "midi_practica_correcta" in origen:
            color, halo, relleno, texto_color = "#16a34a", "#16a34a", "#dcfce7", "#166534"
        elif "hanon_fuera_pulso" in origen or "midi_practica_fuera_pulso" in origen:
            color, halo, relleno, texto_color = "#ca8a04", "#f59e0b", "#fef3c7", "#854d0e"
        elif "hanon_incorrecta" in origen or "midi_practica_incorrecta" in origen:
            color, halo, relleno, texto_color = "#dc2626", "#dc2626", "#fee2e2", "#991b1b"
        else:
            color = "#dc2626" if activa else "#64748b"
            halo, relleno, texto_color = ("#f97316" if activa else "#94a3b8"), ("#ffedd5" if activa else "#f1f5f9"), ("#7c2d12" if activa else "#334155")

        p.save()
        # Halo: deja claro que esto viene del teclado físico, no de una nota estática.
        p.setPen(QPen(QColor(halo), 3 if activa else 2))
        p.setBrush(QColor(relleno))
        p.drawEllipse(QRectF(cx - 19, cy - 19, 38, 38))
        if ledger_do or self._normalizar_nota_midi(nota).startswith("C4"):
            p.setPen(QPen(QColor("#64748b"), 1.6))
            p.drawLine(cx - 24, cy, cx + 24, cy)
        self._dibujar_nota(p, cx, cy, color, True)
        self._puntero(p, cx, cy, "MIDI externo")

        nombre = self._nota_legible_es(nota)
        txt = f"Teclado MIDI: {nombre}"
        if velocity:
            txt += f" · vel {velocity}"
        if canal:
            txt += f" · ch {canal}"
        p.setPen(QColor(texto_color))
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(cx - 130, cy + 22, 260, 24), Qt.AlignCenter, txt)
        self._add_hotspot(
            QRectF(cx - 36, cy - 32, 180, 82),
            "Nota tocada por MIDI externo",
            f"Has tocado {nombre} en el teclado físico. La pizarra lo coloca en el pentagrama {pentagrama}.",
            [nota],
        )
        p.restore()

    def _normalizar_lado_mano_hanon(self, valor: str, item: dict | None = None) -> str:
        texto = str(valor or "").strip().lower()
        if "izq" in texto or "left" in texto or texto == "lh":
            return "izquierda"
        if "der" in texto or "right" in texto or texto == "rh":
            return "derecha"
        try:
            midi = int((item or {}).get("midi", (item or {}).get("midi_number", 0)) or 0)
            return "izquierda" if midi and midi < 60 else "derecha"
        except Exception:
            return "derecha"

    def _dedo_hanon_item(self, item: dict | None) -> int | None:
        item = item or {}
        for clave in ("dedo", "finger", "finger_number"):
            try:
                dedo = int(item.get(clave, 0) or 0)
                if 1 <= dedo <= 5:
                    return dedo
            except Exception:
                pass
        digitacion = item.get("digitacion") if isinstance(item.get("digitacion"), dict) else {}
        try:
            dedo = int((digitacion or {}).get("dedo", 0) or 0)
            if 1 <= dedo <= 5:
                return dedo
        except Exception:
            pass
        return None

    def _items_digitacion_hanon(self) -> list[dict]:
        candidatos = []
        candidatos.extend(list(getattr(self, "hanon_digitacion_activas", []) or []))
        candidatos.append(dict(getattr(self, "hanon_digitacion_actual", {}) or {}))
        candidatos.append(dict(getattr(self, "hanon_digitacion_siguiente", {}) or {}))
        salida = []
        vistos = set()
        for item in candidatos:
            if not isinstance(item, dict) or not item:
                continue
            dedo = self._dedo_hanon_item(item)
            if dedo is None:
                continue
            mano = self._normalizar_lado_mano_hanon(str(item.get("mano", "")), item)
            clave = (mano, dedo, item.get("nota"), item.get("inicio_ms"), item.get("canal"))
            if clave in vistos:
                continue
            vistos.add(clave)
            normalizado = dict(item)
            normalizado["mano"] = mano
            normalizado["dedo"] = dedo
            salida.append(normalizado)
        return salida

    def _cargar_pixmap_mano_hanon(self, lado: str) -> QPixmap:
        lado = "izquierda" if lado == "izquierda" else "derecha"
        if lado in self._pixmap_manos_digitacion:
            return self._pixmap_manos_digitacion[lado]
        nombre = "mano_izquierda_digitacion_hanon.png" if lado == "izquierda" else "mano_derecha_digitacion_hanon.png"
        ruta = ASSETS_DIR / "teoria" / "hanon" / nombre
        pix = QPixmap(str(ruta))
        self._pixmap_manos_digitacion[lado] = pix
        return pix

    def _posicion_dedo_hanon(self, lado: str, dedo: int) -> tuple[float, float]:
        # Coordenadas normalizadas sobre los recortes creados desde la imagen
        # aportada por el usuario. Apuntan al círculo de cada dedo.
        mapa = {
            "izquierda": {
                1: (0.878, 0.396),
                2: (0.651, 0.120),
                3: (0.443, 0.062),
                4: (0.256, 0.120),
                5: (0.103, 0.224),
            },
            "derecha": {
                1: (0.082, 0.396),
                2: (0.284, 0.120),
                3: (0.466, 0.062),
                4: (0.660, 0.120),
                5: (0.821, 0.224),
            },
        }
        return mapa.get(lado, {}).get(int(dedo), (0.5, 0.18))

    def _color_dedo_hanon(self, dedo: int, lado: str = "derecha") -> QColor:
        colores = {
            1: "#dc2626",
            2: "#f59e0b",
            3: "#2563eb",
            4: "#16a34a",
            5: "#7c3aed",
        }
        return QColor(colores.get(int(dedo or 0), "#2563eb"))

    def _texto_nota_corto_hanon(self, item: dict | None) -> str:
        item = item or {}
        return str(item.get("nombre_completo") or item.get("nota") or item.get("note_name") or "—")

    def _dibujar_tarjeta_mano_hanon(self, p: QPainter, rect: QRectF, lado: str, item: dict | None, activo: bool = True):
        lado = "izquierda" if lado == "izquierda" else "derecha"
        item = dict(item or {})
        dedo = self._dedo_hanon_item(item)
        color_base = QColor("#2563eb" if lado == "izquierda" else "#16a34a")
        fondo = QColor("#eff6ff" if lado == "izquierda" else "#f0fdf4")
        if not activo:
            fondo = QColor("#f8fafc")

        p.save()
        p.setPen(QPen(color_base, 2 if activo else 1.2, Qt.SolidLine if activo else Qt.DashLine))
        p.setBrush(fondo)
        p.drawRoundedRect(rect, 12, 12)

        titulo = "Mano izquierda" if lado == "izquierda" else "Mano derecha"
        nota = self._texto_nota_corto_hanon(item)
        subtitulo = f"dedo {dedo} · {nota}" if dedo else "esperando nota"
        p.setPen(color_base)
        f = QFont(); f.setPointSize(10); f.setBold(True); p.setFont(f)
        p.drawText(rect.adjusted(10, 4, -10, 0), Qt.AlignLeft | Qt.AlignTop, titulo)
        p.setPen(QColor("#334155"))
        f2 = QFont(); f2.setPointSize(8); f2.setBold(True); p.setFont(f2)
        p.drawText(rect.adjusted(10, 23, -10, 0), Qt.AlignLeft | Qt.AlignTop, subtitulo)

        pix = self._cargar_pixmap_mano_hanon(lado)
        img_rect = rect.adjusted(8, 38, -8, -8)
        crop_factor = 0.60
        if not pix.isNull():
            # Recorte visual: se elimina la parte baja con muñeca/etiqueta para
            # que los dedos ocupen más espacio dentro de la tarjeta. La imagen
            # original se conserva intacta en assets.
            src = QRectF(0, 0, pix.width(), max(1, pix.height() * crop_factor))
            ratio = src.width() / max(1.0, src.height())
            destino_h = img_rect.height()
            destino_w = destino_h * ratio
            if destino_w > img_rect.width():
                destino_w = img_rect.width()
                destino_h = destino_w / max(0.01, ratio)
            destino = QRectF(
                img_rect.center().x() - destino_w / 2,
                img_rect.top() + (img_rect.height() - destino_h) / 2,
                destino_w,
                destino_h,
            )
            p.setOpacity(1.0 if activo else 0.52)
            p.drawPixmap(destino, pix, src)
            p.setOpacity(1.0)
        else:
            destino = img_rect
            crop_factor = 1.0
            self._dibujar_mano_docente(p, destino.center().x(), destino.center().y(), lado, color_base.name(), 0.9 if activo else 0.35)

        if dedo:
            nx, ny = self._posicion_dedo_hanon(lado, dedo)
            cx = destino.left() + destino.width() * nx
            cy = destino.top() + destino.height() * min(0.98, ny / max(0.01, crop_factor))
            color_dedo = self._color_dedo_hanon(dedo, lado)

            # Anillo pulsante: marca con precisión el dedo correcto para la nota actual.
            pulso = 0.72 + 0.28 * (0.5 + 0.5 * math.sin(time.monotonic() * math.tau * 1.15))
            radio = max(16.0, min(30.0, rect.height() * 0.065)) * (1.0 if activo else 0.82)
            halo = QColor(color_dedo)
            halo.setAlpha(70 if activo else 38)
            p.setBrush(halo)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(cx - radio * 1.55 * pulso, cy - radio * 1.55 * pulso, radio * 3.1 * pulso, radio * 3.1 * pulso))

            p.setPen(QPen(QColor("#ffffff"), 5))
            p.setBrush(color_dedo)
            p.drawEllipse(QRectF(cx - radio, cy - radio, radio * 2, radio * 2))
            p.setPen(QColor("#ffffff"))
            f3 = QFont(); f3.setPointSize(max(10, int(radio * 0.82))); f3.setBold(True); p.setFont(f3)
            p.drawText(QRectF(cx - radio, cy - radio, radio * 2, radio * 2), Qt.AlignCenter, str(dedo))

            etiqueta = f"Toca con dedo {dedo}"
            label_w = min(rect.width() - 20, max(118, len(etiqueta) * 7.4))
            label = QRectF(rect.right() - label_w - 10, rect.top() + 8, label_w, 24)
            p.setPen(QPen(color_dedo, 1.2))
            p.setBrush(QColor("#ffffff"))
            p.drawRoundedRect(label, 8, 8)
            p.setPen(color_dedo)
            f4 = QFont(); f4.setPointSize(8); f4.setBold(True); p.setFont(f4)
            p.drawText(label.adjusted(7, 0, -7, 0), Qt.AlignCenter, etiqueta)
        p.restore()

    def _dibujar_digitacion_hanon_viva(self, p: QPainter, r, x: float, y_base: float, w: float, y_limite: float):
        items = self._items_digitacion_hanon()
        if not items:
            return

        por_mano = {"izquierda": None, "derecha": None}
        for item in items:
            mano = self._normalizar_lado_mano_hanon(str(item.get("mano", "")), item)
            if por_mano.get(mano) is None:
                por_mano[mano] = item

        alto_disp = max(0.0, float(y_limite) - float(y_base))
        if alto_disp < 92:
            # Fallback compacto para ventanas pequeñas: muestra la digitación sin invadir el flujo MIDI.
            p.save()
            texto_items = []
            for mano in ("izquierda", "derecha"):
                item = por_mano.get(mano) or {}
                dedo = self._dedo_hanon_item(item)
                if dedo:
                    texto_items.append(f"{'MI' if mano == 'izquierda' else 'MD'} dedo {dedo} · {self._texto_nota_corto_hanon(item)}")
            if texto_items:
                box = QRectF(x + 8, max(r.top() + 42, y_base - 36), min(w - 16, 460), 30)
                p.setPen(QPen(QColor("#1d4ed8"), 1.2))
                p.setBrush(QColor("#eff6ff"))
                p.drawRoundedRect(box, 8, 8)
                p.setPen(QColor("#0f3768"))
                f = QFont(); f.setPointSize(8); f.setBold(True); p.setFont(f)
                p.drawText(box.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "Digitación Hanon: " + "  |  ".join(texto_items))
            p.restore()
            return

        panel_h = min(310.0, max(190.0, alto_disp))
        card_gap = 14.0
        card_w = (w - card_gap) / 2.0
        if card_w < 160:
            return
        y = y_base + max(0.0, (alto_disp - panel_h) * 0.06)
        left = QRectF(x, y, card_w, panel_h)
        right = QRectF(x + card_w + card_gap, y, card_w, panel_h)

        p.save()
        p.setPen(QColor("#0f3768"))
        f = QFont(); f.setPointSize(10); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(x + 2, y - 22, w - 4, 20), Qt.AlignLeft | Qt.AlignVCenter, "Digitación Hanon sincronizada con la nota activa")
        p.restore()

        self._dibujar_tarjeta_mano_hanon(p, left, "izquierda", por_mano.get("izquierda"), bool(por_mano.get("izquierda")))
        self._dibujar_tarjeta_mano_hanon(p, right, "derecha", por_mano.get("derecha"), bool(por_mano.get("derecha")))

    def _dibujar_midi_didactico_vivo(self, p: QPainter, r):
        x = r.left() + 58
        w = r.width() - 116
        separacion_staff = 14
        # Dejamos una franja superior para estado/paso y liberamos la parte baja
        # para que la digitación Hanon no quede encajonada encima del piano global.
        y1 = r.top() + 104
        y2 = y1 + 126

        self._dibujar_staff(p, x, y1, w, "Pentagrama ND superior · mano derecha", "#2563eb", separacion_staff)
        self._dibujar_staff(p, x, y2, w, "Pentagrama inferior · preparado para mano izquierda", "#16a34a", separacion_staff)

        # Claves vectoriales: no dependen de fuentes externas.
        self._dibujar_clave_sol(p, x + 9, y1 - 18, 0.72, "#0f172a")
        self._dibujar_clave_fa(p, x + 5, y2 - 10, 0.58, "#0f172a")
        self._add_hotspot(
            QRectF(x + 4, y1 - 25, 56, 86),
            "Clave de Sol",
            "La clave de Sol sitúa SOL y sirve como referencia para leer la melodía del MIDI didáctico.",
            ["G4"],
        )
        self._add_hotspot(
            QRectF(x + 4, y2 - 18, 62, 78),
            "Clave de Fa",
            "La clave de Fa prepara la lectura de la mano izquierda y del registro grave.",
            ["F3"],
        )

        notas = list(getattr(self, "midi_vivo_notas", []) or [])
        actual = dict(getattr(self, "midi_vivo_actual", {}) or {})
        siguiente = dict(getattr(self, "midi_vivo_siguiente", {}) or {})
        activas = list(getattr(self, "midi_vivo_activas", []) or [])
        actual_keys = {self._clave_evento_midi_vivo(n) for n in activas}
        siguiente_key = self._clave_evento_midi_vivo(siguiente) if siguiente else None

        # Ventana móvil: la zona activa queda siempre visible durante Play demo.
        max_notas = max(1, min(len(notas), 18))
        foco_key = next(iter(actual_keys), None) or siguiente_key
        foco_idx = 0
        if foco_key is not None:
            for idx, item in enumerate(notas):
                if self._clave_evento_midi_vivo(item) == foco_key:
                    foco_idx = idx
                    break
        inicio = max(0, min(max(0, len(notas) - max_notas), foco_idx - max_notas // 2))
        visibles = notas[inicio:inicio + max_notas]
        x0 = x + 82
        usable = max(120, w - 130)
        step = usable / max(1, max_notas - 1)

        for i, n in enumerate(visibles):
            key = self._clave_evento_midi_vivo(n)
            nota = str(n.get("nota", ""))
            cx = int(x0 + i * step)
            cy, pentagrama, ledger_do = self._nota_dict_a_posicion_midi_vivo(n, y1, y2, separacion_staff)

            is_actual = key in actual_keys
            is_next = siguiente_key is not None and key == siguiente_key
            tiempo = int(getattr(self, "midi_vivo_tiempo_ms", 0) or 0)
            played = int(n.get("fin_ms", n.get("inicio_ms", 0) + n.get("duracion_ms", 0)) or 0) < tiempo

            if is_actual:
                p.setBrush(QColor("#fed7aa"))
                p.setPen(QPen(QColor("#f97316"), 3))
                p.drawEllipse(QRectF(cx - 17, cy - 17, 34, 34))
                color = "#dc2626"
                relleno = True
            elif is_next:
                p.setBrush(QColor("#dbeafe"))
                p.setPen(QPen(QColor("#2563eb"), 2))
                p.drawEllipse(QRectF(cx - 14, cy - 14, 28, 28))
                color = "#2563eb"
                relleno = False
            elif played:
                color = "#94a3b8"
                relleno = True
            else:
                color = "#64748b"
                relleno = False

            # Línea adicional para DO central.
            if ledger_do:
                p.setPen(QPen(QColor("#64748b"), 1.4))
                p.drawLine(cx - 24, cy, cx + 24, cy)

            self._dibujar_accidental_midi_vivo(p, cx, cy, n, color)
            self._dibujar_nota(p, cx, cy, color, relleno, escala=1.28)
            desc_estado = "nota actual" if is_actual else ("nota siguiente" if is_next else ("nota ya reproducida" if played else "nota pendiente"))
            self._add_hotspot(
                QRectF(cx - 22, cy - 22, 60, 74),
                f"{self._nota_legible_es(nota)} · {desc_estado}",
                f"{self._nota_legible_es(nota)} en compás {n.get('compas','?')} y pulso {n.get('pulso','?')}: {desc_estado}.",
                [nota],
            )

            p.setPen(QColor("#0f172a"))
            f = QFont(); f.setPointSize(8); f.setBold(is_actual); p.setFont(f)
            p.drawText(QRectF(cx - 28, cy + 12, 56, 18), Qt.AlignCenter, self._nota_legible_es(nota))
            p.setPen(QColor("#475569"))
            f2 = QFont(); f2.setPointSize(7); p.setFont(f2)
            p.drawText(QRectF(cx - 28, cy + 29, 56, 14), Qt.AlignCenter, f"C{n.get('compas','?')}·P{n.get('pulso','?')}")

            if is_actual:
                self._puntero(p, cx, cy, "nota actual")

        # Panel didáctico específico para Hanon: dos manos visibles y dedo exacto
        # resaltado según la nota activa/próxima del flujo MIDI.
        # Panel didáctico específico para Hanon. La barra/estado ya están fuera
        # de la pizarra, encima de ella, así que la parte baja queda reservada
        # para manos grandes y legibles.
        self._dibujar_digitacion_hanon_viva(p, r, x, y2 + separacion_staff * 5 + 34, w, r.bottom() - 14)

        self._dibujar_metronomo_midi_vivo(p, r)

    def _dibujar_metronomo_midi_vivo(self, p: QPainter, r):
        bpm = int(getattr(self, "midi_vivo_bpm", 60) or 60)
        beat = int(getattr(self, "midi_vivo_beat", 1) or 1)
        total = max(1, int(getattr(self, "midi_vivo_compas_num", 4) or 4))
        x = r.right() - 178
        y = r.top() + 18
        p.save()
        p.setPen(QPen(QColor("#0f172a"), 1))
        p.setBrush(QColor("#f8fafc"))
        p.drawRoundedRect(QRectF(x, y, 166, 38), 7, 7)
        f = QFont(); f.setPointSize(8); f.setBold(True); p.setFont(f)
        p.setPen(QColor("#0f172a"))
        p.drawText(QRectF(x + 8, y + 4, 70, 14), Qt.AlignLeft, f"{bpm} BPM")
        radio = 7
        for i in range(total):
            cx = x + 82 + i * 18
            activo = (i + 1) == beat
            primero = i == 0
            p.setPen(QPen(QColor("#1d4ed8" if activo else "#94a3b8"), 2 if activo else 1))
            p.setBrush(QColor("#f97316" if activo and primero else ("#60a5fa" if activo else "#e2e8f0")))
            p.drawEllipse(QRectF(cx - radio, y + 17 - radio, radio * 2, radio * 2))
        p.restore()

    def _dibujar_piano_interactivo_mini(self, p: QPainter, r):
        notas_activas = {str(n).upper() for n in getattr(self, "piano_interactivo_notas", set())}
        blancas = ["C", "D", "E", "F", "G", "A", "B"]
        negras = {"C#": 0, "D#": 1, "F#": 3, "G#": 4, "A#": 5}
        octavas = [3, 4, 5]
        x = r.left() + 70
        y = r.bottom() - 112
        w = min(r.width() - 140, 430)
        h = 54
        bw = w / (len(octavas) * 7)
        p.save()
        p.setPen(QPen(QColor("#334155"), 1))
        for oi, octava in enumerate(octavas):
            for bi, base in enumerate(blancas):
                nota = f"{base}{octava}"
                rect = QRectF(x + (oi * 7 + bi) * bw, y, bw, h)
                activa = nota.upper() in notas_activas
                p.setBrush(QColor("#93c5fd" if activa else "#fffdf4"))
                p.drawRect(rect)
                if base == "C":
                    f = QFont(); f.setPointSize(7); f.setBold(True); p.setFont(f)
                    p.setPen(QColor("#475569"))
                    p.drawText(rect.adjusted(0, h - 16, 0, 0), Qt.AlignCenter, nota)
                    p.setPen(QPen(QColor("#334155"), 1))
        nw = bw * 0.58
        nh = h * 0.62
        for oi, octava in enumerate(octavas):
            for base, bi in negras.items():
                nota = f"{base}{octava}"
                cx = x + (oi * 7 + bi + 1) * bw
                rect = QRectF(cx - nw / 2, y, nw, nh)
                activa = nota.upper() in notas_activas
                p.setBrush(QColor("#2563eb" if activa else "#111827"))
                p.setPen(QPen(QColor("#93c5fd" if activa else "#020617"), 1))
                p.drawRoundedRect(rect, 2, 2)
        p.setPen(QColor("#0f3768"))
        f = QFont(); f.setPointSize(8); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(x, y - 18, w, 16), Qt.AlignLeft, "Piano interactivo sincronizado")
        p.restore()

    def _dibujar_ritmo(self, p: QPainter, r):
        if not self.capas.get("figuras", True):
            return
        y = r.top() + 110
        x0 = r.left() + 80
        gap = 160
        items = [("Negra", "1 pulso", True), ("Blanca", "2 pulsos", False), ("Redonda", "4 pulsos", False), ("Silencio", "se cuenta", None)]
        for i, (nombre, dur, relleno) in enumerate(items):
            x = x0 + i * gap
            p.setPen(QPen(QColor("#1e293b"), 2))
            if relleno is None:
                self._dibujar_silencio_negra(p, x, y, 1.0, "#1e293b")
            else:
                self._dibujar_nota(p, x, y, "#2563eb" if i <= self.paso else "#94a3b8", relleno)
            self._add_hotspot(
                QRectF(x - 42, y - 52, 92, 92),
                nombre,
                f"{nombre}: {dur}. Pulsa aquí para que el profesor explique esta figura rítmica.",
                ["C4"] if relleno is not None else [],
            )
            if i == self.paso:
                self._puntero(p, x, y-8, nombre)
            p.setPen(QColor("#0f172a"))
            f2 = QFont(); f2.setPointSize(10); f2.setBold(True); p.setFont(f2)
            p.drawText(QRectF(x - 55, y + 36, 110, 22), Qt.AlignCenter, nombre)
            p.setPen(QColor("#475569"))
            f3 = QFont(); f3.setPointSize(9); p.setFont(f3)
            p.drawText(QRectF(x - 55, y + 58, 110, 22), Qt.AlignCenter, dur)

    def _dibujar_pulso(self, p: QPainter, r):
        if not self.capas.get("pulso", True):
            return
        x = r.left() + 90
        y = r.top() + 105
        size = 58
        for i in range(4):
            color = "#2563eb" if i <= self.paso else "#e2e8f0"
            p.setPen(QPen(QColor("#64748b"), 1.5))
            p.setBrush(QColor(color))
            p.drawRoundedRect(x + i*90, y, size, size, 10, 10)
            p.setPen(QColor("#ffffff" if i <= self.paso else "#0f172a"))
            f = QFont(); f.setPointSize(18); f.setBold(True); p.setFont(f)
            p.drawText(QRectF(x + i*90, y, size, size), Qt.AlignCenter, str(i+1))
            self._add_hotspot(
                QRectF(x + i*90, y, size, size),
                f"Pulso {i+1}",
                f"Pulso {i+1} del compás. Hay que mantener una separación regular entre pulsos.",
                ["C4"] if i == self.paso else [],
            )
            if i == self.paso:
                self._puntero(p, x + i*90 + size//2, y + size//2, f"Pulso {i+1}")
        p.setPen(QColor("#0f3768"))
        f2 = QFont(); f2.setPointSize(13); f2.setBold(True); p.setFont(f2)
        p.drawText(QRectF(r.left()+430, y+5, r.width()-460, 60), Qt.AlignLeft | Qt.AlignVCenter, "Compás 4/4: cuenta regular")

    def _dibujar_digitacion(self, p: QPainter, r):
        if not self.capas.get("digitacion", True):
            return
        x = r.left() + 80
        y = r.top() + 100
        key_w = 62
        names = ["DO", "RE", "MI", "FA", "SOL"]
        dedos = ["1", "2", "3", "4", "5"]
        for i, name in enumerate(names):
            xx = x + i * key_w
            p.setPen(QPen(QColor("#334155"), 1.5))
            p.setBrush(QColor("#ffffff"))
            p.drawRoundedRect(xx, y, key_w-4, 82, 8, 8)
            if i <= self.paso + 1:
                p.setBrush(QColor("#dbeafe"))
                p.drawRoundedRect(xx+5, y+8, key_w-14, 36, 8, 8)
            p.setPen(QColor("#0f172a"))
            f = QFont(); f.setPointSize(11); f.setBold(True); p.setFont(f)
            p.drawText(QRectF(xx, y+46, key_w-4, 22), Qt.AlignCenter, name)
            p.setPen(QColor("#2563eb"))
            f2 = QFont(); f2.setPointSize(15); f2.setBold(True); p.setFont(f2)
            p.drawText(QRectF(xx, y+6, key_w-4, 34), Qt.AlignCenter, dedos[i])
            self._add_hotspot(
                QRectF(xx, y, key_w-4, 82),
                f"{name} · dedo {dedos[i]}",
                f"{name} se toca con el dedo {dedos[i]} en esta posición de cinco dedos.",
                [{"DO":"C4","RE":"D4","MI":"E4","FA":"F4","SOL":"G4"}.get(name, "C4")],
            )
            if i == min(self.paso, 4):
                self._puntero(p, xx + int(key_w/2), y + 20, f"Dedo {dedos[i]}")
        p.setPen(QColor("#0f3768"))
        f3 = QFont(); f3.setPointSize(12); f3.setBold(True); p.setFont(f3)
        p.drawText(QRectF(x + 350, y + 12, r.width() - 430, 80), Qt.AlignLeft | Qt.AlignVCenter, "Dedos 1–5: control, continuidad y mano relajada")

    def _dibujar_general(self, p: QPainter, r):
        x = r.left()+65
        y = r.top()+115
        w = r.width()-130
        self._dibujar_staff(p, x, y, w, "Pizarra del profesor", "#0f3768")
        self._dibujar_clave_sol(p, x + 10, y - 18, 0.62, "#0f3768")
        self._dibujar_corchea_simple(p, x + int(w * 0.42), y + 20, 1.0, "#2563eb")
        self._dibujar_silencio_negra(p, x + int(w * 0.58), y + 20, 0.9, "#475569")
        self._add_hotspot(QRectF(x + 8, y - 24, 58, 82), "Clave", "La pizarra puede explicar claves, notas, ritmo, pulso y digitación de forma visual.", ["G4"])
        self._add_hotspot(QRectF(x + int(w * 0.42) - 30, y - 36, 80, 94), "Nota", "Símbolo de nota: se puede conectar con una tecla real del piano.", ["C4"])
        self._add_hotspot(QRectF(x + int(w * 0.58) - 30, y - 36, 80, 94), "Silencio", "El silencio también es música: no se toca, pero se cuenta.", [])
        p.setPen(QColor("#2563eb"))
        f = QFont(); f.setPointSize(13); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(r.left()+80, r.top()+165, r.width()-160, 42), Qt.AlignCenter, "Concepto → símbolo → piano → comprobación")

    def _dibujar_paso(self, p: QPainter, r):
        txt = self.paso_actual_texto()
        if not txt:
            return
        if getattr(self, "midi_vivo_activo", False) or self.modo == "midi_didactico":
            # En Hanon/MIDI didáctico no debe ocupar el hueco entre manos y piano.
            # Lo colocamos arriba como etiqueta compacta.
            box = QRectF(r.left() + 18, r.top() + 48, min(r.width() - 36, 690), 26)
            font_size = 8
        else:
            box = QRectF(r.left()+18, r.bottom()-42, r.width()-36, 34)
            font_size = 9
        p.setPen(QPen(QColor("#bfdbfe"), 1))
        p.setBrush(QColor("#eff6ff"))
        p.drawRoundedRect(box, 8, 8)
        p.setPen(QColor("#0f3768"))
        f = QFont(); f.setPointSize(font_size); f.setBold(True); p.setFont(f)
        p.drawText(box.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, f"Paso {self.paso+1}/{len(self.pasos)}: {txt}")


class PizarraMusicalProfesor(QWidget):
    """Panel superior que sustituye temporalmente el texto por pizarra."""

    paso_leido = Signal(str)
    ejemplo_leido = Signal(str)
    texto_leido = Signal(str)
    notas_resaltadas = Signal(list)
    practica_piano_solicitada = Signal(list, str)
    secuencia_piano_solicitada = Signal(list, str)
    pulso_piano_solicitado = Signal(list, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PizarraMusicalProfesor")
        self._checks = {}
        self._modo_trabajo = "clase"
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(6)

        fila = QHBoxLayout()
        self.lbl_titulo = QLabel("Pizarra musical del profesor")
        self.lbl_titulo.setObjectName("TituloPizarraMusical")
        self.lbl_titulo.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Acciones internas: mantenemos la lógica, pero limpiamos la pantalla con un único menú.
        self.btn_anterior = QPushButton("←")
        self.btn_siguiente = QPushButton("→")
        self.btn_ejemplo = QPushButton("Ejemplo")
        self.btn_tocar_piano = QPushButton("Piano")
        self.btn_tocar_secuencia = QPushButton("Secuencia")
        self.btn_tocar_pulso = QPushButton("Pulso")
        self.btn_texto = QPushButton("Texto")
        self.btn_borrar_pizarra = QPushButton("Borrar pizarra")

        for b in (self.btn_anterior, self.btn_siguiente, self.btn_ejemplo, self.btn_tocar_piano, self.btn_tocar_secuencia, self.btn_tocar_pulso, self.btn_texto, self.btn_borrar_pizarra):
            b.setMinimumHeight(30)
            b.setMinimumWidth(max(54, b.fontMetrics().horizontalAdvance(b.text()) + 30))
            b.setMaximumWidth(16777215)
            b.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            b.setCursor(Qt.PointingHandCursor)
            b.setVisible(True)
            if b.text() and not b.toolTip():
                b.setToolTip(b.text())

        self.btn_menu_clase = QToolButton()
        self.btn_menu_clase.setText("Clase ▾")
        self.btn_menu_clase.setCursor(Qt.PointingHandCursor)
        self.btn_menu_clase.setPopupMode(QToolButton.InstantPopup)
        self.btn_menu_clase.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.menu_clase = QMenu(self.btn_menu_clase)
        self.btn_menu_clase.setMenu(self.menu_clase)

        self.lbl_modo_trabajo = QLabel("Modo: Clase")
        self.lbl_modo_trabajo.setObjectName("ModoTrabajoPizarra")
        self.lbl_modo_trabajo.setAlignment(Qt.AlignCenter)
        self.lbl_modo_trabajo.setMinimumWidth(120)

        # Modos de trabajo de la misma pantalla.
        self._acciones_modo = {}
        for modo, label in (
            ("clase", "Modo clase"),
            ("practica", "Modo práctica"),
            ("examen", "Modo examen"),
        ):
            accion = QAction(label, self)
            accion.setCheckable(True)
            accion.setChecked(modo == "clase")
            accion.triggered.connect(lambda _checked=False, m=modo: self._cambiar_modo_trabajo(m))
            self._acciones_modo[modo] = accion
            self.menu_clase.addAction(accion)
        self.menu_clase.addSeparator()

        act_repetir = QAction("Repetir explicación", self)
        act_repetir.triggered.connect(self._leer_explicacion_actual)
        self.menu_clase.addAction(act_repetir)

        self.menu_clase.addSeparator()
        act_prev = QAction("Paso anterior", self)
        act_prev.triggered.connect(self._paso_anterior)
        self.menu_clase.addAction(act_prev)
        act_next = QAction("Paso siguiente", self)
        act_next.triggered.connect(self._paso_siguiente)
        self.menu_clase.addAction(act_next)
        act_ej = QAction("Mostrar ejemplo", self)
        act_ej.triggered.connect(self._mostrar_ejemplo)
        self.menu_clase.addAction(act_ej)

        self.menu_clase.addSeparator()
        act_piano = QAction("Tocar en piano", self)
        act_piano.triggered.connect(self._pedir_practica_piano)
        self.menu_clase.addAction(act_piano)
        act_seq = QAction("Tocar secuencia", self)
        act_seq.triggered.connect(self._pedir_secuencia_piano)
        self.menu_clase.addAction(act_seq)
        act_pulso = QAction("Tocar con pulso", self)
        act_pulso.triggered.connect(self._pedir_pulso_piano)
        self.menu_clase.addAction(act_pulso)
        act_examen = QAction("Iniciar mini examen del punto", self)
        act_examen.triggered.connect(self._iniciar_mini_examen_punto)
        self.menu_clase.addAction(act_examen)
        act_texto = QAction("Ver / ocultar texto", self)
        act_texto.triggered.connect(self._alternar_texto)
        self.menu_clase.addAction(act_texto)
        act_borrar = QAction("Borrar pizarra", self)
        act_borrar.triggered.connect(self.borrar_pizarra)
        self.menu_clase.addAction(act_borrar)

        self.menu_clase.addSeparator()
        self._acciones_capas = {}
        capas = [
            ("claves", "Mostrar claves"),
            ("notas", "Mostrar notas"),
            ("do_central", "Mostrar DO central"),
            ("manos", "Mostrar manos"),
            ("digitacion", "Mostrar digitación"),
            ("flechas", "Mostrar flechas"),
        ]
        for key, label in capas:
            accion = QAction(label, self)
            accion.setCheckable(True)
            accion.setChecked(True)
            accion.triggered.connect(lambda _checked=False, k=key: self._cambiar_capa(k))
            self._acciones_capas[key] = accion
            self.menu_clase.addAction(accion)

        fila.addWidget(self.lbl_titulo, 1)
        fila.addWidget(self.lbl_modo_trabajo, 0)
        fila.addWidget(self.btn_menu_clase, 0)
        raiz.addLayout(fila)

        fila_acciones = QHBoxLayout()
        fila_acciones.setSpacing(4)
        for b in (self.btn_anterior, self.btn_siguiente, self.btn_ejemplo, self.btn_tocar_piano, self.btn_tocar_secuencia, self.btn_tocar_pulso, self.btn_texto, self.btn_borrar_pizarra):
            fila_acciones.addWidget(b)
        raiz.addLayout(fila_acciones)

        self.canvas = PizarraMusicalCanvas(self)
        self.canvas.setMinimumHeight(280)
        try:
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        try:
            self.canvas.paso_anterior_solicitado.connect(self._paso_anterior)
            self.canvas.paso_siguiente_solicitado.connect(self._paso_siguiente)
            self.canvas.simbolo_pulsado.connect(self._procesar_simbolo_canvas)
            self.canvas.practica_simbolo_solicitada.connect(self._practicar_simbolo_canvas)
        except Exception:
            pass
        raiz.addWidget(self.canvas, 1)

        self.txt_explicacion = QTextEdit()
        self.txt_explicacion.setReadOnly(True)
        self.txt_explicacion.setMaximumHeight(46)
        self.txt_explicacion.setPlaceholderText("El profesor resumirá aquí el punto actual.")
        raiz.addWidget(self.txt_explicacion)

        self.btn_anterior.clicked.connect(self._paso_anterior)
        self.btn_siguiente.clicked.connect(self._paso_siguiente)
        self.btn_ejemplo.clicked.connect(self._mostrar_ejemplo)
        self.btn_tocar_piano.clicked.connect(self._pedir_practica_piano)
        self.btn_tocar_secuencia.clicked.connect(self._pedir_secuencia_piano)
        self.btn_tocar_pulso.clicked.connect(self._pedir_pulso_piano)
        self.btn_texto.clicked.connect(self._alternar_texto)
        self.btn_borrar_pizarra.clicked.connect(self.borrar_pizarra)

        self._texto_original = ""
        self._mostrando_texto = False

        self.setStyleSheet("""
            #TituloPizarraMusical {
                font-weight: bold;
                color: #0f3768;
                font-size: 15px;
            }
            #ModoTrabajoPizarra {
                font-weight: bold;
                border-radius: 8px;
                padding: 5px 8px;
                background: #E0ECFF;
                color: #0f172a;
                border: 1px solid #cbd5e1;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 7px;
                background: #dbeafe;
                color: #0f3768;
                border: 1px solid #93c5fd;
                font-weight: bold;
            }
            QPushButton:hover { background: #bfdbfe; }
            QToolButton {
                padding: 6px 12px;
                border-radius: 7px;
                background: #dbeafe;
                color: #0f3768;
                border: 1px solid #93c5fd;
                font-weight: bold;
            }
            QToolButton:hover { background: #bfdbfe; }
            QCheckBox {
                color: #0f3768;
                font-weight: bold;
                font-size: 11px;
            }
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #ffffff;
                padding: 6px;
            }
        """)

    def preparar_midi_didactico(self, notas: list[dict], titulo: str = "MIDI Didáctico · Pentagrama vivo"):
        """API pública usada por VentanaPrincipal para activar el pentagrama ND."""
        self._texto_original = ""
        self._cambiar_modo_trabajo("clase")
        self.lbl_titulo.setText(str(titulo or "MIDI Didáctico · Pentagrama vivo"))
        self.canvas.preparar_midi_didactico(notas or [], titulo)
        self._mostrando_texto = False
        self.btn_texto.setText("Ver texto")
        texto = (
            "Pentagrama vivo preparado. La nota actual se resaltará en la pizarra, "
            "la siguiente quedará preparada y puedes pulsar sobre cualquier símbolo para explicarlo."
        )
        self.txt_explicacion.setPlainText(texto)
        self.ejemplo_leido.emit(texto)
        self._emitir_notas_docente()

    def limpiar_marcas_docentes(self):
        try:
            self.canvas.limpiar_marcas_docentes()
        except Exception:
            pass

    def borrar_pizarra(self):
        try:
            self.canvas.borrar_pizarra()
        except Exception:
            pass
        texto = "Pizarra borrada: se han limpiado marcas docentes temporales, flechas, halos, etiquetas y notas temporales. El pentagrama base se mantiene."
        self.txt_explicacion.setPlainText(texto)
        self.paso_leido.emit(texto)

    def resaltar_lineas_pentagrama(self):
        self.canvas.resaltar_lineas_pentagrama()

    def senalar_clave_sol(self):
        self.canvas.senalar_clave_sol()

    def senalar_clave_fa(self):
        self.canvas.senalar_clave_fa()

    def mostrar_mano_derecha(self):
        self.canvas.mostrar_mano_derecha()

    def mostrar_mano_izquierda(self):
        self.canvas.mostrar_mano_izquierda()

    def resaltar_do_central(self):
        self.canvas.resaltar_do_central()

    def animar_clave_sol(self):
        self.canvas.animar_clave_sol()

    def animar_clave_fa(self):
        self.canvas.animar_clave_fa()

    def animar_mano_derecha(self):
        self.canvas.animar_mano_derecha()

    def animar_mano_izquierda(self):
        self.canvas.animar_mano_izquierda()

    def aplicar_marca_docente_por_texto(self, texto: str) -> bool:
        try:
            return bool(self.canvas.aplicar_marca_docente_por_texto(texto))
        except Exception:
            return False

    def preparar_secuencia_docente(self, texto: str, duracion_ms: int | None = None) -> bool:
        try:
            return bool(self.canvas.preparar_secuencia_docente(texto, duracion_ms))
        except Exception:
            return False

    def iniciar_secuencia_docente(self, texto: str | None = None, duracion_ms: int | None = None) -> bool:
        try:
            return bool(self.canvas.iniciar_secuencia_docente(texto, duracion_ms))
        except Exception:
            return False

    def pausar_secuencia_docente(self):
        try:
            self.canvas.pausar_secuencia_docente()
        except Exception:
            pass

    def reanudar_secuencia_docente(self):
        try:
            self.canvas.reanudar_secuencia_docente()
        except Exception:
            pass

    def detener_secuencia_docente(self, limpiar: bool = True):
        try:
            self.canvas.detener_secuencia_docente(limpiar)
        except Exception:
            pass

    def clear_highlights(self):
        self.limpiar_marcas_docentes()

    def highlight_staff(self):
        self.resaltar_lineas_pentagrama()

    def highlight_treble_clef(self):
        self.animar_clave_sol()

    def highlight_bass_clef(self):
        self.animar_clave_fa()

    def highlight_right_hand(self):
        self.animar_mano_derecha()

    def highlight_left_hand(self):
        self.animar_mano_izquierda()

    def actualizar_midi_didactico(self, actual: dict | None = None, siguiente: dict | None = None,
                                  activas: list[dict] | None = None, tiempo_ms: int = 0,
                                  progreso: float = 0.0, modo: str = "clase",
                                  bpm: int | None = None, beat: int | None = None,
                                  compas_num: int | None = None):
        """API pública usada por VentanaPrincipal durante la reproducción MIDI."""
        self.canvas.actualizar_midi_didactico(actual, siguiente, activas, tiempo_ms, progreso, modo, bpm, beat, compas_num)
        try:
            nota = actual.get("nota", "") if actual else "—"
            sig = siguiente.get("nota", "") if siguiente else "final"
            self.txt_explicacion.setPlainText(f"Pentagrama vivo: actual {nota}, siguiente {sig}.")
        except Exception:
            pass

    def alternar_piano_interactivo(self, visible: bool | None = None):
        try:
            activo = self.canvas.alternar_piano_interactivo(visible)
        except Exception:
            activo = False
        texto = "Piano interactivo visible y sincronizado." if activo else "Piano interactivo oculto."
        self.txt_explicacion.setPlainText(texto)
        self.paso_leido.emit(texto)
        return activo

    def limpiar_midi_didactico(self):
        """API pública usada por VentanaPrincipal al parar MIDI Didáctico."""
        self.canvas.limpiar_midi_didactico()
        self.txt_explicacion.setPlainText("Pentagrama vivo detenido.")
        self._emitir_notas_docente()

    def mostrar_nota_midi_externa(self, nota: str, velocity: int = 0, canal: int = 0, origen: str = "midi_in"):
        """API pública: muestra en la pizarra la nota que llega desde el piano externo."""
        try:
            self.canvas.mostrar_nota_midi_externa(nota, velocity, canal, origen)
            nombre = self._notas_legibles_pizarra([nota])[0] if nota else "—"
            self.txt_explicacion.setPlainText(
                f"Entrada MIDI externa detectada: {nombre}. La nota queda colocada en el pentagrama y también resaltada en el piano."
            )
        except Exception:
            pass

    def limpiar_nota_midi_externa(self, nota: str | None = None):
        try:
            self.canvas.limpiar_nota_midi_externa(nota)
        except Exception:
            pass

    def _procesar_simbolo_canvas(self, titulo: str, descripcion: str, notas: list):
        """Respuesta docente cuando el alumno pulsa directamente un símbolo de la pizarra."""
        titulo = str(titulo or "Símbolo")
        descripcion = str(descripcion or "Símbolo musical")
        notas = [str(n).strip() for n in (notas or []) if str(n).strip()]
        texto = f"Has señalado {titulo}. {descripcion}"
        if notas:
            texto += " También lo resalto en el piano para unir símbolo y teclado."
            try:
                self.notas_resaltadas.emit(notas)
            except Exception:
                pass
        self.txt_explicacion.setPlainText(texto)
        self.paso_leido.emit(texto)

    def _practicar_simbolo_canvas(self, notas: list, descripcion: str):
        notas = [str(n).strip() for n in (notas or []) if str(n).strip()]
        if not notas:
            return
        texto = str(descripcion or "Practica en el piano lo que está señalando la pizarra.")
        self.practica_piano_solicitada.emit(notas, texto)

    def preparar_desde_punto(self, texto: str, indice: int, total: int, titulo: str = ""):
        self._texto_original = str(texto or "")
        self._cambiar_modo_trabajo("clase")
        titulo_limpio = titulo or f"Punto {indice + 1} de {total}"
        self.lbl_titulo.setText(f"Pizarra musical · {titulo_limpio}")
        self.canvas.preparar(self._texto_original, titulo_limpio)
        # La explicación del profesor debe arrancar con el símbolo importante
        # ya visible y resaltado; no obligamos al alumno a ir avanzando pasos para
        # descubrir el DO central, las claves o las notas.
        try:
            self.canvas.enfocar_concepto_desde_texto(self._texto_original)
        except Exception:
            pass
        self._mostrando_texto = False
        self.btn_texto.setText("Ver texto")
        self._actualizar_explicacion()
        self.aplicar_marca_docente_por_texto(self._texto_original)
        self._emitir_notas_docente()

    def _cambiar_modo_trabajo(self, modo: str):
        modo = str(modo or "clase").strip().lower()
        if modo not in {"clase", "practica", "examen"}:
            modo = "clase"
        self._modo_trabajo = modo

        for key, accion in getattr(self, "_acciones_modo", {}).items():
            try:
                accion.setChecked(key == modo)
            except Exception:
                pass

        nombres = {
            "clase": "Clase",
            "practica": "Práctica",
            "examen": "Examen",
        }
        colores = {
            "clase": "#E0ECFF",
            "practica": "#DCFCE7",
            "examen": "#FEE2E2",
        }
        texto_modo = nombres.get(modo, "Clase")
        try:
            self.lbl_modo_trabajo.setText(f"Modo: {texto_modo}")
            self.lbl_modo_trabajo.setStyleSheet(
                "font-weight:bold; border-radius:8px; padding:5px 8px; "
                f"background:{colores.get(modo, '#E0ECFF')}; color:#0f172a; border:1px solid #cbd5e1;"
            )
        except Exception:
            pass

        if modo == "clase":
            texto = (
                "Modo clase activado. El profesor explica primero y usa la pizarra como una pizarra real."
            )
            self.txt_explicacion.setMaximumHeight(46)
        elif modo == "practica":
            texto = (
                "Modo práctica activado. Ahora la pizarra debe terminar en acción: tocar en piano, tocar secuencia o tocar con pulso."
            )
            self.txt_explicacion.setMaximumHeight(46)
        else:
            texto = (
                "Modo examen activado. El profesor dará menos ayuda y comprobará si respondes con el piano virtual o el teclado MIDI."
            )
            self.txt_explicacion.setMaximumHeight(52)

        self.txt_explicacion.setPlainText(texto)
        self.paso_leido.emit(texto)

    def _iniciar_mini_examen_punto(self):
        self._cambiar_modo_trabajo("examen")
        notas = self.canvas.notas_docente_actuales()
        if notas:
            texto = (
                "Mini examen del punto. No voy a darte la solución por adelantado. "
                "Toca en el piano virtual o en tu teclado MIDI la nota que corresponde a lo que ves en la pizarra."
            )
            self.txt_explicacion.setPlainText(texto)
            self.practica_piano_solicitada.emit(notas, texto)
            self.ejemplo_leido.emit(texto)
            return

        secuencia = self.canvas.secuencia_docente_actual()
        if secuencia:
            texto = (
                "Mini examen del punto. Toca la secuencia que corresponde a esta explicación visual. "
                "El profesor comprobará el orden de las notas."
            )
            self.txt_explicacion.setPlainText(texto)
            self.secuencia_piano_solicitada.emit(secuencia, texto)
            self.ejemplo_leido.emit(texto)
            return

        texto = "Este punto todavía no tiene un mini examen tocable. Avanza a un paso con notas o digitación."
        self.txt_explicacion.setPlainText(texto)
        self.ejemplo_leido.emit(texto)

    def _leer_explicacion_actual(self):
        texto = self.texto_sincronizado_actual()
        if not texto:
            texto = "Esta pizarra sirve para explicar el punto actual con una clase más limpia y visual."

        modo = getattr(self, "_modo_trabajo", "clase")
        if modo == "practica":
            texto += " Ahora intenta convertir esta explicación en una acción sobre el piano."
        elif modo == "examen":
            texto = (
                "Modo examen. Observa la pizarra y responde tocando, sin depender de una pista larga. "
                "Cuando estés preparado, usa la opción de mini examen del punto."
            )

        self.txt_explicacion.setPlainText(texto)
        self._emitir_notas_docente()
        self.ejemplo_leido.emit(texto)

    def texto_sincronizado_actual(self) -> str:
        try:
            texto = self.canvas.texto_narracion_visual_actual()
        except Exception:
            texto = ""
        return str(texto or self.txt_explicacion.toPlainText() or "").strip()

    def _actualizar_explicacion(self):
        texto = self.canvas.paso_actual_texto()
        if not texto:
            texto = "El profesor usará esta pizarra para explicar visualmente el punto actual."
        self.txt_explicacion.setPlainText(texto)
        self.aplicar_marca_docente_por_texto(texto)
        self.btn_anterior.setEnabled(self.canvas.paso > 0)
        self.btn_siguiente.setEnabled(self.canvas.paso < max(0, len(self.canvas.pasos) - 1))

    def _emitir_notas_docente(self):
        try:
            self.notas_resaltadas.emit(self.canvas.notas_docente_actuales())
        except Exception:
            pass

    def _cambiar_capa(self, key: str):
        cb = self._checks.get(key)
        accion = getattr(self, "_acciones_capas", {}).get(key)
        if cb is not None:
            activo = cb.isChecked()
            nombre = cb.text()
            if accion is not None and accion.isChecked() != activo:
                accion.setChecked(activo)
        elif accion is not None:
            activo = accion.isChecked()
            nombre = accion.text().replace("Mostrar ", "")
        else:
            activo = True
            nombre = key
        self.canvas.set_capa(key, activo)
        texto = f"Capa {'activada' if activo else 'ocultada'}: {nombre}."
        self.txt_explicacion.setPlainText(texto)
        self.paso_leido.emit(texto)
        self._emitir_notas_docente()

    def _paso_anterior(self):
        self.canvas.paso_anterior()
        self._actualizar_explicacion()
        self._emitir_notas_docente()
        texto = self.texto_sincronizado_actual()
        if texto:
            self.paso_leido.emit(texto)

    def _paso_siguiente(self):
        self.canvas.paso_siguiente()
        self._actualizar_explicacion()
        self._emitir_notas_docente()
        texto = self.texto_sincronizado_actual()
        if texto:
            self.paso_leido.emit(texto)

    def _mostrar_ejemplo(self):
        if self.canvas.modo == "midi_didactico":
            texto = (
                "Ejemplo MIDI cargado. Usa Play demo en el transporte de la clase para reproducirlo: "
                "la pizarra desplazará la ventana, resaltará la nota activa y mostrará el pulso."
            )
            self.txt_explicacion.setPlainText(texto)
            self.ejemplo_leido.emit(texto)
            return
        modo = self.canvas.modo
        ejemplos = {
            "partitura": "Ejemplo: la clave de Sol te dice dónde está SOL; desde esa referencia lees las demás notas del pentagrama superior. La clave de Fa te dice dónde está FA; desde ahí lees el pentagrama inferior.",
            "ritmo": "Ejemplo: cuatro negras ocupan cuatro pulsos. Dos blancas también ocupan cuatro pulsos. Una redonda ocupa el compás entero en 4/4.",
            "pulso": "Ejemplo: cuenta 1, 2, 3, 4 sin correr. Si tocas en el 1, el resto del compás debe seguir contando por dentro.",
            "digitacion": "Ejemplo: en DO RE MI FA SOL, la mano derecha puede usar 1-2-3-4-5 para mantener continuidad.",
            "general": "Ejemplo: primero dilo con tus palabras, después señálalo en el piano o en la partitura.",
        }
        texto = ejemplos.get(modo, ejemplos["general"])
        if modo == "general":
            notas = [
                {"nota": "C4", "inicio_ms": 0, "duracion_ms": 450, "velocity": 80, "pulso": 1, "compas": 1},
                {"nota": "D4", "inicio_ms": 500, "duracion_ms": 450, "velocity": 80, "pulso": 2, "compas": 1},
                {"nota": "E4", "inicio_ms": 1000, "duracion_ms": 450, "velocity": 80, "pulso": 3, "compas": 1},
                {"nota": "F4", "inicio_ms": 1500, "duracion_ms": 450, "velocity": 80, "pulso": 4, "compas": 1},
                {"nota": "G4", "inicio_ms": 2000, "duracion_ms": 600, "velocity": 84, "pulso": 1, "compas": 2},
            ]
            self.canvas.preparar_midi_didactico(notas, "Ejemplo didáctico · DO RE MI FA SOL")
            self.canvas.alternar_piano_interactivo(True)
            texto = "Ejemplo cargado: DO, RE, MI, FA, SOL. Usa Secuencia o Pulso para practicarlo, o Play demo si estás en una clase con transporte."
        self.txt_explicacion.setPlainText(texto)
        self.aplicar_marca_docente_por_texto(texto)
        self.ejemplo_leido.emit(texto)
        self._emitir_notas_docente()

    def _pedir_practica_piano(self):
        # En MIDI Didáctico/Hanon no basta con enseñar u ocultar el piano:
        # el botón debe proponer la nota activa y emitir la práctica para que
        # VentanaPrincipal pueda evaluarla o mostrarla en el teclado.
        visible = self.canvas.alternar_piano_interactivo(True if self.canvas.modo == "midi_didactico" else None)
        if getattr(self, "_modo_trabajo", "clase") != "examen":
            self._cambiar_modo_trabajo("practica")
        notas = self.canvas.notas_docente_actuales()
        if not notas:
            texto = (
                "En este paso no hay una tecla concreta que tocar. "
                "Primero avanza hasta un paso donde la pizarra marque SOL, FA, DO central o digitación."
            )
            self.txt_explicacion.setPlainText(texto)
            self.ejemplo_leido.emit(texto)
            self.practica_piano_solicitada.emit([], texto)
            return

        nombres = {
            "C4": "DO central",
            "D4": "RE",
            "E4": "MI",
            "F4": "FA",
            "G4": "SOL",
            "F3": "FA grave",
        }
        nombres_legibles = [nombres.get(n, n) for n in notas]
        texto = (
            "Ahora te toca responder en el piano virtual o en tu teclado MIDI. "
            "Pulsa: " + ", ".join(nombres_legibles) + "."
        )
        self.txt_explicacion.setPlainText(texto)
        self.ejemplo_leido.emit(texto)
        self.practica_piano_solicitada.emit(notas, texto)


    def _notas_legibles_pizarra(self, notas):
        nombres = {
            "C4": "DO central",
            "D4": "RE",
            "E4": "MI",
            "F4": "FA",
            "G4": "SOL",
            "A4": "LA",
            "B4": "SI",
            "C5": "DO agudo",
            "F3": "FA grave",
            "C3": "DO grave",
            "G3": "SOL grave",
        }
        salida = []
        for nota in notas or []:
            n = str(nota or "").strip()
            if n:
                salida.append(nombres.get(n, n))
        return salida

    def _pedir_secuencia_piano(self):
        """Pide al alumno tocar una secuencia guiada desde la pizarra.

        Este método faltaba en v4.1.6 pero estaba conectado en botones y menú.
        Emite `secuencia_piano_solicitada`, que VentanaPrincipal conecta con
        `_iniciar_secuencia_pizarra_piano`.
        """
        if getattr(self, "_modo_trabajo", "clase") != "examen":
            self._cambiar_modo_trabajo("practica")

        secuencia = []
        try:
            secuencia = self.canvas.secuencia_docente_actual()
        except Exception:
            secuencia = []
        secuencia = [str(n).strip() for n in (secuencia or []) if str(n).strip()]

        if not secuencia:
            texto = (
                "En este paso no hay una secuencia concreta para tocar. "
                "Avanza hasta una explicación con notas, digitación o pulso."
            )
            self.txt_explicacion.setPlainText(texto)
            self.ejemplo_leido.emit(texto)
            self.secuencia_piano_solicitada.emit([], texto)
            return

        nombres_legibles = self._notas_legibles_pizarra(secuencia)
        texto = (
            "Secuencia guiada desde la pizarra. "
            "Toca en este orden: "
            + " - ".join(nombres_legibles)
            + ". El profesor comprobará orden, nota correcta y teclas de más."
        )
        self.txt_explicacion.setPlainText(texto)
        self.ejemplo_leido.emit(texto)
        self.notas_resaltadas.emit([secuencia[0]])
        self.secuencia_piano_solicitada.emit(secuencia, texto)

    def _pedir_pulso_piano(self):
        """Pide al alumno tocar la secuencia con pulso/metrónomo.

        Este método faltaba en v4.1.6 pero estaba conectado en botones y menú.
        Emite `pulso_piano_solicitado`, que VentanaPrincipal conecta con
        `_iniciar_pulso_pizarra_piano`.
        """
        if getattr(self, "_modo_trabajo", "clase") != "examen":
            self._cambiar_modo_trabajo("practica")

        secuencia = []
        try:
            secuencia = self.canvas.secuencia_docente_actual()
        except Exception:
            secuencia = []
        secuencia = [str(n).strip() for n in (secuencia or []) if str(n).strip()]
        if not secuencia:
            secuencia = ["C4", "C4", "C4", "C4"]

        # Tempo pedagógico inicial. Si el canvas está en modo pulso mantenemos lento.
        bpm = 60
        try:
            if getattr(self.canvas, "modo", "") == "ritmo":
                bpm = 56
            elif getattr(self.canvas, "modo", "") == "digitacion":
                bpm = 60
            elif getattr(self.canvas, "modo", "") == "pulso":
                bpm = 60
        except Exception:
            bpm = 60

        nombres_legibles = self._notas_legibles_pizarra(secuencia)
        texto = (
            f"Reto con pulso a {bpm} BPM. "
            "Toca la secuencia siguiendo el metrónomo: "
            + " - ".join(nombres_legibles)
            + ". No busques velocidad; busca entrar en el pulso con calma."
        )
        self.txt_explicacion.setPlainText(texto)
        self.ejemplo_leido.emit(texto)
        self.notas_resaltadas.emit([secuencia[0]] if secuencia else [])
        self.pulso_piano_solicitado.emit(secuencia, bpm, texto)


    def _alternar_texto(self):
        self._mostrando_texto = not self._mostrando_texto
        if self._mostrando_texto:
            texto = self._texto_original
            self.txt_explicacion.setPlainText(texto)
            self.btn_texto.setText("Ver pizarra")
            if texto.strip():
                self.texto_leido.emit(texto.strip())
        else:
            self.btn_texto.setText("Ver texto")
            self._actualizar_explicacion()
            self._emitir_notas_docente()
            texto = self.texto_sincronizado_actual()
            if texto:
                self.paso_leido.emit(texto)
