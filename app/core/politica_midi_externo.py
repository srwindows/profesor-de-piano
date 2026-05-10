from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import struct


def _leer_varlen(data: bytes, idx: int) -> tuple[int, int]:
    valor = 0
    while idx < len(data):
        b = data[idx]; idx += 1
        valor = (valor << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return valor, idx


@dataclass
class AnalisisMidiExterno:
    ruta: str
    formato: int = 0
    pistas_totales: int = 0
    pistas_con_notas: int = 0
    canales_usados: list[int] | None = None
    tiene_canal_10: bool = False
    tempo_detectado: bool = False
    valido_midi: bool = False
    error: str = ""

    def dict(self) -> dict:
        d = asdict(self)
        d["canales_usados"] = sorted(self.canales_usados or [])
        return d


@dataclass
class ResultadoPoliticaMidiExterno:
    permitido: bool
    nivel: int
    max_pistas: int
    requiere_canal_10: bool
    mensaje_profesor: str
    analisis: AnalisisMidiExterno | None = None

    def dict(self) -> dict:
        return {
            "permitido": self.permitido,
            "nivel": self.nivel,
            "max_pistas": self.max_pistas,
            "requiere_canal_10": self.requiere_canal_10,
            "mensaje_profesor": self.mensaje_profesor,
            "analisis": self.analisis.dict() if self.analisis else None,
        }


class PoliticaMidiExterno:
    def reglas_por_nivel(self, nivel: int) -> dict:
        try:
            nivel = int(nivel)
        except Exception:
            nivel = 0
        if nivel <= 2:
            return {"permitido_base": False, "max_pistas": 0, "requiere_canal_10": False, "descripcion": "bloqueado hasta Nivel 3"}
        if nivel == 3:
            return {"permitido_base": True, "max_pistas": 2, "requiere_canal_10": True, "descripcion": "máximo 2 pistas, una de batería/ritmo en canal 10"}
        if nivel == 4:
            return {"permitido_base": True, "max_pistas": 4, "requiere_canal_10": False, "descripcion": "máximo 4 pistas"}
        return {"permitido_base": True, "max_pistas": 999, "requiere_canal_10": False, "descripcion": "MIDI completo; el alumno podrá elegir pista"}

    def analizar_archivo(self, ruta: str | Path) -> AnalisisMidiExterno:
        path = Path(ruta)
        a = AnalisisMidiExterno(ruta=str(path), canales_usados=[])
        try:
            data = path.read_bytes()
            if data[:4] != b"MThd":
                a.error = "No parece un archivo MIDI estándar."
                return a
            hdr_len = struct.unpack(">I", data[4:8])[0]
            formato, ntracks, _division = struct.unpack(">HHH", data[8:14])
            a.formato = int(formato); a.pistas_totales = int(ntracks); a.valido_midi = True
            idx = 8 + hdr_len
            pistas_con_notas = 0; canales = set(); tempo_detectado = False
            for _ in range(ntracks):
                if idx + 8 > len(data) or data[idx:idx+4] != b"MTrk":
                    break
                trk_len = struct.unpack(">I", data[idx+4:idx+8])[0]
                trk = data[idx+8:idx+8+trk_len]
                idx += 8 + trk_len
                tiene, ch, tempo = self._analizar_track(trk)
                if tiene: pistas_con_notas += 1
                canales.update(ch)
                tempo_detectado = tempo_detectado or tempo
            a.pistas_con_notas = pistas_con_notas
            a.canales_usados = sorted(canales)
            a.tiene_canal_10 = 10 in canales
            a.tempo_detectado = tempo_detectado
            return a
        except Exception as exc:
            a.error = str(exc)
            return a

    def _analizar_track(self, trk: bytes) -> tuple[bool, set[int], bool]:
        idx = 0; running = None; tiene = False; canales = set(); tempo = False
        while idx < len(trk):
            _delta, idx = _leer_varlen(trk, idx)
            if idx >= len(trk): break
            status = trk[idx]
            if status < 0x80:
                if running is None: break
                status = running
            else:
                idx += 1; running = status
            if status == 0xFF:
                if idx >= len(trk): break
                meta = trk[idx]; idx += 1
                ln, idx = _leer_varlen(trk, idx)
                payload = trk[idx:idx+ln]; idx += ln
                if meta == 0x51 and len(payload) == 3: tempo = True
                elif meta == 0x2F: break
                continue
            if status in (0xF0, 0xF7):
                ln, idx = _leer_varlen(trk, idx); idx += ln; continue
            tipo = status & 0xF0; canal = (status & 0x0F) + 1
            if tipo in (0x80,0x90,0xA0,0xB0,0xE0):
                if idx + 2 > len(trk): break
                _a = trk[idx]; b = trk[idx+1]; idx += 2
                if tipo == 0x90 and b > 0:
                    tiene = True; canales.add(canal)
            elif tipo in (0xC0,0xD0):
                idx += 1
            else:
                break
        return tiene, canales, tempo

    def evaluar(self, ruta: str | Path | None, nivel: int) -> ResultadoPoliticaMidiExterno:
        reglas = self.reglas_por_nivel(nivel)
        max_pistas = int(reglas["max_pistas"])
        requiere = bool(reglas["requiere_canal_10"])
        if not reglas["permitido_base"]:
            return ResultadoPoliticaMidiExterno(False, int(nivel), max_pistas, requiere, "La carga de MIDIs externos está bloqueada hasta el Nivel 3. Antes trabajaremos repertorio interno graduado para evitar frustración, impaciencia y malos hábitos.", None)
        if ruta is None:
            return ResultadoPoliticaMidiExterno(True, int(nivel), max_pistas, requiere, f"Nivel {nivel}: carga externa disponible con regla: {reglas['descripcion']}.", None)
        a = self.analizar_archivo(ruta)
        if not a.valido_midi:
            return ResultadoPoliticaMidiExterno(False, int(nivel), max_pistas, requiere, f"No puedo aceptar este archivo: {a.error}", a)
        if a.pistas_con_notas > max_pistas:
            return ResultadoPoliticaMidiExterno(False, int(nivel), max_pistas, requiere, f"Este MIDI tiene {a.pistas_con_notas} pistas con notas. En el Nivel {nivel} solo se permiten {max_pistas} pistas.", a)
        if requiere and not a.tiene_canal_10:
            return ResultadoPoliticaMidiExterno(False, int(nivel), max_pistas, requiere, "En Nivel 3 una de las dos pistas debe ser base de batería/ritmo, normalmente canal MIDI 10. Este archivo no contiene canal 10.", a)
        return ResultadoPoliticaMidiExterno(True, int(nivel), max_pistas, requiere, f"MIDI externo aceptado para Nivel {nivel}. Pistas con notas: {a.pistas_con_notas}. Canales usados: {a.canales_usados}.", a)
