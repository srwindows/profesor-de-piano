from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt


class DialogoAlumno(QDialog):
    """Primer diálogo obligatorio de identificación del alumno.

    Se muestra al arrancar para que el profesor virtual sepa con quién habla,
    cómo llamarle y si debe tratarle en masculino, femenino o neutro.
    """

    def __init__(self, perfil_actual=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Identificación del alumno")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._crear_ui(perfil_actual)

    def _crear_ui(self, perfil_actual):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        titulo = QLabel("Antes de empezar, dime con quién estoy hablando")
        titulo.setObjectName("TituloDialogoAlumno")
        titulo.setAlignment(Qt.AlignCenter)
        lay.addWidget(titulo)

        texto = QLabel(
            "El profesor virtual usará este nombre para dirigirse a ti durante las clases, "
            "las explicaciones, la teoría visual y la práctica. También guardará el trato "
            "en un archivo JSON para recordarlo en los próximos arranques."
        )
        texto.setWordWrap(True)
        lay.addWidget(texto)

        caja = QFrame()
        caja.setObjectName("CajaDialogoAlumno")
        form = QVBoxLayout(caja)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(8)

        form.addWidget(QLabel("Nombre del alumno:"))
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Ejemplo: Javi")
        if perfil_actual and getattr(perfil_actual, "nombre", ""):
            self.input_nombre.setText(perfil_actual.nombre)
        form.addWidget(self.input_nombre)

        form.addWidget(QLabel("Tratamiento:"))
        self.combo_trato = QComboBox()
        self.combo_trato.addItem("Masculino — alumno / preparado", "masculino")
        self.combo_trato.addItem("Femenino — alumna / preparada", "femenino")
        self.combo_trato.addItem("Neutro — estudiante", "neutro")
        actual = getattr(perfil_actual, "tratamiento", "masculino") if perfil_actual else "masculino"
        idx = self.combo_trato.findData(actual)
        if idx >= 0:
            self.combo_trato.setCurrentIndex(idx)
        form.addWidget(self.combo_trato)
        lay.addWidget(caja)

        aviso = QLabel("Este paso es obligatorio para que el avatar pueda hablarte de forma cercana y coherente.")
        aviso.setWordWrap(True)
        aviso.setObjectName("AvisoDialogoAlumno")
        lay.addWidget(aviso)

        fila = QHBoxLayout()
        fila.addStretch(1)
        self.btn_aceptar = QPushButton("Confirmar alumno")
        self.btn_aceptar.setMinimumHeight(38)
        self.btn_aceptar.clicked.connect(self._validar)
        fila.addWidget(self.btn_aceptar)
        lay.addLayout(fila)

        self.setStyleSheet("""
            #TituloDialogoAlumno { font-size: 22px; font-weight: bold; color: #0f3768; }
            #CajaDialogoAlumno { background: #f8fafc; border: 1px solid #93c5fd; border-radius: 12px; }
            #AvisoDialogoAlumno { color: #475569; }
            QLineEdit, QComboBox { padding: 7px; border: 1px solid #94a3b8; border-radius: 6px; }
            QPushButton { background: #2563EB; color: white; font-weight: bold; border-radius: 8px; padding: 8px 14px; }
            QPushButton:hover { background: #1d4ed8; }
        """)

    def _validar(self):
        if not self.input_nombre.text().strip():
            self.input_nombre.setFocus()
            self.input_nombre.setPlaceholderText("Escribe tu nombre para continuar")
            return
        self.accept()

    def datos(self):
        return self.input_nombre.text().strip(), self.combo_trato.currentData()
