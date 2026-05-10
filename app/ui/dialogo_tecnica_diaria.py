from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt



class DialogoTecnicaDiaria(QDialog):
    """Diálogo de rutina técnica diaria.

    Códigos:
    - 10: marcar siguiente rutina completada.
    - 20: ir a práctica.
    - 30: reiniciar rutina.
    """

    def __init__(self, datos: dict, resumen: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.datos = datos or {}
        self.resumen = resumen or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.setWindowTitle("Técnica diaria")
        self.resize(940, 700)
        self.setMinimumSize(780, 580)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(self.datos.get("titulo", "Técnica diaria"))
        titulo.setObjectName("TituloTecnicaDiaria")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraTecnicaDiaria")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        bloque = QVBoxLayout()
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(135)
        self.txt_resumen.setPlainText(self._texto_resumen())
        bloque.addWidget(self.txt_resumen)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(self.resumen.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Técnica: {self.resumen.get('completadas', 0)}/{self.resumen.get('total', 0)} rutinas · %p%"
        )
        bloque.addWidget(self.barra)
        cab_lay.addLayout(bloque, 1)
        raiz.addWidget(cab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)

        completadas = int(self.resumen.get("completadas", 0) or 0)
        for i, rutina in enumerate(self.datos.get("rutinas", [])):
            lay.addWidget(self._card_rutina(rutina, completada=i < completadas, actual=i == completadas))

        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer rutina")
        self.btn_completar = QPushButton("Marcar siguiente completada")
        self.btn_practica = QPushButton("Ir a práctica")
        self.btn_reiniciar = QPushButton("Reiniciar técnica")
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_leer.clicked.connect(lambda: None)
        self.btn_completar.clicked.connect(lambda: self.done(10))
        self.btn_practica.clicked.connect(lambda: self.done(20))
        self.btn_reiniciar.clicked.connect(lambda: self.done(30))
        self.btn_cerrar.clicked.connect(self.reject)
        for btn in (self.btn_leer, self.btn_completar, self.btn_practica, self.btn_reiniciar, self.btn_cerrar):
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_completar)
        fila.addWidget(self.btn_practica)
        fila.addStretch(1)
        fila.addWidget(self.btn_reiniciar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloTecnicaDiaria {
                font-size: 26px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraTecnicaDiaria, #CardRutinaTecnica {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #CardRutinaActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardRutinaCompletada {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloRutinaTecnica {
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

    def _texto_resumen(self):
        sig = self.resumen.get("siguiente", {}) or {}
        return (
            f"{self.datos.get('descripcion', '')}\n\n"
            f"Siguiente rutina: {sig.get('titulo', 'Sin rutina')}.\n"
            f"Duración: {sig.get('duracion_min', '—')} min · Tempo: {sig.get('tempo_min', '—')}–{sig.get('tempo_max', '—')} bpm.\n"
            f"Objetivo: {sig.get('objetivo', '')}\n\n"
            "Haz esta rutina antes de la práctica. Debe sonar lento, claro y sin tensión."
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

    def _card_rutina(self, rutina: dict, completada: bool, actual: bool):
        card = QFrame()
        if completada:
            card.setObjectName("CardRutinaCompletada")
            icono = "✓"
        elif actual:
            card.setObjectName("CardRutinaActual")
            icono = "▶"
        else:
            card.setObjectName("CardRutinaTecnica")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        titulo = QLabel(f"{icono} {rutina.get('titulo', 'Rutina')}")
        titulo.setObjectName("TituloRutinaTecnica")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        meta = QLabel(
            f"Nivel: {rutina.get('nivel', '—')} · Duración: {rutina.get('duracion_min', '—')} min · "
            f"Tempo: {rutina.get('tempo_min', '—')}–{rutina.get('tempo_max', '—')} bpm"
        )
        meta.setWordWrap(True)
        lay.addWidget(meta)

        objetivo = QLabel("Objetivo: " + rutina.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        patron = QLabel("Patrón: " + rutina.get("patron", ""))
        patron.setWordWrap(True)
        lay.addWidget(patron)

        notas = QLabel("Notas: " + rutina.get("notas_referencia", ""))
        notas.setWordWrap(True)
        lay.addWidget(notas)

        criterio = QLabel("Criterio: " + rutina.get("criterio", ""))
        criterio.setWordWrap(True)
        lay.addWidget(criterio)

        instrucciones = rutina.get("instrucciones", [])
        if instrucciones:
            texto = QLabel("Pasos: " + " · ".join(instrucciones))
            texto.setWordWrap(True)
            lay.addWidget(texto)

        return card
