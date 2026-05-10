import time
import json
import random
import re
import warnings
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QTextEdit, QLineEdit, QMessageBox, QFrame, QGroupBox,
    QSlider, QComboBox, QCheckBox, QSpinBox, QGridLayout, QProgressBar,
    QTabWidget, QDialog, QFileDialog, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QImage, QPixmap, QGuiApplication

from app.config import APP_NOMBRE, APP_VERSION, DATA_DIR
from app.core.datos import RepositorioDatos
from app.core.progreso import GestorProgreso
from app.core.ajustes import GestorAjustes
from app.core.evaluador import Evaluador
from app.core.motor_ejercicios import MotorEjercicios
from app.core.profesor_virtual import ProfesorVirtual
from app.core.perfil_alumno import GestorPerfilAlumno
from app.core.profesor_didactico import ProfesorDidactico
from app.core.biblioteca import BibliotecaPedagogica
from app.core.repaso_inteligente import RepasoInteligente
from app.core.plan_personalizado import GestorPlanPersonalizado
from app.core.ruta_curso import GestorRutaCurso
from app.core.tecnica_diaria import GestorTecnicaDiaria
from app.core.sesion_diaria import GestorSesionDiaria
from app.core.repertorio import GestorRepertorio
from app.core.pulso_ritmo import GestorPulsoRitmo
from app.core.lectura_partitura import GestorLecturaPartitura
from app.core.comprobacion_docente import ComprobacionDocente
from app.core.historial_alumno import HistorialAlumno
from app.core.analisis_midi_pro import AnalizadorMidiPro
from app.core.entradas_alumno_pro import GestorEntradasAlumnoPro
from app.core.hanon import GestorHanon
from app.core.midi_didactico import GestorMidiDidactico, PiezaMidiDidactica, NotaMidiDidactica
from app.core.musical_clock import RelojMusical
from app.core.notas import normalizar_nota
from app.core.politica_midi_externo import PoliticaMidiExterno
from app.core.selector_pistas_midi_externo import SelectorPistasMidiExterno
from app.ui.pantalla_inicio import PantallaInicio
from app.ui.piano_virtual import PianoVirtual
from app.ui.avatar_widget import AvatarWidget
from app.ui.dialogo_configuracion import DialogoConfiguracion
from app.ui.dialogo_alumno import DialogoAlumno
from app.ui.dialogo_imagen_teoria import DialogoImagenTeoria
from app.ui.dialogo_estado_alumno import DialogoEstadoAlumno
from app.ui.dialogo_plan_personalizado import DialogoPlanPersonalizado
from app.ui.dialogo_ruta_curso import DialogoRutaCurso
from app.ui.dialogo_tecnica_diaria import DialogoTecnicaDiaria
from app.ui.dialogo_sesion_diaria import DialogoSesionDiaria
from app.ui.dialogo_repertorio import DialogoRepertorio
from app.ui.dialogo_pulso_ritmo import DialogoPulsoRitmo
from app.ui.dialogo_pulso_practica import DialogoPulsoPractica
from app.ui.dialogo_lectura_partitura import DialogoLecturaPartitura
from app.ui.dialogo_reto_comprension import DialogoRetoComprension
from app.ui.pizarra_musical import PizarraMusicalProfesor
from app.ui.celebracion_overlay import CelebracionOverlay
from app.audio.audio_engine import AudioEngine
from app.audio.audio_input_manager import AudioInputManager
from app.midi.midi_manager import MidiManager
from app.vision.camera_manager import CameraManager
from app.recognition.reconocedor_musical import ReconocedorMusical
from app.ia.profesor_ia import ProfesorIA
from app.voice.voz_avatar import VozAvatar


class MidiBridge(QObject):
    nota_on = Signal(str, int, int)
    nota_off = Signal(str, int, int)
    raw = Signal(str)


class VozBridge(QObject):
    inicio = Signal()
    fin = Signal()
    error = Signal(str)


class BarraProgresoInteractiva(QProgressBar):
    """Barra de progreso clicable/arrastrable para el narrador."""

    posicion_cambiada = Signal(float)

    def _emitir_posicion(self, event):
        ancho = max(1, self.width())
        try:
            x = event.position().x()
        except Exception:
            x = event.x()
        ratio = max(0.0, min(1.0, float(x) / float(ancho)))
        self.setValue(int(ratio * self.maximum()))
        self.posicion_cambiada.emit(ratio)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._emitir_posicion(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._emitir_posicion(event)
            event.accept()
            return
        super().mouseMoveEvent(event)


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NOMBRE} — {APP_VERSION}")
        self._ajustar_tamano_inicial_seguro()

        self.repo = RepositorioDatos()
        self.progreso = GestorProgreso()
        self.ajustes = GestorAjustes()
        self.gestor_perfil_alumno = GestorPerfilAlumno()
        self.perfil_alumno = self.gestor_perfil_alumno.perfil
        self.historial_alumno = HistorialAlumno(self.perfil_alumno.nombre or "alumno_principal")
        self.analizador_midi_pro = AnalizadorMidiPro()
        self.entradas_pro = GestorEntradasAlumnoPro()
        self.midi_didactico = GestorMidiDidactico()
        self.hanon = GestorHanon()
        self.politica_midi_externo = PoliticaMidiExterno()
        self.selector_pistas_midi_externo = SelectorPistasMidiExterno(DATA_DIR / "midi_externo")
        self._ultimo_midi_externo_aceptado = ""
        self._ultimo_plan_midi_externo = None
        self.audio_entrada = AudioInputManager()
        self._ultima_entrada_alumno = {"origen": "", "velocity": None, "canal": None, "nota": "", "ts": 0.0}
        self._midi_velocity_min = None
        self._midi_velocity_max = None
        self.evaluador = Evaluador()
        self.profesor = ProfesorVirtual()
        self.profesor_didactico = ProfesorDidactico()
        self.biblioteca = BibliotecaPedagogica()
        self.repaso_ia = RepasoInteligente(self.repo)
        self.plan_personalizado = GestorPlanPersonalizado()
        self.ruta_curso = GestorRutaCurso()
        self.tecnica_diaria = GestorTecnicaDiaria()
        self.sesion_diaria = GestorSesionDiaria()
        self.repertorio = GestorRepertorio()
        self.pulso_ritmo = GestorPulsoRitmo()
        self._pulso_practica_panel = None
        self.lectura_partitura = GestorLecturaPartitura()
        self.comprobador_docente = ComprobacionDocente()
        self.profesor_ia = ProfesorIA()
        self._ultimo_contexto_profesor = ""
        self._ultimo_titulo_profesor = ""
        self._reto_pizarra_notas_esperadas = set()
        self._reto_pizarra_notas_pendientes = set()
        self._reto_pizarra_texto = ""
        self._secuencia_pizarra_esperada = []
        self._secuencia_pizarra_pos = 0
        self._secuencia_pizarra_activa = False
        self._midi_lectura_activa = True
        self._midi_lectura_aciertos = 0
        self._midi_lectura_errores = 0
        self._pulso_pizarra_activo = False
        self._pulso_pizarra_secuencia = []
        self._pulso_pizarra_pos = 0
        self._pulso_pizarra_bpm = 60
        self._pulso_pizarra_beat_actual = 0
        self._pulso_pizarra_ultimo_beat_ts = 0.0
        self._pulso_pizarra_tolerancia = 0.34
        self._pulso_pizarra_timer = QTimer(self)
        self._pulso_pizarra_timer.timeout.connect(self._tick_pulso_pizarra)
        self._hanon_metronomo_practica_activo = True
        self._hanon_metronomo_demo_activo = True
        self._hanon_metronomo_ultimo_click_inicio = 0.0
        self._dialogo_imagen_teoria = None
        self.eval_inicial_preguntas = []
        self.eval_inicial_indice = 0
        self.eval_inicial_aciertos = 0
        self.eval_inicial_bloqueada = False
        self.eval_inicial_detalle = []
        self.eval_inicial_nivel_recomendado = ""
        self.examen_actual = None
        self.fase_didactica = "clase"
        self.ejercicio_desbloqueado = False
        self.secuencia_alumno = []
        self.secuencia_demo = []
        self.indice_demo = 0
        self.aciertos_examen = 0
        self.fallos_examen = 0
        self.motor = MotorEjercicios(self.repo)
        self.audio = AudioEngine()
        self.midi = MidiManager()
        self.camera = CameraManager()
        self.voz_avatar = VozAvatar()
        self.voz_bridge = VozBridge()
        self.voz_bridge.inicio.connect(lambda: self.avatar.iniciar_habla() if hasattr(self, "avatar") else None)
        self.voz_bridge.fin.connect(lambda: self.avatar.parar_habla() if hasattr(self, "avatar") else None)
        self.voz_bridge.inicio.connect(self._voz_inicio_ui)
        self.voz_bridge.fin.connect(self._voz_fin_ui)
        self.voz_bridge.error.connect(self._mostrar_error_voz)
        self.reconocedor = ReconocedorMusical()
        self.ultimo_midi_raw = ""
        self._ultimo_midi_raw_ui_ts = 0.0
        self._ultimo_midi_raw_texto = ""
        self.secuencia_alumno = []
        self.timer_camara = QTimer(self)
        self.timer_camara.setInterval(33)  # ~30 fps
        self.timer_camara.timeout.connect(self._actualizar_vista_camara)

        self.timer_audio_entrada = QTimer(self)
        self.timer_audio_entrada.setInterval(650)
        self.timer_audio_entrada.timeout.connect(self._actualizar_escucha_audio_pro)

        self.timer_midi_didactico = QTimer(self)
        self.timer_midi_didactico.setInterval(35)
        self.timer_midi_didactico.timeout.connect(self._tick_midi_didactico)
        self._midi_didactico_modo = "clase"
        self._midi_didactico_tiempo_ms = 0
        self._midi_didactico_ultimo_ts = 0.0
        self._midi_didactico_notas_sonando = set()
        self._midi_didactico_compas_anunciado = 0
        self.reloj_musical = RelojMusical()
        self._midi_practica_indice = 0
        self._midi_practica_ultimo_beat_ts = 0.0
        self._midi_practica_tolerancia_ms = 180
        self._midi_practica_velocity_objetivo = 80
        self.timer_hanon_demo = QTimer(self)
        self.timer_hanon_demo.setInterval(35)
        self.timer_hanon_demo.timeout.connect(self._tick_hanon_demo)
        self._hanon_modelo = None
        self._hanon_guion = {}
        self._hanon_pizarra = {}
        self._hanon_rubrica = {}
        self._hanon_examen = {}
        self._hanon_pieza = None
        self._hanon_notas = []
        self._hanon_demo_tiempo_ms = 0
        self._hanon_demo_ultimo_ts = 0.0
        self._hanon_demo_sonando = set()
        self._hanon_practica_activa = False
        self._hanon_examen_activo = False
        self._hanon_practica_indice = 0
        self._hanon_practica_ultimo_beat_ts = 0.0
        self._hanon_practica_tolerancia_ms = 180
        self._hanon_eventos = []
        self._hanon_notas_activas_alumno = {}
        self._hanon_paso_actual = 0

        self.midi_bridge = MidiBridge()
        self.midi_bridge.nota_on.connect(self._midi_note_on)
        self.midi_bridge.nota_off.connect(self._midi_note_off)
        self.midi_bridge.raw.connect(self._midi_raw)
        self.midi.on_note_on = self.midi_bridge.nota_on.emit
        self.midi.on_note_off = self.midi_bridge.nota_off.emit
        self.midi.on_raw = self.midi_bridge.raw.emit

        self._configurar_audio_desde_ajustes()

        self.stack = QStackedWidget()
        self.avatar = AvatarWidget(self.ajustes.ajustes.avatar_tipo)
        self.panel_avatar_global = self._crear_panel_avatar_global()

        contenedor_principal = QWidget()
        layout_principal = QHBoxLayout(contenedor_principal)
        layout_principal.setContentsMargins(8, 8, 8, 8)
        layout_principal.setSpacing(10)

        # Piano global: no pertenece a una sola pantalla del stack.
        # Así sigue disponible cuando se cambia a Hanon, Partitura, Pulso,
        # Repertorio, Evaluación o cualquier panel práctico integrado.
        self.panel_central_con_piano = QFrame()
        self.panel_central_con_piano.setObjectName("PanelCentralConPianoGlobal")
        layout_central_piano = QVBoxLayout(self.panel_central_con_piano)
        layout_central_piano.setContentsMargins(0, 0, 0, 0)
        layout_central_piano.setSpacing(6)
        layout_central_piano.addWidget(self.stack, 1)
        self.marco_piano_global = self._crear_marco_piano_global()
        layout_central_piano.addWidget(self.marco_piano_global, 0)

        layout_principal.addWidget(self.panel_central_con_piano, 1)
        layout_principal.addWidget(self.panel_avatar_global, 0)
        self.setCentralWidget(contenedor_principal)
        self.celebracion_overlay = CelebracionOverlay(contenedor_principal)
        self.celebracion_overlay.setGeometry(contenedor_principal.rect())

        self.pantalla_inicio = PantallaInicio(self.repo.obtener_niveles())
        self.pantalla_inicio.set_avatar_tipo(getattr(self.ajustes.ajustes, "avatar_tipo", "chica"))
        self.pantalla_inicio.set_perfil_alumno(self.perfil_alumno.nombre or "alumno", self.perfil_alumno.tratamiento)
        self.pantalla_inicio.iniciar_evaluacion.connect(self.mostrar_evaluacion)
        self.pantalla_inicio.iniciar_manual.connect(self.iniciar_desde_nivel)
        self.pantalla_inicio.continuar.connect(self.continuar_progreso)
        self.pantalla_inicio.leer_texto.connect(self._hablar_con_avatar)
        self.pantalla_inicio.imagen_activada.connect(self._abrir_dialogo_imagen_teoria)
        self.pantalla_inicio.celebracion.connect(self._celebrar_logro)
        self.pantalla_inicio.abrir_hanon.connect(self.abrir_hanon)
        self.pantalla_estudio = self._crear_pantalla_estudio()
        self.pantalla_evaluacion = self._crear_pantalla_evaluacion()
        self.pantalla_hanon = self._crear_pantalla_hanon()
        self.stack.addWidget(self.pantalla_inicio)
        self.stack.addWidget(self.pantalla_estudio)
        self.stack.addWidget(self.pantalla_evaluacion)
        self.stack.addWidget(self.pantalla_hanon)
        try:
            self.stack.currentChanged.connect(self._actualizar_visibilidad_piano_global)
            self._actualizar_visibilidad_piano_global()
        except Exception:
            pass
        self._aplicar_estilo()
        self._confirmar_alumno_al_arrancar()
        self._actualizar_dialogo_avatar(self._mensaje_bienvenida_avatar())
        QTimer.singleShot(300, self._arrancar_audio_si_activo)
        QTimer.singleShot(700, self._conectar_midi_preferido_si_procede)
        QTimer.singleShot(1200, self._precalentar_voz_piper)



    def _ajustar_tamano_inicial_seguro(self):
        """Arranca dentro del área visible de la pantalla.

        La versión anterior abría a 1320x860, que en portátiles de 1366x768
        queda fuera de la pantalla por la barra superior y bordes del sistema.
        Esta función calcula un tamaño inicial proporcional al monitor real.
        """
        try:
            pantalla = QGuiApplication.primaryScreen()
            geo = pantalla.availableGeometry() if pantalla else None
            if geo:
                ancho = min(1180, max(760, int(geo.width() * 0.92)))
                alto = min(720, max(520, int(geo.height() * 0.86)))
                self.resize(ancho, alto)
                self.move(
                    geo.x() + max(0, (geo.width() - ancho) // 2),
                    geo.y() + max(0, (geo.height() - alto) // 2),
                )
                return
        except Exception:
            pass
        self.resize(1080, 680)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "celebracion_overlay") and self.centralWidget() is not None:
            self.celebracion_overlay.setGeometry(self.centralWidget().rect())

    def _celebrar_logro(self, tipo: str, titulo: str):
        """Lanza celebración visual y música al superar lecciones, retos o niveles."""
        nombre = self._nombre_alumno()
        try:
            if hasattr(self, "celebracion_overlay"):
                self.celebracion_overlay.setGeometry(self.centralWidget().rect())
                self.celebracion_overlay.start(tipo or "leccion", titulo or "Logro superado", nombre)
        except Exception:
            pass
        try:
            self.audio.sonido_celebracion(tipo or "leccion")
        except Exception:
            # La celebración visual no debe fallar aunque el equipo no tenga audio activo.
            pass

    def _confirmar_alumno_al_arrancar(self):
        """Pregunta siempre quién es el alumno antes de empezar la sesión."""
        dialogo = DialogoAlumno(self.perfil_alumno, self)
        while True:
            if dialogo.exec() == QDialog.Accepted:
                nombre, tratamiento = dialogo.datos()
                if nombre:
                    self.perfil_alumno = self.gestor_perfil_alumno.guardar(nombre, tratamiento)
                    if hasattr(self, "pantalla_inicio"):
                        self.pantalla_inicio.set_perfil_alumno(self.perfil_alumno.nombre, self.perfil_alumno.tratamiento)
                    if hasattr(self, "lbl_titulo_avatar_global"):
                        self.lbl_titulo_avatar_global.setText(f"Profesor virtual de {self.perfil_alumno.nombre}")
                    return
            # No se permite continuar sin identificar al alumno.
            QMessageBox.information(self, "Alumno necesario", "Necesito saber con quién estoy hablando para poder iniciar la clase.")

    def _alumno_o_alumna(self) -> str:
        try:
            return self.perfil_alumno.alumno_o_alumna
        except Exception:
            return "alumno"

    def _nombre_alumno(self) -> str:
        try:
            return self.perfil_alumno.nombre or "alumno"
        except Exception:
            return "alumno"

    def _mensaje_bienvenida_avatar(self) -> str:
        nombre = self._nombre_alumno()
        alumno = self._alumno_o_alumna()
        return (
            f"Hola, {nombre}. Ya sé que estoy hablando contigo y he guardado tu perfil para tratarte como {alumno}. "
            "Voy a estar presente en todas las pantallas. Mi trabajo no es solo leer botones: debo explicarte qué estás viendo, "
            "para qué sirve cada imagen, cuándo debes mirar, cuándo debes practicar y cuándo conviene repetir. "
            "Puedes pulsar Leer pantalla para que te explique la pantalla actual, o puedes preguntarme directamente. "
            "Cuando abras una imagen, te la explicaré como si estuviéramos en clase: qué debes mirar, para qué sirve, un ejemplo y una comprobación de comprensión."
        )

    def _crear_panel_avatar_global(self):
        """Panel fijo del profesor virtual.

        Permanece visible aunque cambie la pantalla central: inicio, teoría,
        evaluación o práctica. No se reparenta ni se destruye entre vistas.
        """
        panel = QFrame()
        panel.setObjectName("PanelAvatarGlobal")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(260)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self.lbl_titulo_avatar_global = QLabel("Profesor virtual")
        self.lbl_titulo_avatar_global.setObjectName("TituloAvatarGlobal")
        self.lbl_titulo_avatar_global.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_titulo_avatar_global)
        # El avatar visible debe estar solo en el panel derecho global.
        self.avatar.show()
        lay.addWidget(self.avatar, 0, Qt.AlignHCenter)

        self.txt_avatar_dialogo = QTextEdit()
        self.txt_avatar_dialogo.setReadOnly(True)
        self.txt_avatar_dialogo.setMinimumHeight(180)
        self.txt_avatar_dialogo.setMaximumHeight(260)
        self.txt_avatar_dialogo.setPlaceholderText("El profesor responderá aquí.")
        lay.addWidget(self.txt_avatar_dialogo)

        fila_voz = QHBoxLayout()
        fila_voz.setSpacing(4)
        btn_leer = self._crear_boton_icono_transporte("▶", "#0EA5E9", "Leer la pantalla actual")
        btn_leer.clicked.connect(self.leer_pantalla_actual)
        btn_pausa = self._crear_boton_icono_transporte("Ⅱ", "#F59E0B", "Pausar o reanudar narración")
        btn_pausa.clicked.connect(self.pausar_reanudar_voz)
        btn_stop = self._crear_boton_icono_transporte("■", "#64748B", "Detener narración")
        btn_stop.clicked.connect(self.stop_voz)
        fila_voz.addWidget(btn_leer)
        fila_voz.addWidget(btn_pausa)
        fila_voz.addWidget(btn_stop)
        fila_voz.addStretch(1)
        lay.addLayout(fila_voz)
        lay.addWidget(self.crear_barra_tiempo_profesor())

        self.input_avatar_dialogo = QLineEdit()
        self.input_avatar_dialogo.setPlaceholderText("Pregunta al profesor...")
        self.input_avatar_dialogo.returnPressed.connect(self.enviar_dialogo_avatar)
        lay.addWidget(self.input_avatar_dialogo)

        btn_enviar = self._crear_boton_color("Preguntar", "#2563EB", altura=32)
        btn_enviar.clicked.connect(self.enviar_dialogo_avatar)
        lay.addWidget(btn_enviar)

        # Botón fijo para que el nuevo panel no quede oculto en cabeceras estrechas.
        btn_estado_alumno_global = self._crear_boton_color("Estado", "#0F766E", altura=32)
        btn_estado_alumno_global.setToolTip("Abre el diagnóstico de progreso, fallos frecuentes y Repaso IA.")
        btn_estado_alumno_global.clicked.connect(self.mostrar_estado_alumno)
        lay.addWidget(btn_estado_alumno_global)

        btn_plan_alumno_global = self._crear_boton_color("Alumno", "#7C3AED", altura=32)
        btn_plan_alumno_global.setToolTip("Abre el plan personalizado creado tras la evaluación inicial.")
        btn_plan_alumno_global.clicked.connect(self.mostrar_plan_personalizado)
        lay.addWidget(btn_plan_alumno_global)

        btn_ruta_curso_global = self._crear_boton_color("Ruta curso", "#0EA5E9", altura=32)
        btn_ruta_curso_global.setToolTip("Abre el mapa completo del curso por niveles.")
        btn_ruta_curso_global.clicked.connect(self.mostrar_ruta_curso)
        lay.addWidget(btn_ruta_curso_global)

        btn_tecnica_global = self._crear_boton_color("Técnica diaria", "#16A34A", altura=32)
        btn_tecnica_global.setToolTip("Abre la rutina técnica diaria tipo Hanon/preparatoria.")
        btn_tecnica_global.clicked.connect(self.mostrar_tecnica_diaria)
        lay.addWidget(btn_tecnica_global)

        btn_sesion_global = self._crear_boton_color("Sesión diaria", "#F59E0B", altura=32)
        btn_sesion_global.setToolTip("Abre la sesión completa: preparación, técnica, teoría, práctica, repaso y cierre.")
        btn_sesion_global.clicked.connect(self.mostrar_sesion_diaria)
        lay.addWidget(btn_sesion_global)

        btn_repertorio_global = self._crear_boton_color("Repert.", "#9333EA", altura=32)
        btn_repertorio_global.setToolTip("Abre piezas progresivas guiadas para aplicar técnica y teoría.")
        btn_repertorio_global.clicked.connect(self.mostrar_repertorio)
        lay.addWidget(btn_repertorio_global)

        btn_partitura_global = self._crear_boton_color("Partitura", "#0F766E", altura=32)
        btn_partitura_global.setToolTip("Abre la lectura de partitura visual integrada con el piano.")
        btn_partitura_global.clicked.connect(self.mostrar_lectura_partitura)
        lay.addWidget(btn_partitura_global)

        btn_pulso_global = self._crear_boton_color("Pulso", "#0284C7", altura=32)
        btn_pulso_global.setToolTip("Abre el entrenador de pulso y metrónomo guiado.")
        btn_pulso_global.clicked.connect(self.mostrar_pulso_ritmo)
        lay.addWidget(btn_pulso_global)
        lay.addStretch(1)
        return panel

    def _crear_marco_piano_global(self):
        """Crea un único piano interactivo fijo bajo el área central.

        El widget se mantiene fuera del QStackedWidget para que no desaparezca
        cuando se cambia entre pantallas prácticas. Todas las rutinas existentes
        siguen usando self.piano, por lo que no se duplica lógica de MIDI ni de
        evaluación.
        """
        marco = QFrame()
        marco.setObjectName("MarcoPianoVisible")
        try:
            altura_piano = int(self.ajustes.ajustes.piano_altura)
        except Exception:
            altura_piano = 150
        # El piano global sustituye al mini piano interno de la pizarra, por eso
        # debe ser lo bastante alto para practicar digitación sin quedar testimonial.
        altura_piano = max(120, min(170, altura_piano))
        marco.setMinimumHeight(altura_piano + 30)
        marco.setMaximumHeight(altura_piano + 46)
        piano_layout = QVBoxLayout(marco)
        piano_layout.setContentsMargins(8, 3, 8, 6)
        piano_layout.setSpacing(2)

        self.lbl_piano_global = QLabel("Piano interactivo — 88 teclas")
        self.lbl_piano_global.setObjectName("TituloPianoInteractivo")
        self.lbl_piano_global.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.piano = PianoVirtual(octava_base=self.ajustes.ajustes.octava_base)
        self._notas_piano_virtual_activas = set()
        self.piano.nota_pulsada.connect(self._nota_on)
        self.piano.nota_soltada.connect(self._nota_off)
        self.piano.aplicar_configuracion(self.ajustes.ajustes.piano_mostrar_nombres, altura_piano)
        self.piano.setVisible(True)
        piano_layout.addWidget(self.lbl_piano_global)
        piano_layout.addWidget(self.piano, 1)
        marco.setVisible(True)
        return marco

    def _pantalla_actual_usa_piano(self) -> bool:
        """Devuelve si la pantalla actual debe mostrar el piano global."""
        try:
            actual = self.stack.currentWidget()
            # Inicio es una portada/navegación; las demás pantallas pueden usar
            # piano virtual, MIDI, corrección, pizarra, Hanon, pulso o lectura.
            if hasattr(self, "pantalla_inicio") and actual is self.pantalla_inicio:
                return False
        except Exception:
            pass
        return True

    def _actualizar_visibilidad_piano_global(self, *_):
        """Mantiene el piano presente en todas las pantallas prácticas."""
        try:
            if hasattr(self, "marco_piano_global"):
                self.marco_piano_global.setVisible(self._pantalla_actual_usa_piano())
        except Exception:
            pass

    def crear_barra_tiempo_profesor(self):
        """Transportador visible del profesor, sincronizado con la voz."""
        widget = QWidget()
        widget.setObjectName("BarraTiempoProfesor")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.lbl_voz_tiempo_transcurrido = QLabel("00:00")
        self.lbl_voz_tiempo_transcurrido.setMinimumWidth(38)
        self.lbl_voz_tiempo_transcurrido.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.barra_voz_progreso = BarraProgresoInteractiva()
        self.barra_voz_progreso.setRange(0, 1000)
        self.barra_voz_progreso.posicion_cambiada.connect(self._voz_seek_desde_barra)
        self.barra_voz_progreso.setValue(0)
        self.barra_voz_progreso.setTextVisible(False)
        self.barra_voz_progreso.setFixedHeight(10)
        self.barra_voz_progreso.setToolTip("Narración: 00:00 / faltan 00:00")

        self.lbl_voz_tiempo_restante = QLabel("-00:00")
        self.lbl_voz_tiempo_restante.setMinimumWidth(42)
        self.lbl_voz_tiempo_restante.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Etiqueta agregada conservada para la lógica previa y tooltips.
        self.lbl_voz_tiempo = QLabel("00:00 / faltan 00:00")
        self.lbl_voz_tiempo.setVisible(False)

        layout.addWidget(self.lbl_voz_tiempo_transcurrido, 0)
        layout.addWidget(self.barra_voz_progreso, 1)
        layout.addWidget(self.lbl_voz_tiempo_restante, 0)
        return widget

    def _interpretar_fragmento_profesor(self, texto: str) -> str:
        """Convierte notación técnica en lenguaje natural de profesor.

        Esto no pretende cambiar el contenido didáctico, sino evitar que la voz
        lea símbolos literalmente cuando debe explicarlos.
        """
        t = str(texto or "")

        # Casos musicales concretos de partitura.
        t = re.sub(
            r"𝄞\s*pentagrama superior\s*=\s*normalmente mano derecha\s*\|\s*𝄢\s*pentagrama inferior\s*=\s*normalmente mano izquierda",
            "El pentagrama superior, que normalmente se escribe en clave de sol, equivale normalmente a la mano derecha; y el pentagrama inferior, que normalmente se escribe en clave de fa, equivale normalmente a la mano izquierda.",
            t,
            flags=re.I,
        )
        t = re.sub(
            r"pentagrama superior\s*=\s*normalmente mano derecha",
            "el pentagrama superior normalmente equivale a la mano derecha",
            t,
            flags=re.I,
        )
        t = re.sub(
            r"pentagrama inferior\s*=\s*normalmente mano izquierda",
            "el pentagrama inferior normalmente equivale a la mano izquierda",
            t,
            flags=re.I,
        )

        # Figuras rítmicas: no leer el igual como símbolo, sino como concepto.
        reemplazos_exactos = [
            (r"negra\s*=\s*1\s*pulso", "una negra dura un pulso"),
            (r"blanca\s*=\s*2\s*pulsos", "una blanca dura dos pulsos"),
            (r"redonda\s*=\s*4\s*pulsos", "una redonda dura cuatro pulsos"),
            (r"silencio\s*=\s*no tocar", "un silencio significa que no debes tocar, pero sí debes seguir contando el pulso"),
            (r"DO central\s*=\s*nota con una pequeña línea adicional", "El DO central se dibuja como una nota atravesada por una pequeña línea adicional"),
        ]
        for patron, repl in reemplazos_exactos:
            t = re.sub(patron, repl, t, flags=re.I)

        # Símbolos musicales y signos.
        t = t.replace("𝄞", "clave de sol")
        t = t.replace("𝄢", "clave de fa")
        t = t.replace("♩", "negra")
        t = t.replace("𝅗𝅥", "blanca")
        t = t.replace("𝅝", "redonda")
        t = t.replace("✓", "marcado como superado")
        t = t.replace("→", "después")
        t = t.replace("←", "anterior")
        t = t.replace("·", ". ")
        t = t.replace("|", "; y ")

        # Compases y tempo.
        t = re.sub(r"\b4/4\b", "cuatro por cuatro", t)
        t = re.sub(r"\b3/4\b", "tres por cuatro", t)
        t = re.sub(r"\b2/4\b", "dos por cuatro", t)
        t = re.sub(r"\bbpm\b", "pulsaciones por minuto", t, flags=re.I)

        # Igualdad genérica solo si queda en texto didáctico.
        # Ejemplo: "X = Y" -> "X equivale a Y".
        t = re.sub(r"\s+=\s+", " equivale a ", t)

        # Limpiar espacios y dobles signos.
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\s+([,.;:])", r"\1", t)
        t = re.sub(r"([.;:])\s*([.;:])+", r"\1", t)
        return t.strip()

    def _interpretar_texto_profesor(self, texto: str) -> str:
        """Prepara lo que el profesor muestra y pronuncia.

        El profesor no debe leer símbolos como si fueran código. Debe explicar
        su significado. Por eso se procesa el texto antes de ponerlo en el panel
        derecho o mandarlo al motor de voz.
        """
        texto = str(texto or "")
        if not texto.strip():
            return ""

        lineas = []
        for linea in texto.splitlines():
            interpretada = self._interpretar_fragmento_profesor(linea)
            lineas.append(interpretada)

        salida = "\n".join(lineas)
        salida = re.sub(r"\n{3,}", "\n\n", salida)
        return salida.strip()

    def _actualizar_dialogo_avatar(self, texto: str):
        texto = self._interpretar_texto_profesor(texto)
        self._ultimo_contexto_profesor = texto
        if hasattr(self, "txt_avatar_dialogo"):
            self.txt_avatar_dialogo.setPlainText(texto)

    def texto_pantalla_actual(self) -> str:
        """Devuelve un texto legible de la pantalla activa para el avatar."""
        actual = self.stack.currentWidget() if hasattr(self, "stack") else None
        if hasattr(self, "pantalla_inicio") and actual is self.pantalla_inicio:
            return getattr(self.pantalla_inicio, "_texto_actual", "Pantalla de inicio del curso.")
        if hasattr(self, "pantalla_evaluacion") and actual is self.pantalla_evaluacion:
            return (
                f"{self._nombre_alumno()}, esta es la evaluación inicial. Responde mentalmente a las preguntas y marca cuántas dominas. "
                "No es un castigo ni una nota final: solo sirve para colocar tu primer nivel de forma aproximada. "
                "Si sabes localizar DO, distinguir blancas y negras, entender una escala sencilla o reconocer acordes, márcalo con sinceridad. "
                "Así el curso empieza en un punto útil para ti."
            )
        try:
            if hasattr(self, "area_contenido_estudio"):
                actual_estudio = self.area_contenido_estudio.currentWidget()
                if actual_estudio is not None and actual_estudio is not getattr(self, "pagina_clase_practica", None):
                    texto_panel = self._texto_panel_integrado(actual_estudio)
                    if texto_panel:
                        return texto_panel
        except Exception:
            pass
        texto = ""
        try:
            texto = self.txt_profesor.toPlainText().strip()
        except Exception:
            texto = ""
        if not texto:
            texto = getattr(self, "_ultimo_texto_profesor", "")
        return texto or f"Estoy listo para ayudarte, {self._nombre_alumno()}. Puedes pedirme que lea, explique o te guíe."

    def leer_pantalla_actual(self):
        texto = self.texto_pantalla_actual()
        texto = self._envolver_como_profesor_interactivo(texto)
        self._actualizar_dialogo_avatar(texto)
        self._hablar_con_avatar(texto)

    def _envolver_como_profesor_interactivo(self, texto: str) -> str:
        nombre = self._nombre_alumno()
        base = str(texto or "").strip()
        if not base:
            base = "Estoy listo para explicarte la pantalla actual."
        return (
            f"{nombre}, te explico esta pantalla como profesor.\n\n"
            f"{base}\n\n"
            "Ahora quiero que participes: si lo has entendido, escríbeme 'sí'. "
            "Si no lo has entendido, escríbeme 'no' y te lo explicaré de otra manera, con un ejemplo más sencillo. "
            "También puedes escribir 'ejemplo' para que prepare un caso práctico."
        )

    def enviar_dialogo_avatar(self):
        pregunta = ""
        try:
            pregunta = self.input_avatar_dialogo.text().strip()
            self.input_avatar_dialogo.clear()
        except Exception:
            pregunta = ""
        if not pregunta:
            self.leer_pantalla_actual()
            return
        contexto = self.texto_pantalla_actual()
        respuesta = self._respuesta_avatar_local(pregunta, contexto)
        self._actualizar_dialogo_avatar(respuesta)
        self._hablar_con_avatar(respuesta)

    def _respuesta_avatar_local(self, pregunta: str, contexto: str) -> str:
        nombre = self._nombre_alumno()
        alumno = self._alumno_o_alumna()
        p = (pregunta or "").lower()
        contexto = contexto or self._ultimo_contexto_profesor or ""
        if p.strip() in {"si", "sí", "s", "lo entiendo", "entendido", "vale", "ok", "correcto", "no", "n", "no entiendo", "no lo entiendo", "repitemelo", "repítemelo", "otra vez"} or "ejemplo" in p or "para qué" in p or "para que" in p or "siguiente" in p or "continuar" in p:
            return self.profesor_ia.responder_interactivo(pregunta, contexto, self.perfil_alumno, self._ultimo_titulo_profesor)
        if "quién soy" in p or "quien soy" in p or "nombre" in p or "perfil" in p:
            return (
                f"Estoy hablando con {nombre}. Te tengo guardado como {alumno} en data/perfil_alumno.json. "
                "Ese perfil me permite dirigirme a ti de forma coherente en las explicaciones, en la práctica y en los repasos."
            )
        if "digitación" in p or "digitacion" in p or "dedo" in p or "dedos" in p:
            return (
                f"{nombre}, la digitación es la numeración de los dedos. El dedo 1 es el pulgar, el 2 es el índice, "
                "el 3 es el corazón, el 4 es el anular y el 5 es el meñique. Sirve para que no improvises cualquier dedo, "
                "sino que aprendas un movimiento ordenado. Cuando veas una imagen de digitación, mira primero qué número está iluminado, "
                "después identifica ese dedo en tu mano y por último busca la tecla que corresponde."
            )
        if "mano" in p or "postura" in p or "muñeca" in p or "muneca" in p:
            return (
                f"{nombre}, la postura empieza antes de tocar una tecla. Primero colócate en el banco: siéntate cerca del borde, con espalda recta pero no rígida, hombros relajados y pies apoyados. "
                "Después revisa los codos: deben quedar aproximadamente a nivel del teclado para que el antebrazo llegue de forma natural. "
                "Por último revisa las manos: la muñeca debe estar alineada y flexible, y los dedos curvados como si sujetaras una pelota pequeña. "
                "Esto sirve para tocar con menos tensión, más control y mejor sonido."
            )
        if "teclado" in p or "negras" in p or "blancas" in p or "do" in p:
            return (
                "El teclado se entiende por patrones. Las teclas negras aparecen en grupos de dos y de tres. Ese patrón sirve como mapa visual. "
                "Para encontrar DO, busca un grupo de dos teclas negras: DO está justo antes de ese grupo. Las teclas blancas siguen la secuencia "
                "DO, RE, MI, FA, SOL, LA y SI, y después vuelve a empezar."
            )
        if "teoría" in p or "teoria" in p:
            return (
                f"La teoría sirve para entender antes de tocar, {nombre}. En el nivel cero no vamos directamente a canciones: primero aprendemos cómo se colocan las manos, "
                "qué número tiene cada dedo, cómo se organiza el teclado y cómo encontrar las primeras notas. Las imágenes y GIFs no están de adorno: son la explicación visual."
            )
        if "práctica" in p or "practica" in p or "ejercicio" in p:
            return (
                "La práctica sirve para convertir la teoría en movimiento. Primero escuchas la explicación, después observas el ejemplo visual, luego practicas sin penalización "
                "y finalmente haces el ejercicio evaluable. No debes avanzar por avanzar: debes avanzar cuando el ejercicio sale con control."
            )
        if "evaluación" in p or "evaluacion" in p or "nivel" in p:
            return (
                "La evaluación inicial sirve para colocarte en un punto de partida. No es un examen para castigarte; es una forma de evitar que empieces demasiado fácil "
                "o demasiado difícil. También puedes elegir el nivel manualmente si ya sabes dónde quieres empezar."
            )
        if "lee" in p or "leer" in p or "explica" in p or "pantalla" in p:
            return contexto
        return (
            f"{nombre}, te explico la pantalla actual. {contexto} "
            "Puedes preguntarme por manos, digitación, teclas blancas, teclas negras, evaluación o práctica, y te lo explicaré paso a paso."
        )

    def _abrir_dialogo_imagen_teoria(self, ruta: str, titulo: str, explicacion: str):
        """Amplía una imagen/GIF de teoría y activa al profesor virtual."""
        self._ultimo_titulo_profesor = titulo or "Material visual"
        self._ultimo_contexto_profesor = explicacion or ""
        self._actualizar_dialogo_avatar(explicacion)
        try:
            dlg = DialogoImagenTeoria(ruta, titulo, explicacion, self, getattr(self.ajustes.ajustes, "avatar_tipo", "chica"))
            dlg.btn_leer.clicked.connect(lambda: self._hablar_con_avatar(explicacion))
            dlg.btn_entendido.clicked.connect(lambda: self._marcar_imagen_entendida(titulo))
            dlg.btn_no_entendido.clicked.connect(lambda: self._reforzar_imagen_no_entendida(titulo, explicacion))
            dlg.setModal(False)
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()
            self._dialogo_imagen_teoria = dlg
        except Exception as exc:
            QMessageBox.warning(self, "Imagen", f"No he podido abrir la imagen ampliada: {exc}")
        # El profesor se involucra de inmediato, no espera a que el alumno lea solo.
        self._hablar_con_avatar(explicacion)

    def _marcar_imagen_entendida(self, titulo: str):
        texto = self.profesor_ia.confirmar_comprension(
            self._ultimo_contexto_profesor,
            self._nombre_alumno(),
            self._alumno_o_alumna(),
            getattr(self.perfil_alumno, "preparado_o_preparada", "preparado/a"),
        )
        self._actualizar_dialogo_avatar(texto)
        self._hablar_con_avatar(texto)

    def _reforzar_imagen_no_entendida(self, titulo: str, explicacion: str):
        texto = self.profesor_ia.reforzar_explicacion(
            explicacion or self._ultimo_contexto_profesor,
            self._nombre_alumno(),
            self._alumno_o_alumna(),
        )
        self._actualizar_dialogo_avatar(texto)
        self._hablar_con_avatar(texto)

    def _crear_boton_color(self, texto, color, altura=34):
        btn = QPushButton(texto)
        btn.setMinimumHeight(altura)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 1px solid #334155;
                border-radius: 7px;
                padding: 7px 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid #0f172a;
                padding-top: 6px;
                padding-bottom: 8px;
            }}
            QPushButton:pressed {{
                background-color: #334155;
            }}
            QPushButton:disabled {{
                background-color: #94a3b8;
                color: #e2e8f0;
            }}
        """)
        return self._ajustar_boton_texto_completo(btn, minimo=72, extra=36)

    def _crear_boton_icono_transporte(self, texto, color, tooltip=""):
        btn = QPushButton(texto)
        btn.setFixedSize(30, 24)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 0px;
                margin: 0px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid #0f172a;
                background-color: #0284c7;
            }}
            QPushButton:pressed {{
                background-color: #334155;
            }}
        """)
        return btn


    def _ajustar_boton_texto_completo(self, btn, minimo=72, extra=34):
        """Evita que las etiquetas de los botones queden cortadas.

        No cambia la lógica del botón: solo calcula un ancho mínimo real
        según el texto visible y elimina límites máximos demasiado pequeños.
        """
        try:
            texto = btn.text().replace("&", "")
            ancho = btn.fontMetrics().horizontalAdvance(texto) + int(extra)
            btn.setMinimumWidth(max(int(minimo), int(ancho)))
            btn.setMaximumWidth(16777215)
            btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            if texto and not btn.toolTip():
                btn.setToolTip(texto)
        except Exception:
            pass
        return btn

    def _crear_pantalla_estudio(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # Cabecera compacta con estado y acciones principales.
        cabecera_frame = QFrame()
        cabecera_frame.setObjectName("CabeceraEstudioCompacta")
        cabecera_layout = QVBoxLayout(cabecera_frame)
        cabecera_layout.setContentsMargins(8, 6, 8, 6)
        cabecera_layout.setSpacing(5)

        fila_estado = QHBoxLayout()
        fila_estado.setSpacing(8)
        self.lbl_nivel = QLabel("Nivel: sin evaluar")
        self.lbl_estado = QLabel("Superados: 0 | Fallados: 0 | Racha: 0")
        self.lbl_audio = QLabel("Audio: pendiente")
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setRange(0, 100)
        self.barra_progreso.setValue(0)
        self.barra_progreso.setFormat("Progreso del nivel: %p%")
        fila_estado.addWidget(self.lbl_nivel)
        fila_estado.addWidget(self.lbl_estado)
        fila_estado.addWidget(self.lbl_audio)
        fila_estado.addWidget(self.barra_progreso, 1)
        cabecera_layout.addLayout(fila_estado)

        scroll_acciones = QScrollArea()
        scroll_acciones.setWidgetResizable(False)
        scroll_acciones.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_acciones.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_acciones.setFrameShape(QFrame.NoFrame)
        scroll_acciones.setMinimumHeight(46)
        cont_acciones = QWidget()
        fila_acciones = QHBoxLayout(cont_acciones)
        fila_acciones.setContentsMargins(0, 0, 0, 0)
        fila_acciones.setSpacing(6)
        self.btn_estado_alumno = self._crear_boton_color("Estado", "#0F766E", altura=30)
        self.btn_estado_alumno.clicked.connect(self.mostrar_estado_alumno)
        self.btn_repaso_ia = self._crear_boton_color("Repaso IA", "#DC2626", altura=30)
        self.btn_repaso_ia.clicked.connect(self.iniciar_repaso_inteligente)
        self.btn_repaso = self._crear_boton_color("Repasar", "#14B8A6", altura=30)
        self.btn_repaso.clicked.connect(self.repasar_anterior)
        self.btn_examen = self._crear_boton_color("Examen", "#F59E0B", altura=30)
        self.btn_examen.clicked.connect(self.iniciar_examen_nivel)
        self.btn_plan = self._crear_boton_color("Plan", "#7C3AED", altura=30)
        self.btn_plan.clicked.connect(self.mostrar_plan_completo)
        self.btn_plan_alumno = self._crear_boton_color("Alumno", "#8B5CF6", altura=30)
        self.btn_plan_alumno.clicked.connect(self.mostrar_plan_personalizado)
        self.btn_ruta_curso = self._crear_boton_color("Ruta", "#0EA5E9", altura=30)
        self.btn_ruta_curso.clicked.connect(self.mostrar_ruta_curso)
        self.btn_tecnica = self._crear_boton_color("Técnica", "#16A34A", altura=30)
        self.btn_tecnica.clicked.connect(self.mostrar_tecnica_diaria)
        self.btn_sesion = self._crear_boton_color("Sesión", "#F59E0B", altura=30)
        self.btn_sesion.clicked.connect(self.mostrar_sesion_diaria)
        self.btn_repertorio = self._crear_boton_color("Repert.", "#9333EA", altura=30)
        self.btn_repertorio.clicked.connect(self.mostrar_repertorio)
        self.btn_partitura = self._crear_boton_color("Partitura", "#0F766E", altura=30)
        self.btn_partitura.clicked.connect(self.mostrar_lectura_partitura)
        self.btn_pulso = self._crear_boton_color("Pulso", "#0284C7", altura=30)
        self.btn_pulso.clicked.connect(self.mostrar_pulso_ritmo)
        self.btn_config = self._crear_boton_color("Config", "#2563EB", altura=30)
        self.btn_config.clicked.connect(self.abrir_configuracion)
        self.btn_inicio = self._crear_boton_color("Inicio", "#64748B", altura=30)
        self.btn_inicio.clicked.connect(self.volver_al_inicio)
        self.lbl_midi_compacto = QLabel("MIDI alumno: sin conectar")
        self.lbl_midi_ultima = QLabel("Alumno MIDI: —")
        self.lbl_midi_compacto.setMinimumWidth(92)
        self.lbl_midi_ultima.setMinimumWidth(80)

        for btn in (
            self.btn_estado_alumno, self.btn_repaso_ia, self.btn_repaso, self.btn_examen,
            self.btn_plan, self.btn_plan_alumno, self.btn_ruta_curso, self.btn_tecnica,
            self.btn_sesion, self.btn_repertorio, self.btn_partitura, self.btn_pulso, self.btn_config, self.btn_inicio
        ):
            self._ajustar_boton_texto_completo(btn, minimo=78, extra=40)

        fila_acciones.addWidget(self.btn_estado_alumno)
        fila_acciones.addWidget(self.btn_repaso_ia)
        fila_acciones.addWidget(self.btn_repaso)
        fila_acciones.addWidget(self.btn_examen)
        fila_acciones.addWidget(self.btn_plan)
        fila_acciones.addWidget(self.btn_plan_alumno)
        fila_acciones.addWidget(self.btn_ruta_curso)
        fila_acciones.addWidget(self.btn_tecnica)
        fila_acciones.addWidget(self.btn_sesion)
        fila_acciones.addWidget(self.btn_repertorio)
        fila_acciones.addWidget(self.btn_partitura)
        fila_acciones.addWidget(self.btn_pulso)
        fila_acciones.addWidget(self.btn_config)
        fila_acciones.addWidget(self.lbl_midi_compacto)
        fila_acciones.addWidget(self.lbl_midi_ultima)
        fila_acciones.addStretch(1)
        fila_acciones.addWidget(self.btn_inicio)
        cont_acciones.adjustSize()
        cont_acciones.setMinimumWidth(cont_acciones.sizeHint().width())
        scroll_acciones.setWidget(cont_acciones)
        cabecera_layout.addWidget(scroll_acciones)
        layout.addWidget(cabecera_frame)

        linea = QFrame()
        linea.setFrameShape(QFrame.HLine)
        layout.addWidget(linea)

        # Área dinámica: clase/práctica + páginas integradas del profesor.
        # v4.1.9 layout real: primero va la pizarra/partitura, después el piano.
        # Antes el piano se construía antes del contenido y empujaba la pizarra hacia abajo.
        self.area_contenido_estudio = QStackedWidget()
        # Mínimo moderado para que el piano global no quede expulsado de la ventana.
        self.area_contenido_estudio.setMinimumHeight(360)
        self.area_contenido_estudio.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.paginas_estudio_dinamicas = {}

        self.pagina_clase_practica = QWidget()
        zona = QHBoxLayout(self.pagina_clase_practica)
        zona.setContentsMargins(0, 0, 0, 0)
        zona.setSpacing(10)

        self.txt_profesor = QTextEdit()
        self.txt_profesor.setReadOnly(True)
        self.txt_profesor.setMinimumHeight(300)
        self.txt_profesor.setMinimumWidth(420)
        self.txt_profesor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        zona.addWidget(self.txt_profesor, 3)

        panel_lateral = QFrame()
        panel_lateral.setObjectName("PanelClaseLateral")
        panel_lateral.setMinimumWidth(240)
        panel_lateral.setMaximumWidth(360)
        panel_lateral.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        panel = QVBoxLayout(panel_lateral)
        panel.setContentsMargins(8, 6, 8, 6)
        panel.setSpacing(7)
        self.lbl_avatar_estudio = QLabel("Profesor virtual activo")
        self.lbl_avatar_estudio.setMinimumHeight(44)
        self.lbl_avatar_estudio.setAlignment(Qt.AlignCenter)
        self.lbl_avatar_estudio.setObjectName("AvatarAvisoGlobal")
        self.lbl_fase_clase = QLabel("Fase: Clase")
        self.lbl_fase_clase.setObjectName("FaseClase")
        self.lbl_ejercicio = QLabel("Ejercicio actual")
        self.lbl_ejercicio.setObjectName("TituloEjercicio")
        self.lbl_objetivo = QLabel("Objetivo")
        self.lbl_objetivo.setWordWrap(True)

        fila_clase_1 = QHBoxLayout()
        self.btn_ver_clase = self._crear_boton_color("1 Clase", "#2563EB")
        self.btn_ver_clase.clicked.connect(self.ver_clase_actual)
        self.btn_ver_ejemplo = self._crear_boton_color("2 Ver ejemplo", "#16A34A")
        self.btn_ver_ejemplo.clicked.connect(self.ver_ejemplo_actual)
        self.btn_practicar = self._crear_boton_color("3 Practicar", "#F59E0B")
        self.btn_practicar.clicked.connect(self.activar_practica_guiada)
        self.btn_hacer_ejercicio = self._crear_boton_color("4 Hacer ejercicio", "#7C3AED")
        self.btn_hacer_ejercicio.clicked.connect(self.activar_ejercicio_evaluable)
        fila_clase_1.addWidget(self.btn_ver_clase)
        fila_clase_1.addWidget(self.btn_ver_ejemplo)
        fila_clase_1.addWidget(self.btn_practicar)
        fila_clase_1.addWidget(self.btn_hacer_ejercicio)

        fila_clase_2 = QHBoxLayout()
        fila_clase_2.setSpacing(6)
        self.widget_transporte_narrador = QWidget()
        self.widget_transporte_narrador.setObjectName("TransporteNarradorCompacto")
        self.widget_transporte_narrador.setFixedHeight(52)
        self.widget_transporte_narrador.setMinimumWidth(104)
        transporte_layout = QVBoxLayout(self.widget_transporte_narrador)
        transporte_layout.setContentsMargins(0, 0, 0, 0)
        transporte_layout.setSpacing(2)

        fila_iconos_voz = QHBoxLayout()
        fila_iconos_voz.setContentsMargins(0, 0, 0, 0)
        fila_iconos_voz.setSpacing(3)
        self.lbl_voz_estado = QLabel("")
        self.lbl_voz_estado.setVisible(False)
        self.btn_voz_play = self._crear_boton_icono_transporte("▶", "#0EA5E9", "Play: reproduce o reanuda la explicación del profesor.")
        self.btn_voz_play.clicked.connect(self.play_voz_actual)
        self.btn_voz_pausa = self._crear_boton_icono_transporte("Ⅱ", "#F59E0B", "Pausa instantánea de la voz.")
        self.btn_voz_pausa.clicked.connect(self.pausar_reanudar_voz)
        self.btn_voz_stop = self._crear_boton_icono_transporte("■", "#64748B", "Stop: detiene la voz del profesor.")
        self.btn_voz_stop.clicked.connect(self.stop_voz)
        fila_iconos_voz.addWidget(self.btn_voz_play)
        fila_iconos_voz.addWidget(self.btn_voz_pausa)
        fila_iconos_voz.addWidget(self.btn_voz_stop)
        fila_iconos_voz.addStretch(1)

        self.barra_voz_progreso_compacta = BarraProgresoInteractiva()
        self.barra_voz_progreso_compacta.setRange(0, 1000)
        self.barra_voz_progreso_compacta.posicion_cambiada.connect(self._voz_seek_desde_barra)
        self.barra_voz_progreso_compacta.setValue(0)
        self.barra_voz_progreso_compacta.setTextVisible(False)
        self.barra_voz_progreso_compacta.setFixedHeight(8)
        self.barra_voz_progreso_compacta.setToolTip("Narración: 00:00 / faltan 00:00")
        transporte_layout.addLayout(fila_iconos_voz)
        transporte_layout.addWidget(self.barra_voz_progreso_compacta)

        self.btn_pista = self._crear_boton_color("Ver pista", "#14B8A6", altura=30)
        self.btn_pista.clicked.connect(self.mostrar_pista)
        self.btn_siguiente = self._crear_boton_color("Siguiente ejercicio", "#64748B", altura=30)
        self.btn_siguiente.clicked.connect(self.siguiente_forzado)
        fila_clase_2.addWidget(self.widget_transporte_narrador, 0)
        fila_clase_2.addWidget(self.btn_pista, 1)
        fila_clase_2.addWidget(self.btn_siguiente, 1)

        self.timer_voz_progreso = QTimer(self)
        self.timer_voz_progreso.setInterval(120)
        self.timer_voz_progreso.timeout.connect(self._actualizar_progreso_voz)
        self._voz_texto_en_curso = ""
        self._voz_duracion_ms_estimada = 1
        self._voz_inicio_mono = None
        self._voz_ms_acumulados = 0
        self._voz_pausada_transporte = False

        self.input_respuesta = QLineEdit()
        self.input_respuesta.setPlaceholderText("Primero recibe la clase. Después escribe o toca el teclado MIDI.")
        self.input_respuesta.returnPressed.connect(self.comprobar_ejercicio)
        fila_respuesta = QHBoxLayout()
        self.btn_borrar_respuesta = self._crear_boton_color("Borrar respuesta", "#64748B", altura=32)
        self.btn_borrar_respuesta.clicked.connect(self._borrar_respuesta_actual)
        fila_respuesta.addWidget(self.input_respuesta, 1)
        fila_respuesta.addWidget(self.btn_borrar_respuesta, 0)
        self.btn_comprobar = self._crear_boton_color("Comprobar ejercicio", "#16A34A")
        self.btn_comprobar.clicked.connect(self.comprobar_ejercicio)
        self.txt_resultado = QTextEdit()
        self.txt_resultado.setReadOnly(True)
        self.txt_resultado.setMinimumHeight(150)

        panel.addWidget(self.lbl_avatar_estudio)
        panel.addWidget(self.lbl_fase_clase)
        panel.addWidget(self.lbl_ejercicio)
        panel.addWidget(self.lbl_objetivo)
        panel.addLayout(fila_clase_1)
        panel.addLayout(fila_clase_2)
        panel.addLayout(fila_respuesta)
        panel.addWidget(self.btn_comprobar)
        panel.addWidget(self.txt_resultado, 1)
        zona.addWidget(panel_lateral, 1)

        self.area_contenido_estudio.addWidget(self.pagina_clase_practica)
        self.paginas_estudio_dinamicas["clase_practica"] = self.pagina_clase_practica
        self.area_contenido_estudio.setCurrentWidget(self.pagina_clase_practica)
        layout.addWidget(self.area_contenido_estudio, 1)

        # El piano interactivo real ahora es global y se añade una sola vez
        # bajo el stack principal. No se recrea aquí para evitar que desaparezca
        # al cambiar de pantalla.

        self._clave_panel_estudio = "clase_practica"
        return w

    def _desconectar_boton(self, boton):
        """Desconecta señales clicked sin mostrar warnings de PySide.

        PySide6 puede emitir:
        RuntimeWarning: Failed to disconnect (None) from signal "clicked()".
        cuando se intenta desconectar un botón que no tiene conexiones activas.
        No es un fallo grave, pero ensucia la consola. Por eso comprobamos
        primero los receptores y, además, silenciamos ese warning concreto.
        """
        if boton is None:
            return

        try:
            if hasattr(boton, "receivers") and boton.receivers(boton.clicked) <= 0:
                return
        except Exception:
            pass

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                boton.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        except Exception:
            pass

    def _mostrar_panel_clase_practica(self):
        if hasattr(self, "area_contenido_estudio") and hasattr(self, "pagina_clase_practica"):
            self.area_contenido_estudio.setCurrentWidget(self.pagina_clase_practica)
            self._clave_panel_estudio = "clase_practica"
        self.stack.setCurrentWidget(self.pantalla_estudio)

    def _normalizar_texto_lectura(self, texto: str) -> str:
        texto = str(texto or "").replace("\r", "\n")
        texto = re.sub(r"[ \t]+", " ", texto)
        texto = re.sub(r"\n{3,}", "\n\n", texto)
        return texto.strip()

    def _texto_de_widget(self, widget) -> str:
        try:
            if widget is not None and hasattr(widget, "toPlainText"):
                return self._normalizar_texto_lectura(widget.toPlainText())
        except Exception:
            pass
        return ""

    def _titulo_amigable_panel(self, panel, clave: str = "", titulo_previo: str = "") -> str:
        """Devuelve el nombre real de la pestaña.

        Regla importante:
        - nunca usar títulos genéricos como "Pestaña" o "pestaña actual";
        - si conocemos la clave interna, la clave manda;
        - después se usa la clase del diálogo;
        - después el título de ventana;
        - al final, los datos del panel.
        """
        nombre = self._nombre_alumno()
        clase = panel.__class__.__name__ if panel is not None else ""
        clave = str(clave or "").strip()

        invalidos = {
            "",
            "pestaña",
            "pestana",
            "pestaña actual",
            "pestana actual",
            "actual",
            "leer título/resumen",
            "leer titulo/resumen",
            "leer título",
            "leer titulo",
        }

        mapa_clave = {
            "estado_alumno": "Estado del alumno",
            "plan_alumno": "Plan personalizado",
            "ruta_curso": "Ruta curso",
            "ruta": "Ruta curso",
            "tecnica": "Técnica diaria",
            "tecnica_diaria": "Técnica diaria",
            "sesion": "Sesión diaria",
            "sesion_diaria": "Sesión diaria",
            "repertorio": "Repert.",
            "partitura": "Lectura de partitura visual",
            "pulso": "Pulso y metrónomo",
            "pulso_ritmo": "Pulso y metrónomo",
            "pulso_practica": "Práctica de pulso",
            "clase_practica": "Clase y práctica",
        }
        if clave in mapa_clave:
            return mapa_clave[clave]

        mapa_clase = {
            "DialogoEstadoAlumno": "Estado del alumno",
            "DialogoPlanPersonalizado": "Plan personalizado",
            "DialogoRutaCurso": "Ruta curso",
            "DialogoTecnicaDiaria": "Técnica diaria",
            "DialogoSesionDiaria": "Sesión diaria",
            "DialogoRepertorio": "Repert.",
            "DialogoPulsoRitmo": "Pulso y metrónomo",
            "DialogoPulsoPractica": "Práctica de pulso",
            "DialogoLecturaPartitura": "Lectura de partitura visual",
        }
        if clase in mapa_clase:
            return mapa_clase[clase]

        titulo_previo = self._normalizar_texto_lectura(titulo_previo)
        if titulo_previo and titulo_previo.lower() not in invalidos:
            return titulo_previo

        try:
            titulo = self._normalizar_texto_lectura(panel.windowTitle())
            if titulo and titulo.lower() not in invalidos:
                if titulo in {"Estado de " + nombre, "Estado del alumno"}:
                    return "Estado del alumno"
                if titulo == "Plan personalizado del alumno":
                    return "Plan personalizado"
                return titulo
        except Exception:
            pass

        datos = getattr(panel, "datos", {}) or {}
        resumen = getattr(panel, "resumen", {}) or {}
        plan = getattr(panel, "plan", {}) or {}
        sesion = getattr(panel, "sesion", {}) or {}
        estado_ruta = getattr(panel, "estado_ruta", {}) or {}

        for fuente in (datos, resumen, sesion, estado_ruta, plan):
            if isinstance(fuente, dict):
                titulo = self._normalizar_texto_lectura(fuente.get("titulo", ""))
                if titulo and titulo.lower() not in invalidos:
                    return titulo

        if clave:
            return clave.replace("_", " ").strip().title()

        return "pestaña"

    def _texto_titulo_panel(self, panel, clave: str = "") -> str:
        """Lee bien el título y el recuadro superior de la pestaña."""
        if panel is None:
            return ""

        nombre = self._nombre_alumno()

        titulo_previo = ""
        try:
            titulo_previo = self._normalizar_texto_lectura(getattr(panel, "_lectura_titulo_texto", ""))
        except Exception:
            titulo_previo = ""

        if not titulo_previo:
            try:
                btn_titulo = getattr(panel, "btn_leer_titulo_pestana", None)
                if btn_titulo is not None and hasattr(btn_titulo, "text"):
                    titulo_previo = self._normalizar_texto_lectura(btn_titulo.text())
            except Exception:
                pass

        titulo = self._titulo_amigable_panel(panel, clave, titulo_previo)

        # Recuadro superior real: es lo que el usuario ve bajo el título.
        texto_superior = ""
        for attr in ("txt_profesor", "txt_resumen"):
            texto_superior = self._texto_de_widget(getattr(panel, attr, None))
            if texto_superior:
                break

        descripcion = ""
        for fuente in (
            getattr(panel, "datos", {}) or {},
            getattr(panel, "estado_ruta", {}) or {},
            getattr(panel, "sesion", {}) or {},
            getattr(panel, "resumen", {}) or {},
            getattr(panel, "plan", {}) or {},
        ):
            if isinstance(fuente, dict):
                descripcion = self._normalizar_texto_lectura(fuente.get("descripcion", ""))
                if descripcion:
                    break

        partes = [
            f"{nombre}, estás en «{titulo}». Esta pantalla sirve para que el profesor te sitúe, te explique qué estás viendo y te prepare para trabajar los puntos de la clase."
        ]

        if texto_superior:
            partes.append(
                "Lo primero que debo explicarte es el recuadro superior:\n"
                + texto_superior
            )
            if titulo == "Estado del alumno":
                partes.append(
                    "Explicación: este recuadro resume tu situación actual como alumno. "
                    "No se trata solo de decir si vas bien o mal; sirve para decidir qué conviene repasar, "
                    "qué conceptos están todavía flojos y cómo debemos avanzar sin correr. "
                    "Por eso el profesor mira tu progreso, tus fallos, tu racha y tus repasos pendientes antes de mandarte otra tarea."
                )
            else:
                partes.append(
                    "Dicho de otra forma: esta parte no es un adorno. Es el resumen pedagógico. "
                    "Te dice en qué punto estás, qué conviene reforzar y cómo vamos a seguir."
                )
        elif descripcion:
            partes.append("Finalidad de esta pestaña:\n" + descripcion)

        puntos = []
        try:
            puntos = self._puntos_lectura_panel(panel, clave)
        except Exception:
            puntos = []
        if puntos:
            partes.append(
                "Cuando pulses «Leer punto actual», empezaremos por este primer punto:\n"
                + self._normalizar_texto_lectura(puntos[0])
            )

        salida = []
        vistos = set()
        for t in partes:
            t = self._normalizar_texto_lectura(t)
            k = re.sub(r"\s+", " ", t).strip().lower()
            if k and k not in vistos:
                vistos.add(k)
                salida.append(t)
        return "\n\n".join(salida).strip()

    def _texto_frame_lectura(self, frame) -> str:
        partes = []
        try:
            for label in frame.findChildren(QLabel):
                t = self._normalizar_texto_lectura(label.text())
                if not t:
                    continue
                if len(t) <= 2 and not any(ch.isalpha() for ch in t):
                    continue
                if t in {"▶", "Ⅱ", "■", "✓", "○"}:
                    continue
                partes.append(t)
        except Exception:
            pass
        salida = []
        vistos = set()
        for t in partes:
            k = re.sub(r"\s+", " ", t).strip().lower()
            if k and k not in vistos:
                vistos.add(k)
                salida.append(t)
        return "\n".join(salida).strip()

    def _punto_desde_registro_lectura(self, registro: dict, prefijo: str = "Clase activa") -> list[str]:
        """Convierte un registro didáctico del modelo de datos en puntos leíbles."""
        if not isinstance(registro, dict) or not registro:
            return []

        puntos = []
        titulo = registro.get("titulo", "sin título")
        objetivo = registro.get("objetivo", "")
        lectura_visual = registro.get("lectura_visual", "")
        clave = registro.get("clave", "")
        compas = registro.get("compas", "")
        tempo = registro.get("tempo", registro.get("bpm", ""))

        punto_1 = [f"{prefijo}: {titulo}."]
        if objetivo:
            punto_1.append(f"Objetivo: {objetivo}")
        if lectura_visual:
            punto_1.append(f"Explicación visual principal: {lectura_visual}")
        meta = []
        if clave:
            meta.append(f"clave {clave}")
        if compas:
            meta.append(f"compás {compas}")
        if tempo:
            meta.append(f"tempo {tempo}")
        if meta:
            punto_1.append("Datos de trabajo: " + ", ".join(map(str, meta)) + ".")
        puntos.append("\n".join(punto_1))

        conceptos = []
        for key, label in (
            ("notas", "Notas"),
            ("figuras", "Figuras o conceptos"),
            ("digitacion", "Digitación"),
            ("simbolos", "Símbolos de partitura"),
            ("conceptos", "Conceptos"),
        ):
            valor = registro.get(key, [])
            if isinstance(valor, (list, tuple)) and valor:
                conceptos.append(f"{label}: " + ", ".join(map(str, valor)) + ".")
            elif isinstance(valor, str) and valor.strip():
                conceptos.append(f"{label}: {valor.strip()}.")
        for key, label in (
            ("patron", "Patrón"),
            ("notas_referencia", "Notas de referencia"),
            ("mano_derecha", "Mano derecha"),
            ("mano_izquierda", "Mano izquierda"),
            ("digitacion_md", "Digitación mano derecha"),
            ("digitacion_mi", "Digitación mano izquierda"),
            ("interpretacion", "Cómo se interpreta"),
        ):
            valor = registro.get(key, "")
            if isinstance(valor, (list, tuple)) and valor:
                conceptos.append(f"{label}: " + ", ".join(map(str, valor)) + ".")
            elif isinstance(valor, str) and valor.strip():
                conceptos.append(f"{label}: {valor.strip()}.")
        if conceptos:
            puntos.append("\n".join(conceptos))

        pasos = []
        for key in ("pasos", "instrucciones", "fases"):
            valor = registro.get(key, [])
            if isinstance(valor, (list, tuple)) and valor:
                pasos = list(valor)
                break
        for i, paso in enumerate(pasos, 1):
            paso = self._normalizar_texto_lectura(paso)
            if paso:
                puntos.append(f"Paso {i}: {paso}")

        practica = registro.get("practica_notas", [])
        if isinstance(practica, list) and practica:
            resumen_practica = []
            for item in practica:
                if isinstance(item, dict):
                    resumen_practica.append(str(item.get("nombre") or item.get("nota") or "silencio"))
            if resumen_practica:
                puntos.append("Ejercicio práctico en el piano: " + " → ".join(resumen_practica))

        criterio = registro.get("criterio", "")
        if criterio:
            puntos.append("Criterio de superación: " + self._normalizar_texto_lectura(criterio))

        return [self._normalizar_texto_lectura(p) for p in puntos if self._normalizar_texto_lectura(p)]

    def _registro_actual_desde_datos(self, datos: dict, resumen: dict) -> dict:
        if not isinstance(datos, dict):
            return {}
        resumen = resumen or {}
        siguiente = resumen.get("siguiente", {}) if isinstance(resumen, dict) else {}
        siguiente_id = siguiente.get("id", "") if isinstance(siguiente, dict) else ""

        for lista_key in ("ejercicios", "rutinas", "piezas", "niveles", "pasos", "pasos_base"):
            lista = datos.get(lista_key, [])
            if not isinstance(lista, list) or not lista:
                continue
            if siguiente_id:
                for item in lista:
                    if isinstance(item, dict) and item.get("id") == siguiente_id:
                        return item
            return lista[0] if isinstance(lista[0], dict) else {}

        if isinstance(siguiente, dict) and siguiente:
            return siguiente
        return {}

    def _puntos_modelo_panel(self, panel, clave: str = "") -> list[str]:
        """Puntos construidos desde los datos reales del panel."""
        puntos = []
        if panel is None:
            return puntos

        clase = panel.__class__.__name__

        # Estado del alumno: debe empezar explicando el recuadro superior y luego diagnóstico.
        if clave == "estado_alumno" or clase == "DialogoEstadoAlumno":
            resumen = getattr(panel, "resumen", {}) or {}
            texto_profesor = self._texto_de_widget(getattr(panel, "txt_profesor", None))
            texto_detalle = self._texto_de_widget(getattr(panel, "txt_detalle", None))
            if texto_profesor:
                puntos.append(
                    "Punto 1. Resumen del estado del alumno.\n"
                    + texto_profesor
                    + "\n\nExplicación: este resumen sirve para no estudiar a ciegas. "
                      "No miramos solo si aciertas o fallas; miramos qué hay que reforzar, "
                      "por qué conviene repasarlo y cómo avanzar sin saltarse la base."
                )
            metricas = []
            for key, label in (
                ("nivel_actual", "Nivel actual"),
                ("ejercicios_superados", "Ejercicios superados"),
                ("ejercicios_fallados", "Ejercicios fallados"),
                ("tasa_acierto", "Tasa de acierto"),
                ("racha", "Racha actual"),
                ("repasos_pendientes", "Repasos pendientes"),
                ("lecciones_guiadas", "Lecciones guiadas"),
                ("examenes_aprobados", "Exámenes aprobados"),
            ):
                if key in resumen:
                    metricas.append(f"{label}: {resumen.get(key)}")
            if metricas:
                puntos.append(
                    "Punto 2. Lectura de métricas.\n"
                    + "\n".join(metricas)
                    + "\n\nExplicación: estas cifras indican el estado real del aprendizaje. "
                      "Si hay fallos o repasos pendientes, el profesor debe bajar el ritmo y reforzar."
                )
            if texto_detalle:
                puntos.append("Punto 3. Diagnóstico del profesor.\n" + texto_detalle)
            return puntos

        # Plan personalizado.
        plan = getattr(panel, "plan", {}) or {}
        if clave == "plan_alumno" or clase == "DialogoPlanPersonalizado" or plan:
            txt = self._texto_de_widget(getattr(panel, "txt_resumen", None))
            if txt:
                puntos.append(
                    "Punto 1. Resumen del plan personalizado.\n"
                    + txt
                    + "\n\nExplicación: el plan convierte tu evaluación y tu progreso en una ruta concreta de trabajo."
                )
            pasos = plan.get("pasos", []) if isinstance(plan, dict) else []
            for i, paso in enumerate(pasos, 1):
                if isinstance(paso, dict):
                    puntos.append(
                        f"Punto {i + 1}. Paso del plan: {paso.get('titulo', 'sin título')}.\n"
                        f"Estado: {paso.get('estado', 'pendiente')}.\n"
                        f"Tipo: {paso.get('tipo', '—')}.\n"
                        f"Prioridad: {paso.get('prioridad', 'media')}.\n"
                        f"Motivo: {paso.get('motivo', '')}\n"
                        f"Acción: {paso.get('accion', '')}\n\n"
                        "Explicación: este paso existe para ordenar el estudio. No se trata de hacer muchas cosas, "
                        "sino de completar la siguiente acción útil."
                    )
            if puntos:
                return puntos

        datos = getattr(panel, "datos", {}) or {}
        resumen = getattr(panel, "resumen", {}) or {}
        sesion = getattr(panel, "sesion", {}) or {}
        estado_ruta = getattr(panel, "estado_ruta", {}) or {}

        if isinstance(datos, dict) and datos:
            registro = self._registro_actual_desde_datos(datos, resumen)
            if registro:
                puntos.extend(self._punto_desde_registro_lectura(registro, "Primer punto de la clase"))
            else:
                desc = datos.get("descripcion", "")
                if desc:
                    puntos.append(desc)

        if isinstance(sesion, dict) and sesion:
            pasos = sesion.get("pasos", []) or sesion.get("pasos_base", []) or []
            for i, paso in enumerate(pasos, 1):
                if isinstance(paso, dict):
                    puntos.append(
                        f"Paso de sesión {i}: {paso.get('titulo', 'sin título')}.\n"
                        f"Objetivo: {paso.get('objetivo', '')}\n"
                        f"Acción: {paso.get('accion', '')}\n"
                        f"Duración orientativa: {paso.get('duracion_min', '—')} minutos."
                    )

        if isinstance(estado_ruta, dict) and estado_ruta:
            niveles = estado_ruta.get("niveles", []) or []
            for i, nivel in enumerate(niveles[:8], 1):
                if isinstance(nivel, dict):
                    modulos = nivel.get("modulos", [])
                    if isinstance(modulos, list):
                        modulos = ", ".join(map(str, modulos))
                    puntos.append(
                        f"Nivel de ruta {i}: {nivel.get('titulo', 'sin título')}.\n"
                        f"Estado: {nivel.get('estado', nivel.get('estado_inicial', ''))}.\n"
                        f"Objetivo: {nivel.get('objetivo', '')}\n"
                        f"Módulos: {modulos}\n"
                        f"Desbloquea: {nivel.get('desbloquea', '')}"
                    )

        return puntos

    def _puntos_lectura_panel(self, panel, clave: str = "") -> list[str]:
        """Devuelve puntos de clase navegables para la pestaña activa."""
        if panel is None:
            return []

        puntos = []
        puntos.extend(self._puntos_modelo_panel(panel, clave))

        # Respaldo por widgets: tarjetas/paneles inferiores.
        try:
            frames = panel.findChildren(QFrame)
            for frame in frames:
                obj = str(frame.objectName() or "")
                if any(nombre in obj for nombre in (
                    "Card", "Panel", "Cabecera", "Fase", "Ruta", "Tecnica",
                    "Lectura", "Pulso", "Repert.", "Sesion"
                )):
                    t = self._texto_frame_lectura(frame)
                    if t and len(t) > 30:
                        puntos.append(t)
        except Exception:
            pass

        # Texto de detalle/diagnóstico si existe.
        for attr in ("txt_detalle", "txt_resultado"):
            t = self._texto_de_widget(getattr(panel, attr, None))
            if t and len(t) > 30:
                puntos.append(t)

        # Método específico de panel, como último respaldo.
        try:
            metodo = getattr(panel, "texto_para_profesor", None)
            if callable(metodo):
                t = self._normalizar_texto_lectura(metodo())
                if t and len(t) > 30:
                    puntos.append(t)
        except Exception:
            pass

        salida = []
        vistos = set()
        for t in puntos:
            t = self._normalizar_texto_lectura(t)
            if not t or len(t) < 20:
                continue
            k = re.sub(r"\s+", " ", t).strip().lower()
            if k in vistos:
                continue
            vistos.add(k)
            salida.append(t)

        return salida[:30]

    def _texto_panel_integrado(self, panel) -> str:
        if panel is None:
            return ""
        clave = getattr(panel, "_clave_panel_lectura", "")
        titulo = self._texto_titulo_panel(panel, clave)
        puntos = self._puntos_lectura_panel(panel, clave)
        nombre = self._nombre_alumno()
        partes = [
            f"{nombre}, esta es la lectura completa de la pestaña. Primero el contexto y después los puntos de trabajo."
        ]
        if titulo:
            partes.append("ENCABEZADO DE LA PESTAÑA:\n" + titulo)
        if puntos:
            partes.append(
                "PUNTOS DE LA CLASE:\n" +
                "\n\n".join([f"Punto {i+1}. {p}" for i, p in enumerate(puntos)])
            )
        return "\n\n".join([p for p in partes if p]).strip()

    def _buscar_layout_con_widget(self, layout, widget):
        if layout is None or widget is None:
            return None, -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            if item.widget() is widget:
                return layout, i
            sub = item.layout()
            if sub is not None:
                encontrado, idx = self._buscar_layout_con_widget(sub, widget)
                if encontrado is not None:
                    return encontrado, idx
        return None, -1

    def _instalar_controles_lectura_guiada(self, panel, clave: str):
        """Instala controles comunes en todas las pestañas integradas.

        - Botón junto al título: lee solo la parte superior.
        - Junto a "Leer clase": flechas atrás/adelante.
        - El avance solo se habilita tras marcar el punto actual como superado.
        """
        if panel is None or getattr(panel, "_lectura_guiada_instalada", False):
            return
        panel._lectura_guiada_instalada = True
        panel._clave_panel_lectura = clave
        panel._lectura_indice = 0
        panel._lectura_superados = set()

        puntos = self._puntos_lectura_panel(panel, clave)
        if not puntos:
            titulo_tmp = self._texto_titulo_panel(panel, clave)
            puntos = [titulo_tmp or self.texto_pantalla_actual()]
        panel._lectura_puntos = puntos

        # El título del panel se convierte en un botón suave y centrado.
        # Así ahorramos espacio y el propio título sirve para leer el resumen/contexto.
        try:
            layout = panel.layout()
            if layout is not None:
                titulo_widget = None
                titulo_idx = -1
                titulo_texto = "Leer título/resumen"
                for i in range(min(layout.count(), 6)):
                    item = layout.itemAt(i)
                    if item is None:
                        continue
                    w = item.widget()
                    if isinstance(w, QLabel):
                        txt = self._normalizar_texto_lectura(w.text())
                        if txt and len(txt) <= 120:
                            titulo_widget = w
                            titulo_idx = i
                            titulo_texto = txt
                            break

                titulo_texto = self._titulo_amigable_panel(panel, clave, titulo_texto)
                panel._lectura_titulo_texto = titulo_texto
                btn_titulo = QPushButton(titulo_texto)
                btn_titulo.setObjectName("BotonTituloLectura")
                btn_titulo.setCursor(Qt.PointingHandCursor)
                btn_titulo.setMinimumHeight(44)
                btn_titulo.setMinimumWidth(320)
                btn_titulo.setMaximumWidth(760)
                btn_titulo.setToolTip("Pulsa aquí para que el profesor lea el título y el resumen de esta pestaña")
                btn_titulo.setStyleSheet(
                    "QPushButton#BotonTituloLectura {"
                    "background-color: #dce9fb;"
                    "color: #173f73;"
                    "border: 1px solid #a9c4ef;"
                    "border-radius: 16px;"
                    "padding: 8px 22px;"
                    "font-size: 20px;"
                    "font-weight: 700;"
                    "}"
                    "QPushButton#BotonTituloLectura:hover {"
                    "background-color: #e8f1ff;"
                    "border-color: #8fb0e8;"
                    "}"
                    "QPushButton#BotonTituloLectura:pressed {"
                    "background-color: #cddffb;"
                    "}"
                )
                btn_titulo.clicked.connect(lambda _checked=False, panel=panel: self._leer_titulo_panel(panel))

                if titulo_widget is not None and titulo_idx >= 0:
                    layout.takeAt(titulo_idx)
                    try:
                        titulo_widget.setParent(None)
                    except Exception:
                        pass
                    barra_titulo = QFrame()
                    barra_titulo.setObjectName("BarraLecturaTituloIntegrada")
                    lay_titulo = QHBoxLayout(barra_titulo)
                    lay_titulo.setContentsMargins(0, 4, 0, 4)
                    lay_titulo.setSpacing(0)
                    lay_titulo.addStretch(1)
                    lay_titulo.addWidget(btn_titulo, 0, Qt.AlignCenter)
                    lay_titulo.addStretch(1)
                    layout.insertWidget(titulo_idx, barra_titulo)
                else:
                    barra_titulo = QFrame()
                    lay_titulo = QHBoxLayout(barra_titulo)
                    lay_titulo.setContentsMargins(0, 4, 0, 4)
                    lay_titulo.addStretch(1)
                    lay_titulo.addWidget(btn_titulo, 0, Qt.AlignCenter)
                    lay_titulo.addStretch(1)
                    layout.insertWidget(0, barra_titulo)

                panel.btn_leer_titulo_pestana = btn_titulo
        except Exception:
            pass

        # Controles junto al botón Leer.
        try:
            btn_leer = getattr(panel, "btn_leer", None)
            if btn_leer is not None:
                btn_leer.setText("Leer punto actual")
                self._desconectar_boton(btn_leer)
                btn_leer.clicked.connect(lambda _checked=False, panel=panel: self._leer_punto_actual_panel(panel))

                layout_padre, idx = self._buscar_layout_con_widget(panel.layout(), btn_leer)
                if layout_padre is not None:
                    btn_prev = QPushButton("←")
                    btn_prev.setToolTip("Volver al punto anterior")
                    btn_prev.setMinimumHeight(34)
                    btn_prev.setMinimumWidth(42)
                    btn_prev.clicked.connect(lambda _=False, panel=panel: self._punto_anterior_panel(panel))

                    btn_ok = QPushButton("Comprobar")
                    btn_ok.setToolTip("Abre un reto breve de comprensión antes de superar el punto")
                    btn_ok.setMinimumHeight(34)
                    btn_ok.clicked.connect(lambda _=False, panel=panel: self._marcar_punto_superado_panel(panel))

                    btn_next = QPushButton("→")
                    btn_next.setToolTip("Avanzar al punto siguiente")
                    btn_next.setMinimumHeight(34)
                    btn_next.setMinimumWidth(42)
                    btn_next.clicked.connect(lambda _=False, panel=panel: self._punto_siguiente_panel(panel))

                    lbl_punto = QLabel("")
                    lbl_punto.setMinimumWidth(160)

                    layout_padre.insertWidget(idx + 1, btn_prev)
                    layout_padre.insertWidget(idx + 2, btn_ok)
                    layout_padre.insertWidget(idx + 3, btn_next)
                    layout_padre.insertWidget(idx + 4, lbl_punto)

                    panel.btn_punto_anterior = btn_prev
                    panel.btn_punto_superado = btn_ok
                    panel.btn_punto_siguiente = btn_next
                    panel.lbl_estado_punto = lbl_punto
        except Exception:
            pass

        self._actualizar_controles_puntos(panel)

    def _actualizar_controles_puntos(self, panel):
        try:
            puntos = getattr(panel, "_lectura_puntos", []) or []
            idx = int(getattr(panel, "_lectura_indice", 0) or 0)
            total = len(puntos)
            superados = getattr(panel, "_lectura_superados", set()) or set()

            if hasattr(panel, "lbl_estado_punto"):
                panel.lbl_estado_punto.setText(f"Punto {idx + 1}/{total} · superados {len(superados)}/{total}")

            if hasattr(panel, "btn_punto_anterior"):
                panel.btn_punto_anterior.setEnabled(idx > 0)

            if hasattr(panel, "btn_punto_siguiente"):
                # Solo avanza si el punto actual está superado.
                panel.btn_punto_siguiente.setEnabled(idx in superados and idx < total - 1)

            if hasattr(panel, "btn_punto_superado"):
                panel.btn_punto_superado.setEnabled(idx not in superados)
                panel.btn_punto_superado.setText("Comprobar" if idx not in superados else "✓ Superado")
        except Exception:
            pass

    def _leer_titulo_panel(self, panel):
        # QPushButton.clicked puede enviar un bool si la lambda no lo absorbe.
        # Si ocurre, recuperamos el panel integrado activo.
        if panel is None or isinstance(panel, bool):
            try:
                panel = self.area_contenido_estudio.currentWidget()
            except Exception:
                panel = None

        texto = self._texto_titulo_panel(panel, getattr(panel, "_clave_panel_lectura", ""))
        if not texto:
            texto = (
                f"{self._nombre_alumno()}, esta pestaña sirve para continuar el trabajo del curso. "
                "Usa el botón de leer punto actual para avanzar por la explicación paso a paso."
            )
        texto = self._normalizar_texto_lectura(texto)
        self._ultimo_texto_profesor = texto
        self._actualizar_dialogo_avatar(texto)
        return self._hablar_con_avatar(texto)

    def _valor_ms_seguro(self, valor, maximo):
        try:
            if valor is None:
                return 0
            return max(0, min(int(round(float(valor))), int(maximo)))
        except Exception:
            return 0

    def _texto_resultado_diag(self, diag) -> str:
        correcto = getattr(diag, "correcto", None)
        if correcto is True:
            return "Correcto"
        if correcto is False:
            return "A corregir"
        return "Registrado"

    def _actualizar_panel_diagnostico_pro(self, diag):
        try:
            nota = getattr(diag, "nota", "") or "—"
            esperado = getattr(diag, "esperado", None)
            velocity = getattr(diag, "velocity", None)
            velocity_clase = getattr(diag, "velocity_clase", "—")
            pulso_clase = getattr(diag, "pulso_clase", "—")
            diferencia = getattr(diag, "diferencia_pulso_ms", None)
            reaccion = getattr(diag, "tiempo_reaccion_ms", None)
            simultaneidad = getattr(diag, "simultaneidad_ms", None)
            sobrantes = getattr(diag, "notas_sobrantes", []) or []
            faltantes = getattr(diag, "notas_faltantes", []) or []
            mensaje = getattr(diag, "mensaje_docente", "") or "Diagnóstico registrado."

            if hasattr(self, "lbl_diag_nota"):
                self.lbl_diag_nota.setText(f"Nota: {nota}")
                self.lbl_diag_esperado.setText(f"Esperado: {esperado if esperado else '—'}")
                self.lbl_diag_resultado.setText(f"Resultado: {self._texto_resultado_diag(diag)}")
                self.lbl_diag_velocity.setText(f"Velocity: {velocity if velocity is not None else '—'} · {velocity_clase}")
                self.barra_diag_velocity.setValue(max(0, min(int(velocity or 0), 127)))
                self.lbl_diag_pulso.setText(f"Pulso: {pulso_clase}")
                self.barra_diag_pulso.setValue(self._valor_ms_seguro(diferencia, 340))
                self.lbl_diag_reaccion.setText(f"Reacción: {reaccion if reaccion is not None else '—'} ms")
                self.barra_diag_reaccion.setValue(self._valor_ms_seguro(reaccion, 2000))
                self.lbl_diag_simultaneidad.setText(f"Simultaneidad: {simultaneidad if simultaneidad is not None else '—'} ms")
                self.barra_diag_simultaneidad.setValue(self._valor_ms_seguro(simultaneidad, 300))
                if sobrantes or faltantes:
                    self.lbl_diag_notas.setText(
                        "Sobrantes: "
                        + (", ".join(sobrantes) if sobrantes else "—")
                        + " · Faltantes: "
                        + (", ".join(faltantes) if faltantes else "—")
                    )
                else:
                    self.lbl_diag_notas.setText("Sobrantes/faltantes: —")
                self.lbl_diag_docente.setText("Corrección docente: " + mensaje)
        except Exception:
            pass

    def _diagnostico_pro_para_profesor(self, diag) -> str:
        try:
            mensaje = getattr(diag, "mensaje_docente", "") or ""
            velocity = getattr(diag, "velocity_clase", "")
            pulso = getattr(diag, "pulso_clase", "")
            faltantes = getattr(diag, "notas_faltantes", []) or []
            sobrantes = getattr(diag, "notas_sobrantes", []) or []
            extra = []
            if velocity in {"demasiado_fuerte", "muy_suave"}:
                extra.append("Trabaja la pulsación antes de subir velocidad.")
            if pulso == "fuera_de_pulso":
                extra.append("Repite más lento esperando el clic del metrónomo.")
            if faltantes:
                extra.append("Faltan notas: prepara la mano antes de bajar el acorde.")
            if sobrantes:
                extra.append("Sobran notas: revisa colocación y evita apoyar dedos no pedidos.")
            return (mensaje + " " + " ".join(extra)).strip()
        except Exception:
            return ""

    def _registrar_diagnostico_midi_pro(self, diag, origen: str = "midi_pro"):
        self._actualizar_panel_diagnostico_pro(diag)
        try:
            self._registrar_historial_midi(
                nota=getattr(diag, "nota", ""),
                velocity=getattr(diag, "velocity", None),
                canal=getattr(diag, "canal", None),
                origen=origen,
                esperado=getattr(diag, "esperado", None),
                correcto=getattr(diag, "correcto", None),
                diferencia_ms=getattr(diag, "diferencia_pulso_ms", None),
                en_pulso=(getattr(diag, "pulso_clase", "") in {"a_tiempo", "cerca_del_pulso"}),
                tipo=getattr(diag, "tipo", "nota"),
                mensaje=getattr(diag, "mensaje_docente", ""),
                contexto=getattr(diag, "contexto_historial", lambda: {})(),
            )
        except Exception:
            pass
        try:
            texto_profesor = self._diagnostico_pro_para_profesor(diag)
            if texto_profesor and getattr(diag, "correcto", None) is False and hasattr(self, "txt_resultado"):
                self.txt_resultado.setText(texto_profesor)
        except Exception:
            pass

    def _diagnostico_pro_desde_entrada(self, nota: str, velocity=None, canal=None, origen: str = "midi_in"):
        try:
            diag = self.analizador_midi_pro.note_on(
                nota=nota,
                velocity=velocity,
                canal=canal,
                origen=origen,
                ultimo_pulso_ts=getattr(self, "_pulso_pizarra_ultimo_beat_ts", 0.0) or None,
                tolerancia_pulso_ms=float(getattr(self, "_pulso_pizarra_tolerancia", 0.34) or 0.34) * 1000.0,
            )
            self._registrar_diagnostico_midi_pro(diag, origen=origen)
            return diag
        except Exception:
            return None

    def _registrar_historial_midi(
        self,
        nota: str = "",
        velocity: int | None = None,
        canal: int | None = None,
        origen: str = "midi",
        esperado=None,
        correcto=None,
        diferencia_ms=None,
        en_pulso=None,
        tipo: str = "nota",
        mensaje: str = "",
        contexto: dict | None = None,
    ):
        try:
            self.historial_alumno.registrar_midi_evento(
                nota=nota,
                velocity=velocity,
                canal=canal,
                origen=origen,
                esperado=esperado,
                correcto=correcto,
                diferencia_ms=diferencia_ms,
                en_pulso=en_pulso,
                tipo=tipo,
                mensaje=mensaje,
                contexto=contexto or {},
            )
        except Exception:
            pass

    def _resumen_historial_para_profesor(self) -> str:
        try:
            return self.historial_alumno.resumen_docente()
        except Exception:
            return "Historial pedagógico todavía sin datos suficientes."

    def _registrar_resultado_midi_lectura(self, correcto: bool):
        """Acumula resultados de la primera lectura con teclado MIDI."""
        try:
            if correcto:
                self._midi_lectura_aciertos += 1
            else:
                self._midi_lectura_errores += 1
            if hasattr(self, "lbl_midi_ultima"):
                self.lbl_midi_ultima.setText(
                    f"MIDI lectura: {self._midi_lectura_aciertos} aciertos · {self._midi_lectura_errores} errores"
                )
            self._registrar_historial_midi(
                nota="lectura",
                origen="lectura_pentagrama",
                correcto=bool(correcto),
                tipo="resultado_lectura",
                mensaje="Resultado de lectura MIDI/pizarra"
            )
        except Exception:
            pass

    def _midi_o_piano_texto(self) -> str:
        conectado = ""
        try:
            conectado = getattr(self.midi, "nombre_entrada_abierta", "") or ""
        except Exception:
            conectado = ""
        if conectado:
            return f"Puedes tocarlo en el piano virtual o en tu teclado MIDI conectado: {conectado}."
        return "Puedes tocarlo en el piano virtual. Si conectas un teclado MIDI, el profesor también lo evaluará."

    def _iniciar_pulso_pizarra_piano(self, secuencia, bpm: int = 60, texto: str = ""):
        """Activa un reto de pizarra con metrónomo: nota correcta + pulso."""
        secuencia = [str(n).strip() for n in (secuencia or []) if str(n).strip()]
        if not secuencia:
            secuencia = ["C4", "C4", "C4", "C4"]

        self._pulso_pizarra_secuencia = secuencia
        self._pulso_pizarra_pos = 0
        self._pulso_pizarra_bpm = max(40, min(160, int(bpm or 60)))
        self._pulso_pizarra_beat_actual = 0
        self._pulso_pizarra_ultimo_beat_ts = 0.0
        self._pulso_pizarra_activo = True
        try:
            self.analizador_midi_pro.configurar_objetivo(
                tipo="pulso",
                esperado=secuencia,
                permite_simultaneas=False,
                requiere_simultaneo=False
            )
        except Exception:
            pass

        # Cancelamos otros retos activos para que no se mezclen.
        self._secuencia_pizarra_activa = False
        self._secuencia_pizarra_esperada = []
        self._secuencia_pizarra_pos = 0
        self._reto_pizarra_notas_esperadas = set()
        self._reto_pizarra_notas_pendientes = set()

        intervalo_ms = int(60000 / self._pulso_pizarra_bpm)

        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente([secuencia[0]])
        except Exception:
            pass

        nombres = self._nombres_notas_profesor(secuencia)
        mensaje = (
            "Reto con pulso activado. Voy a contar con metrónomo. "
            "Toca en orden: "
            + " - ".join(nombres)
            + f". Tempo: {self._pulso_pizarra_bpm}. "
            "Intenta tocar cada nota justo después del clic."
        )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        self._hablar_con_avatar(mensaje)

        self._pulso_pizarra_timer.stop()
        self._pulso_pizarra_timer.start(intervalo_ms)
        QTimer.singleShot(120, self._tick_pulso_pizarra)

    def _tick_pulso_pizarra(self):
        """Click visual/sonoro del reto con pulso."""
        if not getattr(self, "_pulso_pizarra_activo", False):
            try:
                self._pulso_pizarra_timer.stop()
            except Exception:
                pass
            return

        secuencia = getattr(self, "_pulso_pizarra_secuencia", []) or []
        pos = int(getattr(self, "_pulso_pizarra_pos", 0) or 0)
        if pos >= len(secuencia):
            self._finalizar_pulso_pizarra(completado=True)
            return

        self._pulso_pizarra_beat_actual += 1
        self._pulso_pizarra_ultimo_beat_ts = time.monotonic()
        esperado = secuencia[pos]

        try:
            self.audio.sonido_metronomo(acento=(self._pulso_pizarra_beat_actual % 4 == 1))
        except Exception:
            pass

        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente([esperado])
        except Exception:
            pass

        nombre = self._nombres_notas_profesor([esperado])[0]
        self.txt_resultado.setText(
            f"Pulso {self._pulso_pizarra_beat_actual}: toca {nombre}. "
            "Escucha el clic y toca cerca del pulso."
        )

    def _finalizar_pulso_pizarra(self, completado: bool = False):
        self._pulso_pizarra_activo = False
        try:
            self.timer_audio_entrada.stop()
            self.audio_entrada.detener()
        except Exception:
            pass
        try:
            self._pulso_pizarra_timer.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "piano") and hasattr(self.piano, "limpiar_resaltado_docente"):
                self.piano.limpiar_resaltado_docente()
        except Exception:
            pass
        if completado:
            mensaje = (
                "Reto con pulso completado. Has seguido la secuencia con metrónomo. "
                "Este es el puente entre leer, tocar y mantener tiempo."
            )
            self.txt_resultado.setText(mensaje)
            self._actualizar_dialogo_avatar(mensaje)
            self._hablar_con_avatar(mensaje)

    def _procesar_pulso_pizarra_nota(self, nota: str) -> bool:
        """Valida una nota dentro del reto con metrónomo."""
        if not getattr(self, "_pulso_pizarra_activo", False):
            return False

        secuencia = getattr(self, "_pulso_pizarra_secuencia", []) or []
        pos = int(getattr(self, "_pulso_pizarra_pos", 0) or 0)
        if pos >= len(secuencia):
            self._finalizar_pulso_pizarra(completado=True)
            return True

        nota = str(nota or "").strip()
        esperada = secuencia[pos]
        ahora = time.monotonic()
        ultimo = float(getattr(self, "_pulso_pizarra_ultimo_beat_ts", 0.0) or 0.0)

        # Si aún no ha sonado el primer clic, no aceptamos la nota.
        if ultimo <= 0:
            mensaje = "Espera al primer clic del metrónomo antes de tocar."
            self.txt_resultado.setText(mensaje)
            self._actualizar_dialogo_avatar(mensaje)
            self._hablar_con_avatar(mensaje)
            return True

        diferencia = abs(ahora - ultimo)
        diferencia_ms = round(diferencia * 1000.0, 1)
        dentro_tiempo = diferencia <= float(getattr(self, "_pulso_pizarra_tolerancia", 0.34) or 0.34)

        entrada = getattr(self, "_ultima_entrada_alumno", {}) or {}
        if nota == esperada and dentro_tiempo:
            self._registrar_historial_midi(
                nota=nota,
                velocity=entrada.get("velocity"),
                canal=entrada.get("canal"),
                origen=entrada.get("origen", "alumno"),
                esperado=esperada,
                correcto=True,
                diferencia_ms=diferencia_ms,
                en_pulso=True,
                tipo="pulso",
                mensaje="Nota correcta y dentro del pulso",
                contexto={"tiempo_reaccion_ms": diferencia_ms, "pulso_clase": "a_tiempo"}
            )
            self._registrar_resultado_midi_lectura(True)
            pos += 1
            self._pulso_pizarra_pos = pos

            if pos >= len(secuencia):
                try:
                    self.analizador_midi_pro.avanzar_objetivo()
                except Exception:
                    pass
                self._finalizar_pulso_pizarra(completado=True)
                return True

            try:
                self.analizador_midi_pro.avanzar_objetivo()
            except Exception:
                pass
            siguiente = secuencia[pos]
            try:
                if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                    self.piano.resaltar_notas_docente([siguiente])
            except Exception:
                pass
            mensaje = (
                "Correcto y a tiempo. En el siguiente pulso toca "
                + self._nombres_notas_profesor([siguiente])[0]
                + "."
            )
            self.txt_resultado.setText(mensaje)
            self._actualizar_dialogo_avatar(mensaje)
            self._hablar_con_avatar(mensaje)
            return True

        self._registrar_resultado_midi_lectura(False)
        entrada = getattr(self, "_ultima_entrada_alumno", {}) or {}
        self._registrar_historial_midi(
            nota=nota,
            velocity=entrada.get("velocity"),
            canal=entrada.get("canal"),
            origen=entrada.get("origen", "alumno"),
            esperado=esperada,
            correcto=False,
            diferencia_ms=diferencia_ms,
            en_pulso=dentro_tiempo,
            tipo="pulso",
            mensaje="Error de nota o de pulso",
            contexto={"tiempo_reaccion_ms": diferencia_ms, "pulso_clase": "cerca_o_fuera_de_pulso"}
        )
        nombre_esperado = self._nombres_notas_profesor([esperada])[0]
        if nota != esperada:
            mensaje = (
                "La nota no coincide con la pizarra. Has tocado "
                + str(nota)
                + ", pero esperaba "
                + nombre_esperado
                + ". Seguimos en la misma nota."
            )
        else:
            mensaje = (
                "La nota es correcta, pero ha caído fuera del pulso. "
                "Espera el clic y toca "
                + nombre_esperado
                + " más cerca del tiempo."
            )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        self._hablar_con_avatar(mensaje)
        return True

    def _iniciar_secuencia_pizarra_piano(self, secuencia, texto: str = ""):
        """Activa una secuencia guiada nota por nota desde la pizarra."""
        secuencia = [str(n).strip() for n in (secuencia or []) if str(n).strip()]
        self._secuencia_pizarra_esperada = secuencia
        self._secuencia_pizarra_pos = 0
        self._secuencia_pizarra_activa = bool(secuencia)
        try:
            self.analizador_midi_pro.configurar_objetivo(
                tipo="secuencia",
                esperado=secuencia,
                permite_simultaneas=False,
                requiere_simultaneo=False
            )
        except Exception:
            pass

        # Al iniciar una secuencia, cancelamos un reto de nota aislada.
        self._reto_pizarra_notas_esperadas = set()
        self._reto_pizarra_notas_pendientes = set()
        self._reto_pizarra_texto = ""

        if not secuencia:
            aviso = "Este paso de la pizarra no tiene una secuencia concreta para tocar."
            self._actualizar_dialogo_avatar(aviso)
            return self._hablar_con_avatar(aviso)

        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente([secuencia[0]])
        except Exception:
            pass

        nombres = self._nombres_notas_profesor(secuencia)
        mensaje = (
            "Secuencia guiada activada para lectura aplicada al teclado. Toca en este orden: "
            + " - ".join(nombres)
            + ". Empieza por: "
            + self._nombres_notas_profesor([secuencia[0]])[0]
            + ". "
            + self._midi_o_piano_texto()
        )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        return self._hablar_con_avatar(mensaje)

    def _procesar_secuencia_pizarra_nota(self, nota: str) -> bool:
        """Procesa una nota si hay secuencia guiada activa."""
        if not getattr(self, "_secuencia_pizarra_activa", False):
            return False

        secuencia = getattr(self, "_secuencia_pizarra_esperada", []) or []
        pos = int(getattr(self, "_secuencia_pizarra_pos", 0) or 0)
        if pos >= len(secuencia):
            self._secuencia_pizarra_activa = False
            return False

        nota = str(nota or "").strip()
        esperada = secuencia[pos]

        if nota == esperada:
            pos += 1
            self._secuencia_pizarra_pos = pos
            try:
                self.analizador_midi_pro.avanzar_objetivo()
            except Exception:
                pass

            if pos >= len(secuencia):
                self._secuencia_pizarra_activa = False
                self._secuencia_pizarra_esperada = []
                self._secuencia_pizarra_pos = 0
                try:
                    if hasattr(self, "piano") and hasattr(self.piano, "limpiar_resaltado_docente"):
                        self.piano.limpiar_resaltado_docente()
                except Exception:
                    pass

                self._registrar_resultado_midi_lectura(True)
                mensaje = (
                    "Secuencia completada. Has tocado todas las notas en orden. "
                    "Esto ya empieza a parecer una frase musical: leer, tocar y comprobar."
                )
                self.txt_resultado.setText(mensaje)
                self._actualizar_dialogo_avatar(mensaje)
                self._hablar_con_avatar(mensaje)
                return True

            siguiente = secuencia[pos]
            try:
                if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                    self.piano.resaltar_notas_docente([siguiente])
            except Exception:
                pass

            self._registrar_resultado_midi_lectura(True)
            mensaje = (
                "Correcto. Ahora toca: "
                + self._nombres_notas_profesor([siguiente])[0]
                + "."
            )
            self.txt_resultado.setText(mensaje)
            self._actualizar_dialogo_avatar(mensaje)
            self._hablar_con_avatar(mensaje)
            return True

        # Error: reinicia la secuencia desde el principio.
        self._secuencia_pizarra_pos = 0
        primero = secuencia[0] if secuencia else ""
        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente([primero] if primero else [])
        except Exception:
            pass

        self._registrar_resultado_midi_lectura(False)
        mensaje = (
            "Te has salido de la secuencia. Has tocado "
            + str(nota)
            + ", pero ahora esperaba "
            + self._nombres_notas_profesor([esperada])[0]
            + ". Volvemos al principio: toca "
            + self._nombres_notas_profesor([primero])[0]
            + "."
        )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        self._hablar_con_avatar(mensaje)
        return True

    def _iniciar_reto_pizarra_piano(self, notas, texto: str = ""):
        """Activa un mini-reto: el alumno debe tocar en el piano lo señalado por la pizarra."""
        notas = [str(n).strip() for n in (notas or []) if str(n).strip()]
        self._reto_pizarra_notas_esperadas = set(notas)
        self._reto_pizarra_notas_pendientes = set(notas)
        self._reto_pizarra_texto = self._normalizar_texto_lectura(texto or "")
        try:
            self.analizador_midi_pro.configurar_objetivo(
                tipo="nota",
                esperado=notas,
                permite_simultaneas=False,
                requiere_simultaneo=False
            )
        except Exception:
            pass

        if not notas:
            aviso = (
                "Este paso de la pizarra no tiene una tecla concreta para comprobar. "
                "Avanza a un paso con SOL, FA, DO central o digitación."
            )
            self._actualizar_dialogo_avatar(aviso)
            return self._hablar_con_avatar(aviso)

        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente(notas)
        except Exception:
            pass

        nombres = self._nombres_notas_profesor(notas)
        mensaje = (
            "Reto de pizarra activado para lectura aplicada al teclado. "
            "Ahora toca: " + ", ".join(nombres) + ". "
            "No avanzo esta práctica hasta que pulses la tecla correcta. "
            + self._midi_o_piano_texto()
        )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        return self._hablar_con_avatar(mensaje)

    def _nombres_notas_profesor(self, notas):
        mapa = {
            "C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si",
            "C#": "Do sostenido", "D#": "Re sostenido", "F#": "Fa sostenido",
            "G#": "Sol sostenido", "A#": "La sostenido",
        }
        salida = []
        for nota in notas or []:
            n = str(nota).strip()
            if not n:
                continue
            base = n[:-1] if n[-1:].isdigit() else n
            octava = n[-1] if n[-1:].isdigit() else ""
            if n == "C4":
                salida.append("DO central")
            else:
                salida.append((mapa.get(base, base) + (f" {octava}" if octava else "")).strip())
        return salida

    def _procesar_reto_pizarra_nota(self, nota: str) -> bool:
        """Procesa una nota tocada si hay un reto de pizarra activo.

        Devuelve True si la nota pertenecía al reto y se ha gestionado.
        """
        pendientes = getattr(self, "_reto_pizarra_notas_pendientes", set()) or set()
        esperadas = getattr(self, "_reto_pizarra_notas_esperadas", set()) or set()
        if not pendientes:
            return False

        nota = str(nota or "").strip()
        if nota in pendientes:
            pendientes.discard(nota)
            self._reto_pizarra_notas_pendientes = pendientes

            if not pendientes:
                try:
                    if hasattr(self, "piano") and hasattr(self.piano, "limpiar_resaltado_docente"):
                        self.piano.limpiar_resaltado_docente()
                except Exception:
                    pass
                self._reto_pizarra_notas_esperadas = set()
                self._reto_pizarra_texto = ""
                try:
                    self.analizador_midi_pro.limpiar_objetivo()
                except Exception:
                    pass

                self._registrar_resultado_midi_lectura(True)
                mensaje = (
                    "Correcto. Has tocado la tecla que la pizarra estaba señalando. "
                    "Esto conecta la teoría con el teclado: ver, entender y tocar."
                )
                self.txt_resultado.setText(mensaje)
                self._actualizar_dialogo_avatar(mensaje)
                self._hablar_con_avatar(mensaje)
                return True

            self._registrar_resultado_midi_lectura(True)
            mensaje = (
                "Bien. Esa nota es correcta. Falta tocar: "
                + ", ".join(self._nombres_notas_profesor(sorted(pendientes)))
                + "."
            )
            self.txt_resultado.setText(mensaje)
            self._actualizar_dialogo_avatar(mensaje)
            self._hablar_con_avatar(mensaje)
            return True

        # Nota incorrecta: no consume el reto.
        self._registrar_resultado_midi_lectura(False)
        esperadas_txt = ", ".join(self._nombres_notas_profesor(sorted(esperadas)))
        mensaje = (
            f"Esa tecla no es la que está pidiendo la pizarra. Has tocado {nota}. "
            f"Busca y toca: {esperadas_txt}."
        )
        self.txt_resultado.setText(mensaje)
        self._actualizar_dialogo_avatar(mensaje)
        self._hablar_con_avatar(mensaje)
        return True

    def _resaltar_notas_pizarra_en_piano(self, notas):
        """Resalta en el piano virtual las notas que la pizarra está explicando."""
        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente(notas or [])
        except Exception:
            pass

    def _obtener_pizarra_activa(self):
        """Devuelve la pizarra visible del panel actual, si existe."""
        candidatos = []
        try:
            actual = self.area_contenido_estudio.currentWidget()
            if actual is not None:
                candidatos.append(getattr(actual, "pizarra_musical_profesor", None))
        except Exception:
            pass
        try:
            candidatos.append(getattr(self, "pizarra_midi_didactico", None))
        except Exception:
            pass
        for piz in candidatos:
            try:
                if piz is not None and piz.isVisible():
                    return piz
            except Exception:
                continue
        return None

    def _sincronizar_pizarra_docente_por_texto(self, texto: str):
        """Aplica marcas temporales de pizarra desde el texto que ya usa el profesor."""
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "aplicar_marca_docente_por_texto"):
                pizarra.aplicar_marca_docente_por_texto(texto)
        except Exception:
            pass

    def _preparar_secuencia_pizarra_docente(self, texto: str):
        """Prepara una línea de tiempo de marcas para sincronizar pizarra y voz."""
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is None or not hasattr(pizarra, "preparar_secuencia_docente"):
                return
            duracion = int(getattr(self, "_voz_duracion_ms_estimada", 0) or self._estimar_duracion_voz_ms(texto))
            pizarra.preparar_secuencia_docente(texto, duracion)
        except Exception:
            pass

    def _iniciar_secuencia_pizarra_docente(self):
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "iniciar_secuencia_docente"):
                pizarra.iniciar_secuencia_docente()
        except Exception:
            pass

    def _pausar_secuencia_pizarra_docente(self):
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "pausar_secuencia_docente"):
                pizarra.pausar_secuencia_docente()
        except Exception:
            pass

    def _reanudar_secuencia_pizarra_docente(self):
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "reanudar_secuencia_docente"):
                pizarra.reanudar_secuencia_docente()
        except Exception:
            pass

    def _detener_secuencia_pizarra_docente(self, limpiar: bool = True):
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "detener_secuencia_docente"):
                pizarra.detener_secuencia_docente(limpiar)
        except Exception:
            pass

    def _representar_midi_externo_en_pentagrama(self, nota: str, velocity: int = 0, canal: int = 0):
        """Coloca en el pentagrama la nota recibida desde el teclado MIDI externo."""
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "mostrar_nota_midi_externa"):
                pizarra.mostrar_nota_midi_externa(nota, velocity, canal, "midi_in")
        except Exception:
            pass

    def _limpiar_midi_externo_en_pentagrama(self, nota: str):
        try:
            pizarra = self._obtener_pizarra_activa()
            if pizarra is not None and hasattr(pizarra, "limpiar_nota_midi_externa"):
                pizarra.limpiar_nota_midi_externa(nota)
        except Exception:
            pass

    def _leer_texto_pizarra_musical(self, texto: str):
        """Hace que el profesor lea lo que la pizarra está mostrando en ese momento."""
        texto = self._normalizar_texto_lectura(str(texto or ""))
        if not texto:
            return False
        narracion = "Ahora, la pizarra muestra: " + texto
        self._ultimo_texto_profesor = narracion
        self._actualizar_dialogo_avatar(narracion)
        return self._hablar_con_avatar(narracion)

    def _asegurar_pizarra_musical_panel(self, panel):
        """Crea o recupera la pizarra musical en el recuadro superior del panel.

        Corrección v3.9.2:
        En algunas pestañas, especialmente Partitura, el QTextEdit superior vive
        dentro de un QFrame. La búsqueda anterior solo recorría layouts directos
        y no entraba en el layout del widget padre, por eso la pizarra no se
        insertaba aunque el botón "Leer punto actual" funcionase.
        """
        if panel is None or isinstance(panel, bool):
            return None

        if hasattr(panel, "pizarra_musical_profesor"):
            return panel.pizarra_musical_profesor

        widget_base = None
        for attr in ("txt_profesor", "txt_resumen"):
            w = getattr(panel, attr, None)
            if w is not None and hasattr(w, "parentWidget"):
                widget_base = w
                break

        if widget_base is None:
            return None

        layout_padre = None
        idx = -1

        # 1) Caso importante: QTextEdit dentro de un QFrame con layout propio.
        try:
            parent = widget_base.parentWidget()
            if parent is not None and parent.layout() is not None:
                lay = parent.layout()
                for i in range(lay.count()):
                    item = lay.itemAt(i)
                    if item is not None and item.widget() is widget_base:
                        layout_padre = lay
                        idx = i
                        break
        except Exception:
            layout_padre = None
            idx = -1

        # 2) Fallback: búsqueda recursiva antigua.
        if layout_padre is None:
            try:
                layout_padre, idx = self._buscar_layout_con_widget(panel.layout(), widget_base)
            except Exception:
                layout_padre, idx = None, -1

        if layout_padre is None or idx < 0:
            return None

        pizarra = PizarraMusicalProfesor(panel)
        pizarra.setVisible(False)
        # v4.1.10: pizarra visible desde el primer momento, sin aplastar piano/metrónomo.
        pizarra.setMinimumHeight(460)
        try:
            pizarra.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass

        try:
            pizarra.paso_leido.connect(self._leer_texto_pizarra_musical)
            pizarra.ejemplo_leido.connect(self._leer_texto_pizarra_musical)
            pizarra.texto_leido.connect(self._leer_texto_pizarra_musical)
            pizarra.notas_resaltadas.connect(self._resaltar_notas_pizarra_en_piano)
            pizarra.practica_piano_solicitada.connect(self._iniciar_reto_pizarra_piano)
            pizarra.secuencia_piano_solicitada.connect(self._iniciar_secuencia_pizarra_piano)
            pizarra.pulso_piano_solicitado.connect(self._iniciar_pulso_pizarra_piano)
        except Exception:
            pass

        try:
            layout_padre.insertWidget(idx, pizarra)
            widget_base.setVisible(False)
        except Exception:
            return None

        panel.pizarra_musical_profesor = pizarra
        panel._widget_texto_superior_original = widget_base

        try:
            panel.updateGeometry()
            panel.update()
        except Exception:
            pass

        return pizarra

    def _mostrar_pizarra_musical_para_punto(self, panel, texto_punto: str, idx: int, total: int):
        pizarra = self._asegurar_pizarra_musical_panel(panel)
        if pizarra is None:
            return None
        try:
            titulo = ""
            try:
                titulo = self._titulo_amigable_panel(panel, getattr(panel, "_clave_panel_lectura", ""), "")
            except Exception:
                titulo = ""

            pizarra.preparar_desde_punto(texto_punto, idx, total, titulo or f"Punto {idx + 1}")
            pizarra.setVisible(True)
            pizarra.raise_()

            original = getattr(panel, "_widget_texto_superior_original", None)
            if original is not None:
                original.setVisible(False)

            try:
                if pizarra.parentWidget() is not None:
                    pizarra.parentWidget().updateGeometry()
                    pizarra.parentWidget().update()
                panel.updateGeometry()
                panel.update()
            except Exception:
                pass

            # No forzamos QApplication.processEvents() aquí. Procesar eventos
            # dentro de una actualización de panel puede reentrar en voz/audio/MIDI
            # y dejar Qt aparentemente ocupado. Dejamos que el event loop normal
            # repinte la pizarra.
            return pizarra
        except Exception:
            return None

    def _leer_punto_actual_panel(self, panel):
        # QPushButton.clicked puede enviar un bool si la lambda no lo absorbe.
        # Si ocurre, recuperamos el panel integrado activo.
        if panel is None or isinstance(panel, bool):
            try:
                panel = self.area_contenido_estudio.currentWidget()
            except Exception:
                panel = None

        puntos = getattr(panel, "_lectura_puntos", []) or []
        idx = int(getattr(panel, "_lectura_indice", 0) or 0)
        if not puntos:
            return self._leer_panel_integrado(panel)
        idx = max(0, min(idx, len(puntos) - 1))
        panel._lectura_indice = idx
        pizarra = self._mostrar_pizarra_musical_para_punto(panel, puntos[idx], idx, len(puntos))
        narracion_pizarra = ""
        try:
            if pizarra is not None:
                narracion_pizarra = pizarra.texto_sincronizado_actual()
        except Exception:
            narracion_pizarra = ""

        texto = (
            f"Punto {idx + 1} de {len(puntos)}.\n\n"
            f"{puntos[idx]}\n\n"
            "He abierto la pizarra musical y voy sincronizado con lo que aparece dibujado. "
            "Ahora la pizarra tiene capas didácticas y puede resaltar notas en el piano virtual.\n\n"
            + (f"Ahora, la pizarra muestra: {narracion_pizarra}\n\n" if narracion_pizarra else "")
            + "Puedes activar u ocultar capas como Claves, Notas, DO central, Manos, Figuras, Pulso, Digitación o Puntero. "
            "También puedes pulsar Tocar en piano para convertir lo señalado en un pequeño reto práctico, "
            "Tocar secuencia para tocar varias notas en orden, o Tocar con pulso para hacerlo con metrónomo, usando el piano virtual o tu teclado MIDI externo. "
            "Si pulsas paso anterior, paso siguiente, mostrar ejemplo o ver texto, el profesor leerá exactamente esa parte de la pizarra.\n\n"
            "Cuando entiendas este punto, pulsa «Comprobar». "
            "Si superas el reto breve, se desbloqueará la flecha para avanzar."
        )
        texto = self._normalizar_texto_lectura(texto)
        self._ultimo_texto_profesor = texto
        self._actualizar_dialogo_avatar(texto)
        self._actualizar_controles_puntos(panel)
        return self._hablar_con_avatar(texto)

    def _marcar_punto_superado_panel(self, panel):
        # Antes de superar un punto, el alumno debe pasar un reto breve.
        if panel is None or isinstance(panel, bool):
            try:
                panel = self.area_contenido_estudio.currentWidget()
            except Exception:
                panel = None

        puntos = getattr(panel, "_lectura_puntos", []) or []
        idx = int(getattr(panel, "_lectura_indice", 0) or 0)
        if not puntos:
            return self._leer_panel_integrado(panel)

        idx = max(0, min(idx, len(puntos) - 1))
        texto_punto = self._normalizar_texto_lectura(puntos[idx])
        reto = self.comprobador_docente.generar_reto(texto_punto)

        dlg = DialogoRetoComprension(reto, idx + 1, self)
        resultado = dlg.exec()

        if resultado != QDialog.Accepted or not getattr(dlg, "es_correcta", False):
            texto = (
                "Todavía no marco este punto como superado. "
                "Lee otra vez el punto, escucha la explicación y vuelve a intentarlo.\n\n"
                f"Pregunta: {reto.get('pregunta', '')}\n"
                f"Respuesta correcta: {reto.get('correcta', '')}\n\n"
                f"{reto.get('explicacion', '')}"
            )
            self._actualizar_dialogo_avatar(texto)
            self._actualizar_controles_puntos(panel)
            return self._hablar_con_avatar(texto)

        superados = getattr(panel, "_lectura_superados", set()) or set()
        superados.add(idx)
        panel._lectura_superados = superados

        texto = (
            f"Correcto. Punto {idx + 1} superado. "
            "Ahora puedes avanzar con la flecha hacia la derecha."
        )
        if idx >= len(puntos) - 1:
            texto = (
                "Correcto. Has superado el último punto de esta clase. "
                "Ahora puedes usar el botón principal de la pestaña si corresponde: marcar lectura, completar rutina, pasar a práctica o cerrar."
            )

        self._actualizar_dialogo_avatar(texto)
        self._actualizar_controles_puntos(panel)
        return self._hablar_con_avatar(texto)

    def _punto_anterior_panel(self, panel):
        idx = int(getattr(panel, "_lectura_indice", 0) or 0)
        panel._lectura_indice = max(0, idx - 1)
        self._actualizar_controles_puntos(panel)
        return self._leer_punto_actual_panel(panel)

    def _punto_siguiente_panel(self, panel):
        puntos = getattr(panel, "_lectura_puntos", []) or []
        idx = int(getattr(panel, "_lectura_indice", 0) or 0)
        superados = getattr(panel, "_lectura_superados", set()) or set()
        if idx not in superados:
            texto = (
                "Antes de avanzar, tienes que marcar este punto como superado. "
                "La idea es no pasar por encima de la clase sin entenderla."
            )
            self._actualizar_dialogo_avatar(texto)
            return self._hablar_con_avatar(texto)
        panel._lectura_indice = min(len(puntos) - 1, idx + 1)
        self._actualizar_controles_puntos(panel)
        return self._leer_punto_actual_panel(panel)

    def _leer_panel_integrado(self, panel):
        """Lee la clase completa de una pestaña.

        Se mantiene como opción interna, pero el botón visible lee por puntos.
        """
        texto = self._texto_panel_integrado(panel)
        if not texto:
            texto = self.texto_pantalla_actual()
        texto = self._normalizar_texto_lectura(texto)
        self._ultimo_texto_profesor = texto
        self._actualizar_dialogo_avatar(texto)
        return self._hablar_con_avatar(texto)


    def _preparar_dialogo_como_panel(self, dialogo, clave: str, texto_avatar: str = ""):
        if hasattr(dialogo, "setWindowFlags"):
            dialogo.setWindowFlags(Qt.Widget)
        dialogo.setParent(self.area_contenido_estudio)
        try:
            dialogo.setMinimumSize(0, 0)
            dialogo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            dialogo.setSizePolicy(dialogo.sizePolicy())
        anterior = self.paginas_estudio_dinamicas.get(clave)
        if anterior is not None and anterior is not getattr(self, "pagina_clase_practica", None):
            try:
                self.area_contenido_estudio.removeWidget(anterior)
                anterior.setParent(None)
                anterior.deleteLater()
            except Exception:
                pass
        self.paginas_estudio_dinamicas[clave] = dialogo
        self.area_contenido_estudio.addWidget(dialogo)
        self.area_contenido_estudio.setCurrentWidget(dialogo)
        self._clave_panel_estudio = clave
        self.stack.setCurrentWidget(self.pantalla_estudio)
        self._instalar_controles_lectura_guiada(dialogo, clave)
        if texto_avatar:
            # Al abrir la pestaña se muestra el encabezado; la lectura real se hace por puntos.
            self._actualizar_dialogo_avatar(self._texto_titulo_panel(dialogo, clave) or texto_avatar)
        return dialogo

    def volver_al_inicio(self):
        self.stack.setCurrentWidget(self.pantalla_inicio)
        try:
            self.pantalla_inicio.mostrar_inicio()
            self._actualizar_dialogo_avatar(self.pantalla_inicio._texto_actual)
        except Exception:
            self._actualizar_dialogo_avatar("Has vuelto al inicio del curso.")

    def abrir_configuracion(self):
        dlg = DialogoConfiguracion(self, self)
        dlg.exec()

    def aplicar_configuracion_usuario(self):
        a = self.ajustes.ajustes
        self._configurar_audio_desde_ajustes()
        self.lbl_audio.setText("Audio: activo" if a.audio_activo else "Audio: desactivado")
        if hasattr(self, "avatar"):
            self.avatar.set_tipo(a.avatar_tipo)
        if hasattr(self, "piano"):
            self.piano.aplicar_configuracion(a.piano_mostrar_nombres, a.piano_altura)
        if hasattr(self, "lbl_midi_compacto"):
            conectado_in = getattr(self.midi, "nombre_entrada_abierta", "")
            conectado_out = getattr(self.midi, "nombre_salida_abierta", "")
            partes = []
            if conectado_in:
                partes.append(f"IN: {conectado_in}")
            if conectado_out:
                partes.append(f"OUT: {conectado_out}")
            self.lbl_midi_compacto.setText("MIDI alumno: " + " | ".join(partes) if partes else "MIDI alumno: sin conectar")
        self._aplicar_estilo()

    def _precalentar_voz_piper(self):
        """Carga Piper en caché del sistema para que el primer Play tarde menos."""
        try:
            a = self.ajustes.ajustes
            if not getattr(a, "voz_activa", True):
                return
            self.voz_avatar.precalentar_async(
                avatar_tipo=getattr(a, "avatar_tipo", "chico"),
                modelo_chica=getattr(a, "voz_piper_modelo_chica", ""),
                modelo_chico=getattr(a, "voz_piper_modelo_chico", ""),
                velocidad=getattr(a, "voz_velocidad", 100),
            )
        except Exception:
            pass

    def _precachear_texto_profesor(self, texto: str):
        try:
            texto = str(texto or "").strip()
            if not texto:
                return
            a = self.ajustes.ajustes
            self.voz_avatar.preparar_texto_async(
                texto=texto,
                avatar_tipo=getattr(a, "avatar_tipo", "chico"),
                modelo_chica=getattr(a, "voz_piper_modelo_chica", ""),
                modelo_chico=getattr(a, "voz_piper_modelo_chico", ""),
                velocidad=getattr(a, "voz_velocidad", 100),
                volumen=getattr(a, "voz_volumen", 95),
                pausa_coma_ms=getattr(a, "voz_pausa_coma_ms", 650),
                pausa_punto_ms=getattr(a, "voz_pausa_punto_ms", 1200),
            )
        except Exception:
            pass

    def _conectar_midi_preferido_si_procede(self):
        a = self.ajustes.ajustes
        if not a.conectar_midi_al_iniciar:
            return

        ok_in = True
        ok_out = True
        partes = []

        if a.midi_in_preferido:
            ok_in = self.midi.abrir_entrada(a.midi_in_preferido)
            partes.append(f"IN: {a.midi_in_preferido}" if ok_in else f"IN error: {self.midi.error}")

        if a.midi_out_preferido:
            ok_out = self.midi.abrir_salida(a.midi_out_preferido)
            partes.append(f"OUT: {a.midi_out_preferido}" if ok_out else f"OUT error: {self.midi.error}")

        if hasattr(self, "lbl_midi_compacto"):
            self.lbl_midi_compacto.setText("MIDI alumno: " + " | ".join(partes) if partes else "MIDI alumno: sin puertos")
        if hasattr(self, "lbl_midi_estado"):
            self.lbl_midi_estado.setText("MIDI: " + " | ".join(partes) if partes else "MIDI: sin puertos")

    def _poner_texto_profesor(self, texto: str, hablar: bool = False):
        self._ultimo_texto_profesor = texto or ""
        self.txt_profesor.setText(texto)
        self._actualizar_dialogo_avatar(texto)
        self._sincronizar_pizarra_docente_por_texto(texto)
        # Prepara la voz en segundo plano en cuanto aparece la explicación.
        # Así, al pulsar Play, el arranque sale de caché y no hay espera larga.
        if self.ajustes.ajustes.voz_activa:
            self._precachear_texto_profesor(texto)
        if hablar and self.ajustes.ajustes.voz_activa and self.ajustes.ajustes.leer_clases_automaticamente:
            self._hablar_con_avatar(texto)

    def play_voz_actual(self):
        """Play compacto del narrador.

        Si la voz está pausada, reanuda al instante. Si está detenida, reproduce
        el texto visible actual sin cambiar la fase de la clase.
        """
        try:
            if self.voz_avatar.esta_pausado():
                self.voz_avatar.reanudar()
                self._reanudar_progreso_voz()
                if hasattr(self, "btn_voz_pausa"):
                    self.btn_voz_pausa.setText("Ⅱ")
                if hasattr(self, "avatar"):
                    self.avatar.iniciar_habla()
                return
        except Exception:
            pass
        texto = ""
        try:
            texto = self.txt_profesor.toPlainText().strip()
        except Exception:
            texto = ""
        if not texto:
            texto = getattr(self, "_ultimo_texto_profesor", "")
        if not texto:
            self.explicar_otra_vez()
            return
        self._hablar_con_avatar(texto)

    def _estimar_duracion_voz_ms(self, texto: str) -> int:
        """Estimación estable para la barra de transporte.

        Piper genera el audio antes de reproducirlo; sin leer el WAV final desde
        la UI, esta estimación permite mostrar tiempo transcurrido y faltante de
        forma clara. Se calcula con palabras, puntuación y velocidad configurada.
        """
        try:
            velocidad = max(50, min(220, int(self.ajustes.ajustes.voz_velocidad)))
        except Exception:
            velocidad = 100
        texto = str(texto or "")
        palabras = max(1, len(texto.split()))
        # Ritmo base natural: aprox. 150 palabras/minuto a velocidad 100.
        ms = int((palabras / 150.0) * 60_000 * (100.0 / float(velocidad)))
        ms += texto.count(",") * int(getattr(self.ajustes.ajustes, "voz_pausa_coma_ms", 650))
        ms += (texto.count(".") + texto.count("!") + texto.count("?") + texto.count(":") + texto.count(";")) * int(getattr(self.ajustes.ajustes, "voz_pausa_punto_ms", 1200))
        return max(2_000, min(15 * 60_000, ms))

    def _formatear_tiempo_voz(self, ms: int) -> str:
        ms = max(0, int(ms))
        segundos = ms // 1000
        return f"{segundos // 60:02d}:{segundos % 60:02d}"

    def _barras_progreso_voz(self):
        barras = []
        for nombre in ("barra_voz_progreso", "barra_voz_progreso_compacta"):
            barra = getattr(self, nombre, None)
            if barra is not None:
                barras.append(barra)
        return barras

    def _set_valor_barras_voz(self, valor: int):
        valor = max(0, min(1000, int(valor)))
        for barra in self._barras_progreso_voz():
            barra.setValue(valor)

    def _set_tiempo_barras_voz(self, elapsed_ms: int, restante_ms: int):
        texto_transcurrido = self._formatear_tiempo_voz(elapsed_ms)
        texto_restante = self._formatear_tiempo_voz(restante_ms)
        texto_completo = f"{texto_transcurrido} / faltan {texto_restante}"
        if hasattr(self, "lbl_voz_tiempo"):
            self.lbl_voz_tiempo.setText(texto_completo)
        if hasattr(self, "lbl_voz_tiempo_transcurrido"):
            self.lbl_voz_tiempo_transcurrido.setText(texto_transcurrido)
        if hasattr(self, "lbl_voz_tiempo_restante"):
            self.lbl_voz_tiempo_restante.setText(f"-{texto_restante}")
        for barra in self._barras_progreso_voz():
            barra.setToolTip(f"Narración: {texto_completo}")

    def _preparar_progreso_voz(self, texto: str):
        self._voz_texto_en_curso = texto or ""
        self._voz_duracion_ms_estimada = self._estimar_duracion_voz_ms(texto)
        self._voz_inicio_mono = None
        self._voz_ms_acumulados = 0
        self._voz_pausada_transporte = False
        self._set_valor_barras_voz(0)
        self._set_tiempo_barras_voz(0, self._voz_duracion_ms_estimada)

    def _arrancar_progreso_voz(self):
        self._voz_inicio_mono = time.monotonic()
        self._voz_ms_acumulados = 0
        self._voz_pausada_transporte = False
        if hasattr(self, "timer_voz_progreso"):
            self.timer_voz_progreso.start()
        self._actualizar_progreso_voz()

    def _pausar_progreso_voz(self):
        if self._voz_inicio_mono is not None and not self._voz_pausada_transporte:
            self._voz_ms_acumulados += int((time.monotonic() - self._voz_inicio_mono) * 1000)
        self._voz_inicio_mono = None
        self._voz_pausada_transporte = True
        self._actualizar_progreso_voz()

    def _reanudar_progreso_voz(self):
        self._voz_inicio_mono = time.monotonic()
        self._voz_pausada_transporte = False
        self._actualizar_progreso_voz()

    def _detener_progreso_voz(self, limpiar=True):
        if hasattr(self, "timer_voz_progreso"):
            self.timer_voz_progreso.stop()
        self._voz_inicio_mono = None
        self._voz_ms_acumulados = 0
        self._voz_pausada_transporte = False
        if limpiar:
            self._set_valor_barras_voz(0)
            self._set_tiempo_barras_voz(0, 0)

    def _voz_seek_desde_barra(self, ratio: float):
        """Permite mover la narración desde la barra compacta."""
        try:
            ratio = max(0.0, min(1.0, float(ratio)))
        except Exception:
            return
        dur = max(1, int(getattr(self, "_voz_duracion_ms_estimada", 1)))
        self._voz_ms_acumulados = int(dur * ratio)
        if getattr(self, "_voz_inicio_mono", None) is not None and not getattr(self, "_voz_pausada_transporte", False):
            self._voz_inicio_mono = time.monotonic()
        try:
            self.voz_avatar.saltar_a_porcentaje(ratio)
        except Exception:
            pass
        self._actualizar_progreso_voz()

    def _actualizar_progreso_voz(self):
        dur = max(1, int(getattr(self, "_voz_duracion_ms_estimada", 1)))
        elapsed = int(getattr(self, "_voz_ms_acumulados", 0))
        inicio = getattr(self, "_voz_inicio_mono", None)
        if inicio is not None and not getattr(self, "_voz_pausada_transporte", False):
            elapsed += int((time.monotonic() - inicio) * 1000)
        elapsed = max(0, min(dur, elapsed))
        restante = max(0, dur - elapsed)
        self._set_valor_barras_voz(int((elapsed / dur) * 1000))
        self._set_tiempo_barras_voz(elapsed, restante)
        if elapsed >= dur and getattr(self, "_voz_inicio_mono", None) is not None:
            # Si la estimación termina antes que el reproductor real, se deja
            # la barra completa hasta recibir la señal real de fin.
            self._set_valor_barras_voz(1000)

    def _hablar_con_avatar(self, texto: str) -> bool:
        self._aplicar_ordenes_musicales_profesor(texto)
        texto = self._interpretar_texto_profesor(texto)
        a = self.ajustes.ajustes
        self._preparar_progreso_voz(texto)
        self._preparar_secuencia_pizarra_docente(texto)
        if hasattr(self, "lbl_voz_estado"):
            self.lbl_voz_estado.setText("Narrador: preparando")
        if hasattr(self, "avatar"):
            self.avatar.set_tipo(a.avatar_tipo)
        ok = self.voz_avatar.hablar(
            texto,
            avatar_tipo=a.avatar_tipo,
            velocidad=a.voz_velocidad,
            volumen=a.voz_volumen,
            motor=a.voz_motor,
            pausa_coma_ms=getattr(a, "voz_pausa_coma_ms", 450),
            pausa_punto_ms=getattr(a, "voz_pausa_punto_ms", 850),
            modelo_chica=getattr(a, "voz_piper_modelo_chica", ""),
            modelo_chico=getattr(a, "voz_piper_modelo_chico", ""),
            on_start=self.voz_bridge.inicio.emit,
            on_end=self.voz_bridge.fin.emit,
            on_error=self.voz_bridge.error.emit,
        )
        if not ok and hasattr(self, "avatar"):
            self.avatar.parar_habla()
        return ok

    def _aplicar_ordenes_musicales_profesor(self, texto: str):
        """Permite que el profesor gobierne tempo/metrónomo desde texto estructurado."""
        bruto = str(texto or "").lower()
        if "bpm" not in bruto and "metrónomo" not in bruto and "metronomo" not in bruto:
            return
        m = re.search(r"(\d{2,3})\s*(?:bpm|ppm|pulsos)", bruto)
        if not m:
            m = re.search(r"(?:metrónomo|metronomo|tempo).*?(\d{2,3})", bruto)
        if not m:
            return
        try:
            self.cambiar_bpm_musical(int(m.group(1)), origen="profesor")
        except Exception:
            pass


    def _voz_inicio_ui(self):
        if hasattr(self, "lbl_voz_estado"):
            self.lbl_voz_estado.setText("Narrador: hablando")
        if hasattr(self, "btn_voz_pausa"):
            self.btn_voz_pausa.setText("Ⅱ")
        self._arrancar_progreso_voz()
        self._iniciar_secuencia_pizarra_docente()

    def _voz_fin_ui(self):
        if hasattr(self, "lbl_voz_estado"):
            self.lbl_voz_estado.setText("Narrador: listo")
        if hasattr(self, "btn_voz_pausa"):
            self.btn_voz_pausa.setText("Ⅱ")
        self._set_valor_barras_voz(1000)
        self._set_tiempo_barras_voz(getattr(self, "_voz_duracion_ms_estimada", 0), 0)
        if hasattr(self, "timer_voz_progreso"):
            self.timer_voz_progreso.stop()
        self._detener_secuencia_pizarra_docente(limpiar=True)
        if hasattr(self, "avatar"):
            self.avatar.parar_habla()

    def pausar_reanudar_voz(self):
        pausada = self.voz_avatar.alternar_pausa()
        if hasattr(self, "btn_voz_pausa"):
            self.btn_voz_pausa.setText("▶" if pausada else "Ⅱ")
        if hasattr(self, "lbl_voz_estado"):
            self.lbl_voz_estado.setText("Narrador: pausado" if pausada else "Narrador: hablando")
        if pausada:
            self._pausar_progreso_voz()
            self._pausar_secuencia_pizarra_docente()
        else:
            self._reanudar_progreso_voz()
            self._reanudar_secuencia_pizarra_docente()
        if pausada and hasattr(self, "avatar"):
            self.avatar.parar_habla()
        elif hasattr(self, "avatar"):
            self.avatar.iniciar_habla()

    def stop_voz(self):
        self.voz_avatar.detener()
        self._detener_progreso_voz(limpiar=True)
        self._detener_secuencia_pizarra_docente(limpiar=True)
        if hasattr(self, "avatar"):
            self.avatar.parar_habla()
        if hasattr(self, "btn_voz_pausa"):
            self.btn_voz_pausa.setText("Ⅱ")
        if hasattr(self, "lbl_voz_estado"):
            self.lbl_voz_estado.setText("Narrador: detenido")
        try:
            # También limpia notas de demostración o notas sostenidas.
            self.audio.parar()
        except Exception:
            pass

    def detener_voz(self):
        self.stop_voz()

    def _mostrar_error_voz(self, texto_error: str):
        if hasattr(self, "txt_resultado") and texto_error:
            self.txt_resultado.setText(f"Voz no disponible: {texto_error}")

    def _crear_paneles_profesionales(self):
        tabs = QTabWidget()
        # La zona profesional debe ser compacta: cámara, audio y plan no deben empujar
        # ni tapar el teclado inferior ni el contenido principal de la lección.
        tabs.setMaximumHeight(245)
        tabs.addTab(self._crear_panel_ajustes(), "Audio / MIDI")
        tabs.addTab(self._crear_panel_midi_didactico(), "MIDI Didáctico")
        tabs.addTab(self._crear_panel_diagnostico_pro(), "Diagnóstico Pro")
        tabs.addTab(self._crear_panel_entradas_pro(), "Entradas Pro")
        tabs.addTab(self._crear_panel_camara(), "Cámara / Reconocimiento")
        tabs.addTab(self._crear_panel_plan(), "Plan del profesor")
        return tabs

    def _crear_panel_midi_didactico(self):
        grupo = QGroupBox("Reproductor MIDI didáctico sincronizado")
        grid = QGridLayout(grupo)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(5)

        self.combo_midi_didactico = QComboBox()
        for item in self.midi_didactico.listar_piezas():
            self.combo_midi_didactico.addItem(item.get("titulo", item.get("id", "Pieza")), item)

        btn_cargar = QPushButton("Cargar")
        btn_cargar.clicked.connect(self._midi_didactico_cargar)
        btn_clase1 = QPushButton("Clase 1 Nivel 1")
        btn_clase1.clicked.connect(self._cargar_clase1_nivel1)
        btn_clase = QPushButton("Modo clase")
        btn_clase.clicked.connect(self._midi_didactico_modo_clase)
        btn_escuchar = QPushButton("Escuchar guía")
        btn_escuchar.clicked.connect(self._midi_didactico_escuchar)
        btn_practicar = QPushButton("Practicar")
        btn_practicar.clicked.connect(self._midi_didactico_practicar)
        btn_examen = QPushButton("Examen")
        btn_examen.clicked.connect(self._midi_didactico_examen)
        btn_parar = QPushButton("Parar")
        btn_parar.clicked.connect(self._midi_didactico_parar)
        btn_externo = QPushButton("Cargar MIDI externo")
        btn_externo.clicked.connect(self._midi_externo_intentar_cargar)

        self.lbl_midi_didactico_estado = QLabel("MIDI didáctico: selecciona una pieza o pulsa Clase 1 Nivel 1.")
        self.lbl_midi_didactico_estado.setWordWrap(True)
        self.lbl_midi_externo_plan = QLabel("MIDI externo: bloqueado hasta Nivel 3. Sin plan de pistas activo.")
        self.lbl_midi_externo_plan.setWordWrap(True)
        self.pizarra_midi_didactico = PizarraMusicalProfesor(self)
        # v4.1.9: altura suficiente para pentagrama vivo, barra de acciones y texto docente.
        self.pizarra_midi_didactico.setMinimumHeight(540)
        try:
            self.pizarra_midi_didactico.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.lbl_midi_didactico_actual = QLabel("Actual: —")
        self.lbl_midi_didactico_siguiente = QLabel("Siguiente: —")
        self.lbl_midi_didactico_modo = QLabel("Modo: clase")
        self.barra_midi_didactico = QProgressBar()
        self.barra_midi_didactico.setRange(0, 100)
        self.barra_midi_didactico.setValue(0)
        self.barra_midi_didactico.setFormat("Pieza %p%")

        grid.addWidget(QLabel("Pieza"), 0, 0)
        grid.addWidget(self.combo_midi_didactico, 0, 1, 1, 3)
        grid.addWidget(btn_cargar, 0, 4)
        grid.addWidget(btn_clase1, 1, 0)
        grid.addWidget(btn_clase, 1, 1)
        grid.addWidget(btn_escuchar, 1, 2)
        grid.addWidget(btn_practicar, 1, 3)
        grid.addWidget(btn_examen, 1, 4)
        grid.addWidget(btn_parar, 2, 0)
        grid.addWidget(btn_externo, 2, 1)
        grid.addWidget(self.lbl_midi_didactico_modo, 2, 2)
        grid.addWidget(self.lbl_midi_didactico_actual, 2, 3)
        grid.addWidget(self.lbl_midi_didactico_siguiente, 2, 4)
        grid.addWidget(self.barra_midi_didactico, 3, 0, 1, 5)
        grid.addWidget(self.lbl_midi_didactico_estado, 4, 0, 1, 5)
        grid.addWidget(self.lbl_midi_externo_plan, 5, 0, 1, 5)
        grid.addWidget(self.pizarra_midi_didactico, 6, 0, 1, 5)
        return grupo

    def _hanon_clave_digitacion_evento(self, evento) -> tuple:
        """Clave estable para cruzar notas MIDI Hanon con su digitación calculada."""
        if not evento:
            return ()
        if isinstance(evento, dict):
            try:
                midi = int(evento.get("midi", evento.get("midi_number", 0)) or 0)
            except Exception:
                midi = 0
            try:
                inicio = int(evento.get("inicio_ms", 0) or 0)
            except Exception:
                inicio = 0
            try:
                canal = int(evento.get("canal", 0) or 0)
            except Exception:
                canal = 0
            return (midi, inicio, canal)
        try:
            return (
                int(getattr(evento, "midi", 0) or 0),
                int(getattr(evento, "inicio_ms", 0) or 0),
                int(getattr(evento, "canal", 0) or 0),
            )
        except Exception:
            return ()

    def _hanon_enriquecer_digitacion(self, notas: list[dict]) -> list[dict]:
        """Añade mano/dedo siguiendo la digitación base de Hanon.

        Hanon 1 y los patrones preparatorios del paquete usan células de 8 notas.
        Para mano derecha se visualiza 1-2-3-4-5-4-3-2; para mano izquierda,
        5-4-3-2-1-2-3-4. La cuenta se lleva por mano para que manos simultáneas
        conserven su digitación propia.
        """
        patron = {
            "derecha": [1, 2, 3, 4, 5, 4, 3, 2],
            "izquierda": [5, 4, 3, 2, 1, 2, 3, 4],
        }
        contadores = {"derecha": 0, "izquierda": 0}
        mapa = {}
        enriquecidas = []
        for nota in sorted([dict(n or {}) for n in (notas or [])], key=lambda n: (int(n.get("inicio_ms", 0) or 0), int(n.get("midi", 0) or 0))):
            mano = str(nota.get("mano", "") or "").strip().lower()
            if "izq" in mano or "left" in mano or mano == "lh":
                mano = "izquierda"
            elif "der" in mano or "right" in mano or mano == "rh":
                mano = "derecha"
            else:
                try:
                    mano = "izquierda" if int(nota.get("midi", 0) or 0) < 60 else "derecha"
                except Exception:
                    mano = "derecha"
            seq = patron[mano]
            dedo = seq[contadores[mano] % len(seq)]
            contadores[mano] += 1
            nota["mano"] = mano
            nota["dedo"] = dedo
            nota["finger"] = dedo
            nota["digitacion"] = {
                "metodo": "hanon",
                "mano": mano,
                "dedo": dedo,
                "patron_8_notas": "-".join(str(x) for x in seq),
            }
            mapa[self._hanon_clave_digitacion_evento(nota)] = {
                "mano": mano,
                "dedo": dedo,
                "finger": dedo,
                "digitacion": dict(nota["digitacion"]),
            }
            enriquecidas.append(nota)
        self._hanon_digitacion_por_evento = mapa
        return sorted(enriquecidas, key=lambda n: (int(n.get("inicio_ms", 0) or 0), int(n.get("midi", 0) or 0)))

    def _hanon_aplicar_digitacion_a_dict(self, salida: dict) -> dict:
        try:
            mapa = getattr(self, "_hanon_digitacion_por_evento", {}) or {}
            dig = mapa.get(self._hanon_clave_digitacion_evento(salida))
            if dig:
                salida.update(dig)
        except Exception:
            pass
        return salida

    def _hanon_texto_digitacion(self, evento: dict | None) -> str:
        evento = evento or {}
        try:
            dedo = int(evento.get("dedo", evento.get("finger", 0)) or 0)
        except Exception:
            dedo = 0
        mano = str(evento.get("mano", "") or "").strip().lower()
        if not dedo:
            return ""
        mano_txt = "mano izquierda" if "izq" in mano or mano == "izquierda" else "mano derecha"
        return f"{mano_txt}, dedo {dedo}"

    def _nota_midi_didactica_a_dict(self, nota):
        if nota is None:
            return {}
        try:
            midi = int(getattr(nota, "midi", 0) or 0)
            info = normalizar_nota(getattr(nota, "nota", ""), midi=midi if midi else None)
            salida = {
                "nota": info.get("nota") or getattr(nota, "nota", ""),
                "note_name": info.get("note_name", ""),
                "nombre": info.get("nombre", ""),
                "nombre_completo": info.get("nombre_completo", ""),
                "octave": info.get("octave"),
                "octava": info.get("octava"),
                "midi": int(info.get("midi") or midi or 0),
                "midi_number": int(info.get("midi") or midi or 0),
                "inicio_ms": int(getattr(nota, "inicio_ms", 0) or 0),
                "duracion_ms": int(getattr(nota, "duracion_ms", 0) or 0),
                "fin_ms": int(getattr(nota, "fin_ms")()),
                "velocity": int(getattr(nota, "velocity", 0) or 0),
                "canal": int(getattr(nota, "canal", 0) or 0),
                "pulso": int(getattr(nota, "pulso", 0) or 0),
                "compas": int(getattr(nota, "compas", 0) or 0),
                "mano": getattr(nota, "mano", ""),
            }
            return self._hanon_aplicar_digitacion_a_dict(salida)
        except Exception:
            return {}

    def _normalizar_evento_practica(self, evento) -> dict:
        if not evento:
            return {}
        if isinstance(evento, dict):
            midi = evento.get("midi") or evento.get("midi_number")
            info = normalizar_nota(evento.get("nota") or evento.get("note_name") or evento.get("nombre_completo", ""), midi=int(midi) if midi else None)
            salida = dict(evento)
            salida.update({
                "nota": info.get("nota", salida.get("nota", "")),
                "note_name": info.get("note_name", ""),
                "nombre": info.get("nombre", ""),
                "nombre_completo": info.get("nombre_completo", ""),
                "octave": info.get("octave"),
                "octava": info.get("octava"),
                "midi": info.get("midi"),
                "midi_number": info.get("midi"),
            })
            return self._hanon_aplicar_digitacion_a_dict(salida)
        return self._nota_midi_didactica_a_dict(evento)

    def _debug_practica(self, visual: dict, esperada: dict, recibida: dict, resultado: str):
        try:
            v = self._normalizar_evento_practica(visual)
            e = self._normalizar_evento_practica(esperada)
            r = self._normalizar_evento_practica(recibida)
            print(
                "[DEBUG PRACTICA]\n"
                f"nota_visual = {v.get('nombre_completo') or v.get('nota')} midi={v.get('midi')}\n"
                f"nota_esperada = {e.get('nombre_completo') or e.get('nota')} midi={e.get('midi')}\n"
                f"nota_midi_recibida = {r.get('nombre_completo') or r.get('nota')} midi={r.get('midi')}\n"
                f"resultado = {resultado}"
            )
            if v.get("midi") != e.get("midi"):
                print("[DEBUG PRACTICA] ERROR: visual y esperada no coinciden")
        except Exception:
            pass

    def _midi_didactico_preparar_pentagrama_vivo(self, pieza):
        try:
            notas = [self._nota_midi_didactica_a_dict(n) for n in (pieza.notas or [])]
            notas = [n for n in notas if n]
            if hasattr(self, "pizarra_midi_didactico"):
                self.pizarra_midi_didactico.preparar_midi_didactico(
                    notas,
                    f"ND · Pentagrama vivo · {pieza.titulo}"
                )
        except Exception:
            pass

    def _midi_didactico_actualizar_pentagrama_vivo(self, actual=None, siguiente=None, activas=None):
        try:
            pieza = self.midi_didactico.pieza
            dur = max(1, int(getattr(pieza, "duracion_ms", 1) or 1))
            tiempo = int(getattr(self, "_midi_didactico_tiempo_ms", 0) or 0)
            progreso = max(0.0, min(1.0, tiempo / dur))
            if hasattr(self, "pizarra_midi_didactico"):
                self.pizarra_midi_didactico.actualizar_midi_didactico(
                    actual=self._nota_midi_didactica_a_dict(actual),
                    siguiente=self._nota_midi_didactica_a_dict(siguiente),
                    activas=[self._nota_midi_didactica_a_dict(n) for n in (activas or [])],
                    tiempo_ms=tiempo,
                    progreso=progreso,
                    modo=getattr(self, "_midi_didactico_modo", "clase"),
                    bpm=getattr(self.reloj_musical, "bpm", None),
                    beat=getattr(self.reloj_musical, "beat_compas", lambda: 1)(),
                    compas_num=getattr(self.reloj_musical, "compas_num", 4),
                )
        except Exception:
            pass

    def _cargar_clase1_nivel1(self):
        try:
            pieza = self.midi_didactico.cargar_por_id("n1_midi_tecnica_cinco_dedos_do")
            self._midi_didactico_preparar_pentagrama_vivo(pieza)
            self._midi_didactico_tiempo_ms = 0
            self._midi_didactico_modo = "clase"
            texto = (
                "Nivel 1, clase 1. Técnica de cinco dedos en DO con mano derecha. "
                "Primero colocamos 1-2-3-4-5 sobre DO, RE, MI, FA y SOL. "
                "Después escuchamos la guía, practicamos y hacemos examen."
            )
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
            if hasattr(self, "piano"):
                self.piano.resaltar_notas_docente(["C4", "D4", "E4", "F4", "G4"])
            try:
                self.analizador_midi_pro.configurar_objetivo(
                    tipo="secuencia",
                    esperado=["C4", "D4", "E4", "F4", "G4", "F4", "E4", "D4", "C4"],
                    permite_simultaneas=False
                )
            except Exception:
                pass
            self._midi_didactico_actualizar_panel()
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
            try:
                self.historial_alumno.registrar_clase("n1_01", "Técnica 1: cinco dedos en DO con mano derecha", "clase_iniciada", None, {"version": "4.1.4"})
            except Exception:
                pass
        except Exception as exc:
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(f"No se pudo cargar la Clase 1 Nivel 1: {exc}")

    def _nivel_actual_para_midi_externo(self) -> int:
        try:
            nivel = getattr(self.progreso.estado, "nivel_actual", "nivel_0")
            texto = str(nivel or "nivel_0").strip().lower()
            if texto == "inicial":
                return 0
            if texto.startswith("nivel_"):
                return int(texto.rsplit("_", 1)[1])
            return int(texto)
        except Exception:
            pass
        return 0

    def _midi_externo_intentar_cargar(self):
        nivel = self._nivel_actual_para_midi_externo()
        regla_previa = self.politica_midi_externo.evaluar(None, nivel)
        if not regla_previa.permitido:
            texto = regla_previa.mensaje_profesor
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
            self._hablar_con_avatar(texto)
            QMessageBox.information(self, "MIDI externo bloqueado", texto)
            return

        ruta, _filtro = QFileDialog.getOpenFileName(self, "Seleccionar MIDI externo", str(DATA_DIR.parent), "Archivos MIDI (*.mid *.midi)")
        if not ruta:
            return
        resultado = self.politica_midi_externo.evaluar(ruta, nivel)
        texto = resultado.mensaje_profesor
        if hasattr(self, "lbl_midi_didactico_estado"):
            self.lbl_midi_didactico_estado.setText(texto)
        self._hablar_con_avatar(texto)
        if not resultado.permitido:
            QMessageBox.warning(self, "MIDI externo no aceptado", texto)
            return
        try:
            plan = self.selector_pistas_midi_externo.crear_plan(ruta, nivel)
            self._ultimo_plan_midi_externo = plan
            ruta_plan = self.selector_pistas_midi_externo.guardar_plan(plan)
            resumen_plan = self.selector_pistas_midi_externo.resumen_humano(plan)
            if hasattr(self, "lbl_midi_externo_plan"):
                self.lbl_midi_externo_plan.setText("Plan de pistas: " + resumen_plan)
            self.historial_alumno.registrar_observacion_pro("midi_externo_plan_pistas", resumen_plan, {"nivel": nivel, "ruta": ruta, "plan_guardado": str(ruta_plan), "plan": plan.dict()})
        except Exception as exc:
            resumen_plan = f"MIDI aceptado, pero no he podido crear el plan de pistas: {exc}"
        QMessageBox.information(self, "MIDI externo aceptado", texto + "\n\n" + resumen_plan)

    def _midi_didactico_pieza_actual(self):
        try:
            if self.midi_didactico.pieza is None:
                self._midi_didactico_cargar()
            return self.midi_didactico.pieza
        except Exception:
            return None

    def _midi_didactico_cargar_desde_ejercicio(self, ejercicio: dict):
        ruta_midi = (
            ejercicio.get("archivo_midi")
            or ejercicio.get("midi_path")
            or ejercicio.get("archivo")
        )
        if not ruta_midi:
            return None
        self._midi_didactico_parar(limpiar=False)
        meta = {
            "id": ejercicio.get("id") or ejercicio.get("clase_id") or Path(str(ruta_midi)).stem,
            "titulo": ejercicio.get("titulo") or ejercicio.get("enunciado") or "MIDI de clase",
            "tempo": ejercicio.get("tempo"),
            "compas": ejercicio.get("compas", "4/4"),
            "clase_id": ejercicio.get("clase_id"),
            "nivel": ejercicio.get("nivel"),
        }
        pieza = self.midi_didactico.cargar_por_archivo(ruta_midi, meta)
        self._midi_didactico_preparar_pentagrama_vivo(pieza)
        self._midi_didactico_tiempo_ms = 0
        self._midi_didactico_notas_sonando = set()
        self._midi_didactico_compas_anunciado = 0
        self._midi_didactico_modo = "clase"
        self._midi_didactico_actualizar_panel()
        return pieza

    def _midi_didactico_cargar(self):
        try:
            idx = int(self.combo_midi_didactico.currentIndex()) if hasattr(self, "combo_midi_didactico") else 0
            pieza = self.midi_didactico.cargar_por_indice(idx)
            self._midi_didactico_preparar_pentagrama_vivo(pieza)
            self._midi_didactico_tiempo_ms = 0
            self._midi_didactico_notas_sonando = set()
            self._midi_didactico_compas_anunciado = 0
            self._midi_didactico_modo = "clase"
            self._midi_didactico_actualizar_panel()
            texto = (
                f"MIDI didáctico interno cargado: {pieza.titulo}. "
                f"Tempo {pieza.tempo}, compás {pieza.compas}, {len(pieza.notas or [])} notas. "
                "Primero escucha la guía, después practica y finalmente usa modo examen."
            )
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
        except Exception as exc:
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(f"No se pudo cargar el MIDI didáctico: {exc}")

    def _midi_didactico_modo_clase(self):
        pieza = self._midi_didactico_pieza_actual()
        if not pieza:
            return
        self._midi_didactico_parar()
        self._midi_didactico_modo = "clase"
        if hasattr(self, "lbl_midi_didactico_modo"):
            self.lbl_midi_didactico_modo.setText("Modo: clase")
        primera = (pieza.notas or [None])[0]
        if primera and hasattr(self, "piano"):
            self.piano.resaltar_notas_docente([primera.nota])
        texto = f"Modo clase. Vamos a estudiar {pieza.titulo}. Observa compás, pulso, nota y mano antes de tocar."
        if hasattr(self, "lbl_midi_didactico_estado"):
            self.lbl_midi_didactico_estado.setText(texto)
        self._hablar_con_avatar(texto)

    def _midi_didactico_escuchar(self):
        if self._midi_didactico_pieza_actual():
            self._midi_didactico_iniciar("escuchar")

    def _midi_didactico_practicar(self):
        if self._midi_didactico_pieza_actual():
            self._midi_didactico_iniciar("practica")

    def _midi_didactico_examen(self):
        if self._midi_didactico_pieza_actual():
            self._midi_didactico_iniciar("examen")

    def _midi_didactico_iniciar(self, modo: str):
        pieza = self._midi_didactico_pieza_actual()
        if not pieza:
            return
        self._midi_didactico_parar(limpiar=False)
        self._midi_didactico_modo = modo
        self._midi_didactico_tiempo_ms = 0
        self._midi_didactico_ultimo_ts = time.monotonic()
        self._midi_didactico_notas_sonando = set()
        self._midi_didactico_compas_anunciado = 0
        self.reloj_musical.configurar(pieza.tempo, pieza.compas, pieza.duracion_ms)
        self.reloj_musical.play()
        if modo == "practica":
            self._midi_practica_indice = 0
            self._midi_practica_ultimo_beat_ts = time.monotonic()
            self._midi_practica_velocity_objetivo = int((pieza.notas or [None])[0].velocity) if (pieza.notas or []) else 80
        if hasattr(self, "lbl_midi_didactico_modo"):
            self.lbl_midi_didactico_modo.setText(f"Modo: {modo}")
        if modo == "practica":
            texto = (
                f"Práctica de {pieza.titulo}. No avanzo de nota hasta que toques la nota correcta cerca del pulso. "
                "Si fallas, te diré si fue nota equivocada, antes o tarde, o con dinámica irregular."
            )
        else:
            texto = f"{modo.capitalize()} de {pieza.titulo}. El profesor sincroniza compás, pulso, piano y Motor MIDI Pro."
        if hasattr(self, "lbl_midi_didactico_estado"):
            self.lbl_midi_didactico_estado.setText(texto)
        self._hablar_con_avatar(texto)
        self.timer_midi_didactico.start()

    def cambiar_bpm_musical(self, bpm: int, origen: str = "profesor"):
        self.reloj_musical.set_bpm(bpm)
        texto = f"Metrónomo a {self.reloj_musical.bpm} BPM."
        if origen == "profesor":
            texto = "Profesor: " + texto
        try:
            if hasattr(self, "lbl_hanon_estado") and self.stack.currentWidget() == getattr(self, "pantalla_hanon", None):
                self.lbl_hanon_estado.setText(texto)
            elif hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
        except Exception:
            pass
        self._actualizar_dialogo_avatar(texto)
        return self.reloj_musical.bpm

    def _midi_didactico_note_on_interno(self, nota: str, velocity: int = 96):
        try:
            vel = max(1, min(127, int(velocity or 96)))
            self.audio.note_on(nota, velocity=vel)
        except Exception:
            pass

    def _midi_didactico_note_off_interno(self, nota: str):
        try:
            self.audio.note_off(nota)
        except Exception:
            pass

    def _midi_didactico_parar(self, limpiar=True):
        try:
            self.timer_midi_didactico.stop()
        except Exception:
            pass
        for nota in list(getattr(self, "_midi_didactico_notas_sonando", set())):
            try:
                self._midi_didactico_note_off_interno(nota)
            except Exception:
                pass
        self._midi_didactico_notas_sonando = set()
        try:
            self.reloj_musical.pause()
        except Exception:
            pass
        if limpiar:
            try:
                self.piano.limpiar_resaltado_docente()
            except Exception:
                pass
            try:
                self.analizador_midi_pro.limpiar_objetivo()
            except Exception:
                pass
            try:
                self.pizarra_midi_didactico.limpiar_midi_didactico()
            except Exception:
                pass

    def _midi_practica_nota_esperada(self):
        pieza = getattr(self.midi_didactico, "pieza", None)
        notas = list(getattr(pieza, "notas", []) or [])
        if not notas:
            return None
        idx = max(0, min(int(getattr(self, "_midi_practica_indice", 0) or 0), len(notas) - 1))
        return notas[idx]

    def _midi_practica_actualizar_objetivo(self, estado_reloj: dict | None = None):
        pieza = getattr(self.midi_didactico, "pieza", None)
        esperada = self._midi_practica_nota_esperada()
        if not pieza or not esperada:
            return
        idx = int(getattr(self, "_midi_practica_indice", 0) or 0)
        notas = list(pieza.notas or [])
        siguiente = notas[idx + 1] if idx + 1 < len(notas) else None
        self._midi_didactico_tiempo_ms = int(esperada.inicio_ms)
        progreso = idx / max(1, len(notas))
        visual = self._normalizar_evento_practica(esperada)
        siguiente_visual = self._normalizar_evento_practica(siguiente)
        try:
            self.pizarra_midi_didactico.actualizar_midi_didactico(
                actual=visual,
                siguiente=siguiente_visual,
                activas=[visual],
                tiempo_ms=int(esperada.inicio_ms),
                progreso=progreso,
                modo="practica",
                bpm=getattr(self.reloj_musical, "bpm", None),
                beat=(estado_reloj or {}).get("beat", self.reloj_musical.beat_compas()),
                compas_num=getattr(self.reloj_musical, "compas_num", 4),
            )
        except Exception:
            pass
        try:
            self.piano.resaltar_notas_docente([visual.get("nota", esperada.nota)])
        except Exception:
            pass
        try:
            self.analizador_midi_pro.configurar_objetivo(
                tipo="pulso",
                esperado=[visual.get("nota", esperada.nota)],
                permite_simultaneas=False,
                requiere_simultaneo=False,
            )
        except Exception:
            pass
        if hasattr(self, "lbl_midi_didactico_actual"):
            self.lbl_midi_didactico_actual.setText(f"Practica: {idx + 1}/{len(notas)} · toca {visual.get('nombre_completo') or visual.get('nota')}")
        if hasattr(self, "barra_midi_didactico"):
            self.barra_midi_didactico.setValue(max(0, min(100, int(progreso * 100))))

    def _procesar_midi_didactico_practica_entrada(self, nota: str, velocity: int, canal: int) -> bool:
        if getattr(self, "_midi_didactico_modo", "") != "practica":
            return False
        esperada = self._midi_practica_nota_esperada()
        pieza = getattr(self.midi_didactico, "pieza", None)
        if not esperada or not pieza:
            return False
        evento_esperado = self._normalizar_evento_practica(esperada)
        evento_recibido = normalizar_nota(nota)

        ahora = time.monotonic()
        beat_ms = float(self.reloj_musical.beat_ms())
        desde_beat_ms = max(0.0, (ahora - float(getattr(self, "_midi_practica_ultimo_beat_ts", ahora) or ahora)) * 1000.0)
        hasta_siguiente_ms = max(0.0, beat_ms - desde_beat_ms)
        usa_siguiente = hasta_siguiente_ms < desde_beat_ms
        diff_ms = -hasta_siguiente_ms if usa_siguiente else desde_beat_ms
        en_tiempo = abs(diff_ms) <= int(getattr(self, "_midi_practica_tolerancia_ms", 180) or 180)
        nota_ok = evento_recibido.get("midi") == evento_esperado.get("midi")
        vel = max(0, min(127, int(velocity or 0)))
        vel_obj = max(1, min(127, int(getattr(esperada, "velocity", 0) or getattr(self, "_midi_practica_velocity_objetivo", 80) or 80)))
        vel_baja = vel < max(20, vel_obj - 28)
        vel_alta = vel > min(127, vel_obj + 28)

        if not nota_ok:
            mensaje = (
                f"Nota equivocada: tocaste {evento_recibido.get('nombre_completo') or nota}, "
                f"pero esperaba {evento_esperado.get('nombre_completo') or evento_esperado.get('nota')}. Repite mirando la nota activa."
            )
            correcto = False
        elif not en_tiempo:
            if diff_ms < 0:
                mensaje = f"Te adelantaste {int(abs(diff_ms))} ms. Espera el clic del metrónomo antes de tocar {evento_esperado.get('nombre_completo') or evento_esperado.get('nota')}."
            else:
                mensaje = f"Tocaste tarde {int(abs(diff_ms))} ms. Entra más cerca del pulso con {evento_esperado.get('nombre_completo') or evento_esperado.get('nota')}."
            correcto = False
        else:
            partes = [f"Correcto: {evento_esperado.get('nombre_completo') or evento_esperado.get('nota')} en pulso."]
            if vel_alta:
                partes.append("Ha sonado demasiado fuerte; relaja la mano y baja la velocity.")
            elif vel_baja:
                partes.append("Ha sonado demasiado bajo; apoya un poco más el dedo sin tensión.")
            mensaje = " ".join(partes)
            correcto = True

        try:
            origen = "midi_practica_correcta" if correcto else ("midi_practica_fuera_pulso" if nota_ok else "midi_practica_incorrecta")
            self.pizarra_midi_didactico.mostrar_nota_midi_externa(evento_recibido.get("nota", nota), velocity, canal, origen)
        except Exception:
            pass
        try:
            self.historial_alumno.registrar_midi_evento(
                nota=evento_recibido.get("nota", nota),
                velocity=velocity,
                canal=canal,
                origen="midi_didactico_practica",
                esperado=evento_esperado.get("nota"),
                correcto=correcto,
                diferencia_ms=diff_ms,
                en_pulso=en_tiempo,
                tipo="nota",
                mensaje=mensaje,
                contexto={"pieza": getattr(pieza, "id", ""), "indice": int(getattr(self, "_midi_practica_indice", 0) or 0)},
            )
        except Exception:
            pass

        if hasattr(self, "lbl_midi_didactico_estado"):
            self.lbl_midi_didactico_estado.setText(mensaje)
        self._debug_practica(evento_esperado, evento_esperado, evento_recibido, "CORRECTO" if correcto else "INCORRECTO")
        self._actualizar_dialogo_avatar(mensaje)
        if not correcto:
            self._hablar_con_avatar(mensaje)
            return True

        notas = list(pieza.notas or [])
        self._midi_practica_indice += 1
        if self._midi_practica_indice >= len(notas):
            self._midi_didactico_parar(limpiar=False)
            final = f"Práctica completada: {pieza.titulo}. Has tocado todas las notas en pulso."
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(final)
            self._hablar_con_avatar(final)
            try:
                self.piano.limpiar_resaltado_docente()
            except Exception:
                pass
        else:
            self._midi_practica_actualizar_objetivo()
        return True

    def _tick_midi_didactico(self):
        pieza = self.midi_didactico.pieza
        if pieza is None:
            self.timer_midi_didactico.stop()
            return
        ahora = time.monotonic()
        delta_ms = int((ahora - getattr(self, "_midi_didactico_ultimo_ts", ahora)) * 1000)
        self._midi_didactico_ultimo_ts = ahora
        estado_reloj = self.reloj_musical.avanzar(max(1, delta_ms))
        self._midi_didactico_tiempo_ms = int(estado_reloj.get("tiempo_ms", 0))
        if estado_reloj.get("cambio_beat"):
            self._midi_practica_ultimo_beat_ts = ahora
            try:
                self.audio.sonido_metronomo(acento=estado_reloj.get("primer_tiempo", False))
            except Exception:
                pass

        modo = getattr(self, "_midi_didactico_modo", "clase")
        if modo == "practica":
            self._midi_practica_actualizar_objetivo(estado_reloj)
            return

        if self._midi_didactico_tiempo_ms > int(pieza.duracion_ms) + 250:
            self._midi_didactico_parar(limpiar=False)
            texto = f"Pieza terminada: {pieza.titulo}. Repite en práctica o usa examen."
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
            self._hablar_con_avatar(texto)
            return

        tiempo = int(self._midi_didactico_tiempo_ms)
        activas = self.midi_didactico.notas_activas(tiempo)
        siguiente = self.midi_didactico.siguiente_nota(tiempo)
        actual = self.midi_didactico.evento_actual(tiempo)
        self._midi_didactico_actualizar_pentagrama_vivo(actual, siguiente, activas)
        notas_activas = {n.nota for n in activas}

        if modo == "escuchar":
            for n in activas:
                if n.nota not in self._midi_didactico_notas_sonando:
                    self._midi_didactico_note_on_interno(n.nota, velocity=getattr(n, "velocity", 96))
                    try:
                        if hasattr(self, "piano"):
                            self.piano.nota_externa_on(n.nota)
                    except Exception:
                        pass
                    self._midi_didactico_notas_sonando.add(n.nota)
            for nota in list(self._midi_didactico_notas_sonando):
                if nota not in notas_activas:
                    self._midi_didactico_note_off_interno(nota)
                    try:
                        if hasattr(self, "piano"):
                            self.piano.nota_externa_off(nota)
                    except Exception:
                        pass
                    self._midi_didactico_notas_sonando.remove(nota)

        if modo in {"escuchar", "practica"}:
            try:
                self.piano.resaltar_notas_docente(list(notas_activas) or ([siguiente.nota] if siguiente else []))
            except Exception:
                pass
        elif modo == "examen":
            try:
                self.piano.limpiar_resaltado_docente()
            except Exception:
                pass

        objetivo = list(notas_activas) or ([siguiente.nota] if siguiente else [])
        try:
            if objetivo:
                self.analizador_midi_pro.configurar_objetivo(
                    tipo="acorde" if len(objetivo) > 1 else "pulso",
                    esperado=objetivo,
                    permite_simultaneas=len(objetivo) > 1,
                    requiere_simultaneo=len(objetivo) > 1,
                )
        except Exception:
            pass

        if actual and int(actual.compas) != int(getattr(self, "_midi_didactico_compas_anunciado", 0)):
            self._midi_didactico_compas_anunciado = int(actual.compas)
            texto = f"Compás {actual.compas}. Pulso {actual.pulso}. Toca {actual.nota} con mano {actual.mano}."
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(texto)
            self._actualizar_dialogo_avatar(texto)

        self._midi_didactico_actualizar_panel()

    def _midi_didactico_actualizar_panel(self):
        pieza = self.midi_didactico.pieza
        if not pieza:
            return
        tiempo = int(getattr(self, "_midi_didactico_tiempo_ms", 0))
        actual = self.midi_didactico.evento_actual(tiempo)
        siguiente = self.midi_didactico.siguiente_nota(tiempo)
        dur = max(1, int(pieza.duracion_ms or 1))
        if hasattr(self, "barra_midi_didactico"):
            self.barra_midi_didactico.setValue(max(0, min(100, int(tiempo * 100 / dur))))
        if hasattr(self, "lbl_midi_didactico_actual"):
            self.lbl_midi_didactico_actual.setText(f"Actual: compás {actual.compas} · pulso {actual.pulso} · {actual.nota} · {actual.mano}" if actual else "Actual: preparando")
        if hasattr(self, "lbl_midi_didactico_siguiente"):
            self.lbl_midi_didactico_siguiente.setText(f"Siguiente: compás {siguiente.compas} · pulso {siguiente.pulso} · {siguiente.nota}" if siguiente else "Siguiente: final")

    def _crear_pantalla_hanon(self):
        w = QWidget()
        raiz = QVBoxLayout(w)
        raiz.setSpacing(8)

        cab = QHBoxLayout()
        self.lbl_hanon_titulo = QLabel("Técnica Hanon completa")
        self.lbl_hanon_titulo.setObjectName("TituloSeccionInicio")
        self.lbl_hanon_estado = QLabel("Selecciona un Hanon desde Curso.")
        self.btn_hanon_anterior = self._crear_boton_color("Paso anterior", "#64748B", altura=30)
        self.btn_hanon_siguiente = self._crear_boton_color("Siguiente paso", "#2563EB", altura=30)
        self.btn_hanon_demo = self._crear_boton_color("Play demo", "#16A34A", altura=30)
        self.btn_hanon_pausa = self._crear_boton_color("Pausa", "#F59E0B", altura=30)
        self.btn_hanon_stop = self._crear_boton_color("Stop", "#DC2626", altura=30)
        self.btn_hanon_practica = self._crear_boton_color("Práctica MIDI", "#0F766E", altura=30)
        self.btn_hanon_examen = self._crear_boton_color("Examen", "#9333EA", altura=30)
        self.btn_hanon_finalizar = self._crear_boton_color("Corregir", "#0EA5E9", altura=30)
        self.btn_hanon_inicio = self._crear_boton_color("Curso", "#64748B", altura=30)

        self.chk_hanon_metronomo = QCheckBox("Metrónomo")
        self.chk_hanon_metronomo.setChecked(True)
        self.chk_hanon_metronomo.setToolTip("En práctica MIDI, activa o apaga solo el sonido del metrónomo. La guía visual sigue funcionando.")
        self.chk_hanon_metronomo.toggled.connect(self._hanon_alternar_metronomo_practica)

        self.spin_hanon_bpm = QSpinBox()
        self.spin_hanon_bpm.setRange(30, 220)
        self.spin_hanon_bpm.setSingleStep(1)
        self.spin_hanon_bpm.setValue(60)
        self.spin_hanon_bpm.setSuffix(" BPM")
        self.spin_hanon_bpm.setToolTip("Tempo de práctica Hanon. Se puede cambiar en directo.")
        self.spin_hanon_bpm.setFixedWidth(82)
        self.spin_hanon_bpm.valueChanged.connect(self._hanon_cambiar_tempo_practica)

        for b in (
            self.btn_hanon_anterior, self.btn_hanon_siguiente, self.btn_hanon_demo,
            self.btn_hanon_pausa, self.btn_hanon_stop, self.btn_hanon_practica,
            self.btn_hanon_examen, self.btn_hanon_finalizar, self.btn_hanon_inicio,
        ):
            self._ajustar_boton_texto_completo(b, minimo=74, extra=34)
        self.btn_hanon_anterior.clicked.connect(lambda: self._hanon_avanzar_paso(-1))
        self.btn_hanon_siguiente.clicked.connect(lambda: self._hanon_avanzar_paso(1))
        self.btn_hanon_demo.clicked.connect(self._hanon_demo_play)
        self.btn_hanon_pausa.clicked.connect(self._hanon_demo_pausa)
        self.btn_hanon_stop.clicked.connect(self._hanon_demo_stop)
        self.btn_hanon_practica.clicked.connect(self._hanon_iniciar_practica)
        self.btn_hanon_examen.clicked.connect(self._hanon_iniciar_examen)
        self.btn_hanon_finalizar.clicked.connect(self._hanon_finalizar_practica)
        self.btn_hanon_inicio.clicked.connect(self.volver_al_inicio)
        cab.addWidget(self.lbl_hanon_titulo, 1)
        for b in (
            self.btn_hanon_anterior, self.btn_hanon_siguiente, self.btn_hanon_demo,
            self.btn_hanon_pausa, self.btn_hanon_stop, self.btn_hanon_practica,
            self.btn_hanon_examen, self.btn_hanon_finalizar, self.btn_hanon_inicio,
        ):
            cab.addWidget(b)
        cab.addWidget(self.chk_hanon_metronomo, 0)
        cab.addWidget(self.spin_hanon_bpm, 0)
        raiz.addLayout(cab)

        self.barra_hanon = QProgressBar()
        self.barra_hanon.setRange(0, 100)
        self.barra_hanon.setFormat("Hanon %p%")
        raiz.addWidget(self.barra_hanon)
        self.lbl_hanon_estado.setWordWrap(True)
        raiz.addWidget(self.lbl_hanon_estado)

        cuerpo = QHBoxLayout()
        self.pizarra_hanon = PizarraMusicalProfesor(self)
        # Debe convivir con el piano global en pantallas pequeñas.
        # Antes tenía mínimos de 1080/900 px y empujaba el teclado fuera.
        # La digitación Hanon necesita altura real: si el lienzo baja de aquí,
        # las manos quedan demasiado pequeñas y poco didácticas.
        self.pizarra_hanon.setMinimumHeight(500)
        try:
            self.pizarra_hanon.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.pizarra_hanon.canvas.setMinimumHeight(430)
            self.pizarra_hanon.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        # Hotfix Hanon: los botones internos de la pizarra no pueden quedar
        # decorativos. En esta pantalla se conectan a las acciones reales del
        # método Hanon, sin sustituir ni romper el transporte superior.
        try:
            self.pizarra_hanon.paso_leido.connect(self._leer_texto_pizarra_musical)
            self.pizarra_hanon.ejemplo_leido.connect(self._leer_texto_pizarra_musical)
            self.pizarra_hanon.texto_leido.connect(self._leer_texto_pizarra_musical)
            self.pizarra_hanon.notas_resaltadas.connect(self._resaltar_notas_pizarra_en_piano)
            # En Hanon estos botones no deben ejecutar también las acciones
            # genéricas de la pizarra; si quedan dobles conexiones, el botón
            # Pulso lanza un metrónomo genérico paralelo que luego no se detiene.
            for _btn in (
                self.pizarra_hanon.btn_ejemplo,
                self.pizarra_hanon.btn_tocar_piano,
                self.pizarra_hanon.btn_tocar_secuencia,
                self.pizarra_hanon.btn_tocar_pulso,
            ):
                try:
                    _btn.clicked.disconnect()
                except Exception:
                    pass
            self.pizarra_hanon.btn_ejemplo.clicked.connect(self._hanon_pizarra_boton_ejemplo)
            self.pizarra_hanon.btn_tocar_piano.clicked.connect(self._hanon_pizarra_boton_piano)
            self.pizarra_hanon.btn_tocar_secuencia.clicked.connect(self._hanon_pizarra_boton_secuencia)
            self.pizarra_hanon.btn_tocar_pulso.clicked.connect(self._hanon_pizarra_boton_pulso)
        except Exception:
            pass
        cuerpo.addWidget(self.pizarra_hanon, 5)
        self.txt_hanon_profesor = QTextEdit()
        self.txt_hanon_profesor.setReadOnly(True)
        self.txt_hanon_profesor.setMinimumWidth(300)
        cuerpo.addWidget(self.txt_hanon_profesor, 1)
        raiz.addLayout(cuerpo, 1)
        return w

    def abrir_hanon(self, hanon_id: str):
        ok, aviso = self.hanon.disponible()
        if not ok:
            QMessageBox.warning(self, "Hanon no disponible", aviso)
            return
        clase = self.hanon.clase_por_id(hanon_id) or {}
        estado = self.hanon.estado_clase(clase)
        if estado == "bloqueado":
            QMessageBox.information(self, "Hanon bloqueado", "Debes superar el Hanon anterior antes de abrir este ejercicio.")
            return
        try:
            self._hanon_demo_stop()
            self._hanon_modelo = self.hanon.cargar_modelo(hanon_id)
            self._hanon_guion = self.hanon.cargar_recurso_json(self._hanon_modelo, "guion_profesor", {"pasos": []})
            self._hanon_pizarra = self.hanon.cargar_recurso_json(self._hanon_modelo, "secuencia_pizarra", {"pasos": []})
            self._hanon_rubrica = self.hanon.cargar_recurso_json(self._hanon_modelo, "rubrica", {})
            self._hanon_examen = self.hanon.cargar_recurso_json(self._hanon_modelo, "examen", {})
            self._hanon_pieza = self.hanon.cargar_pieza_demo(self._hanon_modelo)
            self._hanon_digitacion_por_evento = {}
            notas_base = [self._nota_midi_didactica_a_dict(n) for n in (self._hanon_pieza.notas or [])]
            self._hanon_notas = self._hanon_enriquecer_digitacion([n for n in notas_base if n])
            try:
                bpm_practica = int(((self._hanon_modelo.get("tempo") or {}).get("bpm_practica_lenta", 60)) or 60)
                if hasattr(self, "spin_hanon_bpm"):
                    self.spin_hanon_bpm.blockSignals(True)
                    self.spin_hanon_bpm.setValue(max(30, min(220, bpm_practica)))
                    self.spin_hanon_bpm.blockSignals(False)
            except Exception:
                pass
        except Exception as exc:
            QMessageBox.warning(self, "Hanon", f"No se pudo cargar {hanon_id}: {exc}")
            return

        self._hanon_eventos = []
        self._hanon_practica_activa = False
        self._hanon_examen_activo = False
        self._hanon_paso_actual = 0
        titulo = self._hanon_modelo.get("titulo", hanon_id)
        self.lbl_hanon_titulo.setText(titulo)
        self.lbl_hanon_estado.setText("Modelo Hanon cargado. El profesor seguirá el guion estructurado paso a paso.")
        self.txt_hanon_profesor.setPlainText(self._hanon_resumen_modelo())
        self.pizarra_hanon.preparar_midi_didactico(self._hanon_notas, f"Hanon · {titulo}")
        self._hanon_mostrar_paso(0, hablar=True)
        self.stack.setCurrentWidget(self.pantalla_hanon)

    def _hanon_resumen_modelo(self) -> str:
        m = self._hanon_modelo or {}
        tempo = m.get("tempo") or {}
        return (
            f"{m.get('titulo', 'Hanon')}\n\n"
            f"Objetivo: {m.get('objetivo', '')}\n\n"
            f"BPM inicial: {tempo.get('bpm_inicial', 60)} · práctica lenta: {tempo.get('bpm_practica_lenta', 48)} · objetivo: {tempo.get('bpm_objetivo', '')}\n\n"
            "Usa Siguiente paso para que el profesor avance y sincronice pizarra. Play demo reproduce el MIDI interno. Práctica MIDI compara tu teclado externo contra la nota esperada."
        )

    def _hanon_pasos_guion(self):
        pasos = (self._hanon_guion or {}).get("pasos", []) or []
        return sorted([p for p in pasos if isinstance(p, dict)], key=lambda x: int(x.get("orden", 999) or 999))

    def _hanon_avanzar_paso(self, delta: int):
        pasos = self._hanon_pasos_guion()
        if not pasos:
            return
        self._hanon_paso_actual = max(0, min(len(pasos) - 1, int(self._hanon_paso_actual) + int(delta)))
        self._hanon_mostrar_paso(self._hanon_paso_actual, hablar=True)

    def _hanon_mostrar_paso(self, indice: int, hablar: bool = False):
        pasos = self._hanon_pasos_guion()
        if not pasos:
            return
        indice = max(0, min(int(indice), len(pasos) - 1))
        self._hanon_paso_actual = indice
        paso = pasos[indice]
        texto = str(paso.get("texto", ""))
        self.txt_hanon_profesor.setPlainText(texto)
        self.lbl_hanon_estado.setText(f"Paso {indice + 1}/{len(pasos)} · {paso.get('fase', '')}")
        self.barra_hanon.setValue(int((indice + 1) * 100 / max(1, len(pasos))))
        self._hanon_aplicar_pizarra_paso(str(paso.get("pizarra_paso", "")))
        accion = str(paso.get("accion", ""))
        if accion == "reproducir_midi_demo":
            self._hanon_demo_play()
        elif accion == "activar_practica_midi":
            self._hanon_iniciar_practica()
        elif accion == "mostrar_evaluacion" and self._hanon_eventos:
            self._hanon_finalizar_practica()
        if hablar:
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)

    def _hanon_aplicar_pizarra_paso(self, paso_id: str):
        pasos = (self._hanon_pizarra or {}).get("pasos", []) or []
        paso = next((p for p in pasos if p.get("id") == paso_id), {})
        if not paso:
            return
        try:
            if self._hanon_pizarra.get("limpiar_entre_pasos", True):
                self.pizarra_hanon.limpiar_marcas_docentes()
        except Exception:
            pass
        self.pizarra_hanon.txt_explicacion.setPlainText(str(paso.get("texto_profesor", "")))
        for marca in paso.get("marcas", []) or []:
            tipo = str(marca.get("tipo", ""))
            dur = int(marca.get("duracion_ms", 2500) or 2500)
            etiqueta = str(marca.get("texto", "") or tipo)
            try:
                if tipo == "senalar_clave_sol":
                    self.pizarra_hanon.senalar_clave_sol()
                elif tipo == "senalar_clave_fa":
                    self.pizarra_hanon.senalar_clave_fa()
                elif tipo == "mostrar_mano_derecha":
                    self.pizarra_hanon.mostrar_mano_derecha()
                elif tipo == "mostrar_mano_izquierda":
                    self.pizarra_hanon.mostrar_mano_izquierda()
                elif tipo == "resaltar_lineas_pentagrama":
                    self.pizarra_hanon.resaltar_lineas_pentagrama()
                else:
                    self.pizarra_hanon.canvas.iniciar_animacion_marca(tipo, dur, etiqueta)
            except Exception:
                pass

    def _hanon_metronomo_practica_habilitado(self) -> bool:
        try:
            return bool(self.chk_hanon_metronomo.isChecked())
        except Exception:
            return bool(getattr(self, "_hanon_metronomo_practica_activo", True))

    def _hanon_bpm_practica_actual(self) -> int:
        try:
            return max(30, min(220, int(self.spin_hanon_bpm.value())))
        except Exception:
            try:
                return max(30, min(220, int(getattr(self.reloj_musical, "bpm", 60) or 60)))
            except Exception:
                return 60

    def _hanon_alternar_metronomo_practica(self, activo: bool):
        self._hanon_metronomo_practica_activo = bool(activo)
        texto = "Metrónomo de práctica encendido." if activo else "Metrónomo de práctica apagado. La práctica sigue sin clic sonoro."
        try:
            if hasattr(self, "lbl_hanon_estado") and getattr(self, "_hanon_practica_activa", False):
                self.lbl_hanon_estado.setText(texto)
        except Exception:
            pass

    def _hanon_cambiar_tempo_practica(self, bpm: int):
        bpm = max(30, min(220, int(bpm or 60)))
        try:
            self.reloj_musical.set_bpm(bpm)
        except Exception:
            pass
        try:
            if hasattr(self, "lbl_hanon_estado") and getattr(self, "_hanon_practica_activa", False):
                self.lbl_hanon_estado.setText(f"Tempo de práctica Hanon: {bpm} BPM.")
        except Exception:
            pass

    def _hanon_sonar_metronomo(self, acento: bool = False, forzar: bool = False):
        if getattr(self, "_hanon_practica_activa", False) and not self._hanon_metronomo_practica_habilitado():
            return
        try:
            self.audio.sonido_metronomo(acento=bool(acento))
        except Exception:
            pass

    def _hanon_detener_pulso_generico_si_activo(self):
        # El reto Pulso genérico de la pizarra usa otro QTimer. En Hanon no debe
        # quedarse sonando en paralelo al transporte principal.
        try:
            if getattr(self, "_pulso_pizarra_activo", False):
                self._finalizar_pulso_pizarra(completado=False)
            else:
                self._pulso_pizarra_timer.stop()
        except Exception:
            pass

    def _hanon_demo_play(self):
        if not self._hanon_pieza:
            return
        self._hanon_detener_pulso_generico_si_activo()
        self._hanon_practica_activa = False
        self._hanon_examen_activo = False
        if int(getattr(self, "_hanon_demo_tiempo_ms", 0) or 0) <= 0:
            self.reloj_musical.configurar(self._hanon_pieza.tempo, self._hanon_pieza.compas, self._hanon_pieza.duracion_ms)
        self._hanon_demo_tiempo_ms = int(getattr(self, "_hanon_demo_tiempo_ms", 0) or 0)
        self.reloj_musical.posicion_ms = self._hanon_demo_tiempo_ms
        self.reloj_musical.play()
        self._hanon_demo_ultimo_ts = time.monotonic()
        self.timer_hanon_demo.start()
        # Primer clic inmediato: el metrónomo entra con la reproducción, no un
        # segundo después. Los siguientes clics los gobierna RelojMusical.
        self._hanon_sonar_metronomo(acento=True)

    def _hanon_demo_pausa(self):
        try:
            self.timer_hanon_demo.stop()
        except Exception:
            pass
        try:
            self.reloj_musical.pause()
        except Exception:
            pass
        self._hanon_detener_pulso_generico_si_activo()
        for nota in list(getattr(self, "_hanon_demo_sonando", set())):
            try:
                self.audio.note_off(nota)
            except Exception:
                pass
            try:
                if hasattr(self, "piano"):
                    self.piano.nota_externa_off(nota)
            except Exception:
                pass
        self._hanon_demo_sonando = set()

    def _hanon_demo_stop(self):
        self._hanon_demo_pausa()
        self._hanon_practica_activa = False
        self._hanon_examen_activo = False
        self._hanon_demo_tiempo_ms = 0
        self.reloj_musical.stop()
        self.barra_hanon.setValue(0)
        try:
            self.pizarra_hanon.actualizar_midi_didactico(None, None, [], 0, 0.0, "clase", self.reloj_musical.bpm, 1, self.reloj_musical.compas_num)
        except Exception:
            pass

    def _tick_hanon_demo(self):
        pieza = self._hanon_pieza
        if pieza is None:
            self.timer_hanon_demo.stop()
            return
        ahora = time.monotonic()
        delta_ms = int((ahora - getattr(self, "_hanon_demo_ultimo_ts", ahora)) * 1000)
        self._hanon_demo_ultimo_ts = ahora
        estado_reloj = self.reloj_musical.avanzar(max(1, delta_ms))
        if getattr(self, "_hanon_practica_activa", False):
            try:
                self.reloj_musical.set_bpm(self._hanon_bpm_practica_actual())
            except Exception:
                pass
            if estado_reloj.get("cambio_beat"):
                self._hanon_practica_ultimo_beat_ts = ahora
                self._hanon_sonar_metronomo(acento=estado_reloj.get("primer_tiempo", False))
            self._hanon_practica_actualizar_objetivo(estado_reloj)
            return
        self._hanon_demo_tiempo_ms = int(estado_reloj.get("tiempo_ms", 0))
        if estado_reloj.get("cambio_beat"):
            self._hanon_sonar_metronomo(acento=estado_reloj.get("primer_tiempo", False))
        tiempo = int(self._hanon_demo_tiempo_ms)
        if estado_reloj.get("progreso", 0.0) >= 1.0 or tiempo >= int(pieza.duracion_ms or 0):
            self._hanon_demo_stop()
            self.lbl_hanon_estado.setText("Demo Hanon terminada. Puedes iniciar práctica MIDI o examen.")
            return
        activas = [n for n in (pieza.notas or []) if n.inicio_ms <= tiempo < n.fin_ms()]
        siguiente = next((n for n in (pieza.notas or []) if n.inicio_ms > tiempo), None)
        actual = None
        for n in pieza.notas or []:
            if n.inicio_ms <= tiempo:
                actual = n
            else:
                break
        activas_nombres = {n.nota for n in activas}
        for n in activas:
            if n.nota not in self._hanon_demo_sonando:
                self.audio.note_on(n.nota, velocity=getattr(n, "velocity", 96))
                if hasattr(self, "piano"):
                    self.piano.nota_externa_on(n.nota)
                self._hanon_demo_sonando.add(n.nota)
        for nota in list(self._hanon_demo_sonando):
            if nota not in activas_nombres:
                self.audio.note_off(nota)
                try:
                    if hasattr(self, "piano"):
                        self.piano.nota_externa_off(nota)
                except Exception:
                    pass
                self._hanon_demo_sonando.remove(nota)
        progreso = max(0.0, min(1.0, tiempo / max(1, int(pieza.duracion_ms or 1))))
        self.barra_hanon.setValue(int(progreso * 100))
        self.pizarra_hanon.actualizar_midi_didactico(
            self._nota_midi_didactica_a_dict(actual),
            self._nota_midi_didactica_a_dict(siguiente),
            [self._nota_midi_didactica_a_dict(n) for n in activas],
            tiempo,
            progreso,
            "escuchar",
            self.reloj_musical.bpm,
            self.reloj_musical.beat_compas(),
            self.reloj_musical.compas_num,
        )

    def _hanon_iniciar_practica(self):
        if not self._hanon_modelo:
            return
        self._hanon_demo_stop()
        self._hanon_practica_activa = True
        self._hanon_examen_activo = False
        self._hanon_practica_indice = 0
        self._hanon_eventos = []
        self._hanon_resultado_finalizado = False
        self._hanon_notas_activas_alumno = {}
        self._hanon_inicio_practica_ts = time.monotonic()
        self._hanon_practica_ultimo_beat_ts = time.monotonic()
        if self._hanon_pieza:
            bpm_practica = self._hanon_bpm_practica_actual()
            # En práctica el metrónomo no se ata a la duración de la demo: debe
            # seguir hasta que el alumno complete, pause o pulse Stop.
            self.reloj_musical.configurar(bpm_practica, self._hanon_pieza.compas, 0)
            self.reloj_musical.set_bpm(bpm_practica)
            self.reloj_musical.play()
            self._hanon_demo_ultimo_ts = time.monotonic()
            self.timer_hanon_demo.start()
            self._hanon_sonar_metronomo(acento=True)
        self.hanon.iniciar_practica(self._hanon_modelo.get("id", ""))
        self._hanon_practica_actualizar_objetivo()
        self.lbl_hanon_estado.setText("Práctica MIDI activa. No avanzo hasta que toques la nota correcta cerca del pulso.")
        self._actualizar_dialogo_avatar("Práctica Hanon activa. Toca la nota esperada en el pulso; corregiré nota, pulso, velocity y duración.")

    def _hanon_iniciar_examen(self):
        if not self._hanon_modelo:
            return
        self._hanon_demo_stop()
        self._hanon_practica_activa = True
        self._hanon_examen_activo = True
        self._hanon_practica_indice = 0
        self._hanon_eventos = []
        self._hanon_resultado_finalizado = False
        self._hanon_notas_activas_alumno = {}
        self._hanon_inicio_practica_ts = time.monotonic()
        self._hanon_practica_ultimo_beat_ts = time.monotonic()
        if self._hanon_pieza:
            bpm_practica = self._hanon_bpm_practica_actual()
            # En práctica el metrónomo no se ata a la duración de la demo: debe
            # seguir hasta que el alumno complete, pause o pulse Stop.
            self.reloj_musical.configurar(bpm_practica, self._hanon_pieza.compas, 0)
            self.reloj_musical.set_bpm(bpm_practica)
            self.reloj_musical.play()
            self._hanon_demo_ultimo_ts = time.monotonic()
            self.timer_hanon_demo.start()
            self._hanon_sonar_metronomo(acento=True)
        self.pizarra_hanon.limpiar_marcas_docentes()
        self.lbl_hanon_estado.setText("Examen Hanon activo. Ayuda visual reducida. Aprobado desde 80/100.")
        texto = "Examen Hanon. Toca sin depender de demasiada ayuda visual. Guardaré el resultado y desbloquearé el siguiente si apruebas."
        self.txt_hanon_profesor.setPlainText(texto)
        self._hablar_con_avatar(texto)

    def _hanon_objetivo_actual(self, ts_rel_ms: int):
        notas = self._hanon_notas or []
        if not notas:
            return None, 0
        idx = min(len(notas) - 1, int(getattr(self, "_hanon_practica_indice", len(self._hanon_eventos)) or 0))
        objetivo = notas[idx]
        diff = int(ts_rel_ms - int(objetivo.get("inicio_ms", 0) or 0))
        return objetivo, diff

    def _hanon_practica_actualizar_objetivo(self, estado_reloj: dict | None = None):
        if not self._hanon_notas:
            return
        idx = max(0, min(int(getattr(self, "_hanon_practica_indice", 0) or 0), len(self._hanon_notas) - 1))
        objetivo = self._normalizar_evento_practica(self._hanon_notas[idx])
        siguiente = self._normalizar_evento_practica(self._hanon_notas[idx + 1]) if idx + 1 < len(self._hanon_notas) else None
        progreso = idx / max(1, len(self._hanon_notas))
        try:
            self.pizarra_hanon.actualizar_midi_didactico(
                actual=objetivo,
                siguiente=siguiente,
                activas=[] if self._hanon_examen_activo else [objetivo],
                tiempo_ms=int(objetivo.get("inicio_ms", 0) or 0),
                progreso=progreso,
                modo="examen" if self._hanon_examen_activo else "practica",
                bpm=getattr(self.reloj_musical, "bpm", None),
                beat=(estado_reloj or {}).get("beat", self.reloj_musical.beat_compas()),
                compas_num=getattr(self.reloj_musical, "compas_num", 4),
            )
        except Exception:
            pass
        try:
            if not self._hanon_examen_activo and hasattr(self, "piano"):
                self.piano.resaltar_notas_docente([objetivo.get("nota", "")])
        except Exception:
            pass
        if hasattr(self, "barra_hanon"):
            self.barra_hanon.setValue(max(0, min(100, int(progreso * 100))))
        if hasattr(self, "lbl_hanon_estado"):
            ayuda = "Examen" if self._hanon_examen_activo else "Práctica"
            digitacion_txt = self._hanon_texto_digitacion(objetivo)
            extra = f" · {digitacion_txt}" if digitacion_txt else ""
            self.lbl_hanon_estado.setText(f"{ayuda}: {idx + 1}/{len(self._hanon_notas)} · espera el pulso y toca {objetivo.get('nombre_completo') or objetivo.get('nota', '—')}{extra}")

    def _procesar_hanon_midi_entrada(self, nota: str, velocity: int, canal: int):
        if not getattr(self, "_hanon_practica_activa", False) or not self._hanon_modelo:
            return False
        ts_rel_ms = int((time.monotonic() - getattr(self, "_hanon_inicio_practica_ts", time.monotonic())) * 1000)
        objetivo, _diff_modelo = self._hanon_objetivo_actual(ts_rel_ms)
        evento_esperado = self._normalizar_evento_practica(objetivo)
        evento_recibido = normalizar_nota(nota)
        esperado = str(evento_esperado.get("nota", ""))
        digitacion_txt = self._hanon_texto_digitacion(evento_esperado)
        ayuda_digitacion = f" con {digitacion_txt}" if digitacion_txt else ""
        ahora = time.monotonic()
        beat_ms = float(self.reloj_musical.beat_ms())
        desde_beat_ms = max(0.0, (ahora - float(getattr(self, "_hanon_practica_ultimo_beat_ts", ahora) or ahora)) * 1000.0)
        hasta_siguiente_ms = max(0.0, beat_ms - desde_beat_ms)
        usa_siguiente = hasta_siguiente_ms < desde_beat_ms
        diff = -hasta_siguiente_ms if usa_siguiente else desde_beat_ms
        correcto = evento_recibido.get("midi") == evento_esperado.get("midi")
        en_pulso = abs(diff) <= int(getattr(self, "_hanon_practica_tolerancia_ms", 180) or 180)
        vel = max(0, min(127, int(velocity or 0)))
        vel_obj = max(1, min(127, int((objetivo or {}).get("velocity", 80) or 80)))
        vel_baja = vel < max(20, vel_obj - 28)
        vel_alta = vel > min(127, vel_obj + 28)
        origen = "hanon_correcta" if correcto and en_pulso else ("hanon_fuera_pulso" if correcto else "hanon_incorrecta")
        evento = {
            "nota": evento_recibido.get("nota", nota),
            "esperado": esperado,
            "velocity": int(velocity or 0),
            "canal": canal,
            "timestamp_ms": ts_rel_ms,
            "diferencia_ms": diff,
            "correcto": correcto,
            "en_pulso": en_pulso,
        }
        self._hanon_eventos.append(evento)
        self._hanon_notas_activas_alumno[evento_recibido.get("nota", nota)] = len(self._hanon_eventos) - 1
        try:
            self.pizarra_hanon.mostrar_nota_midi_externa(evento_recibido.get("nota", nota), velocity, canal, origen)
        except Exception:
            pass
        self.historial_alumno.registrar_midi_evento(
            nota=evento_recibido.get("nota", nota),
            velocity=velocity,
            canal=canal,
            origen="hanon_examen" if self._hanon_examen_activo else "hanon_practica",
            esperado=esperado,
            correcto=correcto,
            diferencia_ms=diff,
            en_pulso=en_pulso,
            tipo="nota",
            contexto={"hanon_id": self._hanon_modelo.get("id", ""), "timestamp_ms": ts_rel_ms},
        )
        if not correcto:
            mensaje = (
                f"Nota equivocada: tocaste {evento_recibido.get('nombre_completo') or nota}, "
                f"pero esperaba {evento_esperado.get('nombre_completo') or esperado}{ayuda_digitacion}. Repite sin avanzar."
            )
        elif not en_pulso:
            if diff < 0:
                mensaje = f"Te adelantaste {int(abs(diff))} ms. Espera el clic antes de tocar {evento_esperado.get('nombre_completo') or esperado}{ayuda_digitacion}."
            else:
                mensaje = f"Tocaste tarde {int(abs(diff))} ms. Entra más cerca del pulso con {evento_esperado.get('nombre_completo') or esperado}{ayuda_digitacion}."
        else:
            partes = [f"Correcto: {evento_esperado.get('nombre_completo') or esperado}{ayuda_digitacion} en pulso."]
            if vel_alta:
                partes.append("Sonó fuerte; relaja y controla la velocity.")
            elif vel_baja:
                partes.append("Sonó bajo; apoya un poco más sin tensión.")
            mensaje = " ".join(partes)
            self._hanon_practica_indice += 1
            if self._hanon_practica_indice >= len(self._hanon_notas):
                self._hanon_finalizar_practica()
                return True
            self._hanon_practica_actualizar_objetivo()
        self.lbl_hanon_estado.setText(mensaje)
        self._debug_practica(evento_esperado, evento_esperado, evento_recibido, "CORRECTO" if correcto else "INCORRECTO")
        self._actualizar_dialogo_avatar(mensaje)
        if not (correcto and en_pulso):
            self._hablar_con_avatar(mensaje)
        return True

    def _hanon_midi_note_off(self, nota: str):
        if not getattr(self, "_hanon_practica_activa", False):
            return
        idx = self._hanon_notas_activas_alumno.pop(nota, None)
        if idx is None:
            return
        ts_rel_ms = int((time.monotonic() - getattr(self, "_hanon_inicio_practica_ts", time.monotonic())) * 1000)
        if 0 <= idx < len(self._hanon_eventos):
            self._hanon_eventos[idx]["duracion_ms"] = max(1, ts_rel_ms - int(self._hanon_eventos[idx].get("timestamp_ms", ts_rel_ms)))

    def _hanon_finalizar_practica(self):
        if not self._hanon_modelo:
            return
        if getattr(self, "_hanon_finalizando_practica", False):
            return
        if getattr(self, "_hanon_resultado_finalizado", False):
            texto = "La práctica Hanon ya fue corregida. Inicia de nuevo Práctica MIDI o Examen para obtener otro resultado."
            try:
                self.lbl_hanon_estado.setText(texto)
                self._actualizar_dialogo_avatar(texto)
            except Exception:
                pass
            return

        self._hanon_finalizando_practica = True
        try:
            resultado = self.hanon.evaluar_eventos(
                self._hanon_modelo.get("id", ""),
                list(getattr(self, "_hanon_eventos", []) or []),
                list(getattr(self, "_hanon_notas", []) or []),
                self._hanon_rubrica,
            )
            bpm = int((self._hanon_modelo.get("tempo") or {}).get("bpm_inicial", 60) or 60)
            item = self.hanon.registrar_resultado(resultado, bpm=bpm)
            self.historial_alumno.registrar_hanon(item)
            self._hanon_practica_activa = False
            self._hanon_examen_activo = False
            self._hanon_resultado_finalizado = True
            try:
                self.timer_hanon_demo.stop()
                self.reloj_musical.pause()
            except Exception:
                pass
            texto = (
                f"Resultado Hanon: {resultado.puntuacion}/100. "
                f"Notas {resultado.notas_correctas_pct}%, pulso {resultado.pulso_pct}%, "
                f"velocity {resultado.velocity_score}%, duración {resultado.duracion_score}%. "
                f"{'Aprobado; se desbloquea el siguiente.' if resultado.aprobado else 'No aprobado; repite más lento.'}\n\n"
                f"Recomendación: {resultado.recomendacion}"
            )
            self.txt_hanon_profesor.setPlainText(texto)
            self.lbl_hanon_estado.setText(texto)
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
        finally:
            self._hanon_finalizando_practica = False

    def _hanon_eventos_para_pizarra(self, limite: int | None = None) -> list[dict]:
        """Devuelve las notas Hanon ya normalizadas y con digitación.

        Se usa para que los botones internos de la pizarra trabajen sobre la
        misma secuencia que Play demo / Práctica MIDI, no sobre un DO genérico.
        """
        eventos = []
        for n in (getattr(self, "_hanon_notas", []) or []):
            try:
                ev = self._normalizar_evento_practica(n)
            except Exception:
                ev = dict(n or {}) if isinstance(n, dict) else {}
            if ev.get("nota"):
                eventos.append(ev)
        if limite is not None:
            try:
                return eventos[:max(0, int(limite))]
            except Exception:
                return eventos
        return eventos

    def _hanon_evento_objetivo_visual(self) -> tuple[dict, dict, int, list[dict]]:
        eventos = self._hanon_eventos_para_pizarra(None)
        if not eventos:
            return {}, {}, 0, []
        idx = int(getattr(self, "_hanon_practica_indice", 0) or 0)
        idx = max(0, min(idx, len(eventos) - 1))
        actual = eventos[idx]
        siguiente = eventos[idx + 1] if idx + 1 < len(eventos) else {}
        return actual, siguiente, idx, eventos

    def _hanon_nombre_y_dedo(self, evento: dict | None) -> str:
        evento = evento or {}
        nombre = str(evento.get("nombre_completo") or evento.get("nombre") or evento.get("nota") or "nota").strip()
        dig = self._hanon_texto_digitacion(evento)
        return f"{nombre} con {dig}" if dig else nombre

    def _hanon_actualizar_pizarra_objetivo(self, modo: str = "practica", activar_piano: bool = True) -> dict:
        actual, siguiente, idx, eventos = self._hanon_evento_objetivo_visual()
        if not actual:
            return {}
        try:
            # Hanon debe mostrar las manos de digitación en la pizarra.
            # El teclado interactivo real ya está en el piano global inferior;
            # si activamos el mini piano interno, tapa las manos.
            self.pizarra_hanon.canvas.alternar_piano_interactivo(False)
        except Exception:
            pass
        try:
            progreso = idx / max(1, len(eventos))
            self.pizarra_hanon.actualizar_midi_didactico(
                actual=actual,
                siguiente=siguiente,
                activas=[actual],
                tiempo_ms=int(actual.get("inicio_ms", 0) or 0),
                progreso=progreso,
                modo=modo,
                bpm=getattr(self.reloj_musical, "bpm", None) or int(((getattr(self, "_hanon_modelo", {}) or {}).get("tempo") or {}).get("bpm_inicial", 60) or 60),
                beat=int(actual.get("pulso", 1) or 1),
                compas_num=getattr(self.reloj_musical, "compas_num", 4),
            )
        except Exception:
            pass
        try:
            if hasattr(self, "piano") and hasattr(self.piano, "resaltar_notas_docente"):
                self.piano.resaltar_notas_docente([actual.get("nota", "")])
        except Exception:
            pass
        return actual

    def _hanon_mostrar_mensaje_accion(self, texto: str, hablar: bool = False):
        texto = str(texto or "").strip()
        if not texto:
            return
        try:
            if hasattr(self, "lbl_hanon_estado"):
                self.lbl_hanon_estado.setText(texto)
            if hasattr(self, "txt_hanon_profesor"):
                self.txt_hanon_profesor.setPlainText(texto)
            if hasattr(self, "pizarra_hanon"):
                self.pizarra_hanon.txt_explicacion.setPlainText(texto)
        except Exception:
            pass
        try:
            self._actualizar_dialogo_avatar(texto)
        except Exception:
            pass
        if hablar:
            try:
                self._hablar_con_avatar(texto)
            except Exception:
                pass

    def _hanon_pizarra_boton_ejemplo(self):
        """Botón interno 'Ejemplo' en la pizarra Hanon: reproduce la demo real."""
        if not getattr(self, "_hanon_modelo", None):
            self._hanon_mostrar_mensaje_accion("Primero abre un ejercicio Hanon desde Curso.", hablar=True)
            return
        actual = self._hanon_actualizar_pizarra_objetivo("escuchar", activar_piano=True)
        texto = (
            "Ejemplo Hanon activado: escucha la demo interna y mira la pizarra. "
            "La nota activa, la mano y el dedo correcto se irán marcando sincronizados."
        )
        if actual:
            texto += " Primera referencia: " + self._hanon_nombre_y_dedo(actual) + "."
        self._hanon_mostrar_mensaje_accion(texto, hablar=False)
        try:
            self._hanon_demo_play()
        except Exception as exc:
            self._hanon_mostrar_mensaje_accion(f"No se pudo iniciar la demo Hanon: {exc}", hablar=True)

    def _hanon_pizarra_boton_piano(self):
        """Botón interno 'Piano': prepara una nota Hanon concreta para tocar."""
        if not getattr(self, "_hanon_modelo", None):
            self._hanon_mostrar_mensaje_accion("Primero abre un ejercicio Hanon desde Curso.", hablar=True)
            return
        actual = self._hanon_actualizar_pizarra_objetivo("practica", activar_piano=True)
        if not actual:
            self._hanon_mostrar_mensaje_accion("No hay nota Hanon preparada para el piano.", hablar=True)
            return
        nota = str(actual.get("nota", "") or "").strip()
        texto = (
            "Piano Hanon preparado. Toca "
            + self._hanon_nombre_y_dedo(actual)
            + ". La mano y el dedo correcto quedan marcados en la pizarra."
        )
        try:
            self._iniciar_reto_pizarra_piano([nota], texto)
        except Exception:
            pass
        self._hanon_mostrar_mensaje_accion(texto, hablar=True)

    def _hanon_pizarra_boton_secuencia(self):
        """Botón interno 'Secuencia': activa la secuencia Hanon real, no una genérica."""
        if not getattr(self, "_hanon_modelo", None):
            self._hanon_mostrar_mensaje_accion("Primero abre un ejercicio Hanon desde Curso.", hablar=True)
            return
        eventos = self._hanon_eventos_para_pizarra(16)
        if not eventos:
            self._hanon_mostrar_mensaje_accion("No hay secuencia Hanon cargada.", hablar=True)
            return
        self._hanon_actualizar_pizarra_objetivo("secuencia", activar_piano=True)
        secuencia = [str(ev.get("nota", "") or "").strip() for ev in eventos if ev.get("nota")]
        primeras = ", ".join(self._hanon_nombre_y_dedo(ev) for ev in eventos[:8])
        texto = (
            "Secuencia Hanon guiada activada. Toca las notas en orden; la pizarra marca la digitación. "
            "Primer bloque: " + primeras + "."
        )
        try:
            self._iniciar_secuencia_pizarra_piano(secuencia, texto)
        except Exception:
            pass
        self._hanon_mostrar_mensaje_accion(texto, hablar=True)

    def _hanon_pizarra_boton_pulso(self):
        """Botón interno 'Pulso': activa metrónomo y valida nota + tiempo."""
        if not getattr(self, "_hanon_modelo", None):
            self._hanon_mostrar_mensaje_accion("Primero abre un ejercicio Hanon desde Curso.", hablar=True)
            return
        eventos = self._hanon_eventos_para_pizarra(16)
        if not eventos:
            self._hanon_mostrar_mensaje_accion("No hay secuencia Hanon cargada para trabajar el pulso.", hablar=True)
            return
        self._hanon_actualizar_pizarra_objetivo("pulso", activar_piano=True)
        secuencia = [str(ev.get("nota", "") or "").strip() for ev in eventos if ev.get("nota")]
        try:
            bpm = int(((getattr(self, "_hanon_modelo", {}) or {}).get("tempo") or {}).get("bpm_practica_lenta", 60) or 60)
        except Exception:
            bpm = 60
        texto = (
            f"Pulso Hanon activado a {bpm} BPM. "
            "Toca cada nota cerca del clic, usando la mano y el dedo marcados en la pizarra."
        )
        try:
            self._iniciar_pulso_pizarra_piano(secuencia, bpm, texto)
        except Exception:
            pass
        self._hanon_mostrar_mensaje_accion(texto, hablar=True)

    def _crear_panel_diagnostico_pro(self):
        grupo = QGroupBox("Diagnóstico Pro en tiempo real")
        grid = QGridLayout(grupo)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(5)

        self.lbl_diag_nota = QLabel("Nota: —")
        self.lbl_diag_esperado = QLabel("Esperado: —")
        self.lbl_diag_resultado = QLabel("Resultado: esperando entrada")
        self.lbl_diag_resultado.setWordWrap(True)

        self.lbl_diag_velocity = QLabel("Velocity: —")
        self.barra_diag_velocity = QProgressBar()
        self.barra_diag_velocity.setRange(0, 127)
        self.barra_diag_velocity.setValue(0)
        self.barra_diag_velocity.setFormat("Velocity %v/127")

        self.lbl_diag_pulso = QLabel("Pulso: —")
        self.barra_diag_pulso = QProgressBar()
        self.barra_diag_pulso.setRange(0, 340)
        self.barra_diag_pulso.setValue(0)
        self.barra_diag_pulso.setFormat("Diferencia %v ms")

        self.lbl_diag_reaccion = QLabel("Reacción: —")
        self.barra_diag_reaccion = QProgressBar()
        self.barra_diag_reaccion.setRange(0, 2000)
        self.barra_diag_reaccion.setValue(0)
        self.barra_diag_reaccion.setFormat("Reacción %v ms")

        self.lbl_diag_simultaneidad = QLabel("Simultaneidad: —")
        self.barra_diag_simultaneidad = QProgressBar()
        self.barra_diag_simultaneidad.setRange(0, 300)
        self.barra_diag_simultaneidad.setValue(0)
        self.barra_diag_simultaneidad.setFormat("Simultaneidad %v ms")

        self.lbl_diag_notas = QLabel("Sobrantes/faltantes: —")
        self.lbl_diag_docente = QLabel("Corrección docente: toca una nota o inicia un reto de pizarra.")
        self.lbl_diag_docente.setWordWrap(True)

        grid.addWidget(self.lbl_diag_nota, 0, 0)
        grid.addWidget(self.lbl_diag_esperado, 0, 1)
        grid.addWidget(self.lbl_diag_resultado, 0, 2, 1, 2)

        grid.addWidget(self.lbl_diag_velocity, 1, 0)
        grid.addWidget(self.barra_diag_velocity, 1, 1)
        grid.addWidget(self.lbl_diag_pulso, 1, 2)
        grid.addWidget(self.barra_diag_pulso, 1, 3)

        grid.addWidget(self.lbl_diag_reaccion, 2, 0)
        grid.addWidget(self.barra_diag_reaccion, 2, 1)
        grid.addWidget(self.lbl_diag_simultaneidad, 2, 2)
        grid.addWidget(self.barra_diag_simultaneidad, 2, 3)

        grid.addWidget(self.lbl_diag_notas, 3, 0, 1, 2)
        grid.addWidget(self.lbl_diag_docente, 3, 2, 1, 2)
        return grupo

    def _crear_panel_ajustes(self):
        grupo = QGroupBox("Sonido, MIDI real y ajustes")
        grid = QGridLayout(grupo)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        self.chk_audio = QCheckBox("Audio activo")
        self.chk_audio.setChecked(self.ajustes.ajustes.audio_activo)
        self.chk_audio.toggled.connect(self._guardar_ajustes_audio)
        self.slider_vol = self._slider(0, 100, int(self.ajustes.ajustes.volumen * 100))
        self.slider_reverb = self._slider(0, 100, int(self.ajustes.ajustes.reverb * 100))
        self.slider_delay = self._slider(0, 75, int(self.ajustes.ajustes.delay * 100))
        self.slider_brillo = self._slider(0, 100, int(self.ajustes.ajustes.brillo * 100))
        self.slider_sustain = self._slider(5, 95, int(self.ajustes.ajustes.sustain * 100))
        for s in [self.slider_vol, self.slider_reverb, self.slider_delay, self.slider_brillo, self.slider_sustain]:
            s.valueChanged.connect(self._guardar_ajustes_audio)
        self.combo_onda = QComboBox()
        self.combo_onda.addItems(["piano suave", "pad cálido", "órgano", "seno", "sierra", "cuadrada"])
        self.combo_onda.setCurrentText(self.ajustes.ajustes.forma_onda)
        self.combo_onda.currentTextChanged.connect(self._guardar_ajustes_audio)
        self.spin_octava = QSpinBox()
        self.spin_octava.setRange(1, 5)
        self.spin_octava.setValue(self.ajustes.ajustes.octava_base)
        self.spin_octava.valueChanged.connect(self._cambiar_octava)
        self.combo_midi_in = QComboBox()
        self.combo_midi_out = QComboBox()
        self._refrescar_midi()
        btn_midi = QPushButton("Refrescar MIDI")
        btn_midi.clicked.connect(self._refrescar_midi)
        btn_abrir_midi = QPushButton("Conectar MIDI IN/OUT")
        btn_abrir_midi.clicked.connect(self._conectar_midi_in)
        btn_cerrar_midi = QPushButton("Cerrar MIDI")
        btn_cerrar_midi.clicked.connect(self._cerrar_midi)
        self.lbl_midi_estado = QLabel("MIDI: sin conectar")
        self.lbl_midi_ultima = QLabel("Última nota MIDI: —")

        grid.addWidget(self.chk_audio, 0, 0)
        grid.addWidget(QLabel("Preset"), 0, 1)
        grid.addWidget(self.combo_onda, 0, 2)
        grid.addWidget(QLabel("Vol"), 0, 3)
        grid.addWidget(self.slider_vol, 0, 4)
        grid.addWidget(QLabel("Brillo"), 0, 5)
        grid.addWidget(self.slider_brillo, 0, 6)
        grid.addWidget(QLabel("Octava"), 0, 7)
        grid.addWidget(self.spin_octava, 0, 8)
        grid.addWidget(QLabel("Reverb"), 1, 0)
        grid.addWidget(self.slider_reverb, 1, 1, 1, 2)
        grid.addWidget(QLabel("Delay"), 1, 3)
        grid.addWidget(self.slider_delay, 1, 4)
        grid.addWidget(QLabel("Sustain"), 1, 5)
        grid.addWidget(self.slider_sustain, 1, 6)
        grid.addWidget(QLabel("MIDI IN"), 2, 0)
        grid.addWidget(self.combo_midi_in, 2, 1, 1, 3)
        grid.addWidget(QLabel("MIDI OUT"), 2, 4)
        grid.addWidget(self.combo_midi_out, 2, 5, 1, 3)
        grid.addWidget(btn_midi, 2, 8)
        grid.addWidget(btn_abrir_midi, 3, 0, 1, 2)
        grid.addWidget(btn_cerrar_midi, 3, 2, 1, 2)
        grid.addWidget(self.lbl_midi_estado, 3, 4, 1, 3)
        grid.addWidget(self.lbl_midi_ultima, 3, 7, 1, 2)
        return grupo

    def _crear_panel_entradas_pro(self):
        grupo = QGroupBox("Entradas Pro del alumno")
        lay = QVBoxLayout(grupo)
        lay.setSpacing(6)

        self.lbl_entradas_pro = QLabel(self.entradas_pro.resumen())
        self.lbl_entradas_pro.setWordWrap(True)

        info = QLabel(
            "Regla Pro: MIDI siempre activo. Cámara y sonido/micrófono solo se activan si el profesor lo pide y el alumno acepta. "
            "No se graba audio ni vídeo por defecto; solo se guardan observaciones didácticas."
        )
        info.setWordWrap(True)

        fila = QHBoxLayout()
        btn_pedir_camara = QPushButton("Profesor pide cámara")
        btn_pedir_camara.clicked.connect(self._profesor_pedir_camara)
        btn_pedir_audio = QPushButton("Profesor pide escucha")
        btn_pedir_audio.clicked.connect(self._profesor_pedir_audio)
        btn_activar_audio = QPushButton("Activar escucha")
        btn_activar_audio.clicked.connect(self._activar_escucha_audio_pro)
        btn_detener_audio = QPushButton("Detener escucha")
        btn_detener_audio.clicked.connect(self._detener_escucha_audio_pro)

        fila.addWidget(btn_pedir_camara)
        fila.addWidget(btn_pedir_audio)
        fila.addWidget(btn_activar_audio)
        fila.addWidget(btn_detener_audio)

        self.lbl_audio_entrada_pro = QLabel("Escucha/micrófono: inactiva.")
        self.lbl_audio_entrada_pro.setWordWrap(True)

        lay.addWidget(self.lbl_entradas_pro)
        lay.addWidget(info)
        lay.addLayout(fila)
        lay.addWidget(self.lbl_audio_entrada_pro)
        return grupo

    def _crear_panel_camara(self):
        grupo = QGroupBox("Cámara en vivo, postura y reconocimiento visual")
        lay = QHBoxLayout(grupo)
        lay.setSpacing(10)

        panel_control = QVBoxLayout()
        panel_control.setSpacing(6)

        fila_dispositivo = QHBoxLayout()
        self.spin_camara = QSpinBox()
        self.spin_camara.setRange(0, 8)
        self.spin_camara.setValue(0)
        fila_dispositivo.addWidget(QLabel("Dispositivo"))
        fila_dispositivo.addWidget(self.spin_camara)
        fila_dispositivo.addStretch(1)

        fila_botones = QHBoxLayout()
        btn_iniciar = QPushButton("Iniciar cámara")
        btn_iniciar.clicked.connect(self._iniciar_camara_en_vivo)
        btn_detener = QPushButton("Detener cámara")
        btn_detener.clicked.connect(self._detener_camara_en_vivo)
        btn_captura = QPushButton("Capturar frame")
        btn_captura.clicked.connect(self._capturar_frame_camara)
        fila_botones.addWidget(btn_iniciar)
        fila_botones.addWidget(btn_detener)
        fila_botones.addWidget(btn_captura)

        self.lbl_camara = QLabel("Cámara detenida. Pulsa Iniciar cámara. La vista es compacta para no tapar el teclado ni la lección.")
        self.lbl_camara.setWordWrap(True)

        info = QLabel("Reconocimiento previsto: manos, postura, distancia al piano y asistencia visual del alumno.")
        info.setWordWrap(True)

        panel_control.addLayout(fila_dispositivo)
        panel_control.addLayout(fila_botones)
        panel_control.addWidget(self.lbl_camara)
        panel_control.addWidget(info)
        panel_control.addStretch(1)

        self.lbl_video_camara = QLabel("Vista de cámara")
        self.lbl_video_camara.setAlignment(Qt.AlignCenter)
        # Vista previa compacta 16:9. Antes era expansiva y ocupaba demasiado espacio.
        self.lbl_video_camara.setFixedSize(360, 180)
        self.lbl_video_camara.setStyleSheet("background:#111; color:#ddd; border:1px solid #555; border-radius:6px;")
        self.lbl_video_camara.setScaledContents(False)

        lay.addLayout(panel_control, 1)
        lay.addWidget(self.lbl_video_camara, 0, Qt.AlignRight | Qt.AlignVCenter)
        return grupo

    def _crear_panel_plan(self):
        grupo = QGroupBox("Sistema completo previsto del profesor")
        lay = QVBoxLayout(grupo)
        txt = QLabel(
            "Activo ahora: MIDI Pro continuo, historial pedagógico, flujo docente, pizarra, metrónomo, cámara bajo demanda y escucha bajo demanda.\n"
            "El profesor decide cuándo basta MIDI, cuándo necesita ver con cámara y cuándo necesita escuchar sonido real.\n"
            "Siguiente integración fuerte: panel visual de diagnóstico Pro y análisis de postura/manos más detallado."
        )
        txt.setWordWrap(True)
        lay.addWidget(txt)
        return grupo

    def _slider(self, mn, mx, val):
        s = QSlider(Qt.Horizontal)
        s.setRange(mn, mx)
        s.setValue(val)
        return s

    def _crear_pantalla_evaluacion(self):
        """Evaluación inicial interactiva real, pregunta por pregunta."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        titulo = QLabel("Evaluación inicial")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setObjectName("TituloGrande")
        layout.addWidget(titulo)

        self.lbl_eval_intro = QLabel(
            "Ahora no marcas un número a ojo: respondes pregunta por pregunta. "
            "El profesor corrige, explica y calcula tu punto de partida."
        )
        self.lbl_eval_intro.setAlignment(Qt.AlignCenter)
        self.lbl_eval_intro.setWordWrap(True)
        layout.addWidget(self.lbl_eval_intro)

        self.barra_eval_inicial = QProgressBar()
        self.barra_eval_inicial.setRange(0, 100)
        self.barra_eval_inicial.setValue(0)
        self.barra_eval_inicial.setFormat("Evaluación inicial: %p%")
        layout.addWidget(self.barra_eval_inicial)

        marco = QFrame()
        marco.setObjectName("MarcoEvaluacionInicial")
        marco_lay = QVBoxLayout(marco)
        marco_lay.setContentsMargins(14, 14, 14, 14)
        marco_lay.setSpacing(10)

        self.lbl_eval_numero = QLabel("Pregunta 1")
        self.lbl_eval_numero.setObjectName("TituloPreguntaEvaluacion")
        marco_lay.addWidget(self.lbl_eval_numero)

        self.lbl_eval_pregunta = QLabel("")
        self.lbl_eval_pregunta.setObjectName("PreguntaEvaluacionInicial")
        self.lbl_eval_pregunta.setWordWrap(True)
        self.lbl_eval_pregunta.setMinimumHeight(72)
        marco_lay.addWidget(self.lbl_eval_pregunta)

        self.botones_eval_opciones = []
        colores = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FDE2E4"]
        for i in range(4):
            btn = QPushButton("")
            btn.setObjectName("BotonOpcionEvaluacion")
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                f"background:{colores[i]};"
                "border:1px solid #94A3B8;"
                "border-radius:8px;"
                "font-weight:bold;"
                "padding:8px 12px;"
                "text-align:left;"
                "}"
                "QPushButton:hover {border:2px solid #475569; background:#F8FAFC;}"
                "QPushButton:disabled {color:#334155;}"
            )
            btn.clicked.connect(lambda _, idx=i: self._responder_evaluacion_inicial(idx))
            self.botones_eval_opciones.append(btn)
            marco_lay.addWidget(btn)

        self.txt_eval_feedback = QTextEdit()
        self.txt_eval_feedback.setObjectName("FeedbackEvaluacionInicial")
        self.txt_eval_feedback.setReadOnly(True)
        self.txt_eval_feedback.setMinimumHeight(120)
        self.txt_eval_feedback.setPlaceholderText("Aquí aparecerá la explicación del profesor.")
        marco_lay.addWidget(self.txt_eval_feedback)

        self.btn_eval_no_se = QPushButton("No lo sé todavía")
        self.btn_eval_no_se.setMinimumHeight(38)
        self.btn_eval_no_se.setCursor(Qt.PointingHandCursor)
        self.btn_eval_no_se.setStyleSheet(
            "QPushButton {background:#F1F5F9; border:1px dashed #64748B; border-radius:8px; font-weight:bold; padding:8px 12px;}"
            "QPushButton:hover {background:#E2E8F0;}"
        )
        self.btn_eval_no_se.clicked.connect(lambda: self._responder_evaluacion_inicial(-1))
        marco_lay.addWidget(self.btn_eval_no_se)

        fila = QHBoxLayout()
        self.btn_eval_leer = QPushButton("▶ Leer pregunta")
        self.btn_eval_leer.clicked.connect(self._leer_pregunta_evaluacion_inicial)
        self.btn_eval_siguiente = QPushButton("Siguiente pregunta")
        self.btn_eval_siguiente.clicked.connect(self._siguiente_pregunta_evaluacion_inicial)
        self.btn_eval_reiniciar = QPushButton("Reiniciar evaluación")
        self.btn_eval_reiniciar.clicked.connect(self._reiniciar_evaluacion_inicial_interactiva)
        self.btn_eval_continuar = QPushButton("Continuar al nivel recomendado")
        self.btn_eval_continuar.clicked.connect(self._continuar_nivel_recomendado_evaluacion)
        self.btn_eval_continuar.setVisible(False)
        self.btn_eval_teoria_cero = QPushButton("Repasar teoría desde cero")
        self.btn_eval_teoria_cero.clicked.connect(self._ir_teoria_desde_evaluacion)
        self.btn_eval_teoria_cero.setVisible(False)
        self.btn_eval_inicio = QPushButton("Volver al inicio")
        self.btn_eval_inicio.clicked.connect(self.volver_al_inicio)
        for btn in (self.btn_eval_leer, self.btn_eval_siguiente, self.btn_eval_reiniciar, self.btn_eval_continuar, self.btn_eval_teoria_cero, self.btn_eval_inicio):
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
        fila.addWidget(self.btn_eval_leer)
        fila.addWidget(self.btn_eval_siguiente)
        fila.addWidget(self.btn_eval_continuar)
        fila.addWidget(self.btn_eval_teoria_cero)
        fila.addStretch(1)
        fila.addWidget(self.btn_eval_reiniciar)
        fila.addWidget(self.btn_eval_inicio)
        marco_lay.addLayout(fila)

        layout.addWidget(marco, 1)
        return w

    def _preguntas_evaluacion_inicial(self) -> list[dict]:
        """Banco de preguntas de colocación inicial.

        Se barajan preguntas y opciones en cada intento. La evaluación no busca
        castigar: sirve para escoger el primer nivel con más precisión.
        """
        return [
            {
                "id": "eval_do",
                "pregunta": "¿Dónde está la nota DO en el teclado?",
                "opciones": [
                    "La tecla blanca que queda justo antes de un grupo de 2 teclas negras.",
                    "La tecla negra que queda entre RE y MI.",
                    "Cualquier tecla blanca, porque todas pueden llamarse DO.",
                    "La tecla blanca que queda justo después de un grupo de 3 teclas negras.",
                ],
                "correcta": 0,
                "explicacion": (
                    "DO se localiza mirando el patrón de teclas negras. Busca un grupo de 2 negras: "
                    "la tecla blanca inmediatamente a la izquierda de ese grupo es DO. Este truco se repite en todo el teclado."
                ),
            },
            {
                "id": "eval_blancas_negras",
                "pregunta": "¿Qué diferencia básica hay entre teclas blancas y negras?",
                "opciones": [
                    "Las blancas forman la secuencia DO RE MI FA SOL LA SI; las negras son alteraciones entre algunas blancas.",
                    "Las negras siempre se tocan con la mano izquierda y las blancas con la derecha.",
                    "Las blancas suenan más fuerte y las negras más flojo.",
                    "No hay diferencia musical; solo cambia el color.",
                ],
                "correcta": 0,
                "explicacion": (
                    "Las teclas blancas dan los nombres básicos de las notas. Las negras están entre algunas blancas "
                    "y se usan como sostenidos o bemoles. Por eso primero aprendemos el mapa visual del teclado."
                ),
            },
            {
                "id": "eval_escala_do",
                "pregunta": "¿Cuál es la secuencia correcta de teclas blancas desde DO hasta SI?",
                "opciones": [
                    "DO, RE, MI, FA, SOL, LA, SI.",
                    "DO, MI, RE, FA, LA, SOL, SI.",
                    "DO, RE, FA, MI, SOL, SI, LA.",
                    "RE, MI, FA, SOL, LA, SI, DO.",
                ],
                "correcta": 0,
                "explicacion": (
                    "La secuencia natural de teclas blancas es DO, RE, MI, FA, SOL, LA, SI. Después de SI vuelve DO otra vez."
                ),
            },
            {
                "id": "eval_digitacion",
                "pregunta": "En digitación básica, ¿qué número corresponde al pulgar?",
                "opciones": [
                    "1.",
                    "2.",
                    "4.",
                    "5.",
                ],
                "correcta": 0,
                "explicacion": (
                    "El pulgar es siempre el dedo 1 en ambas manos. Después vienen índice 2, corazón 3, anular 4 y meñique 5."
                ),
            },
            {
                "id": "eval_postura",
                "pregunta": "¿Cuál es una postura correcta para empezar a tocar?",
                "opciones": [
                    "Sentarse al borde del banco, espalda recta, hombros relajados y pies apoyados.",
                    "Sentarse muy atrás, espalda encorvada y brazos rígidos.",
                    "Inclinar el cuerpo hacia el teclado para llegar antes a las notas.",
                    "Levantar los hombros para ganar fuerza.",
                ],
                "correcta": 0,
                "explicacion": (
                    "Una buena postura evita tensión. El cuerpo debe estar equilibrado: espalda recta sin rigidez, "
                    "hombros sueltos, codos cómodos y pies apoyados."
                ),
            },
            {
                "id": "eval_manos",
                "pregunta": "¿Cómo deben estar los dedos al tocar una tecla?",
                "opciones": [
                    "Curvados y relajados, tocando con la yema, sin aplastar la tecla.",
                    "Totalmente planos para cubrir más teclas.",
                    "Rígidos y tensos para sonar más fuerte.",
                    "Siempre levantados al máximo antes de tocar.",
                ],
                "correcta": 0,
                "explicacion": (
                    "Los dedos deben estar curvados de forma natural. No buscamos fuerza bruta, sino control y relajación."
                ),
            },
            {
                "id": "eval_acorde_mayor",
                "pregunta": "¿Qué es un acorde, explicado de forma sencilla?",
                "opciones": [
                    "Varias notas sonando juntas.",
                    "Una sola nota muy larga.",
                    "Una tecla negra aislada.",
                    "Un silencio entre dos notas.",
                ],
                "correcta": 0,
                "explicacion": (
                    "Un acorde es un conjunto de notas que suenan al mismo tiempo. Más adelante veremos acordes mayores, menores e inversiones."
                ),
            },
            {
                "id": "eval_lectura",
                "pregunta": "¿Para qué sirve empezar leyendo melodías sencillas?",
                "opciones": [
                    "Para relacionar símbolos, notas y teclado poco a poco.",
                    "Para saltarse la técnica de manos.",
                    "Para tocar siempre más rápido.",
                    "Para no necesitar escuchar el sonido.",
                ],
                "correcta": 0,
                "explicacion": (
                    "Leer melodías sencillas ayuda a unir tres cosas: lo que ves en la partitura, el nombre de la nota y la tecla que pulsas."
                ),
            },
        ]

    def _preparar_preguntas_evaluacion_inicial(self):
        preguntas = []
        for original in self._preguntas_evaluacion_inicial():
            q = dict(original)
            opciones = list(q["opciones"])
            correcta_txt = opciones[int(q["correcta"])]
            random.shuffle(opciones)
            q["opciones"] = opciones
            q["correcta"] = opciones.index(correcta_txt)
            preguntas.append(q)
        random.shuffle(preguntas)
        return preguntas

    def _categoria_evaluacion_inicial(self, pregunta_id: str) -> str:
        mapa = {
            "eval_do": "Localización de DO",
            "eval_blancas_negras": "Mapa del teclado",
            "eval_escala_do": "Teclas blancas",
            "eval_digitacion": "Digitación",
            "eval_postura": "Postura",
            "eval_manos": "Posición de manos",
            "eval_acorde_mayor": "Acordes",
            "eval_lectura": "Lectura musical",
        }
        return mapa.get(pregunta_id, "Concepto general")

    def _diagnostico_evaluacion_inicial(self, nivel: str, aciertos: int, total: int) -> str:
        fallos = [d for d in self.eval_inicial_detalle if not d.get("correcto")]
        if not fallos:
            puntos = "No hay fallos detectados. Aun así, conviene empezar con una clase corta para confirmar técnica y postura."
        else:
            categorias = []
            for item in fallos:
                cat = item.get("categoria", "Concepto general")
                if cat not in categorias:
                    categorias.append(cat)
            puntos = "Puntos a reforzar: " + ", ".join(categorias[:6]) + "."

        porcentaje = int((aciertos / max(1, total)) * 100)
        if porcentaje >= 80:
            tono = "La base es buena para empezar con práctica guiada."
        elif porcentaje >= 50:
            tono = "Hay una base parcial: avanzaremos, pero con repasos frecuentes."
        else:
            tono = "Conviene empezar desde cero con teoría visual y práctica muy corta."

        return (
            f"Diagnóstico del profesor para {self._nombre_alumno()}:\n\n"
            f"Aciertos: {aciertos}/{total} ({porcentaje}%).\n"
            f"Nivel recomendado: {nivel}.\n\n"
            f"{tono}\n\n"
            f"{puntos}\n\n"
            "No voy a usar este resultado como castigo. Lo usaré para decidir qué explicar primero, "
            "qué repetir y cuándo pasar a la práctica."
        )

    def _guardar_evaluacion_inicial_detallada(self, nivel: str, aciertos: int, total: int, diagnostico: str):
        try:
            ruta = DATA_DIR / "evaluacion_inicial.json"
            ruta.write_text(json.dumps({
                "version": APP_VERSION,
                "alumno": self._nombre_alumno(),
                "aciertos": aciertos,
                "total": total,
                "porcentaje": int((aciertos / max(1, total)) * 100),
                "nivel_recomendado": nivel,
                "modo": "interactiva_con_diagnostico",
                "diagnostico": diagnostico,
                "detalle": self.eval_inicial_detalle,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _continuar_nivel_recomendado_evaluacion(self):
        nivel = self.eval_inicial_nivel_recomendado or self.evaluador.evaluar_prueba_inicial(self.eval_inicial_aciertos)
        self.progreso.establecer_nivel(nivel, "evaluacion_interactiva_diagnostico", reiniciar_indice=True)
        self._cargar_estudio(nivel)

    def _ir_teoria_desde_evaluacion(self):
        try:
            self.stack.setCurrentWidget(self.pantalla_inicio)
            self.pantalla_inicio.mostrar_teoria()
            texto = (
                f"{self._nombre_alumno()}, volvemos a teoría desde cero. "
                "Vamos a reforzar lo que la evaluación ha detectado antes de entrar en práctica."
            )
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
        except Exception:
            self.volver_al_inicio()

    def _reiniciar_evaluacion_inicial_interactiva(self):
        self.eval_inicial_preguntas = self._preparar_preguntas_evaluacion_inicial()
        self.eval_inicial_indice = 0
        self.eval_inicial_aciertos = 0
        self.eval_inicial_bloqueada = False
        self.eval_inicial_detalle = []
        self.eval_inicial_nivel_recomendado = ""
        self._actualizar_pregunta_evaluacion_inicial()
        texto = (
            f"{self._nombre_alumno()}, empezamos la evaluación inicial interactiva. "
            "Te haré preguntas una por una. Responde sin miedo: si fallas, te explicaré el motivo. "
            "Al final calcularé tu nivel de inicio."
        )
        self._actualizar_dialogo_avatar(texto)
        self._hablar_con_avatar(texto)

    def _actualizar_pregunta_evaluacion_inicial(self):
        total = max(1, len(self.eval_inicial_preguntas))
        indice = min(self.eval_inicial_indice, total - 1)
        q = self.eval_inicial_preguntas[indice]
        self.eval_inicial_bloqueada = False

        self.lbl_eval_numero.setText(f"Pregunta {indice + 1}/{total} · Aciertos: {self.eval_inicial_aciertos}")
        self.lbl_eval_pregunta.setText(q.get("pregunta", ""))
        self.barra_eval_inicial.setValue(int((indice / total) * 100))
        self.txt_eval_feedback.setPlainText(
            "Elige una respuesta. Después te diré si es correcta y por qué. "
            "No avanzamos sin explicación."
        )
        self.btn_eval_siguiente.setEnabled(False)
        if hasattr(self, "btn_eval_no_se"):
            self.btn_eval_no_se.setEnabled(True)
            self.btn_eval_no_se.setVisible(True)

        opciones = q.get("opciones", [])
        for i, btn in enumerate(self.botones_eval_opciones):
            if i < len(opciones):
                btn.setText(f"{chr(65+i)}) {opciones[i]}")
                btn.setVisible(True)
                btn.setEnabled(True)
            else:
                btn.setVisible(False)

    def _leer_pregunta_evaluacion_inicial(self):
        if not self.eval_inicial_preguntas:
            return
        q = self.eval_inicial_preguntas[min(self.eval_inicial_indice, len(self.eval_inicial_preguntas)-1)]
        texto = (
            f"Pregunta {self.eval_inicial_indice + 1}. {q.get('pregunta', '')} "
            "Elige la opción que creas correcta. Después la corregimos juntos."
        )
        self._actualizar_dialogo_avatar(texto)
        self._hablar_con_avatar(texto)

    def _responder_evaluacion_inicial(self, indice_opcion: int):
        if self.eval_inicial_bloqueada or not self.eval_inicial_preguntas:
            return
        q = self.eval_inicial_preguntas[self.eval_inicial_indice]
        correcta_idx = int(q.get("correcta", -1))
        correcto = int(indice_opcion) == correcta_idx

        opciones = q.get("opciones", [])
        correcta_txt = opciones[correcta_idx] if 0 <= correcta_idx < len(opciones) else ""
        if 0 <= int(indice_opcion) < len(opciones):
            elegida_txt = opciones[int(indice_opcion)]
        else:
            elegida_txt = "No lo sé todavía"

        if correcto:
            self.eval_inicial_aciertos += 1
            self.audio.sonido_acierto()
            cabecera = "Correcto."
        else:
            self.audio.sonido_error()
            cabecera = "No pasa nada. Esto queda anotado para reforzarlo."

        detalle = {
            "id": q.get("id", ""),
            "categoria": self._categoria_evaluacion_inicial(q.get("id", "")),
            "pregunta": q.get("pregunta", ""),
            "respuesta_elegida": elegida_txt,
            "respuesta_correcta": correcta_txt,
            "correcto": bool(correcto),
            "explicacion": q.get("explicacion", ""),
        }
        self.eval_inicial_detalle.append(detalle)

        feedback = (
            f"{cabecera}\n\n"
            f"Tu respuesta: {elegida_txt}\n"
            f"Respuesta correcta: {correcta_txt}\n\n"
            f"Explicación del profesor:\n{q.get('explicacion', '')}\n\n"
            "Cuando estés listo, pulsa Siguiente pregunta."
        )
        self.txt_eval_feedback.setPlainText(feedback)
        self._actualizar_dialogo_avatar(feedback)
        self._hablar_con_avatar(feedback)

        self.eval_inicial_bloqueada = True
        self.btn_eval_siguiente.setEnabled(True)
        if hasattr(self, "btn_eval_no_se"):
            self.btn_eval_no_se.setEnabled(False)
        for i, btn in enumerate(self.botones_eval_opciones):
            btn.setEnabled(False)
            if i == correcta_idx:
                btn.setStyleSheet(
                    "QPushButton {background:#DCFCE7; border:2px solid #16A34A; "
                    "border-radius:8px; font-weight:bold; padding:8px 12px; text-align:left;}"
                )
            elif i == indice_opcion and not correcto:
                btn.setStyleSheet(
                    "QPushButton {background:#FEE2E2; border:2px solid #DC2626; "
                    "border-radius:8px; font-weight:bold; padding:8px 12px; text-align:left;}"
                )

    def _siguiente_pregunta_evaluacion_inicial(self):
        if not self.eval_inicial_preguntas:
            return
        if not self.eval_inicial_bloqueada:
            texto = "Primero responde la pregunta actual para que pueda corregirte y explicarte el motivo."
            self.txt_eval_feedback.setPlainText(texto)
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
            return
        self.eval_inicial_indice += 1
        if self.eval_inicial_indice >= len(self.eval_inicial_preguntas):
            self._finalizar_evaluacion_inicial_interactiva()
            return

        # Restaurar estilos base después de la corrección anterior.
        colores = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FDE2E4"]
        for i, btn in enumerate(self.botones_eval_opciones):
            btn.setStyleSheet(
                "QPushButton {"
                f"background:{colores[i]};"
                "border:1px solid #94A3B8;"
                "border-radius:8px;"
                "font-weight:bold;"
                "padding:8px 12px;"
                "text-align:left;"
                "}"
                "QPushButton:hover {border:2px solid #475569; background:#F8FAFC;}"
                "QPushButton:disabled {color:#334155;}"
            )
        self._actualizar_pregunta_evaluacion_inicial()

    def _finalizar_evaluacion_inicial_interactiva(self):
        total = max(1, len(self.eval_inicial_preguntas))
        aciertos = int(self.eval_inicial_aciertos)
        self.barra_eval_inicial.setValue(100)
        nivel = self.evaluador.evaluar_prueba_inicial(aciertos)
        self.eval_inicial_nivel_recomendado = nivel

        diagnostico = self._diagnostico_evaluacion_inicial(nivel, aciertos, total)
        self.txt_eval_feedback.setPlainText(diagnostico)
        self._actualizar_dialogo_avatar(diagnostico)
        self._hablar_con_avatar(diagnostico)
        self._guardar_evaluacion_inicial_detallada(nivel, aciertos, total, diagnostico)
        try:
            plan = self.plan_personalizado.generar_desde_evaluacion()
            diagnostico = diagnostico + "\n\nPLAN PERSONALIZADO CREADO:\n" + plan.get("resumen", "")
            self.txt_eval_feedback.setPlainText(diagnostico)
            self._actualizar_dialogo_avatar(diagnostico)
        except Exception:
            pass

        # La versión anterior saltaba automáticamente al estudio después de 1,6 s.
        # Ahora dejamos que el alumno lea el diagnóstico y decida continuar o repasar teoría.
        self.btn_eval_siguiente.setVisible(False)
        self.btn_eval_leer.setVisible(False)
        self.btn_eval_continuar.setVisible(True)
        self.btn_eval_teoria_cero.setVisible(True)
        self.btn_eval_continuar.setEnabled(True)
        self.btn_eval_teoria_cero.setEnabled(True)
        if hasattr(self, "btn_eval_no_se"):
            self.btn_eval_no_se.setVisible(False)
        for btn in self.botones_eval_opciones:
            btn.setVisible(False)

        # Preparamos el progreso, pero no cambiamos de pantalla hasta que el alumno pulse continuar.
        self.progreso.establecer_nivel(nivel, "evaluacion_interactiva_diagnostico", reiniciar_indice=True)

    def _seleccionar_combo_por_data(self, combo, data):
        try:
            for i in range(combo.count()):
                if combo.itemData(i) == data:
                    combo.setCurrentIndex(i)
                    return True
        except Exception:
            pass
        return False

    def _refrescar_midi(self):
        entradas = self.midi.entradas()
        salidas = self.midi.salidas()
        self.combo_midi_in.clear()
        self.combo_midi_out.clear()
        self.combo_midi_in.addItem("Sin entrada MIDI", "")
        self.combo_midi_out.addItem("Sin salida MIDI", "")
        for entrada in entradas:
            self.combo_midi_in.addItem(entrada, entrada)
        for salida in salidas:
            self.combo_midi_out.addItem(salida, salida)
        self._seleccionar_combo_por_data(self.combo_midi_in, self.ajustes.ajustes.midi_in_preferido)
        self._seleccionar_combo_por_data(self.combo_midi_out, self.ajustes.ajustes.midi_out_preferido)
        if hasattr(self, "lbl_midi_estado"):
            self.lbl_midi_estado.setText(f"MIDI: {len(entradas)} entradas | {len(salidas)} salidas")

    def _conectar_midi_in(self):
        nombre_in = self.combo_midi_in.currentData() or ""
        nombre_out = self.combo_midi_out.currentData() or ""
        partes = []

        if nombre_in:
            ok_in = self.midi.abrir_entrada(nombre_in)
            partes.append(f"IN conectado: {nombre_in}" if ok_in else f"IN error: {self.midi.error}")
            if ok_in:
                self.ajustes.ajustes.midi_in_preferido = nombre_in
        else:
            self.midi.cerrar_entrada()
            partes.append("IN: sin seleccionar")
            self.ajustes.ajustes.midi_in_preferido = ""

        if nombre_out:
            ok_out = self.midi.abrir_salida(nombre_out)
            partes.append(f"OUT conectado: {nombre_out}" if ok_out else f"OUT error: {self.midi.error}")
            if ok_out:
                self.ajustes.ajustes.midi_out_preferido = nombre_out
        else:
            self.midi.cerrar_salida()
            partes.append("OUT: sin seleccionar")
            self.ajustes.ajustes.midi_out_preferido = ""

        self.ajustes.guardar()
        texto = "MIDI: " + " | ".join(partes)
        self.lbl_midi_estado.setText(texto)
        if hasattr(self, "lbl_midi_compacto"):
            self.lbl_midi_compacto.setText(texto)

    def _cerrar_midi(self):
        self.midi.cerrar()
        self.lbl_midi_estado.setText("MIDI: cerrado")
        if hasattr(self, "lbl_midi_compacto"):
            self.lbl_midi_compacto.setText("MIDI: cerrado")

    def _midi_raw(self, msg: str):
        self.ultimo_midi_raw = msg
        if not msg:
            return
        # Algunos teclados envían active_sensing/clock de forma continua.
        # Actualizar una QLabel por cada paquete puede saturar el hilo gráfico.
        try:
            ahora = time.monotonic()
            importante = ("note_on" in msg) or ("note_off" in msg)
            if (not importante) and ahora - float(getattr(self, "_ultimo_midi_raw_ui_ts", 0.0) or 0.0) < 0.25:
                return
            if msg == getattr(self, "_ultimo_midi_raw_texto", "") and ahora - float(getattr(self, "_ultimo_midi_raw_ui_ts", 0.0) or 0.0) < 0.50:
                return
            self._ultimo_midi_raw_ui_ts = ahora
            self._ultimo_midi_raw_texto = msg
        except Exception:
            pass
        if hasattr(self, "lbl_midi_ultima"):
            self.lbl_midi_ultima.setText(f"Último MIDI RAW: {msg[:90]}")

    def _midi_enviar_note_on_seguro(self, nota: str, velocity: int = 96, canal: int = 1):
        try:
            if hasattr(self, "midi") and self.midi.salida_abierta():
                self.midi.enviar_note_on(nota, velocity=velocity, canal=canal)
        except Exception:
            pass

    def _midi_enviar_note_off_seguro(self, nota: str, velocity: int = 0, canal: int = 1):
        try:
            if hasattr(self, "midi") and self.midi.salida_abierta():
                self.midi.enviar_note_off(nota, velocity=velocity, canal=canal)
        except Exception:
            pass

    def _audio_y_midi_note_on(self, nota: str, velocity: int = 96, canal: int = 1):
        self.audio.note_on(nota, velocity=velocity)
        self._midi_enviar_note_on_seguro(nota, velocity=velocity, canal=canal)

    def _audio_y_midi_note_off(self, nota: str, velocity: int = 0, canal: int = 1, release_segundos=None):
        try:
            self.audio.note_off(nota, release_segundos=release_segundos)
        except TypeError:
            self.audio.note_off(nota)
        self._midi_enviar_note_off_seguro(nota, velocity=velocity, canal=canal)

    def _midi_note_on(self, nota: str, velocidad: int, canal: int):
        self.reconocedor.note_on(nota, velocidad, canal)
        nota_audio = self._normalizar_nota_audio(nota)
        try:
            vel = max(0, min(127, int(velocidad or 0)))
            self._midi_velocity_min = vel if self._midi_velocity_min is None else min(self._midi_velocity_min, vel)
            self._midi_velocity_max = vel if self._midi_velocity_max is None else max(self._midi_velocity_max, vel)
            if hasattr(self, "lbl_midi_compacto"):
                self.lbl_midi_compacto.setText(
                    f"MIDI alumno: {nota_audio} vel={vel} min={self._midi_velocity_min} max={self._midi_velocity_max}"
                )
        except Exception:
            pass
        if hasattr(self, "piano"):
            self.piano.nota_externa_on(nota_audio)
        self._representar_midi_externo_en_pentagrama(nota_audio, velocidad, canal)
        if hasattr(self, "lbl_midi_ultima"):
            self.lbl_midi_ultima.setText(f"MIDI alumno: {nota_audio} vel={velocidad} ch={canal}")
        self._ultima_entrada_alumno = {
            "origen": "midi_in",
            "velocity": velocidad,
            "canal": canal,
            "nota": nota_audio,
            "ts": time.monotonic(),
        }
        diag_pro = self._diagnostico_pro_desde_entrada(nota_audio, velocity=velocidad, canal=canal, origen="midi_in")
        if diag_pro is not None and getattr(diag_pro, "mensaje_docente", ""):
            if hasattr(self, "lbl_midi_ultima"):
                self.lbl_midi_ultima.setText(f"MIDI Pro: {diag_pro.mensaje_docente[:110]}")
            self._evaluar_necesidad_entradas_pro(diag_pro)
        try:
            self.entradas_pro.registrar_midi_continuo({"nota": nota_audio, "velocity": velocidad, "canal": canal})
            self._actualizar_estado_entradas_pro()
        except Exception:
            pass
        self.audio.note_on(nota_audio, velocity=velocidad)

        if self._procesar_midi_didactico_practica_entrada(nota_audio, velocidad, canal):
            return

        if self._procesar_hanon_midi_entrada(nota_audio, velocidad, canal):
            return

        if self._procesar_pulso_practica_entrada(nota_audio, velocidad, canal, origen="midi_in"):
            return

        # Primero evaluamos los retos de la pizarra: primera lectura aplicada al teclado MIDI.
        if self._procesar_pulso_pizarra_nota(nota_audio):
            return

        if self._procesar_secuencia_pizarra_nota(nota_audio):
            return
        if self._procesar_reto_pizarra_nota(nota_audio):
            return

        self._evaluar_nota_midi_si_corresponde(nota)

    def _midi_note_off(self, nota: str, velocidad: int, canal: int):
        self.reconocedor.note_off(nota)
        nota_audio = self._normalizar_nota_audio(nota)
        try:
            duracion_ms = self.analizador_midi_pro.note_off(nota_audio)
            if duracion_ms is not None:
                self._registrar_historial_midi(
                    nota=nota_audio,
                    origen="midi_in",
                    tipo="duracion",
                    mensaje=f"Duración de nota: {duracion_ms} ms",
                    contexto={"duracion_ms": duracion_ms}
                )
        except Exception:
            pass
        if hasattr(self, "piano"):
            self.piano.nota_externa_off(nota_audio)
        self._hanon_midi_note_off(nota_audio)
        self._limpiar_midi_externo_en_pentagrama(nota_audio)
        self.audio.note_off(nota_audio)

    def _normalizar_nota_audio(self, nota: str) -> str:
        return (nota.replace("Do", "C").replace("Re", "D").replace("Mi", "E")
                    .replace("Fa", "F").replace("Sol", "G").replace("La", "A").replace("Si", "B"))

    def _evaluar_nota_midi_si_corresponde(self, nota: str):
        ejercicio = self.motor.ejercicio_actual or {}
        tipo = ejercicio.get("tipo")
        if tipo == "midi_acorde":
            objetivo = str(ejercicio.get("solucion", "")).lower().strip()
            try:
                self.analizador_midi_pro.configurar_objetivo(
                    tipo="acorde",
                    esperado=objetivo,
                    permite_simultaneas=True,
                    requiere_simultaneo=True
                )
            except Exception:
                pass
            actual = self.reconocedor.acorde_actual_texto()
            self.lbl_midi_ultima.setText(f"Acorde MIDI: {actual or nota}")
            if self.fase_didactica != "ejercicio" and not self.progreso.estado.modo_examen:
                if actual:
                    self._gestionar_respuesta_en_practica_o_ejercicio(actual, origen="midi")
                else:
                    self.txt_resultado.setText("Práctica de acorde: mantén varias notas a la vez para que el profesor pueda reconocerlo.")
                return
            if self.reconocedor.coincide_acorde(objetivo):
                self.input_respuesta.setText(actual)
                self.comprobar_ejercicio()
            else:
                self.audio.sonido_error()
                self.txt_resultado.setText(f"Acorde detectado: {actual}. Objetivo: {objetivo}. Mantén todas las notas a la vez.")
            return
        if tipo not in {"midi_nota", "midi_secuencia"}:
            self.txt_resultado.setText(f"MIDI recibido: {nota}. El profesor escucha tu teclado externo. Para probar lectura en pentagrama, abre Partitura, pulsa Leer punto actual y usa Tocar en piano o Tocar secuencia.")
            return
        tocada = self.reconocedor.ultima_nota_base() or self._nota_audio_a_es_base(self._normalizar_nota_audio(nota))
        self._procesar_nota_alumno(tocada, origen="midi")

    def _actualizar_estado_entradas_pro(self):
        try:
            if hasattr(self, "lbl_entradas_pro"):
                self.lbl_entradas_pro.setText(self.entradas_pro.resumen())
        except Exception:
            pass

    def _registrar_observacion_entrada_pro(self, entrada: str, texto: str, detalle: dict | None = None):
        try:
            self.entradas_pro.registrar_observacion(entrada, texto, detalle or {})
        except Exception:
            pass
        try:
            self.historial_alumno.registrar_observacion_pro(entrada, texto, detalle or {})
        except Exception:
            pass
        self._actualizar_estado_entradas_pro()

    def _profesor_pedir_camara(self):
        motivo = "El profesor necesita comprobar postura, manos, muñeca o tensión corporal."
        self.entradas_pro.solicitar_camara(motivo)
        texto = "Profesor: activa la cámara solo si aceptas. Quiero observar postura y manos, no grabar vídeo."
        if hasattr(self, "lbl_camara"):
            self.lbl_camara.setText(texto)
        self._registrar_observacion_entrada_pro("camara", texto, {"motivo": motivo})
        self._hablar_con_avatar(texto)

    def _profesor_pedir_audio(self):
        motivo = "El profesor necesita escuchar el sonido real, ataque, golpes, articulación o nivel acústico."
        self.entradas_pro.solicitar_sonido(motivo)
        texto = "Profesor: activa la escucha solo para este ejercicio si aceptas. No se grabará audio; solo analizaré nivel y observaciones."
        if hasattr(self, "lbl_audio_entrada_pro"):
            self.lbl_audio_entrada_pro.setText(texto)
        self._registrar_observacion_entrada_pro("sonido", texto, {"motivo": motivo})
        self._hablar_con_avatar(texto)

    def _activar_escucha_audio_pro(self):
        ok = self.audio_entrada.iniciar()
        if ok:
            self.entradas_pro.activar("sonido", "Alumno activa escucha bajo demanda.")
            texto = "Escucha activa. El profesor analizará nivel de entrada sin grabar audio."
            self.timer_audio_entrada.start()
        else:
            texto = f"Escucha no disponible: {self.audio_entrada.error}"
        if hasattr(self, "lbl_audio_entrada_pro"):
            self.lbl_audio_entrada_pro.setText(texto)
        self._registrar_observacion_entrada_pro("sonido", texto, {"activo": ok, "error": self.audio_entrada.error})
        self._actualizar_estado_entradas_pro()

    def _detener_escucha_audio_pro(self):
        self.timer_audio_entrada.stop()
        self.audio_entrada.detener()
        self.entradas_pro.desactivar("sonido", "Alumno detiene escucha.")
        texto = "Escucha detenida. No se ha guardado audio."
        if hasattr(self, "lbl_audio_entrada_pro"):
            self.lbl_audio_entrada_pro.setText(texto)
        self._registrar_observacion_entrada_pro("sonido", texto, {"activo": False})

    def _actualizar_escucha_audio_pro(self):
        obs = self.audio_entrada.observacion()
        texto = f"Escucha: {obs.get('texto')} RMS={obs.get('rms')} pico={obs.get('pico')} · sin grabación."
        if hasattr(self, "lbl_audio_entrada_pro"):
            self.lbl_audio_entrada_pro.setText(texto)
        self.entradas_pro.registrar_observacion("sonido", texto, obs)
        # No guardamos cada tick para no llenar el historial. Solo alertas relevantes.
        if obs.get("estado") in {"saturacion", "muy_bajo"}:
            self._registrar_observacion_entrada_pro("sonido", texto, obs)

    def _evaluar_necesidad_entradas_pro(self, diag_pro):
        try:
            decisiones = self.entradas_pro.decidir_por_diagnostico_midi(diag_pro)
        except Exception:
            decisiones = []
        for dec in decisiones:
            entrada = dec.get("entrada")
            motivo = dec.get("motivo", "")
            if entrada == "camara":
                texto = "Profesor: por lo que detecta el MIDI, conviene activar cámara para revisar mano/postura."
                if hasattr(self, "lbl_camara"):
                    self.lbl_camara.setText(texto + " " + motivo)
                self._registrar_observacion_entrada_pro("camara", texto, {"motivo": motivo})
            elif entrada == "sonido":
                texto = "Profesor: por lo que detecta el MIDI, conviene activar escucha para revisar sonido real."
                if hasattr(self, "lbl_audio_entrada_pro"):
                    self.lbl_audio_entrada_pro.setText(texto + " " + motivo)
                self._registrar_observacion_entrada_pro("sonido", texto, {"motivo": motivo})
        self._actualizar_estado_entradas_pro()

    def _probar_camara(self):
        ok = self.camera.abrir(0)
        if ok:
            self.lbl_camara.setText("Cámara: detectada y abierta correctamente. Reconocimiento visual preparado para siguientes capas.")
            self.camera.cerrar()
        else:
            self.lbl_camara.setText(f"Cámara: no disponible ({self.camera.error}). Instala opencv-python o revisa permisos/dispositivo.")

    def _iniciar_camara_en_vivo(self):
        indice = int(self.spin_camara.value())
        ok = self.camera.abrir(indice)
        if not ok:
            self.timer_camara.stop()
            self.lbl_camara.setText(f"Cámara: no disponible ({self.camera.error}). Revisa OpenCV, permisos o número de dispositivo.")
            self.lbl_video_camara.setText("Sin señal de cámara")
            return
        self.lbl_camara.setText(f"Cámara: activa en dispositivo {indice}. Vista en directo funcionando.")
        self.entradas_pro.activar("camara", f"Alumno activa cámara en dispositivo {indice}.")
        self._registrar_observacion_entrada_pro("camara", "Cámara activa bajo permiso del alumno.", {"dispositivo": indice, "sin_grabacion": True})
        self.timer_camara.start()
        self._actualizar_estado_entradas_pro()

    def _detener_camara_en_vivo(self):
        self.timer_camara.stop()
        self.camera.cerrar()
        self.entradas_pro.desactivar("camara", "Alumno detiene cámara.")
        self._registrar_observacion_entrada_pro("camara", "Cámara detenida. No se ha guardado vídeo.", {"sin_grabacion": True})
        self.lbl_camara.setText("Cámara: detenida.")
        self.lbl_video_camara.setPixmap(QPixmap())
        self.lbl_video_camara.setText("Vista de cámara detenida")

    def _actualizar_vista_camara(self):
        frame = self.camera.leer_frame()
        if frame is None:
            self.lbl_camara.setText(f"Cámara: sin frame válido ({self.camera.error or 'sin señal'}).")
            return
        try:
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            alto, ancho, canales = frame_rgb.shape
            bytes_por_linea = canales * ancho
            imagen = QImage(frame_rgb.data, ancho, alto, bytes_por_linea, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(imagen).scaled(
                self.lbl_video_camara.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.lbl_video_camara.setPixmap(pixmap)
        except Exception as exc:
            self.lbl_camara.setText(f"Cámara: error mostrando imagen ({exc}).")

    def _capturar_frame_camara(self):
        frame = self.camera.leer_frame()
        if frame is None:
            self.lbl_camara.setText("Cámara: no hay frame para capturar. Inicia la cámara primero.")
            return
        texto = "Frame observado. Uso didáctico: postura, manos, muñeca y posición sobre el teclado. No se guarda vídeo."
        self.lbl_camara.setText(texto)
        self._registrar_observacion_entrada_pro("camara", texto, {"frame_observado": True, "sin_grabacion": True})

    def _configurar_audio_desde_ajustes(self):
        a = self.ajustes.ajustes
        self.audio.configurar(volumen=a.volumen, forma_onda=a.forma_onda, activo=a.audio_activo, reverb=a.reverb, delay=a.delay, brillo=a.brillo, sustain=a.sustain)

    def _arrancar_audio_si_activo(self):
        # No se abre PortAudio al iniciar la ventana. En algunos equipos Linux el
        # autoarranque de sounddevice provoca violación de segmento. El motor queda
        # preparado y se abre al tocar una tecla o al generar un feedback.
        if self.ajustes.ajustes.audio_activo:
            self.lbl_audio.setText("Audio: listo")
        else:
            self.lbl_audio.setText("Audio: desactivado")

    def _guardar_ajustes_audio(self):
        a = self.ajustes.ajustes
        a.audio_activo = self.chk_audio.isChecked()
        a.volumen = self.slider_vol.value() / 100
        a.forma_onda = self.combo_onda.currentText()
        a.reverb = self.slider_reverb.value() / 100
        a.delay = self.slider_delay.value() / 100
        a.brillo = self.slider_brillo.value() / 100
        a.sustain = self.slider_sustain.value() / 100
        self.ajustes.guardar()
        self._configurar_audio_desde_ajustes()
        self._arrancar_audio_si_activo()

    def _cambiar_octava(self, valor):
        self.ajustes.ajustes.octava_base = int(valor)
        self.ajustes.guardar()
        self.piano.reconstruir(int(valor))

    def mostrar_evaluacion(self):
        self.stack.setCurrentWidget(self.pantalla_evaluacion)
        self._reiniciar_evaluacion_inicial_interactiva()

    def finalizar_evaluacion(self, aciertos: int):
        nivel = self.evaluador.evaluar_prueba_inicial(aciertos)
        try:
            self.pantalla_inicio.seleccionar_nivel_guiado(nivel)
        except Exception:
            pass
        self.progreso.establecer_nivel(nivel, "evaluacion", reiniciar_indice=True)
        self._cargar_estudio(nivel)

    def _abrir_nivel_guiado_si_disponible(self, nivel: str) -> bool:
        if str(nivel) not in {"nivel_0", "nivel_1", "nivel_2"}:
            return False
        try:
            if not self.pantalla_inicio.seleccionar_nivel_guiado(nivel):
                return False
            self.stack.setCurrentWidget(self.pantalla_inicio)
            self.pantalla_inicio.mostrar_teoria()
            self._actualizar_estado()
            return True
        except Exception:
            return False

    def iniciar_desde_nivel(self, nivel: str):
        self.progreso.establecer_nivel(nivel, "manual", reiniciar_indice=True)
        if self._abrir_nivel_guiado_si_disponible(nivel):
            return
        self._cargar_estudio(nivel)

    def continuar_progreso(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            if self._nivel0_teoria_superado():
                self.progreso.establecer_nivel("nivel_1", "nivel_0_superado", reiniciar_indice=True)
                if self._abrir_nivel_guiado_si_disponible("nivel_1"):
                    return
                self._cargar_estudio("nivel_1")
                return
            QMessageBox.information(self, "Sin progreso", "Haz la evaluación o elige un nivel manualmente.")
            return
        try:
            self.pantalla_inicio.seleccionar_nivel_guiado(nivel)
        except Exception:
            pass
        if self._abrir_nivel_guiado_si_disponible(nivel):
            return
        self._cargar_estudio(nivel)

    def _nivel0_teoria_superado(self) -> bool:
        """Comprueba si la teoría/evaluación del Nivel 0 ya está superada."""
        try:
            ruta = DATA_DIR / "progreso_alumno.json"
            datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
            return bool(datos.get("nivel_0_superado") or datos.get("mini_evaluacion_nivel_0_superada"))
        except Exception:
            return False

    def _cargar_estudio(self, nivel: str):
        ejercicio, nivel_real, indice, total = self.motor.cargar_ejercicio(nivel, self.progreso.estado.indice_ejercicio)
        if nivel_real != self.progreso.estado.nivel_actual:
            self.progreso.establecer_nivel(nivel_real, self.progreso.estado.modo_inicio, reiniciar_indice=True)
            nivel = nivel_real
            indice = 0
        self.fase_didactica = "clase"
        self.ejercicio_desbloqueado = False
        self.secuencia_alumno = []
        self.lbl_nivel.setText(f"Nivel: {nivel}")
        self._actualizar_estado()
        self.lbl_ejercicio.setText(f"{ejercicio.get('titulo','Sin ejercicio')}  ({indice+1}/{max(1,total)})")
        self.lbl_objetivo.setText(f"Objetivo: {ejercicio.get('objetivo','')}")
        self.barra_progreso.setValue(self.motor.progreso_nivel_porcentaje(indice))
        self._mostrar_fase_clase(ejercicio, nivel)
        self.txt_resultado.setText(
            "Empieza por la clase. Después usa Ver ejemplo, Practicar y, al final, Hacer ejercicio.\n\n"
            + self._resumen_historial_para_profesor()
        )
        self.input_respuesta.clear()
        self.stack.setCurrentWidget(self.pantalla_estudio)
        self._mostrar_panel_clase_practica()


    def _mostrar_fase_clase(self, ejercicio: dict, nivel: str):
        self.fase_didactica = "clase"
        self.ejercicio_desbloqueado = False
        self.lbl_fase_clase.setText("Fase 1/4: Clase — el profesor explica antes de preguntar")
        self.input_respuesta.setEnabled(False)
        self.btn_comprobar.setEnabled(False)
        self._poner_texto_profesor(self.profesor_didactico.clase(ejercicio, nivel), hablar=True)
        try:
            self._midi_didactico_cargar_desde_ejercicio(ejercicio)
        except Exception:
            pass

    def ver_clase_actual(self):
        ejercicio = self.motor.ejercicio_actual or {}
        nivel = self.progreso.estado.nivel_actual if self.progreso.estado.nivel_actual != "sin_evaluar" else "inicial"
        self._mostrar_fase_clase(ejercicio, nivel)
        self.txt_resultado.setText("Clase repetida. Lee la explicación antes de practicar.")

    def ver_ejemplo_actual(self):
        ejercicio = self.motor.ejercicio_actual or {}
        self.fase_didactica = "ejemplo"
        self.ejercicio_desbloqueado = False
        self.lbl_fase_clase.setText("Fase 2/4: Ejemplo — mira y escucha antes de responder")
        self.input_respuesta.setEnabled(False)
        self.btn_comprobar.setEnabled(False)
        self._poner_texto_profesor(self.profesor_didactico.ejemplo(ejercicio), hablar=True)
        self.txt_resultado.setText("Ejemplo mostrado. Si el ejercicio tiene nota o acorde, sonará una demostración.")
        self._reproducir_demostracion(ejercicio)

    def activar_practica_guiada(self):
        ejercicio = self.motor.ejercicio_actual or {}
        self.fase_didactica = "practica"
        self.ejercicio_desbloqueado = False
        self.secuencia_alumno = []
        self.input_respuesta.clear()
        self.lbl_fase_clase.setText("Fase 3/4: Práctica guiada — no cuenta como fallo")
        self.input_respuesta.setEnabled(True)
        self.btn_comprobar.setEnabled(True)
        self.input_respuesta.setPlaceholderText("Practica aquí. No cuenta como fallo todavía.")
        self._poner_texto_profesor(self.profesor_didactico.practica(ejercicio), hablar=True)
        self.txt_resultado.setText("Modo práctica activo. Puedes tocar o escribir sin perder progreso.")
        self.input_respuesta.setFocus()

    def activar_ejercicio_evaluable(self):
        ejercicio = self.motor.ejercicio_actual or {}
        self.fase_didactica = "ejercicio"
        self.ejercicio_desbloqueado = True
        self.secuencia_alumno = []
        self.lbl_fase_clase.setText("Fase 4/4: Ejercicio evaluable — ahora sí cuenta")
        self.input_respuesta.setEnabled(True)
        self.btn_comprobar.setEnabled(True)
        self.input_respuesta.setPlaceholderText("Ahora responde o toca el teclado MIDI. Esta vez sí se evaluará.")
        self._poner_texto_profesor(self.profesor_didactico.ejercicio(ejercicio), hablar=True)
        self.txt_resultado.setText("Ejercicio desbloqueado. Si aciertas avanzas; si fallas, el profesor vuelve a explicar.")
        self.input_respuesta.clear()
        self.input_respuesta.setFocus()

    def explicar_otra_vez(self):
        ejercicio = self.motor.ejercicio_actual or {}
        nivel = self.progreso.estado.nivel_actual if self.progreso.estado.nivel_actual != "sin_evaluar" else "inicial"
        self._mostrar_fase_clase(ejercicio, nivel)
        self.txt_resultado.setText("El profesor ha vuelto al modo clase. No se evalúa nada hasta que pulses 'Hacer ejercicio'.")

    def _reproducir_demostracion(self, ejercicio: dict):
        try:
            pieza = self._midi_didactico_cargar_desde_ejercicio(ejercicio)
            if pieza and pieza.notas:
                texto = (
                    f"Reproduciendo MIDI interno: {pieza.titulo}. "
                    f"{len(pieza.notas or [])} notas con dinámica real."
                )
                if hasattr(self, "lbl_midi_didactico_estado"):
                    self.lbl_midi_didactico_estado.setText(texto)
                self._midi_didactico_iniciar("escuchar")
                return
        except Exception as exc:
            if hasattr(self, "lbl_midi_didactico_estado"):
                self.lbl_midi_didactico_estado.setText(f"No se pudo reproducir el MIDI interno de la clase: {exc}")

        notas = self._notas_audio_desde_solucion(ejercicio.get("solucion", ""))
        if not notas:
            return
        tipo = ejercicio.get("tipo", "")
        if tipo == "midi_acorde" and len(notas) > 1:
            for nota in notas:
                self._audio_y_midi_note_on(nota)
            QTimer.singleShot(900, lambda notas=notas: [self._audio_y_midi_note_off(n) for n in notas])
            return
        self.secuencia_demo = notas
        self.indice_demo = 0
        self._tocar_siguiente_demo()

    def _tocar_siguiente_demo(self):
        if self.indice_demo >= len(self.secuencia_demo):
            return
        nota = self.secuencia_demo[self.indice_demo]
        self._audio_y_midi_note_on(nota)
        QTimer.singleShot(420, lambda n=nota: self._audio_y_midi_note_off(n))
        self.indice_demo += 1
        if self.indice_demo < len(self.secuencia_demo):
            QTimer.singleShot(520, self._tocar_siguiente_demo)

    def _notas_audio_desde_solucion(self, solucion: str):
        texto = str(solucion or "").strip().lower()
        if not texto:
            return []
        # Solo intentamos reproducir soluciones que representan notas musicales.
        if not any(n in texto for n in ["do", "re", "mi", "fa", "sol", "la", "si"]):
            return []
        piezas = [p.strip() for p in texto.replace(",", "-").replace("+", "-").split("-") if p.strip()]
        if not piezas:
            piezas = [texto]
        octava = int(self.ajustes.ajustes.octava_base) + 1
        mapa = {"do":"C", "re":"D", "mi":"E", "fa":"F", "sol":"G", "la":"A", "si":"B"}
        salida = []
        for pieza in piezas:
            base = mapa.get(pieza)
            if base:
                salida.append(f"{base}{octava}")
        return salida

    def _nota_audio_a_es_base(self, nota: str) -> str:
        """Convierte C4, C#4, Do4, etc. a una respuesta base comparable: do, do#, re..."""
        texto = str(nota or "").strip()
        base = ''.join([c for c in texto if not c.isdigit() and c not in " -_"]).upper()
        base = (
            base.replace("DO#", "C#").replace("RE#", "D#").replace("FA#", "F#")
                .replace("SOL#", "G#").replace("LA#", "A#")
                .replace("DO", "C").replace("RE", "D").replace("MI", "E")
                .replace("FA", "F").replace("SOL", "G").replace("LA", "A").replace("SI", "B")
        )
        mapa = {"C":"do", "C#":"do#", "D":"re", "D#":"re#", "E":"mi", "F":"fa", "F#":"fa#", "G":"sol", "G#":"sol#", "A":"la", "A#":"la#", "B":"si"}
        return mapa.get(base, base.lower())

    def _normalizar_secuencia_musical(self, texto: str) -> list[str]:
        """Convierte una secuencia escrita o tocada a lista comparable: do-re-mi -> [do, re, mi]."""
        valor = str(texto or "").strip().lower()
        if not valor:
            return []
        for sep in [",", "+", ";", "/", "\\", "|"]:
            valor = valor.replace(sep, "-")
        valor = valor.replace(" ", "-")
        partes = [p for p in valor.split("-") if p.strip()]
        return [self._normalizar_respuesta_musical(p) for p in partes if self._normalizar_respuesta_musical(p)]

    def _texto_secuencia(self, secuencia: list[str]) -> str:
        return "-".join([str(x).strip().lower() for x in (secuencia or []) if str(x).strip()])

    def _borrar_respuesta_actual(self):
        """Limpia la respuesta escrita y la memoria de secuencia tocada."""
        self.secuencia_alumno = []
        self.input_respuesta.clear()
        ejercicio = self.motor.ejercicio_actual or {}
        if ejercicio.get("tipo") == "midi_secuencia":
            self.txt_resultado.setText("Secuencia borrada. Vuelve a tocar desde la primera nota.")
        else:
            self.txt_resultado.setText("Respuesta borrada. Puedes intentarlo otra vez.")

    def _normalizar_respuesta_musical(self, texto: str) -> str:
        """Normaliza una respuesta musical para comparar piano virtual, MIDI y texto escrito."""
        valor = str(texto or "").strip().lower()
        if not valor:
            return ""
        valor = valor.replace("♯", "#").replace("sostenido", "#")
        valor = valor.replace(" ", "").replace("-", "").replace("_", "")
        while valor and valor[-1].isdigit():
            valor = valor[:-1]
        mapa = {
            "c": "do", "c#": "do#",
            "d": "re", "d#": "re#",
            "e": "mi",
            "f": "fa", "f#": "fa#",
            "g": "sol", "g#": "sol#",
            "a": "la", "a#": "la#",
            "b": "si",
        }
        return mapa.get(valor, valor)

    def _procesar_nota_alumno(self, nota: str, origen: str = "piano_virtual"):
        """Entrada común para piano virtual y teclado MIDI.

        En práctica da feedback sin contar fallos. En ejercicio registra el resultado
        y avanza solo si la respuesta coincide con la solución del ejercicio activo.
        v1.9.6 añade secuencias: el alumno puede tocar Do-Re-Mi y el programa
        acumula las notas, las muestra y corrige al completar la secuencia.
        """
        ejercicio = self.motor.ejercicio_actual or {}
        if not ejercicio:
            return
        tipo = ejercicio.get("tipo", "texto")

        if tipo == "midi_secuencia":
            nota_norm = self._normalizar_respuesta_musical(nota)
            esperado = self._normalizar_secuencia_musical(ejercicio.get("solucion", ""))
            if not nota_norm:
                return

            if self.fase_didactica not in {"practica", "ejercicio"} and not self.progreso.estado.modo_examen:
                self.txt_resultado.setText(
                    f"Nota detectada: {nota_norm}. Primero escucha la explicación. "
                    "Cuando quieras probar la secuencia, pulsa Practicar."
                )
                return

            # Si el alumno empieza una secuencia nueva tras pasarse de longitud, reiniciamos.
            if len(self.secuencia_alumno) >= max(1, len(esperado)):
                self.secuencia_alumno = []
            self.secuencia_alumno.append(nota_norm)
            texto_seq = self._texto_secuencia(self.secuencia_alumno)
            self.input_respuesta.setText(texto_seq)

            prefijo_correcto = esperado[:len(self.secuencia_alumno)] == self.secuencia_alumno if esperado else False
            completa = bool(esperado) and len(self.secuencia_alumno) >= len(esperado)

            if self.fase_didactica != "ejercicio" and not self.progreso.estado.modo_examen:
                if prefijo_correcto and not completa:
                    self.txt_resultado.setText(
                        f"Vas bien: {texto_seq}. Continúa con la siguiente nota de la secuencia."
                    )
                elif prefijo_correcto and completa:
                    self.audio.sonido_acierto()
                    self.txt_resultado.setText(self.profesor_didactico.practica_correcta(ejercicio, texto_seq))
                else:
                    self.audio.sonido_error()
                    self.txt_resultado.setText(
                        self.profesor_didactico.practica_incorrecta(ejercicio, texto_seq)
                        + "\n\nBorro la secuencia para que puedas empezar otra vez desde la primera nota."
                    )
                    self.secuencia_alumno = []
                    self.input_respuesta.clear()
                return

            # En evaluable esperamos a tener la longitud completa; entonces corregimos.
            if not prefijo_correcto:
                self.txt_resultado.setText(
                    f"Secuencia detectada: {texto_seq}. Parece que se ha torcido. "
                    "Puedes pulsar Borrar respuesta y repetir, o comprobar para que cuente oficialmente."
                )
                return
            if completa:
                self.comprobar_ejercicio()
            else:
                self.txt_resultado.setText(f"Secuencia detectada: {texto_seq}. Sigue tocando hasta completarla.")
            return

        if tipo != "midi_nota":
            self.txt_resultado.setText(f"Nota detectada: {nota}. Esta actividad no está esperando una nota única.")
            return

        respuesta = self._normalizar_respuesta_musical(nota)
        esperado = self._normalizar_respuesta_musical(ejercicio.get("solucion", ""))

        # En clase o ejemplo no corregimos ni marcamos fallo.
        if self.fase_didactica not in {"practica", "ejercicio"} and not self.progreso.estado.modo_examen:
            self.txt_resultado.setText(
                f"Nota detectada: {respuesta or nota}. Primero escucha la explicación. "
                "Cuando quieras probar, pulsa Practicar."
            )
            return

        if self.fase_didactica != "ejercicio" and not self.progreso.estado.modo_examen:
            correcto = bool(esperado) and respuesta == esperado
            if correcto:
                self.audio.sonido_acierto()
                self.txt_resultado.setText(self.profesor_didactico.practica_correcta(ejercicio, respuesta))
            else:
                self.audio.sonido_error()
                self.txt_resultado.setText(self.profesor_didactico.practica_incorrecta(ejercicio, respuesta))
            return

        # Fase evaluable: usa el mismo camino que el botón Comprobar para que
        # contadores, racha, examen y avance queden sincronizados.
        self.input_respuesta.setText(respuesta)
        self.comprobar_ejercicio()


    def _gestionar_respuesta_en_practica_o_ejercicio(self, respuesta: str, origen: str = "texto"):
        ejercicio = self.motor.ejercicio_actual or {}
        if not ejercicio:
            return
        if self.fase_didactica != "ejercicio":
            tipo = ejercicio.get("tipo")
            if tipo == "midi_acorde":
                esperado = set(self.reconocedor.normalizar_lista(ejercicio.get("solucion", "")))
                dado = set(self.reconocedor.normalizar_lista(respuesta))
                correcto = esperado == dado and bool(esperado)
                respuesta_visible = respuesta
            elif tipo == "midi_nota":
                esperado = self._normalizar_respuesta_musical(ejercicio.get("solucion", ""))
                dado = self._normalizar_respuesta_musical(respuesta)
                correcto = bool(esperado) and dado == esperado
                respuesta_visible = dado
            elif tipo == "midi_secuencia":
                esperado = self._normalizar_secuencia_musical(ejercicio.get("solucion", ""))
                dado = self._normalizar_secuencia_musical(respuesta)
                correcto = bool(esperado) and dado == esperado
                respuesta_visible = self._texto_secuencia(dado)
            else:
                esperado = str(ejercicio.get("solucion", "")).lower().strip()
                respuesta_norm = str(respuesta or "").lower().strip()
                correcto = respuesta_norm == esperado
                respuesta_visible = respuesta_norm
            if correcto:
                self.audio.sonido_acierto()
                self.txt_resultado.setText(self.profesor_didactico.practica_correcta(ejercicio, respuesta_visible))
            else:
                self.audio.sonido_error()
                self.txt_resultado.setText(self.profesor_didactico.practica_incorrecta(ejercicio, respuesta_visible))
            return
        # En fase ejercicio se deja que comprobar_ejercicio registre el resultado.
        self.input_respuesta.setText(respuesta)
        self.comprobar_ejercicio()


    def _texto_profesor(self, ejercicio, nivel):
        tipo = ejercicio.get("tipo")
        if tipo == "midi_nota":
            modo = "Este ejercicio puede corregirse tocando en tu teclado MIDI, o usando el piano virtual."
        elif tipo == "midi_acorde":
            modo = "Este ejercicio puede corregirse tocando el acorde en tu teclado MIDI, o escribiendo las notas."
        else:
            modo = "Puedes responder escribiendo, con calma, después de leer la teoría."
        titulo = ejercicio.get('titulo', '')
        teoria = ejercicio.get('teoria', '')
        instruccion = ejercicio.get('instruccion', '')
        return (
            f"Continuamos desde tu nivel actual: {nivel}.\n\n"
            f"PLAN DEL NIVEL:\n{self.biblioteca.resumen_nivel(nivel)}\n\n"
            f"LECCIÓN:\n{titulo}.\n\n"
            f"TEORÍA:\n{teoria}\n\n"
            f"EJERCICIO:\n{instruccion}\n\n"
            f"MODO:\n{modo}\n\n"
            "Regla: si aciertas, avanzas automáticamente. Si fallas, el profesor explica, y repites."
        )

    def _actualizar_estado(self):
        e = self.progreso.estado
        repasos = len(getattr(e, "repasos_pendientes", []) or [])
        self.lbl_estado.setText(
            f"Superados: {e.ejercicios_superados} | Fallados: {e.ejercicios_fallados} | "
            f"Racha: {e.racha} | Repasos: {repasos} | Exámenes: {e.examenes_aprobados}/{e.examenes_fallados}"
        )

    def comprobar_ejercicio(self):
        ejercicio = self.motor.ejercicio_actual
        if not ejercicio:
            return
        tipo = ejercicio.get("tipo", "texto")
        if tipo == "midi_acorde" and not self.input_respuesta.text().strip():
            respuesta = self.reconocedor.acorde_actual_texto()
        else:
            respuesta = self.input_respuesta.text()
        if self.fase_didactica != "ejercicio" and not self.progreso.estado.modo_examen:
            self._gestionar_respuesta_en_practica_o_ejercicio(respuesta, origen="texto")
            return
        if tipo == "midi_acorde":
            esperado = set(self.reconocedor.normalizar_lista(ejercicio.get("solucion", "")))
            dado = set(self.reconocedor.normalizar_lista(respuesta))
            superado = esperado == dado and bool(esperado)
            mensaje = "Correcto. Acorde reconocido." if superado else f"Acorde no superado. Esperado: {ejercicio.get('solucion', '')}. Detectado/escrito: {respuesta}"
        elif tipo == "midi_nota":
            respuesta_norm = self._normalizar_respuesta_musical(respuesta)
            solucion_norm = self._normalizar_respuesta_musical(ejercicio.get("solucion", ""))
            superado = bool(solucion_norm) and respuesta_norm == solucion_norm
            if superado:
                mensaje = f"Correcto. Has tocado {respuesta_norm}."
            else:
                mensaje = f"No está superado todavía. Has tocado o escrito: {respuesta_norm or '(nada)'}. Objetivo: {solucion_norm}."
        elif tipo == "midi_secuencia":
            respuesta_seq = self._normalizar_secuencia_musical(respuesta)
            solucion_seq = self._normalizar_secuencia_musical(ejercicio.get("solucion", ""))
            superado = bool(solucion_seq) and respuesta_seq == solucion_seq
            respuesta_txt = self._texto_secuencia(respuesta_seq) or "(nada)"
            solucion_txt = self._texto_secuencia(solucion_seq)
            if superado:
                mensaje = f"Correcto. Has tocado la secuencia {respuesta_txt}."
            else:
                mensaje = f"No está superado todavía. Has tocado o escrito: {respuesta_txt}. Objetivo: {solucion_txt}."
        else:
            superado, mensaje = self.evaluador.evaluar_respuesta_texto(respuesta, ejercicio.get("solucion", ""))
        self.progreso.registrar_resultado(ejercicio.get("id", ""), superado)
        try:
            self.historial_alumno.registrar_ejercicio(
                ejercicio_id=ejercicio.get("id", ""),
                clase_id=str(ejercicio.get("clase_id", "")),
                correcto=bool(superado),
                tipo=tipo,
                detalle={"titulo": ejercicio.get("titulo", ""), "respuesta": respuesta}
            )
        except Exception:
            pass
        if self.progreso.estado.modo_examen:
            if superado:
                self.aciertos_examen += 1
            else:
                self.fallos_examen += 1
        self._actualizar_estado()
        if self.progreso.estado.modo_examen:
            if not superado:
                # En examen directo los fallos también consumen pregunta.
                # El ejercicio queda añadido a Repaso IA, pero el examen continúa.
                self.progreso.estado.indice_ejercicio += 1
                self.progreso.guardar()
            if superado:
                self.audio.sonido_acierto()
                texto_examen = mensaje + "\n\nMODO EXAMEN: respuesta registrada como correcta. Pasamos a la siguiente pregunta."
                self._poner_texto_profesor("Respuesta correcta registrada. Continúo con la siguiente pregunta del examen.", hablar=True)
            else:
                self.audio.sonido_error()
                texto_examen = (
                    mensaje
                    + "\n\nMODO EXAMEN: respuesta registrada como fallo. "
                    + "La guardo para Repaso IA y pasamos a la siguiente pregunta."
                )
                self._poner_texto_profesor(
                    "Respuesta registrada como fallo. No te detengo en mitad del examen; este punto queda para repaso inteligente.",
                    hablar=True
                )
            self.txt_resultado.setText(texto_examen)
            QTimer.singleShot(900, self._avanzar_tras_acierto)
            return

        if superado:
            self.audio.sonido_acierto()
            extra = self.profesor_ia.explicar_acierto(ejercicio)
            self.txt_resultado.setText(mensaje + "\n\n" + extra + "\n\nSuena confirmación agradable y avanzamos.")
            try:
                self._poner_texto_profesor("Correcto. Has superado el ejercicio. Avanzamos al siguiente paso.", hablar=True)
            except Exception:
                pass
            try:
                self._celebrar_logro("reto", ejercicio.get("titulo", "Ejercicio superado"))
            except Exception:
                pass
            QTimer.singleShot(900, self._avanzar_tras_acierto)
        else:
            self.audio.sonido_error()
            self.fase_didactica = "practica"
            self.ejercicio_desbloqueado = False
            self.lbl_fase_clase.setText("Reexplicación — el profesor corrige antes de repetir")
            self._poner_texto_profesor(self.profesor_didactico.fallo_guiado(ejercicio, respuesta), hablar=True)
            self.input_respuesta.setEnabled(True)
            self.btn_comprobar.setEnabled(True)
            pendientes = len(getattr(self.progreso.estado, "repasos_pendientes", []) or [])
            self.txt_resultado.setText(
                mensaje
                + "\n\nSuena aviso de error. No avanzas todavía; vuelves a práctica guiada."
                + f"\nEste punto queda en Repaso IA. Repasos pendientes: {pendientes}."
            )

    def _avanzar_tras_acierto(self):
        if self.progreso.estado.modo_examen and self.examen_actual:
            if self.progreso.estado.indice_ejercicio >= len(self.examen_actual.get("ejercicios", [])):
                minimo = int(self.examen_actual.get("minimo_aprobado", 0))
                aprobado = self.aciertos_examen >= minimo
                self.progreso.finalizar_examen(aprobado)
                self.audio.sonido_acierto() if aprobado else self.audio.sonido_error()
                self.txt_resultado.setText(
                    f"Examen terminado. Aciertos: {self.aciertos_examen}. Fallos: {self.fallos_examen}.\n"
                    f"Resultado: {'APROBADO' if aprobado else 'A REPASAR'}."
                )
                return
            self._cargar_examen_actual()
        else:
            self._cargar_estudio(self.progreso.estado.nivel_actual)

    def iniciar_examen_nivel(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            QMessageBox.information(self, "Sin nivel", "Haz la evaluación o elige un nivel manualmente.")
            return
        examen = self.biblioteca.examen_de_nivel(nivel)
        if not examen:
            QMessageBox.information(self, "Sin examen", "Aún no hay examen preparado para este nivel.")
            return
        self.examen_actual = examen
        self.aciertos_examen = 0
        self.fallos_examen = 0
        self.progreso.iniciar_examen()
        self._cargar_examen_actual()

    def _cargar_examen_actual(self):
        ejercicio, indice, total = self.motor.cargar_examen(self.examen_actual.get("ejercicios", []), self.progreso.estado.indice_ejercicio)
        self.fase_didactica = "ejercicio"
        self.ejercicio_desbloqueado = True
        self.secuencia_alumno = []
        self.lbl_fase_clase.setText("MODO EXAMEN — evaluación directa")
        self.input_respuesta.setEnabled(True)
        self.btn_comprobar.setEnabled(True)
        self.lbl_nivel.setText(f"EXAMEN: {self.examen_actual.get('titulo')} | Nivel: {self.progreso.estado.nivel_actual}")
        self._actualizar_estado()
        self.lbl_ejercicio.setText(f"{ejercicio.get('titulo','Sin ejercicio')}  ({indice+1}/{max(1,total)})")
        self.lbl_objetivo.setText(f"Objetivo: {ejercicio.get('objetivo','')}")
        self.barra_progreso.setValue(self.motor.progreso_nivel_porcentaje(indice))
        self._poner_texto_profesor(self._texto_profesor(ejercicio, self.progreso.estado.nivel_actual) + "\n\nMODO EXAMEN: aquí no hay fase de clase; el examen comprueba si el bloque está superado.", hablar=True)
        self.txt_resultado.clear()
        self.input_respuesta.clear()
        self.input_respuesta.setFocus()
        self.stack.setCurrentWidget(self.pantalla_estudio)
        self._mostrar_panel_clase_practica()


    def _titulo_ejercicio_por_id(self, ejercicio_id: str) -> str:
        try:
            ejercicio = self.repaso_ia.ejercicio_por_id(ejercicio_id)
            if ejercicio:
                return ejercicio.get("titulo", ejercicio_id)
        except Exception:
            pass
        return ejercicio_id or "ejercicio"

    def _resumen_estado_alumno(self) -> dict:
        estado = self.progreso.estado
        stats = self.progreso.estadisticas()
        nivel = estado.nivel_actual if estado.nivel_actual != "sin_evaluar" else "inicial"

        fallos = []
        try:
            mapa = getattr(estado, "mapa_fallos", {}) or {}
            for eid, total in sorted(mapa.items(), key=lambda kv: int(kv[1]), reverse=True)[:6]:
                fallos.append({
                    "id": eid,
                    "titulo": self._titulo_ejercicio_por_id(eid),
                    "fallos": int(total),
                })
        except Exception:
            fallos = []

        try:
            total_lecciones = len(self.pantalla_inicio.lecciones_guiadas.lecciones())
            superadas = len(set(self.pantalla_inicio.lecciones_guiadas.progreso.get("lecciones_superadas", [])))
            lecciones_guiadas = f"{superadas}/{total_lecciones}"
        except Exception:
            lecciones_guiadas = "0/0"

        pendientes = len(getattr(estado, "repasos_pendientes", []) or [])
        if pendientes:
            recomendacion = "Pulsa Iniciar Repaso IA. Vamos a repasar primero los fallos más recientes y después los más repetidos."
        elif stats.get("tasa", 0) >= 80:
            recomendacion = "Puedes continuar con el siguiente bloque, manteniendo repasos cortos para no perder precisión."
        else:
            recomendacion = "Conviene repetir ejercicios básicos antes de subir la dificultad."

        return {
            "nivel_actual": nivel,
            "ejercicios_superados": int(getattr(estado, "ejercicios_superados", 0) or 0),
            "ejercicios_fallados": int(getattr(estado, "ejercicios_fallados", 0) or 0),
            "tasa_acierto": int(stats.get("tasa", 0) or 0),
            "racha": int(getattr(estado, "racha", 0) or 0),
            "repasos_pendientes": pendientes,
            "lecciones_guiadas": lecciones_guiadas,
            "examenes_aprobados": int(getattr(estado, "examenes_aprobados", 0) or 0),
            "fallos_frecuentes": fallos,
            "recomendacion": recomendacion,
        }


    def _partitura_figura_a_pulsos(self, figura: str) -> float:
        figura = str(figura or "negra").strip().lower().replace(" ", "_")
        mapa = {
            "corchea": 0.5,
            "negra": 1.0,
            "silencio": 1.0,
            "silencio_negra": 1.0,
            "blanca": 2.0,
            "silencio_blanca": 2.0,
            "redonda": 4.0,
            "silencio_redonda": 4.0,
        }
        return float(mapa.get(figura, 1.0))

    def _partitura_ejercicio_actual(self, panel=None) -> dict:
        try:
            if panel is not None:
                sig = getattr(panel, "resumen", {}).get("siguiente", {}) or {}
                if sig:
                    return dict(sig)
        except Exception:
            pass
        nivel = getattr(self.progreso.estado, "nivel_actual", "inicial")
        if nivel == "sin_evaluar":
            nivel = "inicial"
        try:
            return dict(self.lectura_partitura.siguiente_ejercicio(nivel) or {})
        except Exception:
            return {}

    def _partitura_construir_pieza_didactica(self, ejercicio: dict):
        ejercicio = dict(ejercicio or {})
        practica = list(ejercicio.get("practica_notas", []) or [])
        if not practica:
            # Respaldo para ejercicios antiguos: convierte notas simples en negras.
            for i, nota in enumerate(ejercicio.get("notas", []) or []):
                if str(nota).lower().startswith("silencio"):
                    practica.append({"silencio": True, "figura": "negra", "nombre": "silencio"})
                else:
                    practica.append({"nota": str(nota), "figura": "negra", "mano": "derecha", "dedo": str(i + 1)})
        tempo = max(30, min(220, int(ejercicio.get("tempo", 60) or 60)))
        compas = str(ejercicio.get("compas", "4/4") or "4/4")
        try:
            compas_num, compas_den = [int(x) for x in compas.split("/", 1)]
        except Exception:
            compas_num, compas_den = 4, 4
        beat_ms = 60000.0 / max(1, tempo)
        notas = []
        tiempo_ms = 0.0
        for item in practica:
            if not isinstance(item, dict):
                item = {"nota": str(item), "figura": "negra"}
            pulsos = self._partitura_figura_a_pulsos(item.get("figura", "negra"))
            dur_ms = max(80, int(round(beat_ms * pulsos)))
            if item.get("silencio") or not item.get("nota"):
                tiempo_ms += dur_ms
                continue
            info = normalizar_nota(item.get("nota"))
            midi = info.get("midi")
            if midi is None:
                # Si en los datos se escribió Do/Re/Mi sin octava, usamos C4 como entorno inicial.
                info = normalizar_nota(str(item.get("nota", "C4")) + "4")
                midi = info.get("midi")
            if midi is None:
                tiempo_ms += dur_ms
                continue
            pulso = int((tiempo_ms // max(1, beat_ms)) % max(1, compas_num)) + 1
            comp = int((tiempo_ms // max(1, beat_ms * compas_num))) + 1
            notas.append(NotaMidiDidactica(
                nota=info.get("nota") or str(item.get("nota")),
                midi=int(midi),
                inicio_ms=int(round(tiempo_ms)),
                duracion_ms=dur_ms,
                velocity=int(item.get("velocity", 88) or 88),
                canal=0,
                pulso=pulso,
                compas=comp,
                mano=str(item.get("mano") or ("izquierda" if int(midi) < 60 else "derecha")),
            ))
            tiempo_ms += dur_ms
        duracion_ms = int(round(max(tiempo_ms, (notas[-1].fin_ms() if notas else beat_ms))))
        return PiezaMidiDidactica(
            id=str(ejercicio.get("id") or "partitura_practica"),
            titulo=str(ejercicio.get("titulo") or "Práctica de partitura"),
            midi_path="generado_desde_partitura",
            tempo=tempo,
            compas=compas,
            notas=notas,
            duracion_ms=duracion_ms,
            ppq=480,
        )

    def _partitura_iniciar_practica_guiada(self, panel=None):
        ejercicio = self._partitura_ejercicio_actual(panel)
        if not ejercicio:
            texto = "No hay ejercicio de partitura disponible para practicar."
            self._actualizar_dialogo_avatar(texto)
            return self._hablar_con_avatar(texto)
        pieza = self._partitura_construir_pieza_didactica(ejercicio)
        if not pieza.notas:
            texto = (
                f"Esta lección de partitura es teórica: {ejercicio.get('titulo', '')}. "
                "Primero marca la clase como completada y avanza al siguiente ejercicio práctico."
            )
            self._actualizar_dialogo_avatar(texto)
            return self._hablar_con_avatar(texto)
        self.midi_didactico.pieza = pieza
        self._midi_didactico_modo = "practica"
        self._midi_didactico_tiempo_ms = 0
        self._midi_didactico_notas_sonando = set()
        self._midi_didactico_compas_anunciado = 0
        self._midi_practica_indice = 0
        self._midi_practica_tolerancia_ms = 900
        self._midi_practica_ultimo_beat_ts = time.monotonic()
        self._midi_practica_velocity_objetivo = int((pieza.notas or [None])[0].velocity) if (pieza.notas or []) else 80
        try:
            self.reloj_musical.configurar(pieza.tempo, pieza.compas, pieza.duracion_ms)
            self.reloj_musical.play()
            self.timer_midi_didactico.start()
        except Exception:
            pass
        try:
            self._midi_didactico_preparar_pentagrama_vivo(pieza)
            self._midi_practica_actualizar_objetivo()
        except Exception:
            pass
        texto = (
            f"Práctica guiada de Partitura: {pieza.titulo}. "
            "Voy a corregirte nota por nota. Mira primero el símbolo, di el nombre de la nota, cuenta el pulso y toca en el piano global. "
            "Si tocas otra nota, si confundes una alteración o si entras demasiado fuera del pulso, el profesor te lo dirá y no avanzará hasta que lo corrijas."
        )
        try:
            if hasattr(panel, "txt_profesor"):
                panel.txt_profesor.setPlainText(texto + "\n\n" + panel.texto_para_profesor())
        except Exception:
            pass
        try:
            self.piano.resaltar_notas_docente([pieza.notas[0].nota])
        except Exception:
            pass
        self._actualizar_dialogo_avatar(texto)
        return self._hablar_con_avatar(texto)



    def mostrar_lectura_partitura(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            nivel = "inicial"
        datos = self.lectura_partitura.cargar_datos()
        resumen = self.lectura_partitura.resumen(nivel)
        dlg = DialogoLecturaPartitura(
            datos,
            resumen,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_marcar)
        dlg.btn_marcar.clicked.connect(
            lambda: (
                self.lectura_partitura.marcar_completado(
                    ((self.lectura_partitura.resumen(nivel).get("siguiente", {}) or {}).get("id", "")),
                    nivel,
                ),
                self.mostrar_lectura_partitura(),
                self._celebrar_logro("reto", "Lectura de partitura completada"),
            )
        )
        self._desconectar_boton(dlg.btn_practica)
        dlg.btn_practica.clicked.connect(lambda _checked=False, dlg=dlg: self._partitura_iniciar_practica_guiada(dlg))
        self._desconectar_boton(dlg.btn_repertorio)
        dlg.btn_repertorio.clicked.connect(self.mostrar_repertorio)
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.lectura_partitura.reiniciar(), self.mostrar_lectura_partitura()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "partitura", self._texto_panel_integrado(dlg))
        # La pantalla de Partitura debe abrir mostrando ya la pizarra/pentagrama.
        # Antes se veía primero un texto grande y la pizarra solo aparecía al pulsar
        # "Leer punto actual", dejando la interfaz como una lista comprimida.
        try:
            puntos = getattr(dlg, "_lectura_puntos", []) or []
            if puntos:
                self._mostrar_pizarra_musical_para_punto(dlg, puntos[0], 0, len(puntos))
        except Exception:
            pass

    def mostrar_pulso_ritmo(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            nivel = "inicial"
        datos = self.pulso_ritmo.cargar_datos()
        resumen = self.pulso_ritmo.resumen(nivel)
        dlg = DialogoPulsoRitmo(
            datos,
            resumen,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_marcar)
        dlg.btn_marcar.clicked.connect(lambda: (self.pulso_ritmo.marcar_completado(((self.pulso_ritmo.resumen(nivel).get("siguiente", {}) or {}).get("id", "")), nivel), self.mostrar_pulso_ritmo(), self._celebrar_logro("reto", "Pulso completado")))
        self._desconectar_boton(dlg.btn_practica)
        dlg.btn_practica.clicked.connect(self.mostrar_pulso_practica)
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.pulso_ritmo.reiniciar(), self.mostrar_pulso_ritmo()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "pulso", self._texto_panel_integrado(dlg))

    def mostrar_pulso_practica(self):
        """Abre la práctica real de la pestaña Pulso.

        La teoría de Pulso queda en DialogoPulsoRitmo; este panel es el
        entrenamiento práctico: metrónomo, patrones, corrección de tiempo,
        nota, silencios y feedback del profesor.
        """
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            nivel = "inicial"
        datos = self.pulso_ritmo.cargar_datos()
        resumen = self.pulso_ritmo.resumen(nivel)
        dlg = DialogoPulsoPractica(
            datos,
            resumen,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._pulso_practica_panel = dlg
        self._preparar_dialogo_como_panel(dlg, "pulso_practica", self._texto_panel_integrado(dlg))

    def _procesar_pulso_practica_entrada(self, nota: str, velocidad: int = 96, canal=None, origen: str = "piano_virtual") -> bool:
        panel = getattr(self, "_pulso_practica_panel", None)
        if panel is None or not hasattr(panel, "procesar_nota"):
            return False
        try:
            actual = self.area_contenido_estudio.currentWidget() if hasattr(self, "area_contenido_estudio") else None
            if actual is not panel:
                return False
        except Exception:
            pass
        try:
            return bool(panel.procesar_nota(nota, velocidad, canal, origen))
        except RuntimeError:
            self._pulso_practica_panel = None
            return False
        except Exception as exc:
            try:
                self.txt_resultado.setText(f"Error en práctica de pulso: {exc}")
            except Exception:
                pass
            return True

    def mostrar_repertorio(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            nivel = "inicial"
        datos = self.repertorio.cargar_datos()
        resumen = self.repertorio.resumen(nivel)
        dlg = DialogoRepertorio(
            datos,
            resumen,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_marcar)
        dlg.btn_marcar.clicked.connect(lambda: (self.repertorio.marcar_trabajada(((self.repertorio.resumen(nivel).get("siguiente", {}) or {}).get("id", ""))), self.mostrar_repertorio(), self._celebrar_logro("reto", "Pieza trabajada")))
        self._desconectar_boton(dlg.btn_practica)
        dlg.btn_practica.clicked.connect(self._mostrar_panel_clase_practica)
        self._desconectar_boton(dlg.btn_plan)
        dlg.btn_plan.clicked.connect(self.mostrar_plan_personalizado)
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.repertorio.reiniciar(), self.mostrar_repertorio()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "repertorio", self._texto_panel_integrado(dlg))
    def _crear_sesion_diaria_actual(self):
        nivel = self.progreso.estado.nivel_actual
        if nivel == "sin_evaluar":
            nivel = "inicial"
        try:
            plan = self.plan_personalizado.plan_o_generar()
        except Exception:
            plan = {}
        try:
            tecnica = self.tecnica_diaria.resumen()
        except Exception:
            tecnica = {}
        repasos = len(getattr(self.progreso.estado, "repasos_pendientes", []) or [])
        return self.sesion_diaria.crear_sesion(nivel, plan, tecnica, repasos)


    def mostrar_sesion_diaria(self):
        sesion = self._crear_sesion_diaria_actual()
        dlg = DialogoSesionDiaria(
            sesion,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )

        def abrir_paso():
            paso = sesion.get("siguiente", {}) or {}
            tipo = paso.get("tipo", "")
            if tipo == "tecnica":
                self.mostrar_tecnica_diaria()
            elif tipo == "pulso":
                self.mostrar_pulso_ritmo()
            elif tipo == "teoria":
                self._abrir_teoria_desde_panel()
            elif tipo == "partitura":
                self.mostrar_lectura_partitura()
            elif tipo == "repaso":
                self._mostrar_panel_clase_practica()
                self.iniciar_repaso_inteligente()
            elif tipo == "repertorio":
                self.mostrar_repertorio()
            elif tipo == "practica":
                self._mostrar_panel_clase_practica()
            elif tipo == "cierre":
                texto = f"{self._nombre_alumno()}, cierre de sesión: revisa lo que has completado, guarda el plan y descansa."
                self._actualizar_dialogo_avatar(texto)
                self._hablar_con_avatar(texto)
            else:
                texto = f"{self._nombre_alumno()}, preparación inicial: siéntate bien, relaja hombros, coloca manos y escucha antes de tocar."
                self._actualizar_dialogo_avatar(texto)
                self._hablar_con_avatar(texto)

        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_abrir)
        dlg.btn_abrir.clicked.connect(abrir_paso)
        self._desconectar_boton(dlg.btn_completar)
        dlg.btn_completar.clicked.connect(lambda: (self.sesion_diaria.marcar_siguiente_completado(sesion), self.mostrar_sesion_diaria(), self._celebrar_logro("reto", "Paso de sesión completado")))
        self._desconectar_boton(dlg.btn_plan)
        dlg.btn_plan.clicked.connect(self.mostrar_plan_personalizado)
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.sesion_diaria.reiniciar_sesion(), self.mostrar_sesion_diaria()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "sesion", self._texto_panel_integrado(dlg))
    def mostrar_tecnica_diaria(self):
        datos = self.tecnica_diaria.cargar_datos()
        resumen = self.tecnica_diaria.resumen()
        dlg = DialogoTecnicaDiaria(
            datos,
            resumen,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_completar)
        dlg.btn_completar.clicked.connect(lambda: (self.tecnica_diaria.marcar_completada((self.tecnica_diaria.resumen().get("siguiente", {}) or {}).get("id", "")), self.mostrar_tecnica_diaria(), self._celebrar_logro("reto", "Técnica diaria completada")))
        self._desconectar_boton(dlg.btn_practica)
        dlg.btn_practica.clicked.connect(self._mostrar_panel_clase_practica)
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.tecnica_diaria.reiniciar(), self.mostrar_tecnica_diaria()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "tecnica", self._texto_panel_integrado(dlg))
    def mostrar_ruta_curso(self):
        try:
            plan = self.plan_personalizado.plan_o_generar()
        except Exception:
            plan = {}
        try:
            estado = self.ruta_curso.estado_ruta(
                self.progreso.estado,
                plan,
                nivel0_superado=self._nivel0_teoria_superado(),
            )
        except Exception:
            estado = {"niveles": [], "siguiente": {}, "titulo": "Ruta curricular", "descripcion": ""}
        dlg = DialogoRutaCurso(
            estado,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_teoria)
        dlg.btn_teoria.clicked.connect(self._abrir_teoria_desde_panel)
        self._desconectar_boton(dlg.btn_continuar)
        dlg.btn_continuar.clicked.connect(self._continuar_ruta_desde_panel)
        self._desconectar_boton(dlg.btn_plan)
        dlg.btn_plan.clicked.connect(self.mostrar_plan_personalizado)
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "ruta_curso", self._texto_panel_integrado(dlg))
    def mostrar_plan_personalizado(self):
        try:
            plan = self.plan_personalizado.plan_o_generar()
        except Exception:
            plan = {}
        if not plan:
            QMessageBox.information(
                self,
                "Plan personalizado",
                "Aún no hay plan personalizado. Haz primero la evaluación inicial interactiva."
            )
            return
        dlg = DialogoPlanPersonalizado(
            plan,
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_completar)
        dlg.btn_completar.clicked.connect(lambda: (self.plan_personalizado.marcar_siguiente_completado(), self.mostrar_plan_personalizado(), self._celebrar_logro("reto", "Paso del plan completado")))
        self._desconectar_boton(dlg.btn_reiniciar)
        dlg.btn_reiniciar.clicked.connect(lambda: (self.plan_personalizado.reiniciar_seguimiento(), self.mostrar_plan_personalizado()))
        self._desconectar_boton(dlg.btn_teoria)
        dlg.btn_teoria.clicked.connect(self._abrir_teoria_desde_panel)
        self._desconectar_boton(dlg.btn_practica)
        dlg.btn_practica.clicked.connect(self._mostrar_panel_clase_practica)
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "plan_alumno", self._texto_panel_integrado(dlg))
    def mostrar_estado_alumno(self):
        nivel = self.progreso.estado.nivel_actual if self.progreso.estado.nivel_actual != "sin_evaluar" else "inicial"
        resumen = self._resumen_estado_alumno()
        plan_repaso = self.repaso_ia.plan_texto(self.progreso.estado, nivel)
        dlg = DialogoEstadoAlumno(
            self._nombre_alumno(),
            getattr(self.perfil_alumno, "tratamiento", "masculino"),
            getattr(self.ajustes.ajustes, "avatar_tipo", "chica"),
            resumen,
            plan_repaso,
            self,
        )
        self._desconectar_boton(dlg.btn_leer)
        dlg.btn_leer.clicked.connect(lambda dlg=dlg: self._leer_panel_integrado(dlg))
        self._desconectar_boton(dlg.btn_repaso)
        dlg.btn_repaso.clicked.connect(lambda: (self._mostrar_panel_clase_practica(), self.iniciar_repaso_inteligente()))
        self._desconectar_boton(dlg.btn_cerrar)
        dlg.btn_cerrar.clicked.connect(self._mostrar_panel_clase_practica)
        self._preparar_dialogo_como_panel(dlg, "estado_alumno", self._texto_panel_integrado(dlg))
    def mostrar_plan_completo(self):
        nivel = self.progreso.estado.nivel_actual if self.progreso.estado.nivel_actual != "sin_evaluar" else "inicial"
        stats = self.progreso.estadisticas()
        plan_repaso = self.repaso_ia.plan_texto(self.progreso.estado, nivel)
        QMessageBox.information(
            self,
            "Plan completo del profesor",
            f"Nivel actual: {nivel}\n"
            f"Tasa de acierto: {stats['tasa']}%\n"
            f"Racha: {stats['racha']}\n"
            f"Repasos pendientes: {stats.get('repasos_pendientes', 0)}\n"
            f"Exámenes aprobados: {stats['examenes_aprobados']}\n\n"
            f"Lecciones del nivel:\n{self.biblioteca.resumen_nivel(nivel)}\n\n"
            f"{plan_repaso}"
        )


    def _abrir_teoria_desde_panel(self):
        try:
            self.stack.setCurrentWidget(self.pantalla_inicio)
            self.pantalla_inicio.mostrar_teoria()
            texto = f"{self._nombre_alumno()}, abrimos teoría desde el panel integrado."
            self._actualizar_dialogo_avatar(texto)
            self._hablar_con_avatar(texto)
        except Exception:
            self.volver_al_inicio()

    def _continuar_ruta_desde_panel(self):
        try:
            plan = self.plan_personalizado.plan_o_generar()
        except Exception:
            plan = {}
        try:
            estado = self.ruta_curso.estado_ruta(
                self.progreso.estado,
                plan,
                nivel0_superado=self._nivel0_teoria_superado(),
            )
        except Exception:
            estado = {}
        nivel = self.ruta_curso.nivel_para_continuar(estado)
        self.progreso.establecer_nivel(nivel, "ruta_curso", reiniciar_indice=False)
        self._cargar_estudio(nivel)

    def mostrar_pista(self):
        ejercicio = self.motor.ejercicio_actual or {}
        self.txt_resultado.setText("Pista: " + ejercicio.get("pista", "No hay pista para este ejercicio."))

    def siguiente_forzado(self):
        self.progreso.estado.indice_ejercicio += 1
        self.progreso.guardar()
        self._cargar_estudio(self.progreso.estado.nivel_actual)

    def repasar_anterior(self):
        self.progreso.retroceder_para_repaso()
        self._cargar_estudio(self.progreso.estado.nivel_actual)

    def iniciar_repaso_inteligente(self):
        nivel = self.progreso.estado.nivel_actual if self.progreso.estado.nivel_actual != "sin_evaluar" else "inicial"
        ejercicio, motivo = self.repaso_ia.seleccionar(self.progreso.estado, nivel)
        if not ejercicio:
            QMessageBox.information(self, "Repaso inteligente", "No hay ejercicios disponibles para repasar todavía.")
            return
        nivel_objetivo = ejercicio.get("nivel", nivel)
        indice = self.repaso_ia.indice_en_nivel(ejercicio)
        self.progreso.establecer_nivel(nivel_objetivo, "repaso_inteligente", reiniciar_indice=False)
        self.progreso.estado.indice_ejercicio = indice
        self.progreso.guardar()
        self._cargar_estudio(nivel_objetivo)
        mensaje = (
            f"REPASO INTELIGENTE ACTIVADO\n\n"
            f"Vamos a repasar: {ejercicio.get('titulo', 'este ejercicio')}.\n"
            f"Motivo: {motivo}.\n\n"
            "No es un castigo: es entrenamiento dirigido. Primero te lo explico otra vez, después vemos un ejemplo, "
            "luego practicas sin penalización y al final haces el ejercicio evaluable."
        )
        self.txt_resultado.setText("Repaso inteligente cargado. Sigue el orden: Clase → Ver ejemplo → Practicar → Hacer ejercicio.")
        self._poner_texto_profesor(mensaje, hablar=True)

    def _nota_on(self, nota: str):
        if not hasattr(self, "_notas_piano_virtual_activas"):
            self._notas_piano_virtual_activas = set()
        if nota in self._notas_piano_virtual_activas:
            return
        self._notas_piano_virtual_activas.add(nota)
        self._audio_y_midi_note_on(nota, velocity=96, canal=1)
        self._ultima_entrada_alumno = {
            "origen": "piano_virtual",
            "velocity": 64,
            "canal": None,
            "nota": nota,
            "ts": time.monotonic(),
        }
        diag_pro = self._diagnostico_pro_desde_entrada(nota, velocity=64, canal=None, origen="piano_virtual")
        if diag_pro is not None:
            self._evaluar_necesidad_entradas_pro(diag_pro)

        # La práctica MIDI didáctica y la práctica de Partitura usan el piano global.
        # Deben corregirse antes que los retos genéricos de pizarra.
        if self._procesar_midi_didactico_practica_entrada(nota, 96, 1):
            return

        # La práctica de Pulso usa el piano global y debe corregir nota + tiempo
        # antes que los retos genéricos de pizarra.
        if self._procesar_pulso_practica_entrada(nota, 96, None, origen="piano_virtual"):
            return

        # Si la pizarra ha lanzado un reto con pulso, secuencia o nota, se comprueba aquí.
        if self._procesar_pulso_pizarra_nota(nota):
            return

        if self._procesar_secuencia_pizarra_nota(nota):
            return

        if self._procesar_reto_pizarra_nota(nota):
            return

        ejercicio = self.motor.ejercicio_actual or {}
        tipo = ejercicio.get("tipo")
        if tipo in {"midi_nota", "midi_secuencia"}:
            self._procesar_nota_alumno(nota, origen="piano_virtual")
        else:
            self.txt_resultado.setText(f"Nota pulsada: {nota}\nSonido activo. Ajusta preset, brillo, sustain, reverb y delay para más presencia.")

    def _nota_off(self, nota: str):
        if not hasattr(self, "_notas_piano_virtual_activas"):
            self._notas_piano_virtual_activas = set()
        nota_estaba_activa = nota in self._notas_piano_virtual_activas
        if nota_estaba_activa:
            self._notas_piano_virtual_activas.discard(nota)
        try:
            duracion_ms = self.analizador_midi_pro.note_off(nota)
            if duracion_ms is not None:
                self._registrar_historial_midi(
                    nota=nota,
                    origen="piano_virtual",
                    tipo="duracion",
                    mensaje=f"Duración de nota: {duracion_ms} ms",
                    contexto={"duracion_ms": duracion_ms}
                )
                if hasattr(self, "lbl_diag_docente"):
                    self.lbl_diag_docente.setText(f"Corrección docente: duración de {nota}: {duracion_ms} ms.")
        except Exception:
            pass
        # En el piano virtual, soltar una tecla debe ser SILENCIO inmediato.
        # Si la nota no estaba activa, ignoramos el release para evitar dobles
        # eventos de Qt al arrastrar/salir del teclado.
        if not nota_estaba_activa:
            return
        try:
            if hasattr(self.audio, "cortar_nota"):
                self.audio.cortar_nota(nota, limpiar_cola=True)
            else:
                self.audio.note_off(nota, release_segundos=0.0)
        except TypeError:
            try:
                self.audio.note_off(nota)
            except Exception:
                pass
        except Exception:
            pass
        self._midi_enviar_note_off_seguro(nota, velocity=0, canal=1)

    def closeEvent(self, event):
        # Cierre limpio v4.1.6:
        # primero paramos temporizadores y entradas; después audio.
        try:
            self._midi_didactico_parar()
        except Exception:
            pass
        try:
            self.timer_midi_didactico.stop()
        except Exception:
            pass
        try:
            self.timer_audio_entrada.stop()
        except Exception:
            pass
        try:
            self.audio_entrada.detener()
        except Exception:
            pass
        try:
            self.voz_avatar.detener()
        except Exception:
            pass
        try:
            self.timer_camara.stop()
        except Exception:
            pass
        try:
            self._pulso_pizarra_timer.stop()
        except Exception:
            pass
        try:
            self.midi.cerrar()
        except Exception:
            pass
        try:
            self.camera.cerrar()
        except Exception:
            pass
        try:
            self.audio.parar()
        except Exception:
            pass
        event.accept()

    def _aplicar_estilo(self):
        self.setStyleSheet("""
            QWidget { font-size: 14px; }
            QPushButton { padding: 7px 12px; border-radius: 5px; min-height: 28px; }
            QGroupBox { font-weight: bold; border: 1px solid #777; border-radius: 6px; margin-top: 10px; padding: 8px; }
            QTextEdit, QLineEdit, QComboBox, QSpinBox { border: 1px solid #888; border-radius: 4px; padding: 5px; }
            #TituloEjercicio { font-size: 20px; font-weight: bold; }
            #FaseClase { font-size: 15px; font-weight: bold; padding: 5px; background: #e7eef8; border: 1px solid #8aa1c2; border-radius: 5px; }
            #MarcoPianoVisible { background: #eef4fb; border: 1px solid #8aa1c2; border-radius: 8px; }
            #TituloPianoInteractivo { font-size: 14px; font-weight: bold; color: #1f2937; }
            #PianoVirtual88Real { background: #dbeafe; border: 1px solid #64748b; }
            #TransporteNarradorCompacto { background: transparent; }
            #TituloGrande { font-size: 26px; font-weight: bold; }
            QProgressBar { border: 1px solid #64748b; border-radius: 5px; text-align: center; background: #e2e8f0; }
            QProgressBar::chunk { background: #38bdf8; border-radius: 4px; }
            #TransporteNarradorCompacto QProgressBar { border-radius: 3px; max-height: 8px; min-height: 8px; text-align: center; }
            #TransporteNarradorCompacto QProgressBar::chunk { background: #0EA5E9; border-radius: 3px; }
            #PanelAvatarGlobal { background: #f8fafc; border: 1px solid #94a3b8; border-radius: 12px; }
            #CabeceraEstudioCompacta { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; }
            #MarcoEvaluacionInicial { background: #ffffff; border: 1px solid #CBD5E1; border-radius: 10px; }
            #TituloPreguntaEvaluacion { font-size: 18px; font-weight: bold; color: #0f3768; }
            #PreguntaEvaluacionInicial { font-size: 18px; font-weight: bold; color: #0f172a; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; }
            #FeedbackEvaluacionInicial { background: #ffffff; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 14px; }
            #TextoPreguntasEvaluacion { background: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 15px; }
            #TituloAvatarGlobal { font-size: 18px; font-weight: bold; color: #0f172a; }
            #AvatarAvisoGlobal { color: #475569; background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; }
            #InicioCabecera { background: #eef6ff; border: 1px solid #93c5fd; border-radius: 14px; }
            #TituloPrincipalInicio { font-size: 30px; font-weight: bold; color: #0f3768; }
            #SubtituloPrincipalInicio { color: #334155; }
            QPushButton#BotonInicioNav { background: #e2e8f0; border: 1px solid #94a3b8; color: #0f172a; border-radius: 8px; font-weight: bold; }
            QPushButton#BotonInicioNav:hover { background: #bfdbfe; border: 1px solid #2563eb; }
            #HeroInicio { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 14px; }
            #TextoHeroInicio { font-size: 18px; color: #1e293b; }
            #TarjetaInicio, #TarjetaImagenTeoria { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; }
            #TituloTarjetaInicio, #TituloSeccionInicio { font-size: 20px; font-weight: bold; color: #0f3768; }
            #TextoTarjetaInicio, #TextoSeccionInicio { color: #1e293b; }
            #NombreImagenTeoria { color: #334155; font-weight: bold; }
            #DescripcionImagenTeoria { color: #334155; font-size: 12px; }
            #PistaImagenTeoria { color: #2563eb; font-size: 11px; font-weight: bold; }
        """)
