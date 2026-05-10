from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt



class DialogoSesionDiaria(QDialog):
    """Sesión diaria inteligente.

    Códigos:
    - 10: abrir paso recomendado.
    - 20: marcar siguiente completado.
    - 30: reiniciar sesión.
    - 40: abrir plan alumno.
    """

    def __init__(self, sesion: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.sesion = sesion or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.setWindowTitle("Sesión diaria inteligente")
        self.resize(960, 720)
        self.setMinimumSize(800, 600)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(self.sesion.get("titulo", "Sesión diaria inteligente"))
        titulo.setObjectName("TituloSesionDiaria")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraSesionDiaria")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        bloque = QVBoxLayout()
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(135)
        self.txt_resumen.setPlainText(self.sesion.get("resumen", ""))
        bloque.addWidget(self.txt_resumen)

        progreso = self.sesion.get("progreso", {})
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(progreso.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Sesión: {progreso.get('completados', 0)}/{progreso.get('total', 0)} pasos · %p%"
        )
        bloque.addWidget(self.barra)
        cab_lay.addLayout(bloque, 1)
        raiz.addWidget(cab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)
        for paso in self.sesion.get("pasos", []):
            lay.addWidget(self._card_paso(paso))
        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer sesión")
        self.btn_abrir = QPushButton("Abrir paso recomendado")
        self.btn_completar = QPushButton("Marcar siguiente completado")
        self.btn_plan = QPushButton("Plan alumno")
        self.btn_reiniciar = QPushButton("Reiniciar sesión")
        self.btn_cerrar = QPushButton("Cerrar")

        self.btn_leer.clicked.connect(lambda: None)
        self.btn_abrir.clicked.connect(lambda: self.done(10))
        self.btn_completar.clicked.connect(lambda: self.done(20))
        self.btn_plan.clicked.connect(lambda: self.done(40))
        self.btn_reiniciar.clicked.connect(lambda: self.done(30))
        self.btn_cerrar.clicked.connect(self.reject)

        for b in (self.btn_leer, self.btn_abrir, self.btn_completar, self.btn_plan, self.btn_reiniciar, self.btn_cerrar):
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)

        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_abrir)
        fila.addWidget(self.btn_completar)
        fila.addWidget(self.btn_plan)
        fila.addStretch(1)
        fila.addWidget(self.btn_reiniciar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloSesionDiaria {
                font-size: 26px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraSesionDiaria, #CardPasoSesion {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #CardPasoSesionActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardPasoSesionCompletado {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloPasoSesion {
                font-size: 18px;
                font-weight: bold;
                color: #0f172a;
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
        estado = paso.get("estado", "pendiente")
        actual = self.sesion.get("siguiente", {}).get("id") == paso.get("id")
        card = QFrame()
        if estado == "completado":
            card.setObjectName("CardPasoSesionCompletado")
            icono = "✓"
        elif actual:
            card.setObjectName("CardPasoSesionActual")
            icono = "▶"
        else:
            card.setObjectName("CardPasoSesion")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        titulo = QLabel(f"{icono} {paso.get('titulo', 'Paso')}")
        titulo.setObjectName("TituloPasoSesion")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        meta = QLabel(
            f"Tipo: {paso.get('tipo', '—')} · Duración: {paso.get('duracion_min', '—')} min · Estado: {estado}"
        )
        meta.setWordWrap(True)
        lay.addWidget(meta)

        objetivo = QLabel("Objetivo: " + paso.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        accion = QLabel("Acción: " + paso.get("accion", ""))
        accion.setWordWrap(True)
        lay.addWidget(accion)
        return card
