from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFrame, QGridLayout
)
from PySide6.QtCore import Qt



class DialogoEstadoAlumno(QDialog):
    """Panel de seguimiento pedagógico del alumno.

    Resume progreso, racha, fallos frecuentes, repasos pendientes y
    recomendación del profesor. No modifica datos: solo muestra diagnóstico.
    """

    def __init__(
        self,
        nombre_alumno: str,
        tratamiento: str,
        avatar_tipo: str,
        resumen: dict,
        plan_repaso: str,
        parent=None,
    ):
        super().__init__(parent)
        self.nombre_alumno = nombre_alumno or "alumno"
        self.tratamiento = tratamiento or "masculino"
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.resumen = resumen or {}
        self.plan_repaso = plan_repaso or ""
        self.setWindowTitle("Estado del alumno")
        self.resize(880, 680)
        self.setMinimumSize(760, 560)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(f"Estado de {self.nombre_alumno}")
        titulo.setObjectName("TituloDialogoEstadoAlumno")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cabecera = QFrame()
        cabecera.setObjectName("PanelEstadoCabecera")
        cab_lay = QHBoxLayout(cabecera)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        self.txt_profesor = QTextEdit()
        self.txt_profesor.setReadOnly(True)
        self.txt_profesor.setMaximumHeight(160)
        self.txt_profesor.setPlainText(self._texto_profesor())
        cab_lay.addWidget(self.txt_profesor, 1)
        raiz.addWidget(cabecera)

        grid_frame = QFrame()
        grid_frame.setObjectName("PanelEstadoMetricas")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        metricas = [
            ("Nivel actual", self.resumen.get("nivel_actual", "sin evaluar")),
            ("Ejercicios superados", self.resumen.get("ejercicios_superados", 0)),
            ("Ejercicios fallados", self.resumen.get("ejercicios_fallados", 0)),
            ("Tasa de acierto", f"{self.resumen.get('tasa_acierto', 0)}%"),
            ("Racha actual", self.resumen.get("racha", 0)),
            ("Repasos pendientes", self.resumen.get("repasos_pendientes", 0)),
            ("Lecciones guiadas", self.resumen.get("lecciones_guiadas", "0/0")),
            ("Exámenes aprobados", self.resumen.get("examenes_aprobados", 0)),
        ]

        for i, (k, v) in enumerate(metricas):
            card = self._tarjeta_metrica(k, str(v))
            grid.addWidget(card, i // 4, i % 4)

        raiz.addWidget(grid_frame)

        self.txt_detalle = QTextEdit()
        self.txt_detalle.setReadOnly(True)
        self.txt_detalle.setPlainText(self._texto_detalle())
        raiz.addWidget(self.txt_detalle, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer diagnóstico")
        self.btn_repaso = QPushButton("Iniciar Repaso IA")
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_leer.clicked.connect(lambda: None)
        self.btn_repaso.clicked.connect(self.accept)
        self.btn_cerrar.clicked.connect(self.reject)
        for btn in (self.btn_leer, self.btn_repaso, self.btn_cerrar):
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
        fila.addWidget(self.btn_leer)
        fila.addStretch(1)
        fila.addWidget(self.btn_repaso)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloDialogoEstadoAlumno {
                font-size: 24px;
                font-weight: bold;
                color: #0f3768;
            }
            #PanelEstadoCabecera, #PanelEstadoMetricas {
                background: #f8fafc;
                border: 1px solid #94a3b8;
                border-radius: 12px;
            }
            #TarjetaMetrica {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
            }
            #TituloMetrica {
                color: #334155;
                font-size: 12px;
                font-weight: bold;
            }
            #ValorMetrica {
                color: #0f172a;
                font-size: 22px;
                font-weight: bold;
            }
            QTextEdit {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 8px;
                background: #ffffff;
            }
            QPushButton {
                padding: 7px 12px;
                border-radius: 7px;
                background: #2563eb;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)

    def _tarjeta_metrica(self, titulo: str, valor: str):
        card = QFrame()
        card.setObjectName("TarjetaMetrica")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lbl_t = QLabel(titulo)
        lbl_t.setObjectName("TituloMetrica")
        lbl_t.setAlignment(Qt.AlignCenter)
        lbl_v = QLabel(valor)
        lbl_v.setObjectName("ValorMetrica")
        lbl_v.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        return card

    def _texto_profesor(self) -> str:
        pendientes = int(self.resumen.get("repasos_pendientes", 0) or 0)
        tasa = int(self.resumen.get("tasa_acierto", 0) or 0)
        if pendientes > 0:
            prioridad = (
                "Ahora mi prioridad es ayudarte a cerrar los puntos que han quedado pendientes. "
                "No significa que vayas mal: significa que ya tengo datos para enseñarte mejor."
            )
        elif tasa >= 80:
            prioridad = (
                "Tu progreso va bien. Mi recomendación es mantener práctica corta y constante, "
                "sin saltarte las bases."
            )
        else:
            prioridad = (
                "Todavía conviene reforzar algunos conceptos. Vamos a ir con calma, mirando errores y repitiendo lo necesario."
            )
        return (
            f"{self.nombre_alumno}, este panel resume cómo vas. "
            f"Lo importante no es solo acertar, sino saber qué hay que repasar y por qué. {prioridad}"
        )

    def _texto_detalle(self) -> str:
        lineas = []
        lineas.append("DIAGNÓSTICO DEL PROFESOR")
        lineas.append("")
        lineas.append(f"Nivel actual: {self.resumen.get('nivel_actual', 'sin evaluar')}")
        lineas.append(f"Tasa de acierto: {self.resumen.get('tasa_acierto', 0)}%")
        lineas.append(f"Racha actual: {self.resumen.get('racha', 0)}")
        lineas.append(f"Repasos pendientes: {self.resumen.get('repasos_pendientes', 0)}")
        lineas.append("")

        fallos = self.resumen.get("fallos_frecuentes", [])
        if fallos:
            lineas.append("FALLOS FRECUENTES")
            for item in fallos:
                lineas.append(f"- {item.get('titulo', item.get('id', 'ejercicio'))}: {item.get('fallos', 0)} fallo(s)")
        else:
            lineas.append("FALLOS FRECUENTES")
            lineas.append("- No hay fallos acumulados todavía.")
        lineas.append("")

        recomendacion = self.resumen.get("recomendacion", "")
        if recomendacion:
            lineas.append("RECOMENDACIÓN")
            lineas.append(recomendacion)
            lineas.append("")

        lineas.append(self.plan_repaso)
        return "\n".join(lineas)

    def texto_para_profesor(self):
        partes = []
        for attr in ("txt_profesor", "txt_resumen", "txt_detalle"):
            try:
                widget = getattr(self, attr, None)
                if widget is not None and hasattr(widget, "toPlainText"):
                    texto = widget.toPlainText().strip()
                    if texto:
                        partes.append(texto)
            except Exception:
                pass
        try:
            for label in self.findChildren(QLabel):
                texto = label.text().strip()
                if texto and len(texto) > 2:
                    partes.append(texto)
        except Exception:
            pass
        salida = []
        vistos = set()
        for texto in partes:
            clave = " ".join(texto.split()).lower()
            if clave and clave not in vistos:
                vistos.add(clave)
                salida.append(texto)
        return "\n\n".join(salida)
