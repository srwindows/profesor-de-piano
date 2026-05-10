from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar,
    QSpinBox, QApplication, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont


class VisorPatronPulso(QWidget):
    """Dibujo simple del patrón rítmico del ejercicio actual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ejercicio = {}
        self.pulso_actual = 0
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_ejercicio(self, ejercicio: dict):
        self.ejercicio = ejercicio or {}
        self.pulso_actual = 0
        self.update()

    def set_pulso(self, pulso: int):
        self.pulso_actual = int(pulso or 0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 10, -12, -10)
        p.fillRect(self.rect(), QColor("#f8fafc"))

        p.setPen(QPen(QColor("#cbd5e1"), 2))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(rect, 14, 14)

        ejercicio = self.ejercicio or {}
        titulo = ejercicio.get("titulo", "Ejercicio de pulso")
        patron = ejercicio.get("patron", "1 2 3 4")
        compas = int(ejercicio.get("compas", 4) or 4)

        p.setPen(QColor("#0f3768"))
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect.adjusted(14, 10, -14, -10), Qt.AlignLeft | Qt.AlignTop, titulo)

        top = rect.top() + 54
        left = rect.left() + 26
        right = rect.right() - 26
        ancho = max(1, right - left)
        paso = ancho / max(1, compas)

        p.setPen(QPen(QColor("#334155"), 3))
        y = top + 40
        p.drawLine(left, y, right, y)

        for i in range(compas):
            x = left + paso * i + paso / 2
            activo = (i + 1) == self.pulso_actual
            color = QColor("#f59e0b") if activo else QColor("#e2e8f0")
            borde = QColor("#ea580c") if activo else QColor("#64748b")
            p.setPen(QPen(borde, 3 if activo else 2))
            p.setBrush(QBrush(color))
            radio = 18 if activo else 14
            p.drawEllipse(QRectF(x - radio, y - radio, radio * 2, radio * 2))
            p.setPen(QColor("#0f172a"))
            f2 = QFont()
            f2.setPointSize(11)
            f2.setBold(True)
            p.setFont(f2)
            p.drawText(QRectF(x - 20, y - 13, 40, 26), Qt.AlignCenter, str(i + 1))
            if i == 0:
                p.setPen(QColor("#16a34a"))
                p.drawText(QRectF(x - 40, y + 24, 80, 22), Qt.AlignCenter, "fuerte")

        p.setPen(QColor("#1e293b"))
        f3 = QFont()
        f3.setPointSize(12)
        f3.setBold(False)
        p.setFont(f3)
        p.drawText(rect.adjusted(16, 108, -16, -8), Qt.AlignLeft | Qt.AlignVCenter, "Patrón: " + str(patron))


class DialogoPulsoRitmo(QDialog):
    """Entrenador de pulso con docencia, metrónomo y progresión en cinco niveles.

    Códigos:
    - 10: marcar ejercicio completado.
    - 20: ir a práctica.
    - 30: reiniciar progreso.
    """

    def __init__(self, datos: dict, resumen: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.datos = datos or {}
        self.resumen = resumen or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.controlador = parent
        self.pulso_actual = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.setWindowTitle("Pulso y ritmo guiado")
        self.resize(980, 720)
        self.setMinimumSize(0, 0)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(10, 10, 10, 10)
        raiz.setSpacing(8)

        titulo = QLabel(self.datos.get("titulo", "Pulso y ritmo guiado por el profesor"))
        titulo.setObjectName("TituloPulso")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        self.ejercicio_actual = self.resumen.get("siguiente", {}) or self._primer_ejercicio()

        cab = QFrame()
        cab.setObjectName("CabeceraPulso")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 8, 10, 8)
        cab_lay.setSpacing(10)

        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMinimumHeight(105)
        self.txt_resumen.setMaximumHeight(145)
        self.txt_resumen.setPlainText(self._texto_resumen())
        cab_lay.addWidget(self.txt_resumen, 1)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(self.resumen.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Pulso: {self.resumen.get('completados', 0)}/{self.resumen.get('total', 0)} ejercicios · %p%"
        )
        barra_box = QVBoxLayout()
        barra_box.addWidget(QLabel("Progreso de pulso"))
        barra_box.addWidget(self.barra)
        barra_box.addStretch(1)
        cab_lay.addLayout(barra_box, 0)
        raiz.addWidget(cab)

        self.visor_patron = VisorPatronPulso()
        self.visor_patron.set_ejercicio(self.ejercicio_actual)
        raiz.addWidget(self.visor_patron)

        panel_metro = QFrame()
        panel_metro.setObjectName("PanelMetronomo")
        metro_lay = QHBoxLayout(panel_metro)
        metro_lay.setContentsMargins(10, 8, 10, 8)
        metro_lay.setSpacing(8)

        sig = self.ejercicio_actual
        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(40, 220)
        self.spin_bpm.setValue(int(sig.get("bpm", 60) or 60))
        self.spin_bpm.setSuffix(" bpm")
        self.spin_bpm.setMinimumHeight(34)
        self.spin_bpm.valueChanged.connect(self._reiniciar_timer_si_activo)

        self.spin_compas = QSpinBox()
        self.spin_compas.setRange(2, 7)
        self.spin_compas.setValue(int(sig.get("compas", 4) or 4))
        self.spin_compas.setPrefix("Compás ")
        self.spin_compas.setMinimumHeight(34)

        self.chk_sonido_metronomo = QCheckBox("Sonido")
        self.chk_sonido_metronomo.setChecked(True)
        self.chk_sonido_metronomo.setToolTip("Activa o desactiva el clic del metrónomo. El pulso visual seguirá funcionando.")
        self.chk_sonido_metronomo.setMinimumHeight(34)

        self.lbl_pulso = QLabel("1")
        self.lbl_pulso.setObjectName("DisplayPulso")
        self.lbl_pulso.setAlignment(Qt.AlignCenter)
        self.lbl_pulso.setMinimumSize(76, 58)

        self.btn_start = QPushButton("Iniciar metrónomo")
        self.btn_start.clicked.connect(self._toggle_metronomo)
        self.btn_start.setMinimumHeight(36)
        self.btn_start.setMinimumWidth(max(120, self.btn_start.fontMetrics().horizontalAdvance(self.btn_start.text()) + 34))

        self.btn_demo = QPushButton("Demo guiada")
        self.btn_demo.clicked.connect(self._demo_guiada)
        self.btn_demo.setMinimumHeight(36)
        self.btn_demo.setMinimumWidth(max(110, self.btn_demo.fontMetrics().horizontalAdvance(self.btn_demo.text()) + 34))

        metro_lay.addWidget(QLabel("Tempo:"))
        metro_lay.addWidget(self.spin_bpm)
        metro_lay.addWidget(QLabel("Compás:"))
        metro_lay.addWidget(self.spin_compas)
        metro_lay.addWidget(self.chk_sonido_metronomo)
        metro_lay.addWidget(self.lbl_pulso)
        metro_lay.addWidget(self.btn_start)
        metro_lay.addWidget(self.btn_demo)
        metro_lay.addStretch(1)
        raiz.addWidget(panel_metro)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(10)

        bloque_actual = QFrame()
        bloque_actual.setObjectName("CardPulsoActual")
        actual_lay = QVBoxLayout(bloque_actual)
        actual_lay.setContentsMargins(10, 8, 10, 8)
        self.lbl_actual = QLabel()
        self.lbl_actual.setObjectName("TituloEjercicioPulso")
        self.lbl_actual.setWordWrap(True)
        actual_lay.addWidget(self.lbl_actual)
        self.txt_detalle = QTextEdit()
        self.txt_detalle.setReadOnly(True)
        self.txt_detalle.setMinimumHeight(185)
        actual_lay.addWidget(self.txt_detalle, 1)
        cuerpo.addWidget(bloque_actual, 2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)

        completados = set(self._ids_completados_por_orden())
        siguiente_id = self.ejercicio_actual.get("id", "")
        for ejercicio in self.datos.get("ejercicios", []):
            lay.addWidget(self._card_ejercicio(ejercicio, completado=ejercicio.get("id") in completados, actual=ejercicio.get("id") == siguiente_id))

        lay.addStretch(1)
        scroll.setWidget(cont)
        cuerpo.addWidget(scroll, 3)
        raiz.addLayout(cuerpo, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer punto actual")
        self.btn_marcar = QPushButton("Marcar completado")
        self.btn_practica = QPushButton("Ir a práctica")
        self.btn_reiniciar = QPushButton("Reiniciar pulso")
        self.btn_cerrar = QPushButton("Cerrar")

        self.btn_leer.clicked.connect(lambda: None)
        self.btn_marcar.clicked.connect(lambda: self.done(10))
        self.btn_practica.clicked.connect(lambda: self.done(20))
        self.btn_reiniciar.clicked.connect(lambda: self.done(30))
        self.btn_cerrar.clicked.connect(self.reject)

        for b in (self.btn_leer, self.btn_marcar, self.btn_practica, self.btn_reiniciar, self.btn_cerrar):
            b.setMinimumHeight(36)
            b.setMinimumWidth(max(92, b.fontMetrics().horizontalAdvance(b.text()) + 34))
            b.setMaximumWidth(16777215)
            b.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            b.setCursor(Qt.PointingHandCursor)
            if b.text() and not b.toolTip():
                b.setToolTip(b.text())

        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_marcar)
        fila.addWidget(self.btn_practica)
        fila.addStretch(1)
        fila.addWidget(self.btn_reiniciar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self._actualizar_detalle_actual()
        self.setStyleSheet("""
            #TituloPulso {
                font-size: 24px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraPulso, #CardPulso, #PanelMetronomo {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #CardPulsoActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardPulsoCompletado {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloEjercicioPulso {
                font-size: 17px;
                font-weight: bold;
                color: #0f172a;
            }
            #DisplayPulso {
                font-size: 32px;
                font-weight: bold;
                color: #0f172a;
                background: #ffffff;
                border: 2px solid #94a3b8;
                border-radius: 14px;
            }
            QTextEdit {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 7px;
                background: white;
            }
            QPushButton {
                padding: 7px 12px;
                border-radius: 7px;
                background: #2563eb;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)

    def _primer_ejercicio(self):
        ejercicios = self.datos.get("ejercicios", []) or []
        return ejercicios[0] if ejercicios else {}

    def _ids_completados_por_orden(self):
        hechos = int(self.resumen.get("completados", 0) or 0)
        ejercicios = self.datos.get("ejercicios", []) or []
        return [e.get("id", "") for e in ejercicios[:hechos]]

    def _texto_resumen(self):
        sig = self.ejercicio_actual
        pasos = sig.get("instrucciones", [])
        pasos_txt = " · ".join(pasos[:4]) if pasos else "Sin instrucciones."
        return (
            f"{self.datos.get('descripcion', '')}\n\n"
            "El profesor debe guiar cada ejercicio en tres fases: escuchar, contar y tocar. "
            "No se sube de nivel si el alumno pierde el pulso, anticipa la nota o no reconoce el tiempo 1.\n\n"
            f"Ejercicio actual: {sig.get('titulo', 'Sin ejercicio')} · {sig.get('bloque', '')}.\n"
            f"Tempo recomendado: {sig.get('bpm', '—')} bpm · Compás: {sig.get('compas', '—')}/4.\n"
            f"Objetivo: {sig.get('objetivo', '')}\n"
            f"Pasos: {pasos_txt}"
        )

    def _actualizar_detalle_actual(self):
        e = self.ejercicio_actual or {}
        self.lbl_actual.setText(f"Ejercicio actual · {e.get('bloque', '')}\n{e.get('titulo', 'Sin ejercicio')}")
        instrucciones = e.get("instrucciones", []) or []
        texto = [
            f"Objetivo: {e.get('objetivo', '')}",
            f"Patrón: {e.get('patron', '')}",
            f"Tempo: {e.get('bpm', '—')} bpm · Compás: {e.get('compas', '—')}/4 · Duración: {e.get('duracion_compases', '—')} compases",
            "",
            "Guía del profesor:",
            e.get("profesor", "Escucha, cuenta y toca sin perder el pulso."),
            "",
            "Pasos:",
        ]
        texto.extend([f"{i+1}. {p}" for i, p in enumerate(instrucciones)])
        texto.extend(["", f"Criterio para superar: {e.get('criterio', '')}"])
        self.txt_detalle.setPlainText("\n".join(texto))

    def texto_para_profesor(self):
        ejercicios = self.datos.get("ejercicios", []) or []
        niveles = self.datos.get("niveles", []) or []
        niveles_txt = "; ".join([f"{n.get('titulo')}" for n in niveles])
        actual = self.ejercicio_actual or {}
        return (
            f"Pulso y ritmo guiado. {self.datos.get('descripcion', '')}\n\n"
            f"Progresión de cinco niveles: {niveles_txt}.\n\n"
            f"Ejercicio actual: {actual.get('titulo', '')}. Objetivo: {actual.get('objetivo', '')}. "
            f"Patrón: {actual.get('patron', '')}. Criterio: {actual.get('criterio', '')}.\n\n"
            "Docencia: primero escuchar el metrónomo, después contar en voz baja, después tocar. "
            "El profesor corrige si el alumno se adelanta, se retrasa, pierde el tiempo fuerte o acelera al subdividir."
        )

    def _card_ejercicio(self, ejercicio: dict, completado: bool, actual: bool):
        card = QFrame()
        if completado:
            card.setObjectName("CardPulsoCompletado")
            icono = "✓"
        elif actual:
            card.setObjectName("CardPulsoActual")
            icono = "▶"
        else:
            card.setObjectName("CardPulso")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(9, 7, 9, 7)
        lay.setSpacing(4)

        titulo = QLabel(f"{icono} {ejercicio.get('bloque', '')} · {ejercicio.get('titulo', 'Ejercicio')}")
        titulo.setObjectName("TituloEjercicioPulso")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        meta = QLabel(
            f"BPM {ejercicio.get('bpm', '—')} · Compás {ejercicio.get('compas', '—')}/4 · "
            f"Patrón: {ejercicio.get('patron', '—')}"
        )
        meta.setWordWrap(True)
        lay.addWidget(meta)

        objetivo = QLabel("Objetivo: " + ejercicio.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        criterio = QLabel("Supera si: " + ejercicio.get("criterio", ""))
        criterio.setWordWrap(True)
        lay.addWidget(criterio)

        return card

    def _toggle_metronomo(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_start.setText("Iniciar metrónomo")
            return
        self.pulso_actual = 0
        self._iniciar_timer()
        self.btn_start.setText("Detener metrónomo")
        self._tick()

    def _iniciar_timer(self):
        intervalo = max(80, int(60000 / max(1, int(self.spin_bpm.value()))))
        self.timer.start(intervalo)

    def _reiniciar_timer_si_activo(self):
        if self.timer.isActive():
            self._iniciar_timer()

    def _tick(self):
        compas = max(1, int(self.spin_compas.value()))
        self.pulso_actual = (self.pulso_actual % compas) + 1
        self.lbl_pulso.setText(str(self.pulso_actual))
        self.visor_patron.set_pulso(self.pulso_actual)
        if self.pulso_actual == 1:
            self.lbl_pulso.setStyleSheet("background:#DCFCE7; border:2px solid #16A34A; border-radius:14px;")
        else:
            self.lbl_pulso.setStyleSheet("background:#FFFFFF; border:2px solid #94A3B8; border-radius:14px;")
        if getattr(self, "chk_sonido_metronomo", None) is None or self.chk_sonido_metronomo.isChecked():
            self._sonar_click_metronomo(acento=(self.pulso_actual == 1))

    def _demo_guiada(self):
        texto = (
            "Demo guiada de pulso. Escucha cuatro clics sin tocar. "
            "Después cuenta uno, dos, tres, cuatro. Por último toca el patrón del ejercicio actual sin perseguir el clic."
        )
        try:
            if self.controlador is not None:
                self.controlador._actualizar_dialogo_avatar(texto)
                self.controlador._hablar_con_avatar(texto)
        except Exception:
            pass
        if not self.timer.isActive():
            self._toggle_metronomo()

    def _sonar_click_metronomo(self, acento=False):
        controlador = getattr(self, "controlador", None)
        audio = getattr(controlador, "audio", None)
        if audio is not None and hasattr(audio, "sonido_metronomo"):
            try:
                if audio.sonido_metronomo(acento):
                    return
            except Exception:
                pass
        try:
            QApplication.beep()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.timer.stop()
        except Exception:
            pass
        super().closeEvent(event)
