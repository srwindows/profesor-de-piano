import math
import time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QFrame, QScrollArea, QWidget, QProgressBar, QSpinBox, QCheckBox,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class VisorPracticaPulso(QWidget):
    """Línea de tiempo visual para los ejercicios prácticos de pulso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ejercicio = {}
        self.eventos = []
        self.estados = []
        self.beat_actual = -1.0
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_ejercicio(self, ejercicio: dict):
        self.ejercicio = ejercicio or {}
        practica = self.ejercicio.get("practica", {}) or {}
        self.eventos = list(practica.get("eventos", []) or [])
        self.estados = ["pendiente" for _ in self.eventos]
        self.beat_actual = -1.0
        self.update()

    def set_estado(self, estados, beat_actual: float):
        self.estados = list(estados or [])
        self.beat_actual = float(beat_actual or 0.0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#f8fafc"))
        rect = self.rect().adjusted(12, 10, -12, -12)
        p.setPen(QPen(QColor("#cbd5e1"), 2))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(rect, 14, 14)

        e = self.ejercicio or {}
        practica = e.get("practica", {}) or {}
        compas = int(practica.get("compas", e.get("compas", 4)) or 4)
        duracion = float(practica.get("duracion_beats", compas * int(practica.get("compases", 4) or 4)) or 4)
        duracion = max(1.0, duracion)

        titulo_font = QFont(self.font())
        titulo_font.setPointSize(13)
        titulo_font.setBold(True)
        p.setFont(titulo_font)
        p.setPen(QColor("#0f3768"))
        p.drawText(rect.adjusted(14, 8, -14, -8), Qt.AlignLeft | Qt.AlignTop, practica.get("titulo", e.get("titulo", "Práctica de pulso")))

        left = rect.left() + 26
        right = rect.right() - 26
        top = rect.top() + 78
        y = top + 54
        ancho = max(1.0, right - left)

        # Línea base y compases.
        p.setPen(QPen(QColor("#334155"), 3))
        p.drawLine(left, y, right, y)
        total_pulsos = int(math.ceil(duracion))
        small_font = QFont(self.font())
        small_font.setPointSize(8)
        small_font.setBold(True)
        p.setFont(small_font)
        for b in range(total_pulsos + 1):
            x = left + (b / duracion) * ancho
            es_inicio_compas = (b % max(1, compas)) == 0
            p.setPen(QPen(QColor("#0f172a") if es_inicio_compas else QColor("#94a3b8"), 2 if es_inicio_compas else 1))
            p.drawLine(QRectF(x, y - (34 if es_inicio_compas else 18), 0, (68 if es_inicio_compas else 36)).topLeft(), QRectF(x, y - (34 if es_inicio_compas else 18), 0, (68 if es_inicio_compas else 36)).bottomLeft())
            if b < total_pulsos:
                num = (b % max(1, compas)) + 1
                p.setPen(QColor("#64748b"))
                p.drawText(QRectF(x + 2, y + 35, 28, 18), Qt.AlignLeft | Qt.AlignVCenter, str(num))

        # Cursor de reproducción/práctica.
        if self.beat_actual >= 0:
            xcur = left + (min(duracion, max(0.0, self.beat_actual)) / duracion) * ancho
            p.setPen(QPen(QColor("#2563eb"), 3))
            p.drawLine(xcur, y - 58, xcur, y + 58)

        # Eventos esperados.
        label_font = QFont(self.font())
        label_font.setPointSize(8)
        label_font.setBold(True)
        p.setFont(label_font)
        for idx, ev in enumerate(self.eventos):
            try:
                beat = float(ev.get("beat", 0.0) or 0.0)
            except Exception:
                beat = 0.0
            x = left + (beat / duracion) * ancho
            estado = self.estados[idx] if idx < len(self.estados) else "pendiente"
            if estado == "ok":
                fill, border, text = QColor("#dcfce7"), QColor("#16a34a"), "✓"
            elif estado in {"fallo", "tarde", "omitido"}:
                fill, border, text = QColor("#fee2e2"), QColor("#dc2626"), "×"
            else:
                fill = QColor("#fde68a") if ev.get("acento") else QColor("#e0f2fe")
                border = QColor("#f59e0b") if ev.get("acento") else QColor("#0284c7")
                text = str(ev.get("label", ev.get("nota", "")))[:7]
            p.setPen(QPen(border, 2))
            p.setBrush(QBrush(fill))
            p.drawEllipse(QRectF(x - 16, y - 16, 32, 32))
            p.setPen(QColor("#0f172a"))
            p.drawText(QRectF(x - 28, y - 12, 56, 24), Qt.AlignCenter, text)
            nota = str(ev.get("nota", ""))
            if nota:
                p.drawText(QRectF(x - 30, y - 45, 60, 18), Qt.AlignCenter, nota)

        p.setPen(QColor("#334155"))
        info = practica.get("guia", "Toca las notas cerca del pulso señalado.")
        p.drawText(rect.adjusted(16, rect.height() - 42, -16, -8), Qt.AlignLeft | Qt.AlignVCenter, info)


class DialogoPulsoPractica(QDialog):
    """Práctica funcional de pulso: metrónomo, notas, corrección temporal y docente."""

    def __init__(self, datos: dict, resumen: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.datos = datos or {}
        self.resumen = resumen or {}
        self.controlador = parent
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.ejercicios = [e for e in (self.datos.get("ejercicios", []) or []) if (e.get("practica") or {}).get("eventos")]
        self.indice = self._indice_siguiente()
        self.ejercicio_actual = self.ejercicios[self.indice] if self.ejercicios else {}
        self.estados = []
        self.eventos_ok = 0
        self.eventos_error = 0
        self.practica_activa = False
        self.demo_activa = False
        self.start_ts = 0.0
        self.count_in_beats = 0
        self.ultimo_click_beat = None
        self.ultimo_evento_demo = -1
        self.eventos_omitidos = set()
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.setWindowTitle("Práctica de pulso guiada")
        self.resize(1040, 760)
        self.setMinimumSize(0, 0)
        self._crear_ui()
        self._cargar_ejercicio(self.indice)

    def _indice_siguiente(self):
        if not self.ejercicios:
            return 0
        siguiente = (self.resumen.get("siguiente", {}) or {}).get("id", "")
        if siguiente:
            for i, e in enumerate(self.ejercicios):
                if e.get("id") == siguiente:
                    return i
        return 0

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(10, 10, 10, 10)
        raiz.setSpacing(8)

        self.lbl_titulo = QLabel("Práctica de pulso guiada por el profesor")
        self.lbl_titulo.setObjectName("TituloPulsoPractica")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(self.lbl_titulo)

        panel = QFrame()
        panel.setObjectName("PanelPulsoPractica")
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setSpacing(8)

        self.lbl_objetivo = QLabel()
        self.lbl_objetivo.setWordWrap(True)
        self.lbl_objetivo.setObjectName("ObjetivoPulsoPractica")
        grid.addWidget(self.lbl_objetivo, 0, 0, 1, 6)

        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(36, 220)
        self.spin_bpm.setSuffix(" BPM")
        self.spin_bpm.valueChanged.connect(self._bpm_cambiado)
        self.spin_tol = QSpinBox()
        self.spin_tol.setRange(80, 350)
        self.spin_tol.setSuffix(" ms tolerancia")
        self.chk_metro = QCheckBox("Metrónomo")
        self.chk_metro.setChecked(True)
        self.chk_profesor = QCheckBox("Profesor corrige")
        self.chk_profesor.setChecked(True)

        self.btn_clase = QPushButton("1 Clase del ejercicio")
        self.btn_demo = QPushButton("2 Escuchar demo")
        self.btn_practica = QPushButton("3 Iniciar práctica")
        self.btn_stop = QPushButton("Stop")
        self.btn_anterior = QPushButton("← Anterior")
        self.btn_siguiente = QPushButton("Siguiente →")
        self.btn_volver = QPushButton("Volver a teoría")

        self.btn_clase.clicked.connect(self._leer_clase)
        self.btn_demo.clicked.connect(self._iniciar_demo)
        self.btn_practica.clicked.connect(self._iniciar_practica)
        self.btn_stop.clicked.connect(self._parar)
        self.btn_anterior.clicked.connect(lambda: self._cargar_ejercicio(max(0, self.indice - 1)))
        self.btn_siguiente.clicked.connect(lambda: self._cargar_ejercicio(min(len(self.ejercicios) - 1, self.indice + 1)))
        self.btn_volver.clicked.connect(self._volver_teoria)

        for b in (self.btn_clase, self.btn_demo, self.btn_practica, self.btn_stop, self.btn_anterior, self.btn_siguiente, self.btn_volver):
            b.setMinimumHeight(36)
            b.setMinimumWidth(max(92, b.fontMetrics().horizontalAdvance(b.text()) + 34))
            b.setMaximumWidth(16777215)
            b.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            b.setCursor(Qt.PointingHandCursor)
            if b.text() and not b.toolTip():
                b.setToolTip(b.text())

        grid.addWidget(QLabel("Tempo:"), 1, 0)
        grid.addWidget(self.spin_bpm, 1, 1)
        grid.addWidget(QLabel("Margen:"), 1, 2)
        grid.addWidget(self.spin_tol, 1, 3)
        grid.addWidget(self.chk_metro, 1, 4)
        grid.addWidget(self.chk_profesor, 1, 5)
        grid.addWidget(self.btn_clase, 2, 0)
        grid.addWidget(self.btn_demo, 2, 1)
        grid.addWidget(self.btn_practica, 2, 2)
        grid.addWidget(self.btn_stop, 2, 3)
        grid.addWidget(self.btn_anterior, 2, 4)
        grid.addWidget(self.btn_siguiente, 2, 5)
        raiz.addWidget(panel)

        self.visor = VisorPracticaPulso()
        raiz.addWidget(self.visor)

        centro = QHBoxLayout()
        centro.setSpacing(10)
        izquierda = QFrame()
        izquierda.setObjectName("PanelPulsoPractica")
        izq_lay = QVBoxLayout(izquierda)
        izq_lay.setContentsMargins(10, 8, 10, 8)
        self.lbl_estado = QLabel("Estado: preparado")
        self.lbl_estado.setObjectName("EstadoPulsoPractica")
        self.lbl_estado.setWordWrap(True)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.txt_correccion = QTextEdit()
        self.txt_correccion.setReadOnly(True)
        self.txt_correccion.setMinimumHeight(170)
        izq_lay.addWidget(self.lbl_estado)
        izq_lay.addWidget(self.barra)
        izq_lay.addWidget(self.txt_correccion, 1)
        centro.addWidget(izquierda, 2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        self.lista_lay = QVBoxLayout(cont)
        self.lista_lay.setContentsMargins(4, 4, 4, 4)
        self.lista_lay.setSpacing(6)
        scroll.setWidget(cont)
        centro.addWidget(scroll, 2)
        raiz.addLayout(centro, 1)

        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(self.btn_volver)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloPulsoPractica { font-size: 24px; font-weight: bold; color: #0f3768; }
            #PanelPulsoPractica { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; }
            #ObjetivoPulsoPractica { font-size: 15px; font-weight: bold; color: #0f172a; }
            #EstadoPulsoPractica { font-size: 15px; font-weight: bold; color: #0f3768; }
            QTextEdit { border: 1px solid #94a3b8; border-radius: 8px; padding: 7px; background: white; }
            QPushButton { padding: 7px 12px; border-radius: 7px; background: #2563eb; color: white; font-weight: bold; }
            QPushButton:hover { background: #1d4ed8; }
            QSpinBox { min-height: 30px; }
        """)

    def _cargar_ejercicio(self, indice: int):
        self._parar(silencioso=True)
        if not self.ejercicios:
            self.ejercicio_actual = {}
            self.txt_correccion.setPlainText("No hay ejercicios prácticos de pulso cargados.")
            return
        self.indice = max(0, min(int(indice or 0), len(self.ejercicios) - 1))
        self.ejercicio_actual = self.ejercicios[self.indice]
        practica = self.ejercicio_actual.get("practica", {}) or {}
        eventos = practica.get("eventos", []) or []
        self.estados = ["pendiente" for _ in eventos]
        self.eventos_ok = 0
        self.eventos_error = 0
        self.eventos_omitidos = set()
        self.ultimo_click_beat = None
        self.ultimo_evento_demo = -1
        self.spin_bpm.blockSignals(True)
        self.spin_bpm.setValue(int(self.ejercicio_actual.get("bpm", 60) or 60))
        self.spin_bpm.blockSignals(False)
        self.spin_tol.setValue(int(practica.get("tolerancia_ms", 200) or 200))
        self.lbl_titulo.setText(f"Práctica de pulso · {self.indice + 1}/{len(self.ejercicios)}")
        self.lbl_objetivo.setText(
            f"{self.ejercicio_actual.get('bloque', '')} · {self.ejercicio_actual.get('titulo', '')}\n"
            f"Objetivo: {self.ejercicio_actual.get('objetivo', '')}\n"
            f"Práctica: {practica.get('guia', '')}"
        )
        self.visor.set_ejercicio(self.ejercicio_actual)
        self._actualizar_lista()
        self._actualizar_estado_visual(0.0)
        texto = self._texto_clase_corto()
        self.txt_correccion.setPlainText(texto)
        self._resaltar_siguiente_pendiente()
        self._decir(texto, hablar=False)

    def _actualizar_lista(self):
        while self.lista_lay.count():
            item = self.lista_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for i, e in enumerate(self.ejercicios):
            b = QPushButton(f"{i+1:02d}. {e.get('bloque','')} · {e.get('titulo','')}")
            b.setMinimumHeight(30)
            b.setCursor(Qt.PointingHandCursor)
            if i == self.indice:
                b.setStyleSheet("background:#16a34a;color:white;font-weight:bold;border-radius:7px;")
            b.clicked.connect(lambda _=False, idx=i: self._cargar_ejercicio(idx))
            self.lista_lay.addWidget(b)
        self.lista_lay.addStretch(1)

    def _texto_clase_corto(self):
        e = self.ejercicio_actual or {}
        p = e.get("practica", {}) or {}
        return (
            f"Ejercicio práctico: {p.get('titulo', e.get('titulo', 'pulso'))}.\n\n"
            f"Primero escucha la demo. Después pulsa Iniciar práctica. Tendrás un compás de entrada. "
            f"El profesor corregirá nota, pulso, silencios y entradas adelantadas o tardías.\n\n"
            f"Criterio: {p.get('criterio_practico', '')}"
        )

    def texto_para_profesor(self):
        return self._texto_clase_corto()

    def _leer_clase(self):
        e = self.ejercicio_actual or {}
        p = e.get("practica", {}) or {}
        instrucciones = e.get("instrucciones", []) or []
        texto = [
            f"Vamos con la práctica de pulso: {p.get('titulo', e.get('titulo',''))}.",
            f"Objetivo: {e.get('objetivo','')}",
            f"Patrón: {e.get('patron','')}",
            f"Guía: {p.get('guia','')}",
            "Pasos:",
        ]
        texto.extend([f"{i+1}. {x}" for i, x in enumerate(instrucciones)])
        texto.append("Después pulsa Escuchar demo y luego Iniciar práctica. No se supera si se toca fuera de tiempo o durante un silencio.")
        self._feedback("\n".join(texto), hablar=True)

    def _iniciar_demo(self):
        self._parar(silencioso=True)
        if not self.ejercicio_actual:
            return
        self.demo_activa = True
        self.practica_activa = False
        self.start_ts = time.monotonic()
        self.count_in_beats = 0
        self.ultimo_click_beat = None
        self.ultimo_evento_demo = -1
        self.estados = ["pendiente" for _ in (self.ejercicio_actual.get("practica", {}).get("eventos", []) or [])]
        self.btn_demo.setText("Demo sonando")
        self.btn_practica.setText("3 Iniciar práctica")
        self.timer.start()
        self._feedback("Escucha la demo. El profesor marca el patrón, el metrónomo y las teclas que después tendrás que tocar.", hablar=True)

    def _iniciar_practica(self):
        self._parar(silencioso=True)
        if not self.ejercicio_actual:
            return
        practica = self.ejercicio_actual.get("practica", {}) or {}
        self.estados = ["pendiente" for _ in (practica.get("eventos", []) or [])]
        self.eventos_ok = 0
        self.eventos_error = 0
        self.eventos_omitidos = set()
        self.practica_activa = True
        self.demo_activa = False
        self.start_ts = time.monotonic()
        self.count_in_beats = int(practica.get("compas", self.ejercicio_actual.get("compas", 4)) or 4)
        self.ultimo_click_beat = None
        self.btn_practica.setText("Práctica activa")
        self.btn_demo.setText("2 Escuchar demo")
        self.timer.start()
        self._resaltar_siguiente_pendiente()
        self._feedback(
            "Práctica iniciada. Escucha el compás de entrada y toca solo cuando empiece el ejercicio. "
            "Si tocas en un silencio, si te adelantas o si llegas tarde, el profesor lo corregirá.",
            hablar=True,
        )

    def _parar(self, silencioso=False):
        try:
            self.timer.stop()
        except Exception:
            pass
        self.practica_activa = False
        self.demo_activa = False
        self.btn_demo.setText("2 Escuchar demo") if hasattr(self, "btn_demo") else None
        self.btn_practica.setText("3 Iniciar práctica") if hasattr(self, "btn_practica") else None
        self.ultimo_click_beat = None
        self.ultimo_evento_demo = -1
        self._nota_demo_off()
        try:
            if self.controlador is not None and hasattr(self.controlador, "piano"):
                self.controlador.piano.limpiar_resaltado_docente()
        except Exception:
            pass
        if not silencioso and hasattr(self, "txt_correccion"):
            self._feedback("Práctica detenida. Puedes repetir la demo o iniciar de nuevo.", hablar=False)

    def _volver_teoria(self):
        self._parar(silencioso=True)
        try:
            if self.controlador is not None:
                self.controlador.mostrar_pulso_ritmo()
                return
        except Exception:
            pass
        self.accept()

    def _bpm_cambiado(self):
        if self.practica_activa or self.demo_activa:
            self.start_ts = time.monotonic()
            self.ultimo_click_beat = None
            self.ultimo_evento_demo = -1
            self.estados = ["pendiente" for _ in (self.ejercicio_actual.get("practica", {}).get("eventos", []) or [])]
            self.eventos_ok = 0
            self.eventos_error = 0
            self.eventos_omitidos = set()
            self._feedback("Tempo cambiado. Reinicio el conteo para que la corrección temporal sea limpia.", hablar=False)

    def _beat_segundos(self):
        return 60.0 / max(1, int(self.spin_bpm.value()))

    def _beat_actual(self):
        if not self.start_ts:
            return -float(self.count_in_beats)
        return (time.monotonic() - self.start_ts) / self._beat_segundos() - float(self.count_in_beats)

    def _duracion_beats(self):
        p = self.ejercicio_actual.get("practica", {}) or {}
        return float(p.get("duracion_beats", 4.0) or 4.0)

    def _tick(self):
        if not (self.practica_activa or self.demo_activa):
            return
        beat = self._beat_actual()
        p = self.ejercicio_actual.get("practica", {}) or {}
        compas = int(p.get("compas", self.ejercicio_actual.get("compas", 4)) or 4)
        duracion = self._duracion_beats()
        click_index = math.floor(beat + self.count_in_beats) if beat < 0 else math.floor(beat)
        if click_index != self.ultimo_click_beat:
            self.ultimo_click_beat = click_index
            if self.chk_metro.isChecked():
                acento = ((click_index % max(1, compas)) == 0)
                self._sonar_click(acento=acento)
        if self.demo_activa:
            self._tick_demo(beat)
        elif self.practica_activa:
            self._marcar_omisiones(beat)
        self._actualizar_estado_visual(beat)
        if beat > duracion + 0.65:
            if self.demo_activa:
                self._parar(silencioso=True)
                self._feedback("Demo terminada. Ahora pulsa Iniciar práctica y toca el patrón con el profesor.", hablar=True)
            elif self.practica_activa:
                self._finalizar_practica()

    def _tick_demo(self, beat: float):
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        for idx, ev in enumerate(eventos):
            if idx <= self.ultimo_evento_demo:
                continue
            if beat >= float(ev.get("beat", 0.0) or 0.0):
                self.ultimo_evento_demo = idx
                self.estados[idx] = "ok"
                nota = str(ev.get("nota", ""))
                if nota:
                    self._tocar_nota_demo(nota)
                    self._resaltar([nota])
                break

    def _marcar_omisiones(self, beat: float):
        tol_beats = int(self.spin_tol.value()) / 1000.0 / self._beat_segundos()
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        for idx, ev in enumerate(eventos):
            if idx in self.eventos_omitidos:
                continue
            if self.estados[idx] != "pendiente":
                continue
            evbeat = float(ev.get("beat", 0.0) or 0.0)
            if beat > evbeat + tol_beats:
                self.estados[idx] = "omitido"
                self.eventos_error += 1
                self.eventos_omitidos.add(idx)
                self._feedback(
                    "Se ha pasado una entrada sin tocar. Repite desde un tempo más lento y cuenta en voz baja antes de tocar.",
                    hablar=False,
                )
                self._resaltar_siguiente_pendiente()
                break

    def procesar_nota(self, nota: str, velocity: int = 96, canal=None, origen: str = "piano_virtual") -> bool:
        # Si esta pantalla está abierta, gestionamos la entrada para evitar mensajes genéricos.
        if not self.ejercicio_actual:
            return False
        if not self.practica_activa:
            self._feedback("Pulsa primero Iniciar práctica. La demo solo enseña; la corrección empieza en práctica.", hablar=False)
            return True
        nota = self._normalizar_nota(str(nota or ""))
        beat = self._beat_actual()
        if beat < 0:
            self.eventos_error += 1
            self._feedback("Espera. Todavía estamos en el compás de entrada. Toca cuando empiece el ejercicio.", hablar=True)
            return True
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        if not eventos:
            return True
        tol_beats = int(self.spin_tol.value()) / 1000.0 / self._beat_segundos()
        pendientes = [(i, abs(beat - float(ev.get("beat", 0.0) or 0.0))) for i, ev in enumerate(eventos) if self.estados[i] == "pendiente"]
        if not pendientes:
            self._feedback("El patrón ya estaba terminado. Pulsa Siguiente o repite el ejercicio.", hablar=False)
            return True

        # Si hay varias notas en el mismo pulso, elegimos primero la pendiente
        # que coincide con la nota tocada. Así un acorde/entrada simultánea no
        # se corrige como error por el orden interno de la lista.
        candidatas_misma_nota = []
        for i, dif_i in pendientes:
            ev_i = eventos[i]
            if dif_i <= tol_beats and self._normalizar_nota(str(ev_i.get("nota", ""))) == nota:
                candidatas_misma_nota.append((i, dif_i))
        if candidatas_misma_nota:
            idx, dif = min(candidatas_misma_nota, key=lambda x: x[1])
        else:
            idx, dif = min(pendientes, key=lambda x: x[1])

        ev = eventos[idx]
        esperado = self._normalizar_nota(str(ev.get("nota", "")))
        dif_ms = round(dif * self._beat_segundos() * 1000.0, 1)
        if dif <= tol_beats and nota == esperado:
            self.estados[idx] = "ok"
            self.eventos_ok += 1
            self._sonar_acierto()
            self._registrar_historial(nota, esperado, True, dif_ms, origen, velocity, canal, "Correcto y en pulso")
            self._feedback(f"Correcto: {self._nota_humana(nota)} cayó dentro del pulso. Desviación aproximada: {dif_ms} ms.", hablar=False)
            self._resaltar_siguiente_pendiente()
            return True
        self.eventos_error += 1
        if dif <= tol_beats and nota != esperado:
            self.estados[idx] = "fallo"
            mensaje = f"Nota equivocada. Has tocado {self._nota_humana(nota)}, pero el patrón pedía {self._nota_humana(esperado)}. Mantén el pulso y continúa."
            correcto_tiempo = True
        else:
            mensaje = f"Fuera de pulso o durante un silencio. Has tocado {self._nota_humana(nota)} a {dif_ms} ms de la entrada más cercana. Espera el clic o subdivide en voz baja."
            correcto_tiempo = False
        self._sonar_error()
        self._registrar_historial(nota, esperado, False, dif_ms, origen, velocity, canal, mensaje)
        self._feedback(mensaje, hablar=self.chk_profesor.isChecked())
        self._resaltar_siguiente_pendiente()
        return True

    def _finalizar_practica(self):
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        total = max(1, len(eventos))
        ok = len([s for s in self.estados if s == "ok"])
        porcentaje = int((ok / total) * 100)
        errores = len([s for s in self.estados if s in {"fallo", "omitido", "tarde"}]) + self.eventos_error - len([s for s in self.estados if s in {"fallo", "omitido", "tarde"}])
        supera = porcentaje >= 80 and ok >= max(1, int(total * 0.8))
        self._parar(silencioso=True)
        if supera:
            texto = (
                f"Ejercicio superado: {porcentaje}% de precisión. Has mantenido el pulso bastante estable. "
                "Puedes pasar al siguiente ejercicio o repetirlo subiendo un poco el tempo."
            )
            try:
                if self.controlador is not None and hasattr(self.controlador, "pulso_ritmo"):
                    nivel = getattr(getattr(self.controlador, "progreso", None), "estado", None)
                    nivel_actual = getattr(nivel, "nivel_actual", "inicial") or "inicial"
                    if nivel_actual == "sin_evaluar":
                        nivel_actual = "inicial"
                    self.controlador.pulso_ritmo.marcar_completado(self.ejercicio_actual.get("id", ""), nivel_actual)
                    if hasattr(self.controlador, "_celebrar_logro"):
                        self.controlador._celebrar_logro("reto", "Práctica de pulso completada")
            except Exception:
                pass
        else:
            texto = (
                f"Aún no está superado: {porcentaje}% de precisión. Repite más lento. "
                "El objetivo no es correr: es tocar exactamente donde cae el pulso y respetar los silencios."
            )
        self._feedback(texto, hablar=True)
        self._actualizar_estado_visual(self._duracion_beats())

    def _actualizar_estado_visual(self, beat: float):
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        total = max(1, len(eventos))
        ok = len([s for s in self.estados if s == "ok"])
        pct = int((ok / total) * 100)
        self.barra.setValue(pct)
        if beat < 0 and (self.practica_activa or self.demo_activa):
            estado = f"Entrada: faltan {abs(int(math.floor(beat))) + 1} pulsos"
        elif self.practica_activa:
            estado = f"Práctica activa · beat {max(0.0, beat):.2f} · aciertos {ok}/{total}"
        elif self.demo_activa:
            estado = f"Demo activa · beat {max(0.0, beat):.2f}"
        else:
            estado = f"Preparado · aciertos {ok}/{total}"
        self.lbl_estado.setText(estado)
        self.visor.set_estado(self.estados, max(0.0, beat))

    def _resaltar_siguiente_pendiente(self):
        eventos = self.ejercicio_actual.get("practica", {}).get("eventos", []) or []
        notas = []
        for i, ev in enumerate(eventos):
            if i < len(self.estados) and self.estados[i] == "pendiente":
                nota = str(ev.get("nota", ""))
                if nota:
                    notas = [nota]
                break
        self._resaltar(notas)

    def _resaltar(self, notas):
        try:
            if self.controlador is not None and hasattr(self.controlador, "piano"):
                if notas:
                    self.controlador.piano.resaltar_notas_docente(notas)
                else:
                    self.controlador.piano.limpiar_resaltado_docente()
        except Exception:
            pass

    def _feedback(self, texto: str, hablar: bool = False):
        self.txt_correccion.setPlainText(texto)
        self._decir(texto, hablar=hablar)

    def _decir(self, texto: str, hablar: bool = False):
        if not texto:
            return
        try:
            if self.controlador is not None:
                self.controlador._actualizar_dialogo_avatar(texto)
                if hablar:
                    self.controlador._hablar_con_avatar(texto)
        except Exception:
            pass

    def _sonar_click(self, acento=False):
        try:
            audio = getattr(self.controlador, "audio", None)
            if audio is not None and hasattr(audio, "sonido_metronomo"):
                if audio.sonido_metronomo(acento):
                    return
        except Exception:
            pass

    def _sonar_acierto(self):
        try:
            self.controlador.audio.sonido_acierto()
        except Exception:
            pass

    def _sonar_error(self):
        try:
            self.controlador.audio.sonido_error()
        except Exception:
            pass

    def _tocar_nota_demo(self, nota: str):
        self._nota_demo_off()
        self._nota_demo_actual = nota
        try:
            if self.controlador is not None and hasattr(self.controlador, "_audio_y_midi_note_on"):
                self.controlador._audio_y_midi_note_on(nota, velocity=82, canal=1)
                QTimer.singleShot(max(90, int(self._beat_segundos() * 420)), self._nota_demo_off)
        except Exception:
            pass

    def _nota_demo_off(self):
        nota = getattr(self, "_nota_demo_actual", "")
        if not nota:
            return
        try:
            if self.controlador is not None and hasattr(self.controlador, "_audio_y_midi_note_off"):
                self.controlador._audio_y_midi_note_off(nota, velocity=0, canal=1)
        except Exception:
            pass
        self._nota_demo_actual = ""

    def _registrar_historial(self, nota, esperado, correcto, dif_ms, origen, velocity, canal, mensaje):
        try:
            if self.controlador is not None and hasattr(self.controlador, "_registrar_historial_midi"):
                self.controlador._registrar_historial_midi(
                    nota=nota,
                    velocity=velocity,
                    canal=canal,
                    origen=origen,
                    esperado=esperado,
                    correcto=correcto,
                    diferencia_ms=dif_ms,
                    en_pulso=bool(correcto),
                    tipo="pulso_practica",
                    mensaje=mensaje,
                    contexto={"ejercicio_id": self.ejercicio_actual.get("id", ""), "beat": self._beat_actual()},
                )
        except Exception:
            pass

    def _normalizar_nota(self, nota: str) -> str:
        n = str(nota or "").strip()
        mapa = {
            "Do": "C", "Re": "D", "Mi": "E", "Fa": "F", "Sol": "G", "La": "A", "Si": "B",
            "DO": "C", "RE": "D", "MI": "E", "FA": "F", "SOL": "G", "LA": "A", "SI": "B",
        }
        for es, en in sorted(mapa.items(), key=lambda x: -len(x[0])):
            n = n.replace(es, en)
        return n.replace("♯", "#").replace(" ", "")

    def _nota_humana(self, nota: str) -> str:
        n = self._normalizar_nota(nota)
        base = n[:-1] if n[-1:].isdigit() else n
        octava = n[-1] if n[-1:].isdigit() else ""
        mapa = {"C": "Do", "C#": "Do#", "D": "Re", "D#": "Re#", "E": "Mi", "F": "Fa", "F#": "Fa#", "G": "Sol", "G#": "Sol#", "A": "La", "A#": "La#", "B": "Si"}
        return (mapa.get(base, base) + (octava if octava else "")).strip()

    def closeEvent(self, event):
        self._parar(silencioso=True)
        super().closeEvent(event)
