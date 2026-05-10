from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt



class DialogoPlanPersonalizado(QDialog):
    """Plan personalizado con seguimiento.

    Códigos de salida:
    - 10: ir a teoría.
    - 20: ir a práctica.
    - 30: marcar siguiente paso como completado.
    - 40: reiniciar seguimiento.
    """

    def __init__(self, plan: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.plan = plan or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.setWindowTitle("Plan personalizado del alumno")
        self.resize(900, 700)
        self.setMinimumSize(780, 580)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel("Plan personalizado")
        titulo.setObjectName("TituloPlanPersonalizado")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraPlanPersonalizado")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        bloque_resumen = QVBoxLayout()
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(135)
        self.txt_resumen.setPlainText(self._texto_resumen())
        bloque_resumen.addWidget(self.txt_resumen)

        progreso = self.plan.get("progreso", {})
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(progreso.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Plan: {progreso.get('completados', 0)}/{progreso.get('total', 0)} pasos · %p%"
        )
        bloque_resumen.addWidget(self.barra)
        cab_lay.addLayout(bloque_resumen, 1)
        raiz.addWidget(cab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)

        pasos = list(self.plan.get("pasos", []))
        if not pasos:
            aviso = QLabel("No hay pasos todavía. Haz primero la evaluación inicial.")
            aviso.setWordWrap(True)
            lay.addWidget(aviso)
        for paso in pasos:
            lay.addWidget(self._card_paso(paso))

        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer plan")
        self.btn_completar = QPushButton("Marcar siguiente paso completado")
        self.btn_reiniciar = QPushButton("Reiniciar seguimiento")
        self.btn_teoria = QPushButton("Ir a teoría")
        self.btn_practica = QPushButton("Ir a práctica")
        self.btn_cerrar = QPushButton("Cerrar")

        self.btn_leer.clicked.connect(lambda: None)
        self.btn_completar.clicked.connect(lambda: self.done(30))
        self.btn_reiniciar.clicked.connect(lambda: self.done(40))
        self.btn_teoria.clicked.connect(lambda: self.done(10))
        self.btn_practica.clicked.connect(lambda: self.done(20))
        self.btn_cerrar.clicked.connect(self.reject)

        for btn in (
            self.btn_leer, self.btn_completar, self.btn_reiniciar,
            self.btn_teoria, self.btn_practica, self.btn_cerrar
        ):
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)

        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_completar)
        fila.addWidget(self.btn_reiniciar)
        fila.addStretch(1)
        fila.addWidget(self.btn_teoria)
        fila.addWidget(self.btn_practica)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloPlanPersonalizado {
                font-size: 24px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraPlanPersonalizado, #PasoPlanPersonalizado {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #PasoCompletado {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloPasoPlan {
                font-size: 18px;
                font-weight: bold;
                color: #0f172a;
            }
            #MetaPasoPlan {
                color: #475569;
                font-weight: bold;
            }
            #EstadoPasoPendiente {
                color: #b45309;
                font-weight: bold;
            }
            #EstadoPasoCompletado {
                color: #15803d;
                font-weight: bold;
            }
            QTextEdit {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 8px;
                background: white;
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

    def _texto_resumen(self) -> str:
        progreso = self.plan.get("progreso", {})
        siguiente = self.plan.get("siguiente_paso", "Plan completado")
        return (
            f"{self.plan.get('resumen', 'Aún no hay plan personalizado.')}\n\n"
            f"Progreso: {progreso.get('completados', 0)}/{progreso.get('total', 0)} pasos.\n"
            f"Siguiente paso: {siguiente}."
        )

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

    def _card_paso(self, paso: dict):
        completado = paso.get("estado") == "completado"
        card = QFrame()
        card.setObjectName("PasoCompletado" if completado else "PasoPlanPersonalizado")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        icono = "✓" if completado else "○"
        titulo = QLabel(f"{icono} {paso.get('orden', '?')}. {paso.get('titulo', 'Paso')}")
        titulo.setObjectName("TituloPasoPlan")
        titulo.setWordWrap(True)

        estado = QLabel("Estado: completado" if completado else "Estado: pendiente")
        estado.setObjectName("EstadoPasoCompletado" if completado else "EstadoPasoPendiente")
        estado.setWordWrap(True)

        meta = QLabel(f"Tipo: {paso.get('tipo', '—')} · Prioridad: {paso.get('prioridad', 'media')}")
        meta.setObjectName("MetaPasoPlan")
        meta.setWordWrap(True)
        motivo = QLabel("Motivo: " + paso.get("motivo", "—"))
        motivo.setWordWrap(True)
        accion = QLabel("Acción: " + paso.get("accion", "—"))
        accion.setWordWrap(True)

        lay.addWidget(titulo)
        lay.addWidget(estado)
        lay.addWidget(meta)
        lay.addWidget(motivo)
        lay.addWidget(accion)
        return card
