from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt



class DialogoRepertorio(QDialog):
    """Repertorio progresivo guiado.

    Códigos:
    - 10: marcar siguiente pieza trabajada.
    - 20: ir a práctica.
    - 30: reiniciar repertorio.
    - 40: leer/abrir plan.
    """

    def __init__(self, datos: dict, resumen: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.datos = datos or {}
        self.resumen = resumen or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.setWindowTitle("Repertorio progresivo")
        self.resize(980, 740)
        self.setMinimumSize(820, 600)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(self.datos.get("titulo", "Repertorio progresivo"))
        titulo.setObjectName("TituloRepertorio")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraRepertorio")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        bloque = QVBoxLayout()
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(145)
        self.txt_resumen.setPlainText(self._texto_resumen())
        bloque.addWidget(self.txt_resumen)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(int(self.resumen.get("porcentaje", 0)))
        self.barra.setFormat(
            f"Repertorio: {self.resumen.get('trabajadas', 0)}/{self.resumen.get('total', 0)} piezas · %p%"
        )
        bloque.addWidget(self.barra)
        cab_lay.addLayout(bloque, 1)
        raiz.addWidget(cab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)

        trabajadas = int(self.resumen.get("trabajadas", 0) or 0)
        siguiente_id = (self.resumen.get("siguiente", {}) or {}).get("id", "")
        for i, pieza in enumerate(self.datos.get("piezas", [])):
            lay.addWidget(self._card_pieza(pieza, completada=i < trabajadas, actual=pieza.get("id") == siguiente_id))

        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer repertorio")
        self.btn_marcar = QPushButton("Marcar pieza trabajada")
        self.btn_practica = QPushButton("Ir a práctica")
        self.btn_plan = QPushButton("Plan alumno")
        self.btn_reiniciar = QPushButton("Reiniciar repertorio")
        self.btn_cerrar = QPushButton("Cerrar")

        self.btn_leer.clicked.connect(lambda: None)
        self.btn_marcar.clicked.connect(lambda: self.done(10))
        self.btn_practica.clicked.connect(lambda: self.done(20))
        self.btn_plan.clicked.connect(lambda: self.done(40))
        self.btn_reiniciar.clicked.connect(lambda: self.done(30))
        self.btn_cerrar.clicked.connect(self.reject)

        for b in (self.btn_leer, self.btn_marcar, self.btn_practica, self.btn_plan, self.btn_reiniciar, self.btn_cerrar):
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)

        fila.addWidget(self.btn_leer)
        fila.addWidget(self.btn_marcar)
        fila.addWidget(self.btn_practica)
        fila.addWidget(self.btn_plan)
        fila.addStretch(1)
        fila.addWidget(self.btn_reiniciar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloRepertorio {
                font-size: 26px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraRepertorio, #CardPiezaRepertorio {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #CardPiezaActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardPiezaCompletada {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #TituloPiezaRepertorio {
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
        fases = sig.get("fases", [])
        fases_txt = " · ".join(fases[:3]) if fases else "Sin fases."
        return (
            f"{self.datos.get('descripcion', '')}\n\n"
            f"Siguiente pieza: {sig.get('titulo', 'Sin pieza')}.\n"
            f"Tempo: {sig.get('tempo', '—')} bpm · Compás: {sig.get('compas', '—')} · Duración: {sig.get('duracion_estudio_min', '—')} min.\n"
            f"Objetivo: {sig.get('objetivo', '')}\n"
            f"Primeras fases: {fases_txt}"
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

    def _card_pieza(self, pieza: dict, completada: bool, actual: bool):
        card = QFrame()
        if completada:
            card.setObjectName("CardPiezaCompletada")
            icono = "✓"
        elif actual:
            card.setObjectName("CardPiezaActual")
            icono = "▶"
        else:
            card.setObjectName("CardPiezaRepertorio")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(5)

        titulo = QLabel(f"{icono} {pieza.get('titulo', 'Pieza')}")
        titulo.setObjectName("TituloPiezaRepertorio")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        meta = QLabel(
            f"Nivel: {pieza.get('nivel', '—')} · Tempo: {pieza.get('tempo', '—')} bpm · "
            f"Compás: {pieza.get('compas', '—')} · Estudio: {pieza.get('duracion_estudio_min', '—')} min"
        )
        meta.setWordWrap(True)
        lay.addWidget(meta)

        objetivo = QLabel("Objetivo: " + pieza.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        md = QLabel("Mano derecha: " + " ".join(pieza.get("mano_derecha", [])))
        md.setWordWrap(True)
        lay.addWidget(md)

        mi = QLabel("Mano izquierda: " + " ".join(pieza.get("mano_izquierda", [])))
        mi.setWordWrap(True)
        lay.addWidget(mi)

        dig = QLabel(f"Digitación MD: {pieza.get('digitacion_md', '')} · MI: {pieza.get('digitacion_mi', '')}")
        dig.setWordWrap(True)
        lay.addWidget(dig)

        fases = pieza.get("fases", [])
        if fases:
            fases_lbl = QLabel("Fases: " + " · ".join(fases))
            fases_lbl.setWordWrap(True)
            lay.addWidget(fases_lbl)

        midi_path = pieza.get("midi_path") or pieza.get("archivo_midi", "")
        if midi_path:
            midi_lbl = QLabel("Archivo MIDI: " + midi_path)
            midi_lbl.setWordWrap(True)
            lay.addWidget(midi_lbl)

        criterio = QLabel("Criterio: " + pieza.get("criterio", ""))
        criterio.setWordWrap(True)
        lay.addWidget(criterio)

        return card
