from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

class AvatarWidget(QWidget):
    def __init__(self, tipo="chica", parent=None):
        super().__init__(parent)
        self.tipo = tipo if tipo in {"chico", "chica"} else "chica"
        self.hablando = False
        self.boca_abierta = False
        self.setMinimumSize(150, 170)
        self.setMaximumHeight(210)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.timer = QTimer(self)
        self.timer.setInterval(170)
        self.timer.timeout.connect(self._tick_boca)

    def set_tipo(self, tipo: str):
        self.tipo = tipo if tipo in {"chico", "chica"} else "chica"
        self.update()

    def iniciar_habla(self):
        self.hablando = True
        self.boca_abierta = True
        self.timer.start()
        self.update()

    def hablar(self, duracion_ms=None):
        self.iniciar_habla()
        if duracion_ms is not None:
            QTimer.singleShot(max(300, int(duracion_ms)), self.parar_habla)

    def parar_habla(self):
        self.hablando = False
        self.boca_abierta = False
        self.timer.stop()
        self.update()

    def _tick_boca(self):
        if self.hablando:
            self.boca_abierta = not self.boca_abierta
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(4, 4, -4, -4)

        fondo = QColor("#f2f6ff") if self.tipo == "chica" else QColor("#eef7f1")
        borde = QColor("#6d82a8") if self.tipo == "chica" else QColor("#5f8a70")
        p.setBrush(QBrush(fondo))
        p.setPen(QPen(borde, 2))
        p.drawRoundedRect(r, 14, 14)

        cx = r.center().x()
        cara_y = r.top() + 22
        piel = QColor("#f0c7a7")
        pelo = QColor("#4b2c20") if self.tipo == "chica" else QColor("#2e2e32")
        camisa = QColor("#7e9bd8") if self.tipo == "chica" else QColor("#6da884")

        # Pelo/fondo de cabeza
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(pelo))
        if self.tipo == "chica":
            p.drawEllipse(cx - 43, cara_y - 4, 86, 94)
            p.drawRoundedRect(cx - 48, cara_y + 35, 96, 70, 24, 24)
        else:
            p.drawEllipse(cx - 42, cara_y - 6, 84, 74)

        # Cara
        p.setBrush(QBrush(piel))
        p.setPen(QPen(QColor("#8b624d"), 1))
        p.drawEllipse(cx - 36, cara_y + 8, 72, 76)

        # Ojos
        p.setBrush(QBrush(QColor("#222")))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - 19, cara_y + 40, 7, 7)
        p.drawEllipse(cx + 12, cara_y + 40, 7, 7)

        # Cejas
        p.setPen(QPen(QColor("#4a3429"), 2))
        p.drawLine(cx - 24, cara_y + 33, cx - 10, cara_y + 31)
        p.drawLine(cx + 10, cara_y + 31, cx + 24, cara_y + 33)

        # Boca animada
        p.setPen(QPen(QColor("#8e3030"), 2))
        p.setBrush(QBrush(QColor("#b84848")))
        if self.boca_abierta:
            p.drawEllipse(cx - 11, cara_y + 60, 22, 13)
        else:
            p.drawArc(cx - 13, cara_y + 55, 26, 15, 200 * 16, 140 * 16)

        # Cuerpo
        p.setPen(QPen(QColor("#3f4c68"), 1))
        p.setBrush(QBrush(camisa))
        p.drawRoundedRect(cx - 46, cara_y + 92, 92, 48, 18, 18)

        # Texto
        p.setPen(QColor("#20242d"))
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        p.setFont(f)
        nombre = "Profesora IA" if self.tipo == "chica" else "Profesor IA"
        p.drawText(r.left(), r.bottom() - 28, r.width(), 20, Qt.AlignCenter, nombre)
        f.setBold(False)
        f.setPointSize(8)
        p.setFont(f)
        estado = "hablando" if self.hablando else "listo"
        p.drawText(r.left(), r.bottom() - 13, r.width(), 14, Qt.AlignCenter, estado)
