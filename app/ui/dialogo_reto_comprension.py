from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt


class DialogoRetoComprension(QDialog):
    """Reto breve antes de marcar un punto como superado."""

    def __init__(self, reto: dict, punto_numero: int = 1, parent=None):
        super().__init__(parent)
        self.reto = reto or {}
        self.punto_numero = punto_numero
        self.respuesta = ""
        self.es_correcta = False
        self.setWindowTitle("Reto de comprensión")
        self.resize(760, 520)
        self.setMinimumSize(680, 460)
        self._crear_ui()


    def _texto_radio_compatible(self, texto: str, ancho: int = 72) -> str:
        """QRadioButton no tiene setWordWrap en PySide6.

        Para mantener legibilidad, insertamos saltos de línea suaves sin alterar
        la respuesta real, que se guarda aparte en la propiedad `respuesta_original`.
        """
        texto = str(texto or "")
        palabras = texto.split()
        if not palabras:
            return texto
        lineas = []
        actual = ""
        for palabra in palabras:
            candidato = (actual + " " + palabra).strip()
            if len(candidato) > ancho and actual:
                lineas.append(actual)
                actual = palabra
            else:
                actual = candidato
        if actual:
            lineas.append(actual)
        return "\n".join(lineas)

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(f"Reto de comprensión · Punto {self.punto_numero}")
        titulo.setObjectName("TituloReto")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraReto")
        cab_lay = QVBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        pregunta = QLabel(self.reto.get("pregunta", "¿Has entendido este punto?"))
        pregunta.setWordWrap(True)
        pregunta.setObjectName("PreguntaReto")
        cab_lay.addWidget(pregunta)
        raiz.addWidget(cab)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)

        for i, opcion in enumerate(self.reto.get("opciones", [])):
            opcion_original = str(opcion or "")
            rb = QRadioButton(self._texto_radio_compatible(opcion_original))
            rb.setProperty("respuesta_original", opcion_original)
            rb.setToolTip(opcion_original)
            rb.setMinimumHeight(42 if len(opcion_original) > 72 else 34)
            self.grupo.addButton(rb, i)
            raiz.addWidget(rb)

        self.txt_explicacion = QTextEdit()
        self.txt_explicacion.setReadOnly(True)
        self.txt_explicacion.setMaximumHeight(115)
        self.txt_explicacion.setPlaceholderText("La explicación aparecerá aquí si hace falta.")
        raiz.addWidget(self.txt_explicacion)

        fila = QHBoxLayout()
        self.btn_comprobar = QPushButton("Comprobar")
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_comprobar.clicked.connect(self._comprobar)
        self.btn_cancelar.clicked.connect(self.reject)

        for b in (self.btn_comprobar, self.btn_cancelar):
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)

        fila.addStretch(1)
        fila.addWidget(self.btn_comprobar)
        fila.addWidget(self.btn_cancelar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloReto {
                font-size: 22px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraReto {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #PreguntaReto {
                font-size: 16px;
                font-weight: bold;
                color: #0f172a;
            }
            QRadioButton {
                font-size: 15px;
                padding: 6px;
            }
            QTextEdit {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 8px;
                background: white;
            }
            QPushButton {
                padding: 7px 14px;
                border-radius: 7px;
                background: #2563eb;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)

    def _comprobar(self):
        boton = self.grupo.checkedButton()
        if boton is None:
            self.txt_explicacion.setPlainText("Elige una respuesta antes de comprobar.")
            return

        self.respuesta = str(boton.property("respuesta_original") or boton.text()).strip()
        correcta = str(self.reto.get("correcta", "")).strip()
        self.es_correcta = self.respuesta == correcta

        if self.es_correcta:
            self.txt_explicacion.setPlainText(
                "Correcto. " + str(self.reto.get("explicacion", "Puedes avanzar."))
            )
            self.accept()
        else:
            self.txt_explicacion.setPlainText(
                "Todavía no. La respuesta correcta es:\n\n"
                f"{correcta}\n\n"
                + str(self.reto.get("explicacion", "Lee otra vez el punto antes de avanzar."))
            )
