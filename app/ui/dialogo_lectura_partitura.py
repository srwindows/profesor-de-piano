from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar,
    QSpinBox, QCheckBox, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer


class DialogoLecturaPartitura(QDialog):
    """Lectura visual de partitura integrada con piano y metrónomo.

    En el modo panel integrado, el profesor/avatar principal vive a la derecha,
    así que aquí no se repite un segundo avatar a la izquierda.
    """

    def __init__(self, datos: dict, resumen: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.datos = datos or {}
        self.resumen = resumen or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.controlador = parent
        self.pulso_actual = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_metronomo)
        self.setWindowTitle("Lectura de partitura visual")
        self.resize(980, 700)
        # Al integrarse dentro de la ventana principal no puede imponer un tamaño
        # mínimo grande, porque entonces aplasta la pizarra y el piano.
        self.setMinimumSize(0, 0)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(10, 10, 10, 10)
        raiz.setSpacing(8)

        titulo = QLabel(self.datos.get("titulo", "Lectura de partitura"))
        titulo.setObjectName("TituloLecturaPartitura")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setMaximumHeight(40)
        raiz.addWidget(titulo, 0)

        # v4.1.9: rediseño 3/4 + 1/4.
        # Izquierda: pizarra/partitura y controles propios.
        # Derecha: puntos de clase y ejercicios, visibles de arriba abajo.
        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(10)

        columna_partitura = QFrame()
        columna_partitura.setObjectName("PanelPartituraPrincipal")
        columna_partitura.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay_partitura = QVBoxLayout(columna_partitura)
        lay_partitura.setContentsMargins(0, 0, 0, 0)
        lay_partitura.setSpacing(8)

        cab = QFrame()
        cab.setObjectName("CabeceraLectura")
        cab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cab_lay = QVBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(8)

        self.txt_profesor = QTextEdit()
        self.txt_profesor.setReadOnly(True)
        self.txt_profesor.setMinimumHeight(260)
        self.txt_profesor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.txt_profesor.setPlainText(self._texto_profesor_completo())
        cab_lay.addWidget(self.txt_profesor, 1)

        # Guía docente fija: en Partitura no basta con listar ejercicios; el
        # alumno novel necesita ver qué significa cada símbolo y cómo se lee.
        self.lbl_guia_lectura = QLabel(self._texto_guia_simbolos())
        self.lbl_guia_lectura.setObjectName("GuiaSimbolosPartitura")
        self.lbl_guia_lectura.setWordWrap(True)
        self.lbl_guia_lectura.setMinimumHeight(80)
        cab_lay.addWidget(self.lbl_guia_lectura, 0)

        # Compatibilidad con versiones anteriores y con la pizarra integrada.
        self.txt_resumen = self.txt_profesor
        lay_partitura.addWidget(cab, 1)

        self.panel_metronomo_lectura = self._crear_panel_metronomo()
        lay_partitura.addWidget(self.panel_metronomo_lectura, 0)

        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_leer = QPushButton("▶ Leer clase")
        self.btn_marcar = QPushButton("Marcar completada")
        self.btn_practica = QPushButton("Ir a práctica")
        self.btn_repertorio = QPushButton("Repertorio")
        self.btn_reiniciar = QPushButton("Reiniciar")
        self.btn_cerrar = QPushButton("Cerrar")

        self.btn_marcar.clicked.connect(lambda: self.done(10))
        self.btn_practica.clicked.connect(lambda: self.done(20))
        self.btn_repertorio.clicked.connect(lambda: self.done(40))
        self.btn_reiniciar.clicked.connect(lambda: self.done(30))
        self.btn_cerrar.clicked.connect(self.reject)

        for b in (self.btn_leer, self.btn_marcar, self.btn_practica, self.btn_repertorio, self.btn_reiniciar, self.btn_cerrar):
            b.setMinimumHeight(32)
            b.setCursor(Qt.PointingHandCursor)

        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_marcar)
        fila.addWidget(self.btn_practica)
        fila.addWidget(self.btn_repertorio)
        fila.addStretch(1)
        fila.addWidget(self.btn_reiniciar)
        fila.addWidget(self.btn_cerrar)
        lay_partitura.addLayout(fila, 0)

        cuerpo.addWidget(columna_partitura, 3)

        columna_puntos = QFrame()
        columna_puntos.setObjectName("PanelPuntosLectura")
        columna_puntos.setMinimumWidth(260)
        columna_puntos.setMaximumWidth(360)
        columna_puntos.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        lay_puntos = QVBoxLayout(columna_puntos)
        lay_puntos.setContentsMargins(10, 10, 10, 10)
        lay_puntos.setSpacing(8)

        lbl_puntos = QLabel("Puntos de clase y ejercicios")
        lbl_puntos.setObjectName("TituloPuntosLectura")
        lbl_puntos.setAlignment(Qt.AlignCenter)
        lay_puntos.addWidget(lbl_puntos, 0)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(self.resumen.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Lectura: {self.resumen.get('completados', 0)}/{self.resumen.get('total', 0)} · %p%"
        )
        lay_puntos.addWidget(self.barra, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        completados = int(self.resumen.get("completados", 0) or 0)
        siguiente_id = (self.resumen.get("siguiente", {}) or {}).get("id", "")
        for i, ejercicio in enumerate(self.datos.get("ejercicios", [])):
            lay.addWidget(self._card_ejercicio(
                ejercicio,
                completado=i < completados,
                actual=ejercicio.get("id") == siguiente_id
            ))

        lay.addStretch(1)
        scroll.setWidget(cont)
        lay_puntos.addWidget(scroll, 1)

        cuerpo.addWidget(columna_puntos, 1)
        raiz.addLayout(cuerpo, 1)

        self.setStyleSheet("""
            #TituloLecturaPartitura {
                font-size: 22px;
                font-weight: bold;
                color: #0f3768;
            }
            #PanelPartituraPrincipal, #PanelPuntosLectura, #CabeceraLectura, #CardLectura, #PanelMetronomoLectura {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #PanelPuntosLectura {
                background: #f1f5f9;
            }
            #TituloPuntosLectura {
                font-size: 16px;
                font-weight: bold;
                color: #0f3768;
            }
            #CardLecturaActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardLecturaCompletada {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloEjercicioLectura {
                font-size: 15px;
                font-weight: bold;
                color: #0f172a;
            }
            #GuiaSimbolosPartitura {
                background: #eef6ff;
                border: 1px solid #93c5fd;
                border-radius: 10px;
                padding: 8px;
                color: #0f3768;
                font-weight: 600;
            }
            #PentagramaVisual {
                font-family: monospace;
                font-size: 15px;
                font-weight: bold;
                color: #1e293b;
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px;
            }
            #DisplayPulsoLectura {
                font-size: 22px;
                font-weight: bold;
                color: #0f172a;
                background: #ffffff;
                border: 2px solid #94a3b8;
                border-radius: 10px;
            }
            QTextEdit {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 8px;
                background: white;
            }
            QPushButton {
                padding: 6px 10px;
                border-radius: 7px;
                background: #2563eb;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)

    def _crear_panel_metronomo(self):
        sig = self.resumen.get("siguiente", {}) or {}
        panel = QFrame()
        panel.setObjectName("PanelMetronomoLectura")
        panel.setMaximumHeight(64)
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(7)

        titulo = QLabel("Metrónomo")
        titulo.setStyleSheet("font-weight:bold; color:#0f3768;")

        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(40, 220)
        self.spin_bpm.setValue(int(sig.get("tempo", 60) or 60))
        self.spin_bpm.setSuffix(" bpm")
        self.spin_bpm.setMinimumHeight(30)
        self.spin_bpm.setMaximumWidth(98)

        self.spin_compas = QSpinBox()
        self.spin_compas.setRange(2, 7)
        compas_txt = str(sig.get("compas", "4/4")).split("/")[0]
        try:
            compas_val = int(compas_txt)
        except Exception:
            compas_val = 4
        self.spin_compas.setValue(compas_val)
        self.spin_compas.setPrefix("Compás ")
        self.spin_compas.setMinimumHeight(30)
        self.spin_compas.setMaximumWidth(110)

        self.chk_sonido_metronomo = QCheckBox("Sonido")
        self.chk_sonido_metronomo.setChecked(True)
        self.chk_sonido_metronomo.setToolTip("Activa o desactiva el click del metrónomo.")

        self.lbl_pulso = QLabel("1")
        self.lbl_pulso.setObjectName("DisplayPulsoLectura")
        self.lbl_pulso.setAlignment(Qt.AlignCenter)
        self.lbl_pulso.setMinimumSize(46, 38)
        self.lbl_pulso.setMaximumSize(54, 42)

        self.btn_metro = QPushButton("Iniciar")
        self.btn_metro.setMinimumHeight(30)
        self.btn_metro.setMaximumWidth(96)
        self.btn_metro.clicked.connect(self._toggle_metronomo)

        lay.addWidget(titulo)
        lay.addWidget(QLabel("Tempo:"))
        lay.addWidget(self.spin_bpm)
        lay.addWidget(self.spin_compas)
        lay.addWidget(self.chk_sonido_metronomo)
        lay.addStretch(1)
        lay.addWidget(self.lbl_pulso)
        lay.addWidget(self.btn_metro)
        return panel

    def _texto_musical_seguro(self, texto: str) -> str:
        """Evita cuadrados por fuentes que no soportan símbolos musicales Unicode.

        Las claves reales se dibujan en la pizarra con QPainter; en etiquetas de texto
        usamos nombres legibles para que en Debian/Windows/macOS no aparezcan glifos vacíos.
        """
        t = str(texto or "")
        reemplazos = {
            "𝄞": "Clave de Sol",
            "𝄢": "Clave de Fa",
            "♩": "negra",
            "♪": "corchea",
            "♫": "corcheas",
            "♬": "semicorcheas",
        }
        for a, b in reemplazos.items():
            t = t.replace(a, b)
        return t

    def _siguiente_ejercicio(self):
        siguiente = (self.resumen.get("siguiente", {}) or {})
        siguiente_id = siguiente.get("id", "")
        ejercicios = self.datos.get("ejercicios", []) or []
        for ejercicio in ejercicios:
            if ejercicio.get("id") == siguiente_id:
                return ejercicio
        return ejercicios[0] if ejercicios else {}

    def _texto_guia_simbolos(self):
        teoria = self.datos.get("teoria", []) or []
        if teoria:
            partes = []
            for bloque in teoria[:4]:
                if isinstance(bloque, dict):
                    partes.append(f"{bloque.get('titulo', '')}: {bloque.get('texto', '')}")
            return "\n".join([p for p in partes if p])
        return (
            "Qué es: escritura de la música. Para qué sirve: leer, estudiar y corregir. "
            "Símbolos: pentagrama, clave, nota, figura, silencio, compás, barra, alteración y digitación. "
            "Cómo se lee: clave, compás, posición de la nota, duración, pulso, mano y dedo."
        )

    def _texto_profesor_completo(self):
        nombre = "alumno"
        try:
            nombre = getattr(self.controlador, '_nombre_alumno')()
        except Exception:
            pass
        sig = self._siguiente_ejercicio() or {}
        descripcion = str(self.datos.get('descripcion', '') or '').strip()
        teoria = self.datos.get('teoria', []) or []
        teoria_txt = []
        for bloque in teoria[:4]:
            if isinstance(bloque, dict):
                teoria_txt.append(f"{bloque.get('titulo', '')}: {bloque.get('texto', '')}")
        partes = [
            f"{nombre}, esta pantalla de Partitura está pensada para empezar desde cero, sin dar por supuesto que ya conoces teoría musical.",
            descripcion,
            "Primero vamos a entender el idioma de la partitura y después lo llevamos al piano con ejercicios prácticos corregidos.",
            "\n".join(teoria_txt),
        ]
        if sig:
            partes.append(
                f"Ahora mismo la lección activa es '{sig.get('titulo', 'sin título')}'. "
                f"Su objetivo es: {sig.get('objetivo', '')}"
            )
            if sig.get('lectura_visual'):
                partes.append(
                    "Lectura visual clave de esta lección: " + str(sig.get('lectura_visual'))
                )
            notas = sig.get('notas', []) or []
            if notas:
                partes.append("Notas implicadas: " + ", ".join(map(str, notas)) + ".")
            simbolos = sig.get('simbolos', []) or []
            if simbolos:
                partes.append("Símbolos que debes reconocer: " + ", ".join(map(str, simbolos)) + ".")
            figuras = sig.get('figuras', []) or []
            if figuras:
                partes.append("Figuras o conceptos que debes reconocer: " + ", ".join(map(str, figuras)) + ".")
            interpretacion = str(sig.get('interpretacion', '') or '').strip()
            if interpretacion:
                partes.append("Cómo se interpreta: " + interpretacion)
            dig = sig.get('digitacion', []) or []
            if dig:
                partes.append("Digitación asociada: " + ", ".join(map(str, dig)) + ".")
            pasos = sig.get('pasos', []) or []
            if pasos:
                pasos_txt = []
                for i, paso in enumerate(pasos, 1):
                    pasos_txt.append(f"{i}. {paso}")
                partes.append(
                    "Te lo explico en detalle, siguiendo lo que aparece en el bloque inferior:\n" + "\n".join(pasos_txt)
                )
            criterio = str(sig.get('criterio', '') or '').strip()
            if criterio:
                partes.append("Qué quiero comprobar como profesor: " + criterio)
        partes.append(
            "Cómo usar esta pantalla: primero escucha la explicación de la clase; después mira el pentagrama y los símbolos; luego pulsa Ir a práctica para que el profesor cargue el ejercicio en el piano global y te corrija nota por nota."
        )
        partes.append(
            "Si pulsas 'Leer clase', el profesor de la derecha debe leer y explicar tanto el resumen superior como el contenido pedagógico de debajo."
        )
        return self._texto_musical_seguro("\n\n".join([p for p in partes if p]))

    def texto_para_profesor(self):
        return self._texto_profesor_completo()

    def _card_ejercicio(self, ejercicio: dict, completado: bool, actual: bool):
        card = QFrame()
        if completado:
            card.setObjectName("CardLecturaCompletada")
            icono = "✓"
        elif actual:
            card.setObjectName("CardLecturaActual")
            icono = "▶"
        else:
            card.setObjectName("CardLectura")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        titulo = QLabel(f"{icono} {ejercicio.get('titulo', 'Ejercicio')}")
        titulo.setObjectName("TituloEjercicioLectura")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        meta = QLabel(
            f"Nivel: {ejercicio.get('nivel', '—')} · Clave: {ejercicio.get('clave', '—')} · "
            f"Compás: {ejercicio.get('compas', '—')} · Tempo: {ejercicio.get('tempo', '—')} bpm"
        )
        meta.setWordWrap(True)
        lay.addWidget(meta)

        visual = QLabel(self._texto_musical_seguro(ejercicio.get("lectura_visual", "")))
        visual.setObjectName("PentagramaVisual")
        visual.setWordWrap(True)
        lay.addWidget(visual)

        objetivo = QLabel("Objetivo: " + ejercicio.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        notas_lista = ejercicio.get("notas", [])
        if notas_lista:
            notas = QLabel("Notas: " + " · ".join(notas_lista))
            notas.setWordWrap(True)
            lay.addWidget(notas)

        figuras_lista = ejercicio.get("figuras", [])
        if figuras_lista:
            figuras = QLabel("Figuras: " + " · ".join(map(str, figuras_lista)))
            figuras.setWordWrap(True)
            lay.addWidget(figuras)

        simbolos_lista = ejercicio.get("simbolos", [])
        if simbolos_lista:
            simbolos = QLabel("Símbolos: " + " · ".join(map(str, simbolos_lista)))
            simbolos.setWordWrap(True)
            lay.addWidget(simbolos)

        interpretacion_txt = str(ejercicio.get("interpretacion", "") or "").strip()
        if interpretacion_txt:
            interpretacion = QLabel("Cómo se interpreta: " + interpretacion_txt)
            interpretacion.setWordWrap(True)
            lay.addWidget(interpretacion)

        practica_lista = ejercicio.get("practica_notas", []) or []
        if practica_lista:
            resumen_practica = []
            for item in practica_lista:
                if isinstance(item, dict):
                    resumen_practica.append(str(item.get("nombre") or item.get("nota") or "silencio"))
            if resumen_practica:
                practica = QLabel("Práctica: " + " · ".join(resumen_practica))
                practica.setWordWrap(True)
                lay.addWidget(practica)

        digitacion_lista = ejercicio.get("digitacion", [])
        if digitacion_lista:
            digitacion = QLabel("Digitación: " + " · ".join(digitacion_lista))
            digitacion.setWordWrap(True)
            lay.addWidget(digitacion)

        pasos = ejercicio.get("pasos", [])
        if pasos:
            pasos_lbl = QLabel("Pasos: " + " · ".join(pasos))
            pasos_lbl.setWordWrap(True)
            lay.addWidget(pasos_lbl)

        criterio = QLabel("Criterio: " + ejercicio.get("criterio", ""))
        criterio.setWordWrap(True)
        lay.addWidget(criterio)
        return card

    def _toggle_metronomo(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_metro.setText("Iniciar metrónomo")
            return
        self.pulso_actual = 0
        intervalo = max(80, int(60000 / max(1, int(self.spin_bpm.value()))))
        self.timer.start(intervalo)
        self.btn_metro.setText("Detener metrónomo")
        self._tick_metronomo()

    def _tick_metronomo(self):
        compas = max(1, int(self.spin_compas.value()))
        self.pulso_actual = (self.pulso_actual % compas) + 1
        self.lbl_pulso.setText(str(self.pulso_actual))
        acento = self.pulso_actual == 1
        if acento:
            self.lbl_pulso.setStyleSheet("background:#DCFCE7; border:2px solid #16A34A; border-radius:14px;")
        else:
            self.lbl_pulso.setStyleSheet("background:#FFFFFF; border:2px solid #94A3B8; border-radius:14px;")
        if self.chk_sonido_metronomo.isChecked():
            self._sonar_click_metronomo(acento)

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
