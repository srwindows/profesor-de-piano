from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Signal, Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont


class PianoVirtual(QWidget):
    """Piano virtual interactivo de 88 teclas: A0 - C8.

    Versión v1.8.7: limpieza visual del teclado.
    - Se eliminan los números/octavas dentro de las teclas.
    - El nombre de la nota se dibuja más abajo para mayor legibilidad.
    - Se añaden marcas profesionales de grupo/octava bajo el teclado
      mediante una línea con su etiqueta (C1, C2, C3...).
    """

    nota_pulsada = Signal(str)
    nota_soltada = Signal(str)

    NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def __init__(self, octava_base=3, parent=None):
        super().__init__(parent)
        self.setObjectName("PianoVirtual88Real")
        self.mostrar_nombres = True
        self.altura = 150
        self.teclas = self._crear_88_teclas()
        self.teclas_pulsadas = set()
        self.teclas_docente = set()
        self._rects_blancas = {}
        self._rects_negras = {}
        self._grupos_octava = []
        self._nota_mouse = None
        self.setMouseTracking(True)
        self.setMinimumHeight(self.altura)
        self.setMaximumHeight(self.altura)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def reconstruir(self, octava_base=3):
        self.update()

    def aplicar_configuracion(self, mostrar_nombres=True, altura=150):
        self.mostrar_nombres = bool(mostrar_nombres)
        try:
            altura = int(altura)
        except Exception:
            altura = 150
        self.altura = max(105, min(240, altura))
        self.setMinimumHeight(self.altura)
        self.setMaximumHeight(self.altura)
        self.updateGeometry()
        self.update()

    def _crear_88_teclas(self):
        teclas = []
        teclas.extend([("A", 0, False), ("A#", 0, True), ("B", 0, False)])
        for octava in range(1, 8):
            for n in self.NOTAS:
                teclas.append((n, octava, "#" in n))
        teclas.append(("C", 8, False))
        return teclas

    def _nombre_nota(self, nombre, octava):
        return f"{nombre}{octava}"

    def _texto_nota(self, nota):
        if not self.mostrar_nombres:
            return ""
        base = nota[:-1]
        mapa = {
            "C": "Do", "C#": "Do#", "D": "Re", "D#": "Re#", "E": "Mi", "F": "Fa",
            "F#": "Fa#", "G": "Sol", "G#": "Sol#", "A": "La", "A#": "La#", "B": "Si",
        }
        return mapa.get(base, base)

    def _calcular_rects(self):
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        margen_x = 4.0
        margen_y = 5.0
        margen_inferior_grupos = max(18.0, min(28.0, h * 0.16))
        ancho_total = max(1.0, w - margen_x * 2.0)
        alto_total = max(1.0, h - margen_y * 2.0 - margen_inferior_grupos)
        ancho_blanca = ancho_total / 52.0
        alto_blanca = alto_total
        alto_negra = alto_total * 0.64
        ancho_negra = max(4.0, ancho_blanca * 0.58)

        self._rects_blancas = {}
        self._rects_negras = {}
        self._grupos_octava = []

        blanca_idx = 0
        ultima_blanca_idx_por_octava = {}
        for nombre, octava, negra in self.teclas:
            nota = self._nombre_nota(nombre, octava)
            if not negra:
                x = margen_x + blanca_idx * ancho_blanca
                self._rects_blancas[nota] = QRectF(x, margen_y, ancho_blanca, alto_blanca)
                ultima_blanca_idx_por_octava[(nombre, octava)] = blanca_idx
                blanca_idx += 1

        for nombre, octava, negra in self.teclas:
            if not negra:
                continue
            nota = self._nombre_nota(nombre, octava)
            if octava == 0:
                idx_izq = 0
            else:
                base_izq = nombre.replace("#", "")
                idx_izq = ultima_blanca_idx_por_octava.get((base_izq, octava))
                if idx_izq is None:
                    continue
            x_centro = margen_x + (idx_izq + 1.0) * ancho_blanca
            x = x_centro - ancho_negra / 2.0
            self._rects_negras[nota] = QRectF(x, margen_y, ancho_negra, alto_negra)

        # Grupos de octava: línea inferior desde Cn hasta Bn y etiqueta centrada.
        for octava in range(1, 8):
            inicio = self._rects_blancas.get(f"C{octava}")
            fin = self._rects_blancas.get(f"B{octava}")
            if not inicio or not fin:
                continue
            x1 = inicio.left() + 2.0
            x2 = fin.right() - 2.0
            self._grupos_octava.append((x1, x2, f"C{octava}"))
        # Grupo final C8 solo sobre su Do final.
        final_c8 = self._rects_blancas.get("C8")
        if final_c8:
            self._grupos_octava.append((final_c8.left() + 2.0, final_c8.right() - 2.0, "C8"))

    def paintEvent(self, event):
        self._calcular_rects()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#dbeafe"))

        # Blancas: marfil claro, bordes finos y sombreado inferior.
        for nota, rect in self._rects_blancas.items():
            activa = nota in self.teclas_pulsadas
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            docente = nota in self.teclas_docente
            if activa:
                grad.setColorAt(0.0, QColor("#bfdbfe"))
                grad.setColorAt(1.0, QColor("#60a5fa"))
                borde = QColor("#1d4ed8")
            elif docente:
                grad.setColorAt(0.0, QColor("#fde68a"))
                grad.setColorAt(0.55, QColor("#fef3c7"))
                grad.setColorAt(1.0, QColor("#f59e0b"))
                borde = QColor("#d97706")
            else:
                grad.setColorAt(0.0, QColor("#fffdf4"))
                grad.setColorAt(0.55, QColor("#f8fafc"))
                grad.setColorAt(1.0, QColor("#d6d3d1"))
                borde = QColor("#374151")
            p.setBrush(QBrush(grad))
            p.setPen(QPen(borde, 0.8))
            p.drawRoundedRect(rect, 2.0, 2.0)

        # Línea horizontal superior como labio del teclado real.
        p.setPen(QPen(QColor("#111827"), 2.0))
        p.drawLine(4, 5, self.width() - 4, 5)

        # Negras: superpuestas, estrechas y más cortas.
        for nota, rect in self._rects_negras.items():
            activa = nota in self.teclas_pulsadas
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            docente = nota in self.teclas_docente
            if activa:
                grad.setColorAt(0.0, QColor("#1e40af"))
                grad.setColorAt(1.0, QColor("#60a5fa"))
                borde = QColor("#93c5fd")
            elif docente:
                grad.setColorAt(0.0, QColor("#f59e0b"))
                grad.setColorAt(0.45, QColor("#b45309"))
                grad.setColorAt(1.0, QColor("#78350f"))
                borde = QColor("#fde68a")
            else:
                grad.setColorAt(0.0, QColor("#3f3f46"))
                grad.setColorAt(0.45, QColor("#111827"))
                grad.setColorAt(1.0, QColor("#020617"))
                borde = QColor("#020617")
            p.setBrush(QBrush(grad))
            p.setPen(QPen(borde, 1.0))
            p.drawRoundedRect(rect, 2.5, 2.5)

        # Nombres de notas: solo en blancas, más abajo y más legibles.
        if self.mostrar_nombres:
            font = QFont(self.font())
            font.setPointSize(max(5, min(9, int(self.height() / 20))))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#475569"))
            for nota, rect in self._rects_blancas.items():
                if rect.width() < 12:
                    continue
                texto_rect = rect.adjusted(0, int(rect.height() * 0.76), 0, -2)
                p.drawText(texto_rect, Qt.AlignHCenter | Qt.AlignVCenter, self._texto_nota(nota))

        # Marcas de grupo/octava debajo del teclado.
        if self._grupos_octava:
            y_base = max(r.bottom() for r in self._rects_blancas.values()) + 8.0
            p.setPen(QPen(QColor("#64748b"), 1.4))
            label_font = QFont(self.font())
            label_font.setPointSize(max(6, min(8, int(self.height() / 24))))
            label_font.setBold(True)
            p.setFont(label_font)
            for x1, x2, etiqueta in self._grupos_octava:
                # línea horizontal del grupo
                p.drawLine(QPointF(x1, y_base), QPointF(x2, y_base))
                # pequeñas marcas en extremos
                p.drawLine(QPointF(x1, y_base - 3), QPointF(x1, y_base + 3))
                p.drawLine(QPointF(x2, y_base - 3), QPointF(x2, y_base + 3))
                # etiqueta centrada bajo la línea
                text_rect = QRectF(x1, y_base + 2, max(20.0, x2 - x1), 14.0)
                p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, etiqueta)

    def _nota_en_posicion(self, pos):
        for nota, rect in self._rects_negras.items():
            if rect.contains(pos):
                return nota
        for nota, rect in self._rects_blancas.items():
            if rect.contains(pos):
                return nota
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self._calcular_rects()
        nota = self._nota_en_posicion(event.position())
        if nota:
            self._nota_mouse = nota
            self._presionar_nota(nota)
            event.accept()
            return
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        self._calcular_rects()
        nota = self._nota_en_posicion(event.position())
        if nota != self._nota_mouse:
            if self._nota_mouse:
                self._soltar_nota(self._nota_mouse)
            self._nota_mouse = nota
            if nota:
                self._presionar_nota(nota)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mouseReleaseEvent(event)
        nota = self._nota_mouse
        self._nota_mouse = None
        if nota:
            # Soltar una tecla solo emite nota_soltada. Nunca debe lanzar
            # nota_pulsada ni reactivar sonido.
            self._soltar_nota(nota)
        event.accept()

    def leaveEvent(self, event):
        if self._nota_mouse:
            self._soltar_nota(self._nota_mouse)
            self._nota_mouse = None
        super().leaveEvent(event)

    def _presionar_nota(self, nota):
        if nota not in self.teclas_pulsadas:
            self.teclas_pulsadas.add(nota)
            self.update()
            self.nota_pulsada.emit(nota)

    def _soltar_nota(self, nota):
        if nota in self.teclas_pulsadas:
            self.teclas_pulsadas.remove(nota)
            self.update()
            self.nota_soltada.emit(nota)

    def resaltar_notas_docente(self, notas):
        """Resalta notas desde la pizarra del profesor sin emitir sonido."""
        nuevas = set()
        for nota in notas or []:
            n = str(nota).strip()
            if not n:
                continue
            # Permite DO4/Do4/C4 o notas ya en formato interno.
            mapa = {
                "DO": "C", "RE": "D", "MI": "E", "FA": "F", "SOL": "G", "LA": "A", "SI": "B",
                "DO#": "C#", "RE#": "D#", "FA#": "F#", "SOL#": "G#", "LA#": "A#",
            }
            if len(n) >= 2 and n[-1].isdigit():
                base = n[:-1].upper().replace("Ó", "O")
                octava = n[-1]
                nuevas.add(mapa.get(base, base) + octava)
            else:
                nuevas.add(n)
        self.teclas_docente = nuevas
        self.update()

    def limpiar_resaltado_docente(self):
        self.teclas_docente.clear()
        self.update()

    def nota_externa_on(self, nota):
        if nota not in self.teclas_pulsadas:
            self.teclas_pulsadas.add(nota)
            self.update()

    def nota_externa_off(self, nota):
        if nota in self.teclas_pulsadas:
            self.teclas_pulsadas.remove(nota)
            self.update()
