from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QCheckBox, QComboBox, QSlider, QSpinBox, QGroupBox,
    QDialogButtonBox, QMessageBox, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from app.vision.camera_manager import CameraManager
from app.voice.voz_avatar import VozAvatar

class DialogoConfiguracion(QDialog):
    """Panel único de configuración para mantener limpia la pantalla principal."""
    def __init__(self, ventana, parent=None):
        super().__init__(parent)
        self.ventana = ventana
        self.ajustes = ventana.ajustes.ajustes
        self.setWindowTitle("Configuración del profesor")
        self.resize(920, 620)
        self.camera_preview = CameraManager()
        self.timer_camara = QTimer(self)
        self.timer_camara.setInterval(33)
        self.timer_camara.timeout.connect(self._actualizar_preview_camara)

        layout = QVBoxLayout(self)
        titulo = QLabel("Configuración general")
        titulo.setObjectName("TituloConfig")
        layout.addWidget(titulo)

        self.botones_config = []
        barra_botones = QHBoxLayout()
        barra_botones.setSpacing(8)
        self.stack_config = QStackedWidget()
        secciones = [
            ("Audio", "#2563EB", self._tab_audio()),
            ("MIDI", "#16A34A", self._tab_midi()),
            ("Cámara", "#F59E0B", self._tab_camara()),
            ("Avatar y voz", "#7C3AED", self._tab_avatar()),
            ("Interfaz", "#0EA5E9", self._tab_interfaz()),
            ("Profesor", "#14B8A6", self._tab_progreso()),
        ]
        for indice, (nombre, color, widget) in enumerate(secciones):
            btn = self._crear_boton_seccion(nombre, color)
            btn.clicked.connect(lambda _checked=False, i=indice: self._mostrar_seccion(i))
            barra_botones.addWidget(btn)
            self.botones_config.append(btn)
            self.stack_config.addWidget(widget)
        layout.addLayout(barra_botones)
        layout.addWidget(self.stack_config, 1)
        self._mostrar_seccion(0)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Save).setText("Guardar configuración")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self._guardar_y_cerrar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

        self.setStyleSheet("""
            #TituloConfig { font-size: 21px; font-weight: bold; padding: 6px; }
            QGroupBox { font-weight: bold; border: 1px solid #888; border-radius: 6px; margin-top: 10px; padding: 8px; }
            QPushButton { padding: 7px; border-radius: 6px; font-weight: 600; }
            QLabel { font-size: 13px; }
        """)

    def _slider(self, mn, mx, val):
        s = QSlider(Qt.Horizontal)
        s.setRange(mn, mx)
        s.setValue(int(val))
        return s

    def _crear_boton_seccion(self, texto, color):
        btn = QPushButton(texto)
        btn.setMinimumHeight(34)
        btn.setCursor(Qt.PointingHandCursor)
        btn._color_base = color
        btn.setStyleSheet(self._estilo_boton_seccion(color, activo=False))
        return btn

    def _estilo_boton_seccion(self, color, activo=False):
        borde = "#111827" if activo else "#334155"
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {borde};
                border-radius: 8px;
                padding: 7px 12px;
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
        """

    def _mostrar_seccion(self, indice):
        self.stack_config.setCurrentIndex(indice)
        for i, btn in enumerate(self.botones_config):
            btn.setStyleSheet(self._estilo_boton_seccion(btn._color_base, activo=(i == indice)))


    def _tab_audio(self):
        w = QWidget(); lay = QVBoxLayout(w)
        g = QGroupBox("Motor de sonido")
        grid = QGridLayout(g)
        self.chk_audio_cfg = QCheckBox("Audio activo")
        self.chk_audio_cfg.setChecked(self.ajustes.audio_activo)
        self.combo_preset_cfg = QComboBox()
        self.combo_preset_cfg.addItems(["piano suave", "pad cálido", "órgano", "seno", "sierra", "cuadrada"])
        self.combo_preset_cfg.setCurrentText(self.ajustes.forma_onda)
        self.sl_vol_cfg = self._slider(0, 100, self.ajustes.volumen * 100)
        self.sl_brillo_cfg = self._slider(0, 100, self.ajustes.brillo * 100)
        self.sl_sustain_cfg = self._slider(5, 95, self.ajustes.sustain * 100)
        self.sl_reverb_cfg = self._slider(0, 100, self.ajustes.reverb * 100)
        self.sl_delay_cfg = self._slider(0, 75, self.ajustes.delay * 100)
        self.btn_probar_audio = QPushButton("Probar sonido")
        self.btn_probar_audio.clicked.connect(lambda: self.ventana.audio.sonido_acierto())
        grid.addWidget(self.chk_audio_cfg, 0, 0, 1, 2)
        grid.addWidget(QLabel("Preset"), 1, 0); grid.addWidget(self.combo_preset_cfg, 1, 1)
        grid.addWidget(QLabel("Volumen"), 2, 0); grid.addWidget(self.sl_vol_cfg, 2, 1)
        grid.addWidget(QLabel("Brillo"), 3, 0); grid.addWidget(self.sl_brillo_cfg, 3, 1)
        grid.addWidget(QLabel("Sustain"), 4, 0); grid.addWidget(self.sl_sustain_cfg, 4, 1)
        grid.addWidget(QLabel("Reverb"), 5, 0); grid.addWidget(self.sl_reverb_cfg, 5, 1)
        grid.addWidget(QLabel("Delay"), 6, 0); grid.addWidget(self.sl_delay_cfg, 6, 1)
        grid.addWidget(self.btn_probar_audio, 7, 0, 1, 2)
        lay.addWidget(g); lay.addStretch(1)
        return w

    def _tab_midi(self):
        w = QWidget(); lay = QVBoxLayout(w)
        g = QGroupBox("Teclado externo y puertos MIDI")
        grid = QGridLayout(g)
        self.combo_midi_in_cfg = QComboBox()
        self.combo_midi_out_cfg = QComboBox()
        self.chk_midi_auto_cfg = QCheckBox("Conectar MIDI IN/OUT automáticamente al iniciar")
        self.chk_midi_auto_cfg.setChecked(self.ajustes.conectar_midi_al_iniciar)
        self.lbl_midi_cfg = QLabel("MIDI: sin comprobar")
        btn_refrescar = QPushButton("Refrescar puertos")
        btn_conectar = QPushButton("Conectar MIDI IN/OUT ahora")
        btn_cerrar = QPushButton("Cerrar MIDI")
        btn_refrescar.clicked.connect(self._refrescar_midi_cfg)
        btn_conectar.clicked.connect(self._conectar_midi_cfg)
        btn_cerrar.clicked.connect(self._cerrar_midi_cfg)
        grid.addWidget(QLabel("MIDI IN"), 0, 0); grid.addWidget(self.combo_midi_in_cfg, 0, 1, 1, 3)
        grid.addWidget(QLabel("MIDI OUT"), 1, 0); grid.addWidget(self.combo_midi_out_cfg, 1, 1, 1, 3)
        grid.addWidget(self.chk_midi_auto_cfg, 2, 0, 1, 4)
        grid.addWidget(btn_refrescar, 3, 0); grid.addWidget(btn_conectar, 3, 1); grid.addWidget(btn_cerrar, 3, 2)
        grid.addWidget(self.lbl_midi_cfg, 4, 0, 1, 4)
        lay.addWidget(g)
        info = QLabel("Cuando el MIDI IN está conectado, las 88 teclas del piano se iluminan, suena el motor de audio y el profesor puede corregir notas/acordes. Cuando MIDI OUT está conectado, el piano virtual, las demostraciones y el MIDI didáctico envían notas reales al teclado externo seleccionado.")
        info.setWordWrap(True); lay.addWidget(info); lay.addStretch(1)
        self._refrescar_midi_cfg()
        return w

    def _tab_camara(self):
        w = QWidget(); lay = QVBoxLayout(w)
        g = QGroupBox("Vista de cámara y reconocimiento")
        gl = QGridLayout(g)
        self.spin_camara_cfg = QSpinBox(); self.spin_camara_cfg.setRange(0, 8); self.spin_camara_cfg.setValue(self.ajustes.camara_dispositivo)
        self.spin_cam_ancho = QSpinBox(); self.spin_cam_ancho.setRange(240, 960); self.spin_cam_ancho.setValue(self.ajustes.camara_ancho)
        self.spin_cam_alto = QSpinBox(); self.spin_cam_alto.setRange(135, 540); self.spin_cam_alto.setValue(self.ajustes.camara_alto)
        self.lbl_preview_camara = QLabel("Vista previa de cámara")
        self.lbl_preview_camara.setAlignment(Qt.AlignCenter)
        self.lbl_preview_camara.setFixedSize(420, 236)
        self.lbl_preview_camara.setStyleSheet("background:#111; color:#ddd; border:1px solid #555; border-radius:6px;")
        btn_ini = QPushButton("Iniciar vista previa")
        btn_stop = QPushButton("Detener")
        btn_ini.clicked.connect(self._iniciar_preview_camara)
        btn_stop.clicked.connect(self._detener_preview_camara)
        self.lbl_camara_cfg = QLabel("Cámara detenida.")
        self.lbl_camara_cfg.setWordWrap(True)
        gl.addWidget(QLabel("Dispositivo"), 0, 0); gl.addWidget(self.spin_camara_cfg, 0, 1)
        gl.addWidget(QLabel("Ancho vista"), 1, 0); gl.addWidget(self.spin_cam_ancho, 1, 1)
        gl.addWidget(QLabel("Alto vista"), 2, 0); gl.addWidget(self.spin_cam_alto, 2, 1)
        gl.addWidget(btn_ini, 3, 0); gl.addWidget(btn_stop, 3, 1)
        gl.addWidget(self.lbl_camara_cfg, 4, 0, 1, 2)
        gl.addWidget(self.lbl_preview_camara, 0, 2, 5, 1)
        lay.addWidget(g)
        nota = QLabel("Esta cámara queda preparada para postura, manos y reconocimiento visual. La vista está en configuración para no ensuciar la clase principal.")
        nota.setWordWrap(True); lay.addWidget(nota); lay.addStretch(1)
        return w

    def _tab_avatar(self):
        w = QWidget(); lay = QVBoxLayout(w)
        g = QGroupBox("Avatar del profesor")
        grid = QGridLayout(g)
        self.combo_avatar_cfg = QComboBox(); self.combo_avatar_cfg.addItems(["chica", "chico"]); self.combo_avatar_cfg.setCurrentText(self.ajustes.avatar_tipo)
        self.chk_voz_cfg = QCheckBox("Voz activa")
        self.chk_voz_cfg.setChecked(self.ajustes.voz_activa)
        self.chk_leer_auto_cfg = QCheckBox("Leer las clases automáticamente")
        self.chk_leer_auto_cfg.setChecked(self.ajustes.leer_clases_automaticamente)
        self.combo_motor_voz_cfg = QComboBox(); self.combo_motor_voz_cfg.addItems(["piper"]); self.combo_motor_voz_cfg.setCurrentText("piper")
        self.combo_motor_voz_cfg.setEnabled(False)
        self.edit_modelo_chica = QLineEdit(getattr(self.ajustes, "voz_piper_modelo_chica", ""))
        self.edit_modelo_chico = QLineEdit(getattr(self.ajustes, "voz_piper_modelo_chico", ""))
        btn_modelo_chica = QPushButton("Elegir modelo chica")
        btn_modelo_chico = QPushButton("Elegir modelo chico")
        btn_modelo_chica.clicked.connect(lambda: self._elegir_modelo_piper(self.edit_modelo_chica))
        btn_modelo_chico.clicked.connect(lambda: self._elegir_modelo_piper(self.edit_modelo_chico))
        self.spin_velocidad_voz_cfg = QSpinBox(); self.spin_velocidad_voz_cfg.setRange(50, 220); self.spin_velocidad_voz_cfg.setSuffix(" %"); self.spin_velocidad_voz_cfg.setValue(self.ajustes.voz_velocidad)
        self.spin_vol_voz_cfg = QSpinBox(); self.spin_vol_voz_cfg.setRange(0, 200); self.spin_vol_voz_cfg.setValue(self.ajustes.voz_volumen)
        self.spin_pausa_coma_cfg = QSpinBox(); self.spin_pausa_coma_cfg.setRange(0, 3000); self.spin_pausa_coma_cfg.setSuffix(" ms"); self.spin_pausa_coma_cfg.setSingleStep(50); self.spin_pausa_coma_cfg.setValue(getattr(self.ajustes, "voz_pausa_coma_ms", 250))
        self.spin_pausa_punto_cfg = QSpinBox(); self.spin_pausa_punto_cfg.setRange(0, 4000); self.spin_pausa_punto_cfg.setSuffix(" ms"); self.spin_pausa_punto_cfg.setSingleStep(50); self.spin_pausa_punto_cfg.setValue(getattr(self.ajustes, "voz_pausa_punto_ms", 750))
        btn_probar = QPushButton("Probar voz")
        btn_probar.clicked.connect(self._probar_voz_cfg)
        btn_pausa_voz = QPushButton("Pausa / Reanudar")
        btn_pausa_voz.clicked.connect(self.ventana.pausar_reanudar_voz)
        btn_stop_voz = QPushButton("Stop voz")
        btn_stop_voz.clicked.connect(self.ventana.stop_voz)
        btn_diag = QPushButton("Diagnóstico de voz")
        btn_diag.clicked.connect(self._diagnostico_voz_cfg)
        btn_texto_narrado = QPushButton("Ver texto narrado")
        btn_texto_narrado.clicked.connect(self._ver_texto_narrado_cfg)
        for _btn, _color in ((btn_probar, "#16A34A"), (btn_pausa_voz, "#F59E0B"), (btn_stop_voz, "#64748B"), (btn_diag, "#2563EB"), (btn_texto_narrado, "#0EA5E9")):
            _btn.setStyleSheet(f"background-color: {_color}; color: white; font-weight: bold; border-radius: 6px; padding: 7px;")
        grid.addWidget(QLabel("Avatar"), 0, 0); grid.addWidget(self.combo_avatar_cfg, 0, 1)
        grid.addWidget(self.chk_voz_cfg, 1, 0, 1, 2)
        grid.addWidget(self.chk_leer_auto_cfg, 2, 0, 1, 2)
        grid.addWidget(QLabel("Motor"), 3, 0); grid.addWidget(self.combo_motor_voz_cfg, 3, 1)
        grid.addWidget(QLabel("Piper chica (.onnx)"), 4, 0); grid.addWidget(self.edit_modelo_chica, 4, 1); grid.addWidget(btn_modelo_chica, 4, 2)
        grid.addWidget(QLabel("Piper chico (.onnx)"), 5, 0); grid.addWidget(self.edit_modelo_chico, 5, 1); grid.addWidget(btn_modelo_chico, 5, 2)
        grid.addWidget(QLabel("Velocidad"), 6, 0); grid.addWidget(self.spin_velocidad_voz_cfg, 6, 1); grid.addWidget(QLabel("50 lento · 100 natural · 220 rápido"), 6, 2)
        grid.addWidget(QLabel("Volumen voz"), 7, 0); grid.addWidget(self.spin_vol_voz_cfg, 7, 1)
        grid.addWidget(QLabel("Pausa tras coma"), 8, 0); grid.addWidget(self.spin_pausa_coma_cfg, 8, 1); grid.addWidget(QLabel("Ajusta respiraciones cortas"), 8, 2)
        grid.addWidget(QLabel("Pausa tras punto"), 9, 0); grid.addWidget(self.spin_pausa_punto_cfg, 9, 1); grid.addWidget(QLabel("Ajusta separaciones entre frases"), 9, 2)
        grid.addWidget(btn_probar, 10, 0)
        grid.addWidget(btn_pausa_voz, 10, 1)
        grid.addWidget(btn_stop_voz, 10, 2)
        grid.addWidget(btn_diag, 11, 0, 1, 2)
        grid.addWidget(btn_texto_narrado, 11, 2)
        lay.addWidget(g)
        info = QLabel("La voz robótica queda desactivada: el avatar habla solo con Piper. Por defecto se usa el avatar chico y el modelo de chico. La velocidad ahora controla --length-scale de Piper y se guarda en data/ajustes_usuario.json.")
        info.setWordWrap(True); lay.addWidget(info); lay.addStretch(1)
        return w

    def _tab_interfaz(self):
        w = QWidget(); lay = QVBoxLayout(w)
        g = QGroupBox("Limpieza visual y piano")
        grid = QGridLayout(g)
        self.chk_piano88_cfg = QCheckBox("Usar piano completo de 88 teclas")
        self.chk_piano88_cfg.setChecked(True)
        self.chk_piano88_cfg.setEnabled(False)
        self.chk_nombres_cfg = QCheckBox("Mostrar nombres en las teclas")
        self.chk_nombres_cfg.setChecked(self.ajustes.piano_mostrar_nombres)
        self.spin_altura_piano_cfg = QSpinBox(); self.spin_altura_piano_cfg.setRange(90, 220); self.spin_altura_piano_cfg.setValue(self.ajustes.piano_altura)
        self.chk_limpia_cfg = QCheckBox("Mantener interfaz principal limpia")
        self.chk_limpia_cfg.setChecked(self.ajustes.interfaz_limpia)
        self.combo_tema_cfg = QComboBox(); self.combo_tema_cfg.addItems(["claro", "oscuro"]); self.combo_tema_cfg.setCurrentText(self.ajustes.tema)
        grid.addWidget(self.chk_piano88_cfg, 0, 0, 1, 2)
        grid.addWidget(self.chk_nombres_cfg, 1, 0, 1, 2)
        grid.addWidget(QLabel("Altura del piano"), 2, 0); grid.addWidget(self.spin_altura_piano_cfg, 2, 1)
        grid.addWidget(self.chk_limpia_cfg, 3, 0, 1, 2)
        grid.addWidget(QLabel("Tema"), 4, 0); grid.addWidget(self.combo_tema_cfg, 4, 1)
        lay.addWidget(g); lay.addStretch(1)
        return w

    def _tab_progreso(self):
        w = QWidget(); lay = QVBoxLayout(w)
        stats = self.ventana.progreso.estadisticas()
        txt = QLabel(
            f"Nivel actual: {self.ventana.progreso.estado.nivel_actual}\n"
            f"Ejercicios superados: {self.ventana.progreso.estado.ejercicios_superados}\n"
            f"Ejercicios fallados: {self.ventana.progreso.estado.ejercicios_fallados}\n"
            f"Racha: {stats['racha']}\n"
            f"Tasa de acierto: {stats['tasa']}%\n\n"
            "Aquí quedarán agrupadas las opciones pedagógicas: ritmo de avance, repasos, exámenes, cámara, MIDI y voz del profesor."
        )
        txt.setWordWrap(True); lay.addWidget(txt); lay.addStretch(1)
        return w

    def _refrescar_midi_cfg(self):
        entradas = self.ventana.midi.entradas()
        salidas = self.ventana.midi.salidas()
        self.combo_midi_in_cfg.clear(); self.combo_midi_out_cfg.clear()
        self.combo_midi_in_cfg.addItem("Sin entrada MIDI", "")
        self.combo_midi_out_cfg.addItem("Sin salida MIDI", "")
        for e in entradas: self.combo_midi_in_cfg.addItem(e, e)
        for s in salidas: self.combo_midi_out_cfg.addItem(s, s)
        self._seleccionar_combo_por_data(self.combo_midi_in_cfg, self.ajustes.midi_in_preferido)
        self._seleccionar_combo_por_data(self.combo_midi_out_cfg, self.ajustes.midi_out_preferido)
        self.lbl_midi_cfg.setText(f"Entradas: {len(entradas)} | Salidas: {len(salidas)}")

    def _seleccionar_combo_por_data(self, combo, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i); return

    def _conectar_midi_cfg(self):
        nombre_in = self.combo_midi_in_cfg.currentData() or ""
        nombre_out = self.combo_midi_out_cfg.currentData() or ""
        partes = []

        if nombre_in:
            ok_in = self.ventana.midi.abrir_entrada(nombre_in)
            partes.append(f"IN conectado: {nombre_in}" if ok_in else f"IN error: {self.ventana.midi.error}")
            if ok_in:
                self.ajustes.midi_in_preferido = nombre_in
        else:
            self.ventana.midi.cerrar_entrada()
            self.ajustes.midi_in_preferido = ""
            partes.append("IN: sin seleccionar")

        if nombre_out:
            ok_out = self.ventana.midi.abrir_salida(nombre_out)
            partes.append(f"OUT conectado: {nombre_out}" if ok_out else f"OUT error: {self.ventana.midi.error}")
            if ok_out:
                self.ajustes.midi_out_preferido = nombre_out
        else:
            self.ventana.midi.cerrar_salida()
            self.ajustes.midi_out_preferido = ""
            partes.append("OUT: sin seleccionar")

        self.ventana.ajustes.guardar()
        texto = "MIDI: " + " | ".join(partes)
        self.lbl_midi_cfg.setText(texto)
        if hasattr(self.ventana, "lbl_midi_compacto"):
            self.ventana.lbl_midi_compacto.setText(texto)

    def _cerrar_midi_cfg(self):
        self.ventana.midi.cerrar()
        self.lbl_midi_cfg.setText("MIDI cerrado")
        if hasattr(self.ventana, "lbl_midi_compacto"):
            self.ventana.lbl_midi_compacto.setText("MIDI: cerrado")

    def _iniciar_preview_camara(self):
        indice = int(self.spin_camara_cfg.value())
        ok = self.camera_preview.abrir(indice)
        if not ok:
            self.lbl_camara_cfg.setText(f"No se pudo abrir la cámara: {self.camera_preview.error}")
            self.lbl_preview_camara.setText("Sin cámara")
            return
        self.lbl_camara_cfg.setText(f"Cámara activa en dispositivo {indice}")
        self.timer_camara.start()

    def _detener_preview_camara(self):
        self.timer_camara.stop()
        self.camera_preview.cerrar()
        self.lbl_preview_camara.setPixmap(QPixmap())
        self.lbl_preview_camara.setText("Vista previa detenida")
        self.lbl_camara_cfg.setText("Cámara detenida.")

    def _actualizar_preview_camara(self):
        frame = self.camera_preview.leer_frame()
        if frame is None:
            return
        try:
            import cv2
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            alto, ancho, canales = frame_rgb.shape
            qimg = QImage(frame_rgb.data, ancho, alto, canales * ancho, QImage.Format_RGB888).copy()
            self.lbl_preview_camara.setPixmap(QPixmap.fromImage(qimg).scaled(self.lbl_preview_camara.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as exc:
            self.lbl_camara_cfg.setText(f"Error mostrando cámara: {exc}")

    def _elegir_modelo_piper(self, destino):
        ruta, _ = QFileDialog.getOpenFileName(self, "Elegir modelo Piper .onnx", "", "Modelos Piper (*.onnx);;Todos los archivos (*)")
        if ruta:
            destino.setText(ruta)

    def _probar_voz_cfg(self):
        voz = self.ventana.voz_avatar
        tipo = self.combo_avatar_cfg.currentText()
        texto = (
            "Hola. Soy tu profesora de piano. Primero te explicaré la clase y después practicaremos juntas."
            if tipo == "chica"
            else "Hola. Soy tu profesor de piano. Primero te explicaré la clase y después practicaremos juntos."
        )
        if hasattr(self.ventana, "avatar"):
            self.ventana.avatar.set_tipo(tipo)
        ok = voz.hablar(
            texto,
            avatar_tipo=tipo,
            velocidad=self.spin_velocidad_voz_cfg.value(),
            volumen=self.spin_vol_voz_cfg.value(),
            motor=self.combo_motor_voz_cfg.currentText(),
            pausa_coma_ms=self.spin_pausa_coma_cfg.value(),
            pausa_punto_ms=self.spin_pausa_punto_cfg.value(),
            modelo_chica=self.edit_modelo_chica.text().strip(),
            modelo_chico=self.edit_modelo_chico.text().strip(),
            on_start=self.ventana.voz_bridge.inicio.emit,
            on_end=self.ventana.voz_bridge.fin.emit,
            on_error=self.ventana.voz_bridge.error.emit,
        )
        if not ok:
            QMessageBox.information(self, "Voz Piper no disponible", "Configura un modelo Piper .onnx válido para este avatar. No se usará espeak ni otra voz robótica de respaldo.")

    def _ver_texto_narrado_cfg(self):
        """Muestra exactamente qué texto y qué bloques recibe Piper."""
        texto_visual = ""
        try:
            texto_visual = self.ventana.txt_profesor.toPlainText()
        except Exception:
            texto_visual = getattr(self.ventana, "_ultimo_texto_profesor", "")
        if not str(texto_visual or "").strip():
            QMessageBox.information(self, "Texto narrado", "No hay texto de clase cargado todavía.")
            return
        try:
            texto = self.ventana.voz_avatar.diagnostico_texto_narrado(
                texto_visual,
                pausa_coma_ms=self.spin_pausa_coma_cfg.value(),
                pausa_punto_ms=self.spin_pausa_punto_cfg.value(),
            )
        except Exception as exc:
            texto = f"No se pudo preparar el diagnóstico del texto narrado:\n{exc}"
        QMessageBox.information(self, "Texto exacto enviado al narrador", texto)

    def _diagnostico_voz_cfg(self):
        voz = VozAvatar()
        d = voz.diagnostico(
            self.combo_motor_voz_cfg.currentText(),
            avatar_tipo=self.combo_avatar_cfg.currentText(),
            modelo_chica=self.edit_modelo_chica.text().strip(),
            modelo_chico=self.edit_modelo_chico.text().strip(),
        )
        texto = (
            f"Backend elegido: {d['backend'] or 'NO ENCONTRADO'}\n"
            f"Motor/binario: {d['motor'] or 'NO ENCONTRADO'}\n"
            f"Modelo Piper: {d['modelo'] or '-'}\n"
            f"Config Piper: {d.get('config') or '-'}\n"
            f"Reproductor: {d['reproductor']}\n"
            f"piper: {d['piper'] or '-'}\n"
            f"paplay: {d['paplay'] or '-'}\n"
            f"pw-play: {d['pw_play'] or '-'}\n"
            f"aplay: {d['aplay'] or '-'}\n"
            f"Último error: {d['ultimo_error'] or '-'}"
        )
        QMessageBox.information(self, "Diagnóstico de voz", texto)

    def _guardar_y_cerrar(self):
        a = self.ajustes
        a.audio_activo = self.chk_audio_cfg.isChecked()
        a.forma_onda = self.combo_preset_cfg.currentText()
        a.volumen = self.sl_vol_cfg.value() / 100
        a.brillo = self.sl_brillo_cfg.value() / 100
        a.sustain = self.sl_sustain_cfg.value() / 100
        a.reverb = self.sl_reverb_cfg.value() / 100
        a.delay = self.sl_delay_cfg.value() / 100
        a.midi_in_preferido = self.combo_midi_in_cfg.currentData() or ""
        a.midi_out_preferido = self.combo_midi_out_cfg.currentData() or ""
        a.conectar_midi_al_iniciar = self.chk_midi_auto_cfg.isChecked()
        a.camara_dispositivo = int(self.spin_camara_cfg.value())
        a.camara_ancho = int(self.spin_cam_ancho.value())
        a.camara_alto = int(self.spin_cam_alto.value())
        a.avatar_tipo = self.combo_avatar_cfg.currentText()
        a.voz_activa = self.chk_voz_cfg.isChecked()
        a.leer_clases_automaticamente = self.chk_leer_auto_cfg.isChecked()
        a.voz_motor = "piper"
        a.voz_piper_modelo_chica = self.edit_modelo_chica.text().strip()
        a.voz_piper_modelo_chico = self.edit_modelo_chico.text().strip()
        a.voz_velocidad = int(self.spin_velocidad_voz_cfg.value())
        a.voz_volumen = int(self.spin_vol_voz_cfg.value())
        a.voz_pausa_coma_ms = int(self.spin_pausa_coma_cfg.value())
        a.voz_pausa_punto_ms = int(self.spin_pausa_punto_cfg.value())
        a.piano_mostrar_nombres = self.chk_nombres_cfg.isChecked()
        a.piano_altura = int(self.spin_altura_piano_cfg.value())
        a.interfaz_limpia = self.chk_limpia_cfg.isChecked()
        a.tema = self.combo_tema_cfg.currentText()
        self.ventana.ajustes.guardar()
        try:
            if a.midi_in_preferido:
                self.ventana.midi.abrir_entrada(a.midi_in_preferido)
            else:
                self.ventana.midi.cerrar_entrada()
            if a.midi_out_preferido:
                self.ventana.midi.abrir_salida(a.midi_out_preferido)
            else:
                self.ventana.midi.cerrar_salida()
        except Exception:
            pass
        self._detener_preview_camara()
        self.ventana.aplicar_configuracion_usuario()
        self.accept()

    def closeEvent(self, event):
        self._detener_preview_camara()
        super().closeEvent(event)
