import math
import random
import time
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


@dataclass
class Particula:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: QColor
    vida: float
    edad: float = 0.0
    rot: float = 0.0
    vrot: float = 0.0
    tipo: str = "rect"
    gravedad: float = 520.0


class CelebracionOverlay(QWidget):
    """Capa visual para celebraciones pedagógicas.

    Se coloca encima de toda la interfaz central y se activa cuando el alumno
    supera una lección, reto o nivel. No bloquea permanentemente la UI: dura
    pocos segundos y se oculta sola.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()
        self.particulas: list[Particula] = []
        self.tipo = "leccion"
        self.titulo = ""
        self.subtitulo = ""
        self._inicio = time.monotonic()
        self._ultimo = self._inicio
        self._duracion = 2.8
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    def start(self, tipo: str = "leccion", titulo: str = "", alumno: str = ""):
        self.tipo = tipo or "leccion"
        self.titulo = titulo or "Lección superada"
        if self.tipo == "nivel":
            self.subtitulo = f"¡Enhorabuena, {alumno}! Has completado una meta importante." if alumno else "¡Nivel completado!"
            self._duracion = 4.4
        elif self.tipo == "reto":
            self.subtitulo = f"Buen trabajo, {alumno}. Has resuelto el reto." if alumno else "Reto superado."
            self._duracion = 3.4
        else:
            self.subtitulo = f"Muy bien, {alumno}. Continuamos con la siguiente lección." if alumno else "Lección superada."
            self._duracion = 2.9
        self._inicio = time.monotonic()
        self._ultimo = self._inicio
        self.particulas.clear()
        self._crear_particulas_iniciales()
        self.setGeometry(self.parentWidget().rect() if self.parentWidget() else self.geometry())
        self.show()
        self.raise_()
        self.timer.start()
        self.update()

    def _crear_particulas_iniciales(self):
        w = max(300, self.width() or 1200)
        h = max(250, self.height() or 800)
        if self.tipo == "nivel":
            cantidad = 260
        elif self.tipo == "reto":
            cantidad = 180
        else:
            cantidad = 120
        colores = [
            QColor("#2563EB"), QColor("#22C55E"), QColor("#F59E0B"), QColor("#EF4444"),
            QColor("#A855F7"), QColor("#EC4899"), QColor("#14B8A6"), QColor("#FDE047"),
        ]
        # Confeti/serpentinas desde la parte superior y laterales.
        for i in range(cantidad):
            desde_lateral = random.random() < 0.28
            if desde_lateral:
                izquierda = random.random() < 0.5
                x = -20 if izquierda else w + 20
                y = random.uniform(40, h * 0.55)
                vx = random.uniform(240, 560) * (1 if izquierda else -1)
                vy = random.uniform(-420, -80)
            else:
                x = random.uniform(0, w)
                y = random.uniform(-80, 80)
                vx = random.uniform(-180, 180)
                vy = random.uniform(40, 250)
            self.particulas.append(Particula(
                x=x, y=y, vx=vx, vy=vy,
                size=random.uniform(5, 14),
                color=random.choice(colores),
                vida=random.uniform(1.8, self._duracion + 0.7),
                rot=random.uniform(0, 360),
                vrot=random.uniform(-420, 420),
                tipo=random.choice(["rect", "circle", "star", "ribbon"]),
                gravedad=random.uniform(180, 520),
            ))
        # Fuegos artificiales suaves para reto/nivel.
        if self.tipo in {"reto", "nivel"}:
            centros = [(w*0.22, h*0.25), (w*0.78, h*0.28)]
            if self.tipo == "nivel":
                centros += [(w*0.5, h*0.2), (w*0.35, h*0.42), (w*0.65, h*0.43)]
            for cx, cy in centros:
                for j in range(34):
                    ang = (math.tau * j / 34.0) + random.uniform(-0.08, 0.08)
                    vel = random.uniform(120, 330)
                    self.particulas.append(Particula(
                        x=cx, y=cy, vx=math.cos(ang)*vel, vy=math.sin(ang)*vel,
                        size=random.uniform(4, 9), color=random.choice(colores),
                        vida=random.uniform(1.0, 2.2), rot=random.uniform(0, 360),
                        vrot=random.uniform(-240, 240), tipo=random.choice(["circle", "star"]),
                        gravedad=random.uniform(60, 180),
                    ))

    def _tick(self):
        ahora = time.monotonic()
        dt = min(0.05, ahora - self._ultimo)
        self._ultimo = ahora
        elapsed = ahora - self._inicio
        vivas = []
        for p in self.particulas:
            p.edad += dt
            if p.edad < p.vida:
                p.vy += p.gravedad * dt
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.rot += p.vrot * dt
                # pequeña oscilación tipo serpentina
                if p.tipo == "ribbon":
                    p.x += math.sin((p.edad * 9.0) + p.size) * 1.8
                vivas.append(p)
        self.particulas = vivas
        if elapsed > self._duracion and not self.particulas:
            self.timer.stop()
            self.hide()
        elif elapsed > self._duracion + 0.4:
            self.timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        elapsed = time.monotonic() - self._inicio
        # Tarjeta central de logro.
        fade_in = min(1.0, elapsed / 0.25)
        fade_out = min(1.0, max(0.0, (self._duracion - elapsed) / 0.45))
        alpha = int(235 * min(fade_in, max(0.0, fade_out)))
        if alpha > 0:
            self._pintar_tarjeta(painter, alpha)
        # Partículas.
        for p in self.particulas:
            a = max(0.0, min(1.0, 1.0 - (p.edad / max(0.1, p.vida))))
            c = QColor(p.color)
            c.setAlpha(int(255 * a))
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(c))
            s = p.size
            if p.tipo == "circle":
                painter.drawEllipse(QPointF(0, 0), s, s)
            elif p.tipo == "star":
                painter.setPen(QPen(c, max(2, int(s/3))))
                painter.drawLine(QPointF(-s, 0), QPointF(s, 0))
                painter.drawLine(QPointF(0, -s), QPointF(0, s))
                painter.drawLine(QPointF(-s*0.7, -s*0.7), QPointF(s*0.7, s*0.7))
                painter.drawLine(QPointF(-s*0.7, s*0.7), QPointF(s*0.7, -s*0.7))
            elif p.tipo == "ribbon":
                painter.drawRoundedRect(int(-s*1.4), int(-s/2), int(s*2.8), int(s), 3, 3)
            else:
                painter.drawRect(int(-s/2), int(-s/2), int(s*1.2), int(s*0.75))
            painter.restore()

    def _pintar_tarjeta(self, painter: QPainter, alpha: int):
        w, h = self.width(), self.height()
        card_w = min(620, int(w * 0.58))
        card_h = 150 if self.tipo != "nivel" else 180
        x = int((w - card_w) / 2)
        y = int(max(90, h * 0.12))
        bg = QColor(255, 255, 255, alpha)
        border = QColor(37, 99, 235, alpha)
        painter.setPen(QPen(border, 4))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(x, y, card_w, card_h, 24, 24)
        icon = "🏆" if self.tipo == "nivel" else ("⭐" if self.tipo == "reto" else "✓")
        title = "Nivel completado" if self.tipo == "nivel" else ("Reto superado" if self.tipo == "reto" else "Lección superada")
        painter.setPen(QColor(15, 55, 105, alpha))
        f1 = QFont()
        f1.setPointSize(30 if self.tipo != "nivel" else 34)
        f1.setBold(True)
        painter.setFont(f1)
        painter.drawText(x + 28, y + 54, f"{icon} {title}")
        f2 = QFont()
        f2.setPointSize(17)
        f2.setBold(True)
        painter.setFont(f2)
        painter.setPen(QColor(37, 99, 235, alpha))
        painter.drawText(x + 32, y + 95, self.titulo[:62])
        f3 = QFont()
        f3.setPointSize(14)
        painter.setFont(f3)
        painter.setPen(QColor(31, 41, 55, alpha))
        painter.drawText(x + 32, y + 128, self.subtitulo[:88])
