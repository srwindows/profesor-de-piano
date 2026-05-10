from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QMovie

from app.ui.avatar_widget import AvatarWidget


class DialogoImagenTeoria(QDialog):
    """Visor ampliado de material visual con explicación pedagógica.

    Se usa desde la teoría visual: el alumno pulsa una imagen/GIF y se abre
    una vista grande, con texto del profesor y botones de comprensión.
    """

    def __init__(self, ruta: str | Path, titulo: str, explicacion: str, parent=None, avatar_tipo: str = "chica"):
        super().__init__(parent)
        self.ruta = Path(ruta)
        self.titulo = titulo or self.ruta.name
        self.explicacion = explicacion or ""
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        self._movie = None

        self.setWindowTitle(f"Profesor virtual — {self.titulo}")
        self.resize(1080, 780)
        self.setMinimumSize(880, 620)
        self._crear_ui()

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        lbl_titulo = QLabel(self.titulo)
        lbl_titulo.setObjectName("TituloDialogoImagenTeoria")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(lbl_titulo)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(12)

        scroll_img = QScrollArea()
        scroll_img.setWidgetResizable(True)
        scroll_img.setObjectName("ScrollImagenTeoriaGrande")
        cont_img = QWidget()
        lay_img = QVBoxLayout(cont_img)
        lay_img.setContentsMargins(8, 8, 8, 8)
        lay_img.setSpacing(8)

        self.lbl_imagen = QLabel()
        self.lbl_imagen.setAlignment(Qt.AlignCenter)
        self.lbl_imagen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_imagen.setMinimumSize(620, 430)
        self._cargar_material_visual()
        lay_img.addWidget(self.lbl_imagen, 1)

        lbl_nombre = QLabel(str(self.ruta.name))
        lbl_nombre.setAlignment(Qt.AlignCenter)
        lbl_nombre.setObjectName("NombreImagenTeoriaGrande")
        lay_img.addWidget(lbl_nombre)
        scroll_img.setWidget(cont_img)
        cuerpo.addWidget(scroll_img, 3)

        panel_profesor = QVBoxLayout()
        panel_profesor.setSpacing(8)
        lbl_prof = QLabel("Profesor virtual")
        lbl_prof.setObjectName("TituloProfesorDialogo")
        lbl_prof.setAlignment(Qt.AlignCenter)
        panel_profesor.addWidget(lbl_prof)

        self.avatar_dialogo = AvatarWidget(self.avatar_tipo)
        self.avatar_dialogo.setMinimumSize(126, 148)
        self.avatar_dialogo.setMaximumHeight(170)
        panel_profesor.addWidget(self.avatar_dialogo, 0, Qt.AlignHCenter)

        self.txt_explicacion = QTextEdit()
        self.txt_explicacion.setReadOnly(True)
        self.txt_explicacion.setObjectName("TextoProfesorImagen")
        self.txt_explicacion.setPlainText(self.explicacion)
        panel_profesor.addWidget(self.txt_explicacion, 1)

        self.btn_leer = QPushButton("▶ Leer explicación")
        self.btn_entendido = QPushButton("Sí, lo he entendido")
        self.btn_no_entendido = QPushButton("No, explícamelo otra vez")
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.close)
        self.btn_leer.clicked.connect(lambda: self.avatar_dialogo.hablar(6500))
        self.btn_entendido.clicked.connect(lambda: self.avatar_dialogo.hablar(2800))
        self.btn_no_entendido.clicked.connect(lambda: self.avatar_dialogo.hablar(6500))
        for b in (self.btn_leer, self.btn_entendido, self.btn_no_entendido, self.btn_cerrar):
            b.setMinimumHeight(34)
            b.setCursor(Qt.PointingHandCursor)
        panel_profesor.addWidget(self.btn_leer)
        panel_profesor.addWidget(self.btn_entendido)
        panel_profesor.addWidget(self.btn_no_entendido)
        panel_profesor.addWidget(self.btn_cerrar)

        cuerpo.addLayout(panel_profesor, 1)
        raiz.addLayout(cuerpo, 1)

        self.setStyleSheet("""
            QDialog { background: #f8fafc; }
            QLabel#TituloDialogoImagenTeoria {
                font-size: 24px;
                font-weight: 800;
                color: #0f3a67;
                padding: 8px;
            }
            QLabel#NombreImagenTeoriaGrande {
                font-size: 13px;
                font-weight: 700;
                color: #334155;
            }
            QLabel#TituloProfesorDialogo {
                font-size: 18px;
                font-weight: 800;
                color: #0f3a67;
            }
            QTextEdit#TextoProfesorImagen {
                background: white;
                border: 1px solid #bfd0df;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                line-height: 1.35;
            }
            QPushButton {
                border: 1px solid #94a3b8;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 700;
                background: #e2e8f0;
                color: #0f172a;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)

    def _cargar_material_visual(self):
        if not self.ruta.exists():
            self.lbl_imagen.setText("No se encontró el archivo visual.")
            return
        suf = self.ruta.suffix.lower()
        if suf == ".gif":
            movie = QMovie(str(self.ruta))
            if movie.isValid():
                movie.setScaledSize(QSize(850, 560))
                self.lbl_imagen.setMovie(movie)
                movie.start()
                self._movie = movie
                return
            self.lbl_imagen.setText("No se pudo cargar el GIF.")
            return
        if suf in {".md", ".txt"}:
            try:
                texto = self.ruta.read_text(encoding="utf-8")
            except Exception:
                texto = "No se pudo leer el material de teoría."
            self.lbl_imagen.setText(texto[:12000])
            self.lbl_imagen.setWordWrap(True)
            self.lbl_imagen.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            return
        pix = QPixmap(str(self.ruta))
        if pix.isNull():
            self.lbl_imagen.setText("No se pudo cargar la imagen.")
            return
        self.lbl_imagen.setPixmap(pix.scaled(850, 560, Qt.KeepAspectRatio, Qt.SmoothTransformation))
