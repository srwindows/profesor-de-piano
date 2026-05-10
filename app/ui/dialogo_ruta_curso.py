from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QScrollArea, QWidget, QProgressBar
)
from PySide6.QtCore import Qt



class DialogoRutaCurso(QDialog):
    """Mapa curricular general.

    Códigos:
    - 10: abrir teoría.
    - 20: continuar práctica/ruta.
    - 30: abrir plan personalizado.
    """

    def __init__(self, estado_ruta: dict, avatar_tipo: str = "chica", parent=None):
        super().__init__(parent)
        self.estado_ruta = estado_ruta or {}
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self.setWindowTitle("Ruta curricular del curso")
        self.resize(980, 720)
        self.setMinimumSize(820, 600)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(self.estado_ruta.get("titulo", "Ruta curricular"))
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setObjectName("TituloRutaCurso")
        raiz.addWidget(titulo)

        cab = QFrame()
        cab.setObjectName("CabeceraRutaCurso")
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(10, 10, 10, 10)
        cab_lay.setSpacing(10)
        # El avatar visual se muestra solo en el panel derecho global.

        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMaximumHeight(150)
        self.txt_resumen.setPlainText(self._texto_resumen())
        cab_lay.addWidget(self.txt_resumen, 1)
        raiz.addWidget(cab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)
        for nivel in self.estado_ruta.get("niveles", []):
            lay.addWidget(self._card_nivel(nivel))
        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        fila = QHBoxLayout()
        self.btn_leer = QPushButton("▶ Leer ruta")
        self.btn_teoria = QPushButton("Ir a teoría")
        self.btn_plan = QPushButton("Abrir Plan alumno")
        self.btn_continuar = QPushButton("Continuar ruta")
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_leer.clicked.connect(lambda: None)
        self.btn_teoria.clicked.connect(lambda: self.done(10))
        self.btn_plan.clicked.connect(lambda: self.done(30))
        self.btn_continuar.clicked.connect(lambda: self.done(20))
        self.btn_cerrar.clicked.connect(self.reject)
        for b in (self.btn_leer, self.btn_teoria, self.btn_plan, self.btn_continuar, self.btn_cerrar):
            b.setMinimumHeight(36)
            b.setCursor(Qt.PointingHandCursor)
        fila.addWidget(self.btn_leer)
        fila.addStretch(1)
        fila.addWidget(self.btn_teoria)
        fila.addWidget(self.btn_plan)
        fila.addWidget(self.btn_continuar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

        self.setStyleSheet("""
            #TituloRutaCurso {
                font-size: 26px;
                font-weight: bold;
                color: #0f3768;
            }
            #CabeceraRutaCurso, #CardNivelRuta {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
            }
            #CardNivelActual {
                background: #eff6ff;
                border: 2px solid #2563eb;
                border-radius: 12px;
            }
            #CardNivelCompletado {
                background: #ecfdf5;
                border: 2px solid #16a34a;
                border-radius: 12px;
            }
            #CardNivelBloqueado {
                background: #f1f5f9;
                border: 1px dashed #94a3b8;
                border-radius: 12px;
            }
            #TituloNivelRuta {
                font-size: 18px;
                font-weight: bold;
                color: #0f172a;
            }
            #EstadoNivelRuta {
                font-weight: bold;
                color: #334155;
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
        siguiente = self.estado_ruta.get("siguiente", {})
        return (
            f"{self.estado_ruta.get('descripcion', '')}\n\n"
            f"Nivel de práctica actual: {self.estado_ruta.get('nivel_actual', 'sin evaluar')}.\n"
            f"Siguiente bloque recomendado: {siguiente.get('titulo', 'Sin definir')}.\n\n"
            "Esta pantalla es el mapa grande del curso: teoría, práctica, exámenes, repaso y plan personalizado."
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

    def _card_nivel(self, nivel: dict):
        estado = nivel.get("estado", "bloqueado")
        card = QFrame()
        if estado == "actual":
            card.setObjectName("CardNivelActual")
            icono = "▶"
        elif estado == "completado":
            card.setObjectName("CardNivelCompletado")
            icono = "✓"
        elif estado == "bloqueado":
            card.setObjectName("CardNivelBloqueado")
            icono = "🔒"
        else:
            card.setObjectName("CardNivelRuta")
            icono = "○"

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        titulo = QLabel(f"{icono} {nivel.get('titulo', 'Nivel')}")
        titulo.setObjectName("TituloNivelRuta")
        titulo.setWordWrap(True)
        lay.addWidget(titulo)

        estado_lbl = QLabel(f"Estado: {estado}")
        estado_lbl.setObjectName("EstadoNivelRuta")
        lay.addWidget(estado_lbl)

        objetivo = QLabel("Objetivo: " + nivel.get("objetivo", ""))
        objetivo.setWordWrap(True)
        lay.addWidget(objetivo)

        modulos = nivel.get("modulos", [])
        if modulos:
            mods = QLabel("Módulos: " + " · ".join(modulos))
            mods.setWordWrap(True)
            lay.addWidget(mods)

        desbloquea = QLabel("Desbloquea: " + nivel.get("desbloquea", ""))
        desbloquea.setWordWrap(True)
        lay.addWidget(desbloquea)

        if int(nivel.get("plan_porcentaje", 0) or 0) > 0:
            barra = QProgressBar()
            barra.setRange(0, 100)
            barra.setValue(int(nivel.get("plan_porcentaje", 0)))
            barra.setFormat("Plan personalizado del bloque: %p%")
            lay.addWidget(barra)

        return card
