from pathlib import Path
import random
import copy
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QStackedWidget, QFrame, QScrollArea, QSizePolicy, QGridLayout, QProgressBar, QTextEdit, QDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPixmap, QMovie

from app.config import ASSETS_DIR, DATA_DIR
from app.core.hanon import GestorHanon
from app.core.lecciones_guiadas import GestorLeccionesGuiadas
from app.ui.avatar_widget import AvatarWidget


class ClickableMediaLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class MiniEvaluacionNivel0Dialog(QDialog):
    """Diálogo de evaluación final del Nivel 0.

    A diferencia de la versión anterior, no pregunta una a una en ventanas sueltas:
    presenta todo el examen, corrige con informe y permite repetir sin cerrar.
    """

    def __init__(self, mini: dict, nombre_alumno: str = "alumno", parent=None, avatar_tipo: str = "chica"):
        super().__init__(parent)
        self.mini = mini or {}
        self.nombre_alumno = nombre_alumno or "alumno"
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"
        # v1.9.5: cada apertura de la examen global baraja el orden de
        # preguntas y también el orden de respuestas de cada pregunta.
        # La respuesta correcta se recalcula para que el informe siga siendo fiable.
        self.preguntas = self._preparar_preguntas_aleatorias(self.mini.get("preguntas", []))
        self.minimo = int(self.mini.get("minimo_aprobado", max(1, len(self.preguntas))))
        self.aciertos = 0
        self.aprobado = False
        self.detalle = []
        self.combos = []
        self.setWindowTitle(self.mini.get("titulo", "Examen global Nivel 0"))
        self.resize(760, 620)
        self._crear_ui()

    def _preparar_preguntas_aleatorias(self, preguntas_originales):
        """Devuelve preguntas barajadas y opciones barajadas.

        El JSON base mantiene las respuestas correctas por índice para que sea
        fácil editarlo a mano. En tiempo de ejecución no mostramos siempre el
        mismo examen: copiamos los datos, cambiamos el orden de las preguntas y
        mezclamos las opciones de cada una, actualizando ``respuesta_correcta``.
        """
        preguntas = []
        for indice_original, pregunta in enumerate(preguntas_originales, start=1):
            q = copy.deepcopy(pregunta)
            q["numero_original"] = indice_original
            opciones = list(q.get("opciones", []))
            correcto_original = int(q.get("respuesta_correcta", -1))
            correcta_txt = opciones[correcto_original] if 0 <= correcto_original < len(opciones) else None
            pares = list(enumerate(opciones))
            random.shuffle(pares)
            q["opciones"] = [texto for _, texto in pares]
            if correcta_txt is not None:
                q["respuesta_correcta"] = q["opciones"].index(correcta_txt)
            else:
                q["respuesta_correcta"] = -1
            preguntas.append(q)
        random.shuffle(preguntas)
        return preguntas

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(10)

        titulo = QLabel(self.mini.get("titulo", "Examen global final Nivel 0"))
        titulo.setObjectName("TituloSeccionInicio")
        titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(titulo)

        intro = QLabel(
            f"{self.nombre_alumno}, esta evaluación comprueba si puedes continuar con seguridad. "
            f"Necesitas {self.minimo}/{len(self.preguntas)} aciertos. Las preguntas y respuestas aparecen en orden aleatorio cada vez. "
            "Si fallas, no pasa nada: el profesor te dirá qué repasar."
        )
        intro.setWordWrap(True)
        raiz.addWidget(intro)

        panel_avatar = QFrame()
        panel_avatar.setObjectName("PanelAvatarMiniEvaluacion")
        lay_avatar = QHBoxLayout(panel_avatar)
        lay_avatar.setContentsMargins(8, 8, 8, 8)
        lay_avatar.setSpacing(8)
        self.avatar_mini = AvatarWidget(self.avatar_tipo)
        self.avatar_mini.setMinimumSize(112, 132)
        self.avatar_mini.setMaximumHeight(150)
        self.txt_avatar_mini = QTextEdit()
        self.txt_avatar_mini.setReadOnly(True)
        self.txt_avatar_mini.setMaximumHeight(120)
        self.txt_avatar_mini.setPlainText(
            f"{self.nombre_alumno}, estoy aquí contigo durante la evaluación. "
            "Lee cada pregunta con calma. No memorices posiciones: las preguntas y respuestas cambian de orden para comprobar comprensión real."
        )
        lay_avatar.addWidget(self.avatar_mini, 0)
        lay_avatar.addWidget(self.txt_avatar_mini, 1)
        raiz.addWidget(panel_avatar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(10)
        for i, pregunta in enumerate(self.preguntas, start=1):
            card = QFrame()
            card.setObjectName("TarjetaImagenTeoria")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            lbl = QLabel(f"{i}. {pregunta.get('pregunta', '')}")
            lbl.setWordWrap(True)
            lbl.setObjectName("TituloTarjetaInicio")
            combo = QComboBox()
            combo.setMinimumHeight(32)
            combo.addItem("— Elige una respuesta —", -1)
            for j, opcion in enumerate(pregunta.get("opciones", [])):
                combo.addItem(opcion, j)
            cl.addWidget(lbl)
            cl.addWidget(combo)
            lay.addWidget(card)
            self.combos.append(combo)
        lay.addStretch(1)
        scroll.setWidget(cont)
        raiz.addWidget(scroll, 1)

        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setObjectName("DescripcionImagenTeoria")
        raiz.addWidget(self.lbl_resultado)

        self.txt_informe = QTextEdit()
        self.txt_informe.setReadOnly(True)
        self.txt_informe.setMaximumHeight(150)
        self.txt_informe.setVisible(False)
        raiz.addWidget(self.txt_informe)

        fila = QHBoxLayout()
        self.btn_corregir = QPushButton("Corregir evaluación")
        self.btn_corregir.setMinimumHeight(38)
        self.btn_corregir.clicked.connect(self._corregir)
        self.btn_reintentar = QPushButton("Reintentar incorrectas")
        self.btn_reintentar.setMinimumHeight(38)
        self.btn_reintentar.setEnabled(False)
        self.btn_reintentar.clicked.connect(self._preparar_reintento)
        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.setMinimumHeight(38)
        self.btn_cerrar.clicked.connect(self.reject)
        fila.addWidget(self.btn_corregir)
        fila.addWidget(self.btn_reintentar)
        fila.addWidget(self.btn_cerrar)
        raiz.addLayout(fila)

    def _corregir(self):
        self.detalle = []
        self.aciertos = 0
        sin_responder = []
        for i, (pregunta, combo) in enumerate(zip(self.preguntas, self.combos), start=1):
            elegido = combo.currentData()
            if elegido is None or int(elegido) < 0:
                sin_responder.append(i)
                combo.setStyleSheet("QComboBox { border: 2px solid #F59E0B; }")
                continue
            correcto_idx = int(pregunta.get("respuesta_correcta", -1))
            correcto = int(elegido) == correcto_idx
            if correcto:
                self.aciertos += 1
                combo.setStyleSheet("QComboBox { border: 2px solid #16A34A; }")
            else:
                combo.setStyleSheet("QComboBox { border: 2px solid #DC2626; }")
            opciones = pregunta.get("opciones", [])
            correcta_txt = opciones[correcto_idx] if 0 <= correcto_idx < len(opciones) else "—"
            elegida_txt = combo.currentText()
            self.detalle.append({
                "numero": i,
                "numero_original": pregunta.get("numero_original", i),
                "pregunta": pregunta.get("pregunta", ""),
                "elegida": elegida_txt,
                "correcta": correcta_txt,
                "correcto": correcto,
                "explicacion": pregunta.get("explicacion", ""),
            })
        if sin_responder:
            self.lbl_resultado.setText(
                "Hay preguntas sin responder: " + ", ".join(map(str, sin_responder)) + ". Contesta todas antes de corregir."
            )
            return

        total = len(self.preguntas)
        self.aprobado = self.aciertos >= self.minimo
        informe = []
        for item in self.detalle:
            if item["correcto"]:
                informe.append(f"✓ {item['numero']}. Correcta: {item['correcta']}")
            else:
                informe.append(
                    f"✗ {item['numero']}. Tu respuesta: {item['elegida']}\n"
                    f"   Correcta: {item['correcta']}\n"
                    f"   Repaso: {item['explicacion']}"
                )
        self.txt_informe.setPlainText("\n\n".join(informe))
        self.txt_informe.setVisible(True)

        if self.aprobado:
            self.lbl_resultado.setText(
                f"Resultado: {self.aciertos}/{total}. Nivel superado. Pulsa 'Guardar evaluación superada' para guardar el resultado y continuar."
            )
            self.btn_corregir.setText("Guardar evaluación superada")
            self.btn_corregir.clicked.disconnect()
            self.btn_corregir.clicked.connect(self.accept)
            self.btn_reintentar.setEnabled(False)
            self.btn_cerrar.setEnabled(False)
            self.txt_avatar_mini.setPlainText(
                f"Excelente, {self.nombre_alumno}. Has aprobado la examen global. Eso significa que la base del nivel está clara."
            )
            self.avatar_mini.hablar(4500)
        else:
            self.lbl_resultado.setText(
                f"Resultado: {self.aciertos}/{total}. Aún no está superado. Revisa el informe y reintenta las preguntas marcadas en rojo."
            )
            self.btn_reintentar.setEnabled(True)
            self.txt_avatar_mini.setPlainText(
                f"No pasa nada, {self.nombre_alumno}. Mira el informe: ahí te digo exactamente qué debes repasar antes de repetir."
            )
            self.avatar_mini.hablar(5200)

    def _preparar_reintento(self):
        for item, combo in zip(self.detalle, self.combos):
            if item.get("correcto"):
                combo.setEnabled(False)
            else:
                combo.setCurrentIndex(0)
                combo.setEnabled(True)
                combo.setStyleSheet("QComboBox { border: 2px solid #2563EB; }")
        self.lbl_resultado.setText("Reintenta solo las preguntas marcadas. Las correctas quedan protegidas.")
        self.btn_reintentar.setEnabled(False)


class PantallaInicio(QWidget):
    """Pantalla de entrada v1.9.0.

    Diseño horizontal tipo panel principal. Incluye presentación del curso,
    teoría visual, práctica y lectura guiada por el avatar global.
    """

    iniciar_evaluacion = Signal()
    iniciar_manual = Signal(str)
    continuar = Signal()
    leer_texto = Signal(str)
    imagen_activada = Signal(str, str, str)  # ruta, título, explicación amplia
    celebracion = Signal(str, str)  # tipo, título
    abrir_hanon = Signal(str)

    def __init__(self, niveles: list[dict], parent=None):
        super().__init__(parent)
        self.niveles = niveles or []
        self.nombre_alumno = "alumno"
        self.tratamiento = "masculino"
        self.avatar_tipo = "chica"
        self._texto_actual = ""
        self.lecciones_guiadas = GestorLeccionesGuiadas()
        self.hanon = GestorHanon()
        self._leccion_actual = self.lecciones_guiadas.leccion_actual()
        self._crear_ui()
        self.mostrar_inicio()

    def set_avatar_tipo(self, avatar_tipo: str):
        self.avatar_tipo = avatar_tipo if avatar_tipo in {"chico", "chica"} else "chica"

    def set_perfil_alumno(self, nombre: str, tratamiento: str):
        self.nombre_alumno = (nombre or "alumno").strip()
        self.tratamiento = tratamiento or "masculino"
        self._actualizar_textos_personales()
        self.mostrar_inicio()

    def _nivel_guiado_disponible(self, nivel_id: str) -> bool:
        try:
            n = int(str(nivel_id).rsplit("_", 1)[1])
        except Exception:
            n = 0 if str(nivel_id) in {"inicial", "nivel_0"} else -1
        return n >= 0 and (DATA_DIR / f"lecciones_nivel_{n}.json").exists()

    def seleccionar_nivel_guiado(self, nivel_id: str | None):
        nivel_id = str(nivel_id or "nivel_0")
        if nivel_id == "inicial":
            nivel_id = "nivel_0"
        if not self._nivel_guiado_disponible(nivel_id):
            return False
        self.lecciones_guiadas.configurar_nivel(nivel_id)
        self._leccion_actual = self.lecciones_guiadas.leccion_actual()
        if hasattr(self, "combo_nivel_guiado"):
            idx = self.combo_nivel_guiado.findData(self.lecciones_guiadas.nivel_id)
            if idx >= 0 and self.combo_nivel_guiado.currentIndex() != idx:
                self.combo_nivel_guiado.blockSignals(True)
                self.combo_nivel_guiado.setCurrentIndex(idx)
                self.combo_nivel_guiado.blockSignals(False)
        self._actualizar_panel_leccion_guiada(emitir_texto=False, corregir_bloqueo=True)
        self._actualizar_galeria_materiales()
        return True

    def _cambiar_nivel_guiado_desde_combo(self):
        if hasattr(self, "combo_nivel_guiado"):
            self.seleccionar_nivel_guiado(self.combo_nivel_guiado.currentData())

    def _etiqueta_nivel_guiado(self) -> str:
        return self.lecciones_guiadas.etiqueta_nivel()

    def _alumno_o_alumna(self):
        if self.tratamiento == "femenino":
            return "alumna"
        if self.tratamiento == "masculino":
            return "alumno"
        return "estudiante"

    def _preparado_o_preparada(self):
        if self.tratamiento == "femenino":
            return "preparada"
        if self.tratamiento == "masculino":
            return "preparado"
        return "preparado/a"

    def _crear_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 14, 18, 14)
        raiz.setSpacing(10)

        cabecera = QFrame()
        cabecera.setObjectName("InicioCabecera")
        cab = QVBoxLayout(cabecera)
        cab.setContentsMargins(18, 12, 18, 12)
        cab.setSpacing(3)
        titulo = QLabel("Profesor de Piano IA")
        titulo.setObjectName("TituloPrincipalInicio")
        titulo.setAlignment(Qt.AlignCenter)
        self.subtitulo = QLabel("Curso guiado desde cero: teoría visual, práctica, evaluación y profesor virtual interactivo.")
        self.subtitulo.setObjectName("SubtituloPrincipalInicio")
        self.subtitulo.setAlignment(Qt.AlignCenter)
        cab.addWidget(titulo)
        cab.addWidget(self.subtitulo)
        raiz.addWidget(cabecera)

        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.btn_inicio = self._boton_nav("Inicio")
        self.btn_curso = self._boton_nav("Curso")
        self.btn_teoria = self._boton_nav("Teoría")
        self.btn_practica = self._boton_nav("Práctica")
        self.btn_como = self._boton_nav("Cómo funciona")
        self.btn_leer = self._boton_nav("Leer pantalla")
        self.btn_inicio.clicked.connect(self.mostrar_inicio)
        self.btn_curso.clicked.connect(self.mostrar_curso)
        self.btn_teoria.clicked.connect(self.mostrar_teoria)
        self.btn_practica.clicked.connect(self.mostrar_practica)
        self.btn_como.clicked.connect(self.mostrar_como_funciona)
        self.btn_leer.clicked.connect(self._leer_actual)
        for b in [self.btn_inicio, self.btn_curso, self.btn_teoria, self.btn_practica, self.btn_como]:
            barra.addWidget(b)
        barra.addStretch(1)
        barra.addWidget(self.btn_leer)
        raiz.addLayout(barra)

        self.stack = QStackedWidget()
        self.stack.setObjectName("StackInicioInterno")
        self.pagina_inicio = self._pagina_inicio()
        self.pagina_curso = self._pagina_curso()
        self.pagina_teoria = self._pagina_teoria()
        self.pagina_practica = self._pagina_practica()
        self.pagina_como = self._pagina_como_funciona()
        for p in [self.pagina_inicio, self.pagina_curso, self.pagina_teoria, self.pagina_practica, self.pagina_como]:
            self.stack.addWidget(p)
        raiz.addWidget(self.stack, 1)

    def _actualizar_textos_personales(self):
        if hasattr(self, "subtitulo"):
            self.subtitulo.setText(
                f"Curso guiado para {self.nombre_alumno}: teoría visual, práctica, evaluación y profesor virtual interactivo."
            )
        if hasattr(self, "lbl_hero_inicio"):
            self.lbl_hero_inicio.setText(
                f"Bienvenido, {self.nombre_alumno}. Aquí puedes empezar desde cero, consultar teoría con imágenes, "
                "practicar con el piano interactivo o continuar tu progreso guardado. El profesor virtual estará presente "
                "para explicarte qué ves, para qué sirve y cuál es el siguiente paso."
            )

    def _boton_nav(self, texto):
        btn = QPushButton(texto)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(38)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setObjectName("BotonInicioNav")
        return btn

    def _boton_accion(self, texto, color):
        btn = QPushButton(texto)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(46)
        btn.setObjectName("BotonInicioAccion")
        btn.setStyleSheet(f"""
            QPushButton#BotonInicioAccion {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton#BotonInicioAccion:hover {{ background-color: #0f172a; }}
        """)
        return btn

    def _tarjeta(self, titulo, texto):
        frame = QFrame()
        frame.setObjectName("TarjetaInicio")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        t = QLabel(titulo)
        t.setObjectName("TituloTarjetaInicio")
        x = QLabel(texto)
        x.setWordWrap(True)
        x.setObjectName("TextoTarjetaInicio")
        lay.addWidget(t)
        lay.addWidget(x)
        return frame

    def _pagina_inicio(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("HeroInicio")
        h = QHBoxLayout(hero)
        h.setContentsMargins(20, 18, 20, 18)
        h.setSpacing(16)
        self.lbl_hero_inicio = QLabel("")
        self.lbl_hero_inicio.setWordWrap(True)
        self.lbl_hero_inicio.setObjectName("TextoHeroInicio")
        h.addWidget(self.lbl_hero_inicio, 2)

        acciones = QVBoxLayout()
        acciones.setSpacing(8)
        btn_eval = self._boton_accion("Empezar con evaluación inicial", "#2563EB")
        btn_cont = self._boton_accion("Continuar progreso guardado", "#16A34A")
        btn_teoria = self._boton_accion("Ir a teoría desde cero", "#7C3AED")
        btn_pract = self._boton_accion("Ir a práctica", "#F59E0B")
        btn_eval.clicked.connect(self.iniciar_evaluacion.emit)
        btn_cont.clicked.connect(self.continuar.emit)
        btn_teoria.clicked.connect(self.mostrar_teoria)
        btn_pract.clicked.connect(self.mostrar_practica)
        acciones.addWidget(btn_eval)
        acciones.addWidget(btn_cont)
        acciones.addWidget(btn_teoria)
        acciones.addWidget(btn_pract)
        h.addLayout(acciones, 1)
        lay.addWidget(hero)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self._tarjeta("Curso", "Mapa completo de niveles. Sirve para ver el camino de aprendizaje: postura, lectura, ritmo, técnica, práctica y exámenes."), 0, 0)
        grid.addWidget(self._tarjeta("Teoría visual", "Explica cada concepto con imágenes y GIFs antes de tocar. Aquí el avatar debe comportarse como profesor: señalar qué mirar y por qué importa."), 0, 1)
        grid.addWidget(self._tarjeta("Práctica", "Ejercicios interactivos con corrección, repaso y avance solo cuando se supera. No se trata de correr, sino de tocar bien."), 1, 0)
        grid.addWidget(self._tarjeta("Profesor virtual", "Avatar siempre presente. Lee la pantalla, explica el material, responde preguntas y adapta el trato al alumno guardado en JSON."), 1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)
        return w

    def _pagina_curso(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        titulo = QLabel("Curso completo")
        titulo.setObjectName("TituloSeccionInicio")
        lay.addWidget(titulo)

        cuerpo = QTextEdit()
        cuerpo.setReadOnly(True)
        cuerpo.setPlainText(self._texto_curso_completo())
        cuerpo.setObjectName("TextoSeccionInicio")
        cuerpo.setLineWrapMode(QTextEdit.WidgetWidth)
        cuerpo.setMinimumHeight(260)
        lay.addWidget(cuerpo, 1)
        lay.addWidget(self._bloque_hanon_curso(), 2)
        return w

    def _bloque_hanon_curso(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(8)

        titulo = QLabel("Técnica Hanon completa")
        titulo.setObjectName("TituloTarjetaInicio")
        lay.addWidget(titulo)

        ok, aviso = self.hanon.disponible()
        if not ok:
            lbl = QLabel(aviso)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
            scroll.setWidget(cont)
            return scroll

        for nivel in self.hanon.estado_por_niveles():
            n = int(nivel.get("nivel", 0) or 0)
            ejercicios = nivel.get("ejercicios_detalle", []) or []
            if not ejercicios:
                continue
            primero = int(str(ejercicios[0].get("id", "hanon_00")).rsplit("_", 1)[1])
            ultimo = int(str(ejercicios[-1].get("id", "hanon_00")).rsplit("_", 1)[1])
            cab = QLabel(f"Nivel {n}: Hanon {primero:02d}-{ultimo:02d} · {nivel.get('objetivo', '')}")
            cab.setWordWrap(True)
            cab.setObjectName("DescripcionImagenTeoria")
            lay.addWidget(cab)
            for clase in ejercicios:
                fila = QFrame()
                fila.setObjectName("TarjetaInicio")
                fl = QGridLayout(fila)
                fl.setContentsMargins(8, 6, 8, 6)
                fl.setHorizontalSpacing(8)
                estado = str(clase.get("estado_hanon", "bloqueado"))
                titulo_clase = QLabel(str(clase.get("titulo") or clase.get("id")))
                titulo_clase.setObjectName("TituloTarjetaInicio")
                objetivo = QLabel(str(clase.get("objetivo") or "Objetivo técnico Hanon."))
                objetivo.setWordWrap(True)
                estado_lbl = QLabel(f"Estado: {estado}")
                btn = QPushButton("Abrir" if estado != "bloqueado" else "Bloqueado")
                btn.setEnabled(estado != "bloqueado")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _checked=False, hid=clase.get("id", ""): self.abrir_hanon.emit(str(hid)))
                fl.addWidget(titulo_clase, 0, 0)
                fl.addWidget(estado_lbl, 0, 1)
                fl.addWidget(btn, 0, 2)
                fl.addWidget(objetivo, 1, 0, 1, 3)
                lay.addWidget(fila)
        lay.addStretch(1)
        scroll.setWidget(cont)
        return scroll

    def _cargar_json_seguro(self, ruta):
        try:
            ruta = Path(ruta)
            if not ruta.is_absolute():
                ruta = DATA_DIR.parent / ruta
            if not ruta.exists():
                return None
            with ruta.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _indice_objetivos_lecciones(self, ruta_relativa: str) -> dict:
        datos = self._cargar_json_seguro(ruta_relativa)
        indice = {}
        if isinstance(datos, dict):
            for item in datos.get("lecciones", []) or []:
                if isinstance(item, dict):
                    indice[str(item.get("id", ""))] = item
        elif isinstance(datos, list):
            for item in datos:
                if isinstance(item, dict):
                    indice[str(item.get("id", ""))] = item
        return indice

    def _texto_curso_completo(self) -> str:
        """Construye la pantalla Curso desde los JSON reales del proyecto.

        Así la pantalla no se queda en un resumen pobre: muestra niveles, objetivos,
        módulos, desbloqueos, clases y objetivo de cada clase cuando existe en la
        colección.
        """
        ruta = self._cargar_json_seguro(DATA_DIR / "ruta_curso.json") or {}
        lineas = []
        lineas.append("PRESENTACIÓN DEL CURSO")
        lineas.append("")
        lineas.append(str(ruta.get("descripcion") or "Curso progresivo de piano con teoría, práctica, evaluación y profesor virtual."))
        lineas.append("")
        lineas.append("Estructura didáctica obligatoria")
        lineas.append("• Primero: clase teórica clara, visual y explicada por el profesor.")
        lineas.append("• Después: varios ejercicios asociados a esa clase.")
        lineas.append("• Después: examen final de clase antes de avanzar.")
        lineas.append("• Al terminar la última clase de un nivel: examen global del nivel.")
        lineas.append("• El alumno no debe avanzar por prisa: avanza cuando demuestra comprensión y práctica correcta.")
        lineas.append("")
        lineas.append("Entradas del profesor")
        lineas.append("• MIDI continuo: nota, velocity, tiempo de reacción, pulso, simultaneidad y errores.")
        lineas.append("• Cámara opcional Pro: postura, manos, muñeca, tensión y distancia al piano.")
        lineas.append("• Audio opcional Pro: escucha del sonido real, ataque, golpes y estabilidad.")
        lineas.append("• Historial didáctico: errores recurrentes, aciertos, progreso y recomendaciones.")
        lineas.append("")

        niveles = ruta.get("niveles", []) if isinstance(ruta, dict) else []
        if not niveles:
            niveles = []

        for n, nivel in enumerate(niveles, start=1):
            if not isinstance(nivel, dict):
                continue
            titulo = nivel.get("titulo") or nivel.get("id") or f"Nivel {n}"
            lineas.append("=" * 72)
            lineas.append(str(titulo))
            lineas.append("=" * 72)
            objetivo = nivel.get("objetivo") or nivel.get("descripcion") or "Objetivo pendiente de concretar."
            lineas.append(f"Objetivo del nivel: {objetivo}")
            if nivel.get("estado_inicial"):
                lineas.append(f"Estado inicial: {nivel.get('estado_inicial')}")
            if nivel.get("desbloquea"):
                lineas.append(f"Desbloquea: {nivel.get('desbloquea')}")
            modulos = nivel.get("modulos", []) or []
            if modulos:
                lineas.append("Módulos del nivel:")
                for m in modulos:
                    lineas.append(f"  • {m}")

            coleccion = nivel.get("coleccion")
            clases = []
            objetivos_por_id = {}
            if coleccion:
                col = self._cargar_json_seguro(coleccion) or {}
                clases = col.get("clases", []) if isinstance(col, dict) else []
                origen = col.get("archivo_origen", "") if isinstance(col, dict) else ""
                if origen:
                    objetivos_por_id = self._indice_objetivos_lecciones(origen)

            if clases:
                lineas.append("")
                lineas.append(f"Clases previstas: {len(clases)}")
                for clase in sorted(clases, key=lambda c: int(c.get("orden", 9999) or 9999)):
                    cid = str(clase.get("id", ""))
                    detalle = objetivos_por_id.get(cid, {})
                    orden = clase.get("orden", "")
                    titulo_clase = clase.get("titulo", cid or "Clase")
                    objetivo_clase = (
                        clase.get("objetivo")
                        or detalle.get("objetivo")
                        or detalle.get("resumen")
                        or clase.get("resumen")
                        or "Objetivo preparado en la colección; pendiente de desarrollo completo."
                    )
                    estado = clase.get("estado", "")
                    lineas.append(f"  {orden}. {titulo_clase}")
                    lineas.append(f"     Objetivo: {objetivo_clase}")
                    if estado:
                        lineas.append(f"     Estado: {estado}")
                    ejercicios = clase.get("ejercicios_asociados") or detalle.get("ejercicios_asociados") or []
                    if ejercicios:
                        nombres = []
                        for ej in ejercicios[:5]:
                            if isinstance(ej, dict):
                                nombres.append(str(ej.get("titulo") or ej.get("id") or "ejercicio"))
                        if nombres:
                            lineas.append("     Ejercicios: " + "; ".join(nombres))
                    examen = clase.get("examen_clase") or detalle.get("examen_clase") or {}
                    if isinstance(examen, dict) and examen:
                        lineas.append("     Examen: " + str(examen.get("titulo") or examen.get("id") or "examen de clase"))
            else:
                lineas.append("")
                lineas.append("Clases previstas: se desarrollarán progresivamente sobre esta estructura.")
            lineas.append("")

        lineas.append("Resumen práctico")
        lineas.append("El curso no es una lista de botones. Cada pantalla debe enseñar, pedir una acción al alumno, comprobarla y guardar el resultado. La pizarra, el piano, el MIDI y el profesor deben ir sincronizados.")
        return "\n".join(lineas)

    def _pagina_teoria(self):
        """Página de teoría visual convertida en clase guiada v1.9.2."""
        w = QWidget()
        raiz = QVBoxLayout(w)
        raiz.setSpacing(8)

        titulo = QLabel("Teoría guiada · Clase con flujo docente")
        titulo.setObjectName("TituloSeccionInicio")
        raiz.addWidget(titulo)

        intro = QLabel(
            "Ahora la teoría funciona como una clase: el profesor presenta una lección, explica la imagen, pone un ejemplo, "
            "hace una pregunta de comprobación, guarda el progreso y celebra con confeti y música cuando superas una meta antes de pasar a la siguiente."
        )
        intro.setWordWrap(True)
        raiz.addWidget(intro)

        fila_nivel = QHBoxLayout()
        fila_nivel.addWidget(QLabel("Nivel guiado:"))
        self.combo_nivel_guiado = QComboBox()
        for nivel in self.niveles:
            nivel_id = nivel.get("id")
            if self._nivel_guiado_disponible(nivel_id):
                self.combo_nivel_guiado.addItem(nivel.get("nombre", nivel_id), nivel_id)
        if self.combo_nivel_guiado.count() == 0:
            self.combo_nivel_guiado.addItem("Nivel 0", "nivel_0")
        idx_nivel = self.combo_nivel_guiado.findData(self.lecciones_guiadas.nivel_id)
        if idx_nivel >= 0:
            self.combo_nivel_guiado.setCurrentIndex(idx_nivel)
        self.combo_nivel_guiado.currentIndexChanged.connect(self._cambiar_nivel_guiado_desde_combo)
        fila_nivel.addWidget(self.combo_nivel_guiado, 1)
        raiz.addLayout(fila_nivel)

        panel = QFrame()
        panel.setObjectName("PanelLeccionGuiada")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        fila_sup = QHBoxLayout()
        self.lbl_leccion_guiada = QLabel("")
        self.lbl_leccion_guiada.setObjectName("TituloTarjetaInicio")
        self.barra_leccion_guiada = QProgressBar()
        self.barra_leccion_guiada.setRange(0, 100)
        self.barra_leccion_guiada.setFormat("Progreso guiado: %p%")
        fila_sup.addWidget(self.lbl_leccion_guiada, 2)
        fila_sup.addWidget(self.barra_leccion_guiada, 1)
        lay.addLayout(fila_sup)

        self.txt_leccion_guiada = QTextEdit()
        self.txt_leccion_guiada.setReadOnly(True)
        self.txt_leccion_guiada.setMinimumHeight(126)
        self.txt_leccion_guiada.setObjectName("TextoLeccionGuiada")
        lay.addWidget(self.txt_leccion_guiada)

        fila_lectura = QHBoxLayout()
        self.btn_leer_leccion_guiada = self._boton_nav("Leer esta lección")
        self.btn_leer_leccion_guiada.clicked.connect(lambda: self.leer_texto.emit(getattr(self, "_texto_actual", "")))
        self.btn_abrir_visual_leccion = self._boton_nav("Abrir imagen de la lección")
        self.btn_abrir_visual_leccion.clicked.connect(self._abrir_visual_leccion_actual)
        self.btn_mini_eval_nivel0 = self._boton_nav("Examen global")
        self.btn_mini_eval_nivel0.clicked.connect(self._mini_evaluacion_nivel0)
        fila_lectura.addWidget(self.btn_leer_leccion_guiada)
        fila_lectura.addWidget(self.btn_abrir_visual_leccion)
        fila_lectura.addWidget(self.btn_mini_eval_nivel0)
        lay.addLayout(fila_lectura)

        fila_pregunta = QHBoxLayout()
        self.combo_respuesta_leccion = QComboBox()
        self.combo_respuesta_leccion.setMinimumHeight(34)
        self.btn_comprobar_leccion = self._boton_nav("Examen final de clase")
        self.btn_comprobar_leccion.clicked.connect(self._comprobar_respuesta_leccion_actual)
        self.btn_marcar_leccion = self._boton_nav("Teoría + ejercicios realizados")
        self.btn_marcar_leccion.clicked.connect(self._marcar_leccion_actual_aprendida)
        self.btn_anterior_leccion = self._boton_nav("Lección anterior")
        self.btn_anterior_leccion.clicked.connect(self._leccion_anterior)
        self.btn_siguiente_leccion = self._boton_nav("Siguiente lección")
        self.btn_siguiente_leccion.clicked.connect(self._siguiente_leccion)
        fila_pregunta.addWidget(self.combo_respuesta_leccion, 2)
        fila_pregunta.addWidget(self.btn_comprobar_leccion)
        fila_pregunta.addWidget(self.btn_marcar_leccion)
        fila_pregunta.addWidget(self.btn_anterior_leccion)
        fila_pregunta.addWidget(self.btn_siguiente_leccion)
        lay.addLayout(fila_pregunta)

        self.lbl_bloqueo_leccion = QLabel("")
        self.lbl_bloqueo_leccion.setWordWrap(True)
        self.lbl_bloqueo_leccion.setObjectName("DescripcionImagenTeoria")
        lay.addWidget(self.lbl_bloqueo_leccion)
        raiz.addWidget(panel)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.cont_materiales_teoria = QWidget()
        self.grid_materiales_teoria = QGridLayout(self.cont_materiales_teoria)
        self.grid_materiales_teoria.setSpacing(12)
        self._actualizar_galeria_materiales()
        scroll.setWidget(self.cont_materiales_teoria)
        raiz.addWidget(scroll, 1)

        self._actualizar_panel_leccion_guiada(emitir_texto=False, corregir_bloqueo=True)
        return w

    def _texto_leccion_para_profesor(self, leccion: dict) -> str:
        nombre = self.nombre_alumno or "alumno"
        flujo = leccion.get("flujo_docente", {}) if isinstance(leccion, dict) else {}
        ejercicios = flujo.get("ejercicios_asociados", []) if isinstance(flujo, dict) else []
        examen = flujo.get("examen_clase", {}) if isinstance(flujo, dict) else {}

        if ejercicios:
            texto_ejercicios = "\n".join(
                f"- {ej.get('titulo', 'Ejercicio')}: {ej.get('objetivo', '')}\n  Instrucción: {ej.get('instruccion', '')}"
                for ej in ejercicios
            )
        else:
            texto_ejercicios = leccion.get("practica", "")

        pregunta_examen = examen.get("pregunta", leccion.get("pregunta", ""))

        try:
            resumen_historial = self.lecciones_guiadas.historial_alumno.resumen_docente()
        except Exception:
            resumen_historial = "Todavía no hay historial pedagógico suficiente para adaptar esta clase."

        return (
            f"{nombre}, estamos en la lección: {leccion.get('titulo', '')}.\n\n"
            "FLUJO OBLIGATORIO DE ESTA CLASE:\n"
            "1. Clase teórica.\n"
            "2. Ejercicios asociados.\n"
            "3. Examen final de clase.\n\n"
            f"OBJETIVO:\n{leccion.get('objetivo', '')}\n\n"
            f"HISTORIAL DEL ALUMNO QUE CONSULTA EL PROFESOR:\n{resumen_historial}\n\n"
            f"CLASE TEÓRICA:\n{leccion.get('explicacion', '')}\n\n"
            f"EJEMPLO DEL PROFESOR:\n{leccion.get('ejemplo', '')}\n\n"
            f"EJERCICIOS ASOCIADOS:\n{texto_ejercicios}\n\n"
            f"EXAMEN FINAL DE CLASE:\n{pregunta_examen}"
        )

    def _actualizar_panel_leccion_guiada(self, emitir_texto: bool = False, corregir_bloqueo: bool = False):
        if not hasattr(self, "lecciones_guiadas"):
            return
        leccion = self.lecciones_guiadas.leccion_actual()
        if corregir_bloqueo and leccion and self.lecciones_guiadas.esta_superada(leccion.get("id", "")):
            # Si el progreso guardó esta lección como superada pero dejó
            # leccion_actual_id apuntando a ella, saltamos a la primera pendiente.
            leccion = self.lecciones_guiadas.primera_pendiente_desde_actual()
        self._leccion_actual = leccion
        if not leccion:
            return
        superada = self.lecciones_guiadas.esta_superada(leccion.get("id", ""))
        self.lbl_leccion_guiada.setText(self.lecciones_guiadas.texto_resumen_progreso())
        self.barra_leccion_guiada.setValue(self.lecciones_guiadas.porcentaje())
        total = len(self.lecciones_guiadas.lecciones())
        superadas = len(set(self.lecciones_guiadas.progreso.get("lecciones_superadas", [])))
        if hasattr(self, "btn_mini_eval_nivel0"):
            etiqueta_nivel = self._etiqueta_nivel_guiado()
            evaluacion_superada = bool(self.lecciones_guiadas.progreso.get(self.lecciones_guiadas.clave_mini_evaluacion_superada()))
            self.btn_mini_eval_nivel0.setEnabled(total > 0 and superadas >= total)
            if evaluacion_superada:
                self.btn_mini_eval_nivel0.setText(f"{etiqueta_nivel} superado ✓")
                self.btn_mini_eval_nivel0.setToolTip("Puedes repetir la evaluación si quieres reforzar el nivel.")
            else:
                self.btn_mini_eval_nivel0.setText(f"Examen global {etiqueta_nivel}")
                if superadas < total:
                    self.btn_mini_eval_nivel0.setToolTip(f"Se desbloquea cuando superes el examen final de todas las clases del {etiqueta_nivel}.")
                else:
                    self.btn_mini_eval_nivel0.setToolTip(f"Comprobación final: {total} clases del {etiqueta_nivel}.")
        texto = self._texto_leccion_para_profesor(leccion)
        self.txt_leccion_guiada.setPlainText(texto)
        self.combo_respuesta_leccion.clear()
        opciones_leccion = list(enumerate(leccion.get("opciones", [])))
        random.shuffle(opciones_leccion)
        for idx_original, opcion in opciones_leccion:
            self.combo_respuesta_leccion.addItem(opcion, idx_original)
        if superada:
            self.lbl_bloqueo_leccion.setText("Lección superada. Puedes avanzar a la siguiente o repasarla si quieres reforzarla.")
            self.btn_siguiente_leccion.setEnabled(True)
        else:
            self.lbl_bloqueo_leccion.setText("Flujo de clase: primero teoría, después ejercicios asociados y por último examen final de clase. No se avanza sin superar el examen.")
            self.btn_siguiente_leccion.setEnabled(False)
        self._texto_actual = texto
        if emitir_texto:
            self.leer_texto.emit(texto)

    def _abrir_visual_leccion_actual(self):
        leccion = getattr(self, "_leccion_actual", None) or self.lecciones_guiadas.leccion_actual()
        if not leccion:
            return
        ruta = Path(leccion.get("archivo", ""))
        if not ruta.is_absolute():
            # El JSON guarda rutas relativas a la raíz del proyecto.
            ruta = ASSETS_DIR.parent / ruta
        if ruta.exists():
            self.imagen_activada.emit(str(ruta), leccion.get("titulo", ruta.name), self._texto_leccion_para_profesor(leccion))
        else:
            self.leer_texto.emit(f"No encuentro el archivo visual de esta lección: {ruta}")

    def _texto_inicio_nueva_leccion(self, leccion: dict, prefijo: str = "") -> str:
        if not leccion:
            return prefijo or ""
        cuerpo = self._texto_leccion_para_profesor(leccion)
        if prefijo:
            return f"{prefijo}\n\nAhora pasamos a la siguiente lección: {leccion.get('titulo', '')}.\n\n{cuerpo}"
        return cuerpo

    def _avanzar_despues_de_superar(self, leccion_superada: dict, mensaje_superacion: str):
        """Avanza automáticamente tras superar una lección.

        Esto corrige el bloqueo percibido en la primera pregunta: cuando el alumno
        responde bien o confirma que lo entendió, el curso pasa directamente a la
        siguiente lección y refresca la pregunta, la imagen y el progreso.
        """
        leccion_id = leccion_superada.get("id", "") if leccion_superada else ""
        titulo_logro = leccion_superada.get("titulo", "Lección superada") if leccion_superada else "Lección superada"
        self.celebracion.emit("leccion", titulo_logro)
        if not self.lecciones_guiadas.hay_siguiente():
            etiqueta_nivel = self._etiqueta_nivel_guiado()
            self._actualizar_panel_leccion_guiada(emitir_texto=False)
            texto = (
                f"{mensaje_superacion}\n\n"
                f"Has terminado todas las clases guiadas de este nivel. Ahora puedes hacer el Examen global del {etiqueta_nivel}."
            )
            self._texto_actual = texto
            self.leer_texto.emit(texto)
            self.celebracion.emit("nivel", f"Lecciones guiadas del {etiqueta_nivel} completadas")
            return
        nueva = self.lecciones_guiadas.avanzar_desde(leccion_id)
        self._leccion_actual = nueva
        self._actualizar_panel_leccion_guiada(emitir_texto=False)
        texto = self._texto_inicio_nueva_leccion(nueva, mensaje_superacion)
        self._texto_actual = texto
        self.leer_texto.emit(texto)

    def _comprobar_respuesta_leccion_actual(self):
        leccion = getattr(self, "_leccion_actual", None) or self.lecciones_guiadas.leccion_actual()
        if not leccion:
            return
        nombre = self.nombre_alumno or "alumno"
        # Si esta lección ya figuraba como superada, no volvemos a bloquear al alumno
        # por la opción que haya quedado seleccionada en el desplegable. Avanzamos.
        if self.lecciones_guiadas.esta_superada(leccion.get("id", "")) and self.lecciones_guiadas.hay_siguiente():
            nueva = self.lecciones_guiadas.siguiente_por_indice(leccion.get("id", ""))
            self._leccion_actual = nueva
            self._actualizar_panel_leccion_guiada(emitir_texto=False)
            texto = self._texto_inicio_nueva_leccion(
                nueva,
                f"{nombre}, esta lección ya estaba guardada como superada. Para evitar que te quedes bloqueado, avanzo a la siguiente."
            )
            self._texto_actual = texto
            self.leer_texto.emit(texto)
            return
        idx = self.combo_respuesta_leccion.currentData()
        if idx is None:
            idx = self.combo_respuesta_leccion.currentIndex()
        resultado = self.lecciones_guiadas.comprobar_respuesta(leccion.get("id", ""), int(idx))
        if resultado.correcto:
            texto = (
                f"Correcto, {nombre}. {resultado.mensaje}\n\n"
                "Has superado el examen final de esta clase. Ahora sí se desbloquea el siguiente paso del curso."
            )
            self._avanzar_despues_de_superar(leccion, texto)
            return
        texto = (
            f"Casi, {nombre}. {resultado.mensaje}\n\n"
            f"Te lo vuelvo a explicar de forma más directa: {leccion.get('explicacion', '')}\n\n"
            "Prueba de nuevo antes de avanzar. Equivocarse aquí forma parte de aprender."
        )
        self._texto_actual = texto
        self.leer_texto.emit(texto)
        self._actualizar_panel_leccion_guiada(emitir_texto=False)

    def _marcar_leccion_actual_aprendida(self):
        leccion = getattr(self, "_leccion_actual", None) or self.lecciones_guiadas.leccion_actual()
        if not leccion:
            return
        nombre = self.nombre_alumno or "alumno"

        # v4.0.5: este botón ya no supera la clase completa.
        # Registra que la teoría y los ejercicios asociados se han trabajado.
        clase_id = leccion.get("id", "")
        flujo = getattr(self.lecciones_guiadas, "flujo_docente", None)
        if flujo is not None:
            flujo.marcar_teoria_superada(clase_id)
            ejercicios = leccion.get("flujo_docente", {}).get("ejercicios_asociados", [])
            for ej in ejercicios:
                flujo.marcar_ejercicio_superado(clase_id, ej.get("id", ""))
                try:
                    self.lecciones_guiadas.historial_alumno.registrar_ejercicio(
                        ejercicio_id=ej.get("id", ""),
                        clase_id=clase_id,
                        correcto=True,
                        tipo=ej.get("tipo", ""),
                        detalle={"titulo": ej.get("titulo", ""), "origen": "teoria_ejercicios_realizados"}
                    )
                except Exception:
                    pass

        texto = (
            f"He guardado teoría y ejercicios como realizados, {nombre}.\n\n"
            f"Idea principal: {leccion.get('resumen', '')}\n\n"
            "Ahora falta superar el examen final de clase para avanzar de forma profesional."
        )
        self._texto_actual = texto
        self.leer_texto.emit(texto)
        self._actualizar_panel_leccion_guiada(emitir_texto=False)

    def _siguiente_leccion(self):
        leccion = getattr(self, "_leccion_actual", None) or self.lecciones_guiadas.leccion_actual()
        if not leccion:
            return
        leccion_id = leccion.get("id", "")
        # Si no está superada, el bloqueo es pedagógico: primero debe responder o confirmar comprensión.
        if not self.lecciones_guiadas.esta_superada(leccion_id):
            texto = (
                f"Todavía no avanzo, {self.nombre_alumno}. Quiero asegurarme de que has entendido esta parte. "
                "Responde correctamente la pregunta o pulsa 'Teoría + ejercicios realizados' si de verdad ya lo tienes claro."
            )
            self._texto_actual = texto
            self.leer_texto.emit(texto)
            return

        nueva = self.lecciones_guiadas.siguiente_por_indice(leccion_id)
        if not nueva:
            return
        # Si seguimos en el mismo id, no hay lección posterior.
        if nueva.get("id") == leccion_id:
            etiqueta_nivel = self._etiqueta_nivel_guiado()
            texto = (
                f"{self.nombre_alumno}, ya estás en la última lección guiada del {etiqueta_nivel}. "
                f"Cuando esté superada, puedes hacer el Examen global del {etiqueta_nivel}."
            )
            self._texto_actual = texto
            self.leer_texto.emit(texto)
            self._actualizar_panel_leccion_guiada(emitir_texto=False)
            return

        self._leccion_actual = nueva
        self._actualizar_panel_leccion_guiada(emitir_texto=False)
        texto = self._texto_inicio_nueva_leccion(
            nueva,
            f"Perfecto, {self.nombre_alumno}. Avanzo a la siguiente lección."
        )
        self._texto_actual = texto
        self.leer_texto.emit(texto)

    def _leccion_anterior(self):
        nueva = self.lecciones_guiadas.retroceder()
        if nueva:
            self._actualizar_panel_leccion_guiada(emitir_texto=True)
    def _mini_evaluacion_nivel0(self):
        datos = getattr(self.lecciones_guiadas, "datos", {})
        mini = datos.get("mini_evaluacion", {})
        preguntas = mini.get("preguntas", [])
        total_lecciones = len(self.lecciones_guiadas.lecciones())
        superadas = len(set(self.lecciones_guiadas.progreso.get("lecciones_superadas", [])))
        etiqueta_nivel = self._etiqueta_nivel_guiado()
        if total_lecciones > 0 and superadas < total_lecciones:
            texto = (
                f"Todavía no abro la examen global, {self.nombre_alumno}. "
                f"Primero termina las lecciones guiadas: llevas {superadas}/{total_lecciones}. "
                "Cuando estén superadas, la evaluación será una comprobación final, no una adivinanza."
            )
            self._texto_actual = texto
            self.leer_texto.emit(texto)
            return
        if not preguntas:
            self.leer_texto.emit("Aún no hay examen global configurada para este nivel.")
            return

        dlg = MiniEvaluacionNivel0Dialog(mini, self.nombre_alumno, self, self.avatar_tipo)
        if dlg.exec() != QDialog.Accepted:
            if dlg.detalle:
                self._guardar_intento_mini_evaluacion(dlg, aprobado=False)
                texto = self._texto_repaso_mini_evaluacion(dlg)
                self._texto_actual = texto
                self.leer_texto.emit(texto)
            return

        self._guardar_intento_mini_evaluacion(dlg, aprobado=True)
        self.lecciones_guiadas.progreso[self.lecciones_guiadas.clave_mini_evaluacion_superada()] = True
        self.lecciones_guiadas.progreso[self.lecciones_guiadas.clave_nivel_superado()] = True
        self.lecciones_guiadas.progreso["siguiente_recomendado"] = f"practica_nivel_{self.lecciones_guiadas.nivel_numero}"
        try:
            self.lecciones_guiadas.historial_alumno.registrar_clase(
                clase_id=mini.get("id", f"examen_global_nivel_{self.lecciones_guiadas.nivel_numero}"),
                titulo=f"Examen global {etiqueta_nivel}",
                evento="examen_global_superado",
                correcto=True,
                detalle={"aciertos": dlg.aciertos, "total": len(preguntas)}
            )
        except Exception:
            pass
        self.lecciones_guiadas.guardar()
        self.celebracion.emit("nivel", f"{etiqueta_nivel} superado")
        texto = (
            f"Excelente, {self.nombre_alumno}. Has superado la examen global final del {etiqueta_nivel} con {dlg.aciertos}/{len(preguntas)} aciertos.\n\n"
            "Has demostrado que entiendes el objetivo del nivel, sus clases y sus criterios de avance.\n\n"
            f"Te entrego una medalla de {etiqueta_nivel} superado y guardo tu progreso. El siguiente paso será practicar con ejercicios y corrección inmediata."
        )
        QMessageBox.information(self, f"{etiqueta_nivel} superado", texto)
        self.leer_texto.emit(texto)
        self._texto_actual = texto
        self._actualizar_panel_leccion_guiada(emitir_texto=False)

    def _guardar_intento_mini_evaluacion(self, dlg: MiniEvaluacionNivel0Dialog, aprobado: bool):
        intento = {
            "evaluacion_id": dlg.mini.get("id", f"examen_global_nivel_{self.lecciones_guiadas.nivel_numero}"),
            "aciertos": int(dlg.aciertos),
            "total": len(dlg.preguntas),
            "minimo_aprobado": int(dlg.minimo),
            "aprobado": bool(aprobado),
            "orden_aleatorio": True,
            "respuestas_aleatorias": True,
            "detalle": dlg.detalle[-20:],
        }
        clave_intentos = f"mini_evaluacion_nivel_{self.lecciones_guiadas.nivel_numero}_intentos"
        clave_ultimo = f"ultimo_resultado_mini_evaluacion_nivel_{self.lecciones_guiadas.nivel_numero}"
        intentos = list(self.lecciones_guiadas.progreso.get(clave_intentos, []))
        intentos.append(intento)
        self.lecciones_guiadas.progreso[clave_intentos] = intentos[-30:]
        self.lecciones_guiadas.progreso[clave_ultimo] = intento
        self.lecciones_guiadas.guardar()

    def _texto_repaso_mini_evaluacion(self, dlg: MiniEvaluacionNivel0Dialog) -> str:
        fallos = [x for x in dlg.detalle if not x.get("correcto")]
        etiqueta_nivel = self._etiqueta_nivel_guiado()
        if not fallos:
            return (
                f"{self.nombre_alumno}, has cerrado la examen global antes de guardarla. "
                f"Puedes volver a abrirla cuando quieras desde el botón Examen global {etiqueta_nivel}."
            )
        partes = [
            f"{self.nombre_alumno}, esta vez no damos el {etiqueta_nivel} por superado todavía. Resultado: {dlg.aciertos}/{len(dlg.preguntas)}.",
            "Vamos a repasar exactamente lo que ha fallado:",
        ]
        for item in fallos[:6]:
            partes.append(
                f"- Pregunta {item.get('numero')}: {item.get('pregunta')}\n"
                f"  Respuesta correcta: {item.get('correcta')}\n"
                f"  Repaso: {item.get('explicacion')}"
            )
        partes.append(f"Cuando lo repases, vuelve a pulsar Examen global {etiqueta_nivel}. No avanzamos de nivel hasta que esta base esté clara.")
        return "\n\n".join(partes)

    def _materiales_nivel_guiado(self):
        if getattr(self.lecciones_guiadas, "nivel_numero", 0) == 0:
            return self._imagenes_nivel_0()
        base = ASSETS_DIR / "teoria" / f"nivel_{self.lecciones_guiadas.nivel_numero}"
        if not base.exists():
            return []
        return sorted(base.glob("clase_*.md"))

    def _actualizar_galeria_materiales(self):
        if not hasattr(self, "grid_materiales_teoria"):
            return
        while self.grid_materiales_teoria.count():
            item = self.grid_materiales_teoria.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        materiales = self._materiales_nivel_guiado()
        if not materiales:
            etiqueta = self._etiqueta_nivel_guiado()
            aviso = QLabel(f"No se han encontrado materiales visuales o guiones en assets/teoria/{etiqueta.lower().replace(' ', '_')}/.")
            aviso.setWordWrap(True)
            self.grid_materiales_teoria.addWidget(aviso, 0, 0)
            return
        for i, ruta in enumerate(materiales):
            card = self._tarjeta_imagen(ruta)
            self.grid_materiales_teoria.addWidget(card, i // 2, i % 2)

    def _imagenes_nivel_0(self):
        base = ASSETS_DIR / "teoria" / "nivel_0"
        if not base.exists():
            return []
        exts = ("*.png", "*.jpg", "*.jpeg", "*.gif")
        rutas = []
        for ext in exts:
            rutas.extend(base.glob(ext))
            rutas.extend((base / "gifs").glob(ext) if (base / "gifs").exists() else [])

        # En la pantalla de teoría solo se muestran materiales finales.
        # Los fotogramas sueltos usados para construir GIFs quedan en assets,
        # pero no se enseñan al alumno para evitar ruido visual y errores antiguos.
        rutas = [p for p in rutas if "frame" not in p.name.lower() and "original" not in p.name.lower()]

        prioridad = {
            "postura_mala_correcta.png": 0,
            "postura_al_piano.png": 1,
            "mano_correcta.png": 2,
            "digitacion_1_5_base.png": 3,
            "digitacion_1_5_pro_suave.gif": 4,
            "patron_teclado.png": 5,
            "teclas_blancas.png": 6,
        }
        return sorted(set(rutas), key=lambda p: (prioridad.get(p.name, 50), str(p).lower()))

    def _descripcion_imagen(self, ruta: Path) -> str:
        n = ruta.name.lower()
        if ruta.suffix.lower() in {".md", ".txt"}:
            return "Guion de teoría de la clase. Pulsa para abrirlo con la explicación completa del profesor."
        if "postura_mala_correcta" in n:
            return (
                "Esta imagen compara una postura incorrecta con una postura correcta. Sirve para entender por qué no debemos encorvar la espalda, "
                "cerrar los hombros ni acercarnos demasiado al piano. La postura correcta permite tocar con menos tensión y más control."
            )
        if "postura_al_piano" in n:
            return (
                "Esta imagen resume los puntos técnicos de la postura al piano: sentarse al borde del banco, espalda recta, hombros relajados, "
                "codos a nivel del teclado, pies apoyados y muñecas relajadas."
            )
        if "mano_correcta" in n:
            return (
                "Esta imagen sirve para explicar la postura básica: muñeca relajada, dedos curvados y pulsación con la yema. "
                "No debes aplastar la tecla con el dedo plano; la mano debe quedar natural, como si sujetaras una pequeña pelota."
            )
        if "digitacion_1_5_base" in n:
            return (
                "Aquí se ve la numeración de los dedos. El pulgar es 1, índice 2, corazón 3, anular 4 y meñique 5. "
                "Esta numeración se usa en partituras y ejercicios para indicar qué dedo debe tocar cada nota."
            )
        if "digitacion" in n and n.endswith(".gif"):
            return (
                "Este GIF anima la digitación. Sirve para que el alumno vea el orden de movimiento de los dedos y relacione dedo, número y tecla. "
                "El objetivo no es tocar fuerte, sino mover cada dedo con control."
            )
        if "frame_2" in n:
            return (
                "Fotograma de digitación del dedo 2. El dedo 2 corresponde al índice. Si una imagen antigua marcaba el 3 en la mano izquierda, "
                "debe corregirse porque el movimiento correcto del dedo 2 es el índice."
            )
        if "frame" in n:
            return "Fotograma de apoyo para la animación de digitación. Sirve para construir el movimiento paso a paso del dedo indicado."
        if "patron_teclado" in n:
            return (
                "Esta imagen explica el patrón del teclado: primero aparecen grupos de dos teclas negras y después grupos de tres teclas negras. "
                "Ese patrón permite encontrar DO y orientarse sin memorizar todo de golpe."
            )
        if "teclas_blancas" in n:
            return (
                "Esta imagen muestra las teclas blancas: DO, RE, MI, FA, SOL, LA y SI. Sirve para aprender la secuencia natural de notas antes de trabajar sostenidos y bemoles."
            )
        return "Material visual del nivel. El profesor virtual puede describirlo y explicar para qué sirve dentro de la lección."

    def _tarjeta_imagen(self, ruta: Path):
        frame = QFrame()
        frame.setObjectName("TarjetaImagenTeoria")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)
        lbl = ClickableMediaLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setCursor(Qt.PointingHandCursor)
        lbl.setToolTip("Pulsa para ampliar esta imagen y escuchar la explicación del profesor.")
        suf = ruta.suffix.lower()
        if suf in {".md", ".txt"}:
            lbl.setText("Guion de clase\n" + ruta.stem.replace("_", " ").title())
            lbl.setWordWrap(True)
            lbl.setMinimumHeight(160)
        elif suf == ".gif":
            movie = QMovie(str(ruta))
            if movie.isValid():
                movie.setScaledSize(QSize(360, 230))
                lbl.setMovie(movie)
                movie.start()
                lbl._movie = movie
            else:
                lbl.setText("No se pudo cargar el GIF")
        else:
            pix = QPixmap(str(ruta))
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(360, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                lbl.setText("No se pudo cargar")
        nombre = QLabel(ruta.name)
        nombre.setAlignment(Qt.AlignCenter)
        nombre.setObjectName("NombreImagenTeoria")
        desc = QLabel(self._descripcion_imagen(ruta))
        desc.setWordWrap(True)
        desc.setObjectName("DescripcionImagenTeoria")
        pista = QLabel("Pulsa para ampliar y escuchar al profesor")
        pista.setAlignment(Qt.AlignCenter)
        pista.setObjectName("PistaImagenTeoria")
        lay.addWidget(lbl)
        lay.addWidget(nombre)
        lay.addWidget(desc)
        lay.addWidget(pista)
        lbl.clicked.connect(lambda ruta=ruta: self._emitir_imagen_activada(ruta))
        frame.mousePressEvent = lambda event, ruta=ruta: self._emitir_imagen_activada(ruta)
        frame.setCursor(Qt.PointingHandCursor)
        return frame

    def _titulo_imagen(self, ruta: Path) -> str:
        n = ruta.name.lower()
        if ruta.suffix.lower() in {".md", ".txt"}:
            return ruta.stem.replace("_", " ").title()
        if "postura_mala_correcta" in n:
            return "Postura al piano: incorrecto y correcto"
        if "postura_al_piano" in n:
            return "Postura al piano: guía paso a paso"
        if "mano_correcta" in n:
            return "Postura correcta de la mano"
        if "digitacion" in n and n.endswith(".gif"):
            return "Digitación animada 1–5"
        if "digitacion" in n:
            return "Numeración de los dedos 1–5"
        if "patron_teclado" in n:
            return "Patrón del teclado: grupos de 2 y 3 negras"
        if "teclas_blancas" in n:
            return "Teclas blancas: DO RE MI FA SOL LA SI"
        return ruta.name

    def _emitir_imagen_activada(self, ruta: Path):
        self.imagen_activada.emit(str(ruta), self._titulo_imagen(ruta), self._explicacion_imagen_extendida(ruta))

    def _explicacion_imagen_extendida(self, ruta: Path) -> str:
        n = ruta.name.lower()
        nombre = self.nombre_alumno or "alumno"
        alumno = self._alumno_o_alumna()
        preparado = self._preparado_o_preparada()
        if ruta.suffix.lower() in {".md", ".txt"}:
            try:
                contenido = ruta.read_text(encoding="utf-8")
            except Exception:
                contenido = ""
            return (
                f"{nombre}, este es el guion de teoría de la clase. Primero léelo como una explicación, "
                "después relaciona el objetivo con los ejercicios asociados y finalmente usa el examen de clase para comprobarlo.\n\n"
                + contenido
            ).strip()
        if "postura_mala_correcta" in n:
            return (
                f"{nombre}, esta imagen es muy importante porque antes de tocar notas necesitamos preparar el cuerpo. Si el cuerpo se coloca mal, la mano suele tocar peor aunque sepas la nota correcta.\n\n"
                "1. Qué debes mirar en la parte incorrecta\n"
                "Observa la espalda encorvada, la cabeza caída y los hombros cerrados. Esa posición obliga a los brazos a trabajar con tensión. "
                "Además, si el alumno se acerca demasiado al piano, los codos se quedan sin espacio y la muñeca termina forzada.\n\n"
                "2. Qué debes mirar en la parte correcta\n"
                "La espalda está recta sin estar rígida, los hombros están bajos y relajados, y los antebrazos llegan al teclado de forma natural. "
                "No buscamos una postura militar; buscamos una postura estable, cómoda y preparada para moverse.\n\n"
                "3. Para qué sirve\n"
                "Sirve para evitar cansancio, tensión en cuello y hombros, dedos torpes y errores de precisión. Una mala postura puede parecer poca cosa al principio, "
                "pero cuando practicas varios minutos se nota enseguida: la mano se endurece y el sonido se vuelve más brusco.\n\n"
                "4. Ejemplo práctico\n"
                "Siéntate y prueba dos segundos encorvado. Nota cómo los hombros se van hacia delante. Después enderézate, relaja hombros y deja que los brazos caigan. "
                "Esa segunda sensación es la que queremos antes de tocar.\n\n"
                f"Ahora quiero comprobarlo, {nombre}: ¿sabes distinguir en la imagen qué postura es incorrecta y cuál es correcta? Respóndeme 'sí' o 'no'."
            )
        if "postura_al_piano" in n:
            return (
                f"{nombre}, esta imagen es una guía paso a paso para colocarte frente al piano antes de tocar. No la mires como una lista: úsala como una revisión técnica.\n\n"
                "1. Siéntate al borde del banco\n"
                "No te sientes demasiado atrás. Si te sientas al borde, el cuerpo queda más libre y puedes equilibrarte mejor. El peso no debe caer completamente hacia atrás.\n\n"
                "2. Espalda recta y hombros relajados\n"
                "La espalda debe crecer hacia arriba, pero sin tensión. Los hombros no deben subir hacia las orejas. Si notas los hombros duros, suelta aire y déjalos caer.\n\n"
                "3. Codos a nivel del teclado\n"
                "Los codos no deben quedar ni muy bajos ni muy altos. Si están muy bajos, la muñeca se hunde; si están muy altos, la mano se vuelve rígida. "
                "La referencia es que el antebrazo llegue al teclado con naturalidad.\n\n"
                "4. Pies apoyados en el suelo\n"
                "Los pies dan estabilidad. Aunque todavía no usemos pedal, no deben colgar ni moverse sin control. Si el alumno es pequeño, más adelante se puede usar un apoyo.\n\n"
                "5. Muñecas relajadas\n"
                "La muñeca es el puente entre brazo y dedos. Si está tensa, el dedo pierde libertad. Queremos una muñeca viva, alineada y flexible.\n\n"
                f"Antes de continuar, {nombre}, dime si puedes revisar esos cinco puntos en tu propia postura: banco, espalda, codos, pies y muñecas."
            )
        if "mano_correcta" in n:
            return (
                f"{nombre}, vamos a estudiar esta imagen como en una clase real, no como una simple foto.\n\n"
                "1. Qué debes mirar primero\n"
                "Mira la muñeca. No debe estar hundida hacia abajo ni levantada con tensión. Tiene que estar relajada y alineada con el antebrazo.\n\n"
                "2. Qué debes mirar después\n"
                "Mira los dedos. Están curvados, no rectos. Esa curva permite que la yema del dedo caiga sobre la tecla con control.\n\n"
                "3. Para qué sirve\n"
                "Sirve para tocar sin rigidez. Si el dedo está plano, cuesta más controlar la tecla, la mano se cansa antes y la precisión baja. "
                "Si el dedo está curvado, el movimiento es más corto y más limpio.\n\n"
                "4. Ejemplo práctico\n"
                "Coloca la mano sobre una mesa como si sujetaras una pelota pequeña. Esa sensación es parecida a la que buscamos en el piano. "
                "Después apoya solo la yema de un dedo y baja suavemente, sin golpear.\n\n"
                "Antes de seguir, quiero comprobarlo: ¿entiendes por qué no conviene tocar con los dedos planos? "
                "Respóndeme 'sí' o 'no' en el cuadro del profesor."
            )
        if "digitacion" in n and n.endswith(".gif"):
            return (
                f"{nombre}, este GIF es una guía de movimiento. No está solo para decorar: sirve para que relaciones dedo, número y tecla.\n\n"
                "1. Qué significa la numeración\n"
                "Dedo 1: pulgar. Dedo 2: índice. Dedo 3: corazón. Dedo 4: anular. Dedo 5: meñique.\n\n"
                "2. Qué debes observar en la animación\n"
                "Mira qué dedo se ilumina, después mira qué tecla se ilumina. La idea es que tu cerebro conecte tres cosas: número, dedo y lugar del teclado.\n\n"
                "3. Para qué sirve en una partitura\n"
                "Cuando veas un número sobre una nota, ese número te dice qué dedo usar. Esto evita que cambies de dedo al azar. "
                "Una buena digitación hace que una frase musical sea más fácil y más estable.\n\n"
                "4. Ejemplo\n"
                "Si una nota tiene el número 2 encima, no debes usar cualquier dedo: debes buscar el índice. "
                "Si aparece el 5, usas el meñique. En manos pequeñas, esto es todavía más importante porque ayuda a ordenar el movimiento.\n\n"
                f"Ahora dime, {nombre}: cuando ves el número 2, ¿sabes qué dedo debes usar? Respóndeme 'sí' o 'no'."
            )
        if "digitacion" in n:
            return (
                f"{nombre}, esta imagen resume la digitación básica. Es una de las primeras herramientas de cualquier pianista.\n\n"
                "1. Mano izquierda\n"
                "El pulgar sigue siendo 1, aunque esté hacia el centro del cuerpo. El meñique es 5.\n\n"
                "2. Mano derecha\n"
                "También aquí el pulgar es 1 y el meñique es 5. La numeración no cambia por ser otra mano.\n\n"
                "3. Por qué es importante\n"
                "La digitación sirve para tocar de forma ordenada. Sin digitación, puedes acertar una nota una vez, pero repetirla igual varias veces será más difícil.\n\n"
                "4. Ejercicio mental\n"
                "Levanta una mano y di en voz alta: 1 pulgar, 2 índice, 3 corazón, 4 anular, 5 meñique. Después repítelo con la otra mano.\n\n"
                "Quiero saber si ha quedado claro: ¿puedes identificar ya los dedos del 1 al 5?"
            )
        if "patron_teclado" in n:
            return (
                f"{nombre}, esta imagen explica el mapa del teclado. El piano parece enorme, pero se entiende por patrones.\n\n"
                "1. Observa las teclas negras\n"
                "No aparecen una por una. Se agrupan en bloques de dos y bloques de tres. Ese patrón se repite en todo el teclado.\n\n"
                "2. Para qué sirve\n"
                "Sirve para orientarte sin memorizar ochenta y ocho teclas. Solo necesitas reconocer el patrón.\n\n"
                "3. Cómo encontrar DO\n"
                "Busca un grupo de dos teclas negras. La tecla blanca que queda justo antes de ese grupo es DO. "
                "Ese DO se repite en distintas alturas: grave, medio y agudo.\n\n"
                "4. Ejemplo\n"
                "Si estás perdido en el teclado, no busques letras. Busca visualmente dos teclas negras juntas. Cuando las encuentres, mira la tecla blanca de la izquierda: ahí tienes DO.\n\n"
                "Antes de continuar: ¿entiendes cómo usar los grupos de dos teclas negras para encontrar DO?"
            )
        if "teclas_blancas" in n:
            return (
                f"{nombre}, esta imagen muestra la secuencia de las teclas blancas.\n\n"
                "1. Secuencia básica\n"
                "DO, RE, MI, FA, SOL, LA, SI. Después de SI vuelve DO otra vez.\n\n"
                "2. Para qué sirve\n"
                "Sirve para empezar a leer melodías y ubicar notas sin depender todavía de sostenidos y bemoles.\n\n"
                "3. Ejemplo\n"
                "Si empiezas en DO y avanzas una tecla blanca, llegas a RE. Otra más, MI. Otra más, FA. Así puedes construir pasos sencillos en el teclado.\n\n"
                "4. Error típico\n"
                "No pienses que solo hay un DO. Hay muchos DO repetidos en distintas zonas del piano. El nombre se repite, pero cambia la altura.\n\n"
                f"Dime, {nombre}: si estás en MI y subes una tecla blanca, ¿sabes que llegas a FA?"
            )
        return (
            f"{nombre}, este material visual pertenece al nivel cero. Obsérvalo despacio. Primero identifica qué elemento se destaca, después piensa para qué sirve, "
            "y por último intenta explicarlo con tus palabras. Si puedes explicarlo, estás más cerca de poder tocarlo. ¿Lo has entendido?"
        )

    def _pagina_practica(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        t = QLabel("Práctica")
        t.setObjectName("TituloSeccionInicio")
        lay.addWidget(t)
        texto = QLabel(
            "Desde aquí puedes pasar de la teoría visual a la práctica real. "
            "En la v1.9.6, el Nivel 0 ya tiene ejercicios interactivos de teclado: tocar Do, Re, Mi y pequeñas secuencias como Do-Re-Mi. "
            "Primero se practica sin penalización y después se hace el ejercicio evaluable."
        )
        texto.setWordWrap(True)
        lay.addWidget(texto)
        fila = QHBoxLayout()
        self.combo_nivel = QComboBox()
        for nivel in self.niveles:
            self.combo_nivel.addItem(nivel.get("nombre", nivel.get("id", "Nivel")), nivel.get("id"))
        btn_manual = self._boton_accion("Empezar desde nivel seleccionado", "#7C3AED")
        btn_practica_n0 = self._boton_accion("Abrir práctica Nivel 0", "#0EA5E9")
        btn_cont = self._boton_accion("Continuar progreso", "#16A34A")
        btn_eval = self._boton_accion("Evaluación inicial", "#2563EB")
        btn_manual.clicked.connect(self._emitir_manual)
        btn_practica_n0.clicked.connect(lambda: self.iniciar_manual.emit("inicial"))
        btn_cont.clicked.connect(self.continuar.emit)
        btn_eval.clicked.connect(self.iniciar_evaluacion.emit)
        fila.addWidget(QLabel("Nivel:"))
        fila.addWidget(self.combo_nivel, 1)
        lay.addLayout(fila)
        lay.addWidget(btn_manual)
        lay.addWidget(btn_practica_n0)
        lay.addWidget(btn_cont)
        lay.addWidget(btn_eval)
        lay.addStretch(1)
        return w

    def _pagina_como_funciona(self):
        return self._scroll_texto(
            "Cómo funciona",
            "1. Al iniciar, el programa pregunta con quién habla. Guarda el nombre y el tratamiento en data/perfil_alumno.json.\n"
            "2. Puedes empezar con evaluación inicial o elegir nivel manualmente.\n"
            "3. Cada lección tiene teoría, ejemplo, práctica y ejercicio evaluable.\n"
            "4. El alumno no debe avanzar hasta superar el ejercicio.\n"
            "5. Cada cierto tiempo habrá examen de nivel.\n"
            "6. El avatar permanece visible en todas las pantallas. Debe leer, explicar, responder y guiar, no solo decorar.\n"
            "7. El material visual se añade por carpetas para evitar ZIPs enormes y poder actualizar imágenes, GIFs y vídeos sin tocar el código."
        )

    def _scroll_texto(self, titulo, texto):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        t = QLabel(titulo)
        t.setObjectName("TituloSeccionInicio")
        lay.addWidget(t)

        cuerpo = QTextEdit()
        cuerpo.setReadOnly(True)
        cuerpo.setPlainText(str(texto or ""))
        cuerpo.setObjectName("TextoSeccionInicio")
        cuerpo.setLineWrapMode(QTextEdit.WidgetWidth)
        cuerpo.setMinimumHeight(420)
        lay.addWidget(cuerpo, 1)
        return w

    def mostrar_inicio(self):
        self.stack.setCurrentWidget(self.pagina_inicio)
        self._actualizar_textos_personales()
        self._texto_actual = (
            f"Hola, {self.nombre_alumno}. Esta es la pantalla de inicio. Aquí puedes decidir por dónde empezar. "
            "El botón de evaluación inicial sirve para calcular tu punto de partida. Continuar progreso recupera lo último que estabas haciendo. "
            "Teoría desde cero abre explicaciones con imágenes y GIFs. Práctica abre ejercicios. Yo estaré presente para leerte la pantalla, explicarte los conceptos y resolver dudas."
        )

    def mostrar_curso(self):
        try:
            idx = self.stack.indexOf(self.pagina_curso)
            self.stack.removeWidget(self.pagina_curso)
            self.pagina_curso.deleteLater()
            self.pagina_curso = self._pagina_curso()
            self.stack.insertWidget(max(0, idx), self.pagina_curso)
        except Exception:
            pass
        self.stack.setCurrentWidget(self.pagina_curso)
        self._texto_actual = (
            "Esta es la presentación completa del curso. Aquí ves todos los niveles disponibles, el objetivo de cada nivel, "
            "sus módulos, las clases previstas y el objetivo didáctico de cada clase. La estructura correcta es siempre: "
            "clase teórica, ejercicios asociados, examen de clase y, al terminar el nivel, examen global."
        )

    def mostrar_teoria(self):
        self.stack.setCurrentWidget(self.pagina_teoria)
        # Repara automáticamente progresos antiguos/inconsistentes: si una lección
        # ya está superada pero sigue marcada como actual, pasa a la primera pendiente.
        self._actualizar_panel_leccion_guiada(emitir_texto=False, corregir_bloqueo=True)
        self._texto_actual = getattr(self, "_texto_actual", "") or self.texto_teoria_nivel_0()

    def texto_teoria_nivel_0(self):
        return (
            f"{self.nombre_alumno}, estamos en teoría desde cero, nivel cero. Lo primero es la postura del cuerpo y después la postura de las manos. "
            "Observa primero las imágenes de postura al piano: debes sentarte al borde del banco, mantener la espalda recta sin tensión, relajar hombros, apoyar los pies y colocar los codos a nivel del teclado. "
            "Después observa la imagen de mano correcta: la muñeca debe estar relajada, ni hundida ni levantada en exceso. "
            "Los dedos deben estar curvados, porque así el peso cae mejor sobre la tecla y evitamos tensión. "
            "Después mira la digitación uno a cinco. El dedo uno es el pulgar, el dos es el índice, el tres es el corazón, el cuatro el anular y el cinco el meñique. "
            "Esto sirve para que cuando una partitura o un ejercicio indique un número, sepas qué dedo usar sin dudar. "
            "El GIF de digitación muestra el orden del movimiento. Debes mirar cómo se activa un dedo cada vez y asociarlo con la tecla iluminada. "
            "Luego está el patrón del teclado. Las teclas negras no están repartidas al azar: se agrupan en dos y en tres. Ese patrón es la brújula del piano. "
            "Para encontrar DO, busca un grupo de dos teclas negras; DO suele estar justo antes de ese grupo. "
            "Por último, las teclas blancas se nombran DO, RE, MI, FA, SOL, LA y SI. Esta secuencia se repite por todo el teclado. "
            "Pulsa una imagen para verla grande. Yo te la explicaré de forma más técnica, con ejemplos, y después te preguntaré si lo has entendido antes de pasar a la práctica."
        )

    def mostrar_practica(self):
        self.stack.setCurrentWidget(self.pagina_practica)
        self._texto_actual = (
            "En práctica puedes continuar tu progreso, elegir nivel o hacer la evaluación inicial. Primero escucha la explicación, luego practica sin prisa y finalmente haz el ejercicio evaluable."
        )

    def mostrar_como_funciona(self):
        self.stack.setCurrentWidget(self.pagina_como)
        self._texto_actual = (
            "El sistema identifica al alumno, explica la teoría, muestra ejemplos, deja practicar y solo permite avanzar cuando el ejercicio se supera. "
            "El avatar debe acompañarte de forma constante, cercana y explícita."
        )

    def _leer_actual(self):
        self.leer_texto.emit(getattr(self, "_texto_actual", ""))

    def _emitir_manual(self):
        nivel = self.combo_nivel.currentData()
        self.seleccionar_nivel_guiado(nivel)
        self.iniciar_manual.emit(nivel)
