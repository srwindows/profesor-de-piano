import json
from dataclasses import dataclass, asdict
from pathlib import Path
from app.config import AJUSTES_PATH

@dataclass
class AjustesUsuario:
    # Audio
    audio_activo: bool = True
    volumen: float = 0.55
    forma_onda: str = "piano suave"
    octava_base: int = 3
    reverb: float = 0.22
    delay: float = 0.08
    brillo: float = 0.55
    sustain: float = 0.35

    # MIDI
    midi_in_preferido: str = ""
    midi_out_preferido: str = ""
    conectar_midi_al_iniciar: bool = False

    # Cámara / reconocimiento visual
    camara_dispositivo: int = 0
    camara_ancho: int = 360
    camara_alto: int = 202

    # Avatar y voz
    avatar_tipo: str = "chico"       # chica / chico
    voz_activa: bool = True
    voz_velocidad: int = 100
    voz_volumen: int = 95
    voz_motor: str = "piper"        # Solo Piper: sin respaldo robótico
    voz_pausa_coma_ms: int = 250
    voz_pausa_punto_ms: int = 750
    voz_piper_modelo_chica: str = "voices/piper/laura/es_MX-laura-high.onnx"
    voz_piper_modelo_chico: str = "voices/piper/es_ES-carlfm-high.onnx"
    leer_clases_automaticamente: bool = True

    # Interfaz
    piano_88_teclas: bool = True
    piano_mostrar_nombres: bool = True
    piano_altura: int = 150
    interfaz_limpia: bool = True
    tema: str = "claro"

class GestorAjustes:
    def __init__(self, ruta: Path = AJUSTES_PATH):
        self.ruta = ruta
        self.ajustes = AjustesUsuario()
        self.cargar()

    def cargar(self):
        if not self.ruta.exists():
            self.guardar(); return
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            base = asdict(AjustesUsuario())
            # Mantiene compatibilidad hacia atrás con JSON antiguos.
            for k, v in datos.items():
                if k in base:
                    base[k] = v

            # Normalización v1.7.4: Piper, velocidad real y avatar chico por defecto.
            cambiado = False
            if base.get("voz_motor") in ("", "auto", "espeak", "espeak-ng"):
                base["voz_motor"] = "piper"
                cambiado = True
            if not base.get("voz_piper_modelo_chica"):
                base["voz_piper_modelo_chica"] = "voices/piper/laura/es_MX-laura-high.onnx"
                cambiado = True
            if not base.get("voz_piper_modelo_chico"):
                base["voz_piper_modelo_chico"] = "voices/piper/es_ES-carlfm-high.onnx"
                cambiado = True
            if base.get("avatar_tipo") not in ("chica", "chico"):
                base["avatar_tipo"] = "chico"
                cambiado = True
            try:
                vel = int(base.get("voz_velocidad", 100))
            except Exception:
                vel = 100
            if vel < 50 or vel > 220:
                base["voz_velocidad"] = 100
                cambiado = True
            for clave, minimo, maximo, defecto in (
                ("voz_pausa_coma_ms", 0, 3000, 250),
                ("voz_pausa_punto_ms", 0, 4000, 750),
            ):
                try:
                    valor = int(base.get(clave, defecto))
                except Exception:
                    valor = defecto
                if valor < minimo or valor > maximo:
                    valor = defecto
                    cambiado = True
                base[clave] = valor
            self.ajustes = AjustesUsuario(**base)
            if cambiado:
                self.guardar()
        except Exception:
            self.ajustes = AjustesUsuario(); self.guardar()

    def guardar(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps(asdict(self.ajustes), indent=2, ensure_ascii=False), encoding="utf-8")
