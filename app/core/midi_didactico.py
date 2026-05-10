from __future__ import annotations

import json
import struct
from dataclasses import dataclass, asdict
from pathlib import Path

from app.config import DATA_DIR
from app.core.notas import midi_a_nombre


NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
REPERTORIO_N1_PATH = DATA_DIR / "colecciones" / "nivel_1" / "repertorio.json"
CATALOGOS_MIDI_DIDACTICO = [
    DATA_DIR / "midi_didactico_nivel_1.json",
    DATA_DIR / "midi_didactico_nivel_2.json",
]


def nota_midi_a_nombre(n: int) -> str:
    return midi_a_nombre(int(n))


def leer_varlen(data: bytes, idx: int) -> tuple[int, int]:
    valor = 0
    while True:
        b = data[idx]
        idx += 1
        valor = (valor << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return valor, idx


@dataclass
class NotaMidiDidactica:
    nota: str
    midi: int
    inicio_ms: int
    duracion_ms: int
    velocity: int
    canal: int
    pulso: int
    compas: int
    mano: str = "derecha"

    def fin_ms(self) -> int:
        return int(self.inicio_ms + self.duracion_ms)


@dataclass
class PiezaMidiDidactica:
    id: str
    titulo: str
    midi_path: str
    tempo: int = 60
    compas: str = "4/4"
    notas: list[NotaMidiDidactica] | None = None
    duracion_ms: int = 0
    ppq: int = 480

    def notas_dict(self) -> list[dict]:
        return [asdict(n) for n in (self.notas or [])]


class MidiDidacticoParser:
    """Parser MIDI mínimo para convertir repertorio en flujo docente."""

    def parse_file(self, path: Path, meta: dict | None = None) -> PiezaMidiDidactica:
        path = Path(path)
        data = path.read_bytes()
        if data[:4] != b"MThd":
            raise ValueError(f"No parece MIDI válido: {path}")
        hdr_len = struct.unpack(">I", data[4:8])[0]
        _formato, ntracks, division = struct.unpack(">HHH", data[8:14])
        ppq = int(division & 0x7FFF)
        idx = 8 + hdr_len

        tempo_us_qn = 500000
        eventos = []
        for _ in range(ntracks):
            if data[idx:idx+4] != b"MTrk":
                raise ValueError("Chunk MTrk no encontrado.")
            trk_len = struct.unpack(">I", data[idx+4:idx+8])[0]
            trk = data[idx+8:idx+8+trk_len]
            idx += 8 + trk_len
            eventos.extend(self._parse_track(trk))

        tempos = [e for e in eventos if e[1] == "tempo"]
        if tempos:
            tempo_us_qn = int(tempos[0][2])

        ms_por_tick = tempo_us_qn / 1000.0 / max(1, ppq)
        notas = self._construir_notas(eventos, ms_por_tick, ppq, meta or {})
        duracion_ms = max([n.fin_ms() for n in notas] or [0])
        tempo_bpm = int(round(60000000 / tempo_us_qn))
        if meta and meta.get("tempo"):
            try:
                tempo_bpm = int(meta.get("tempo"))
            except Exception:
                pass

        return PiezaMidiDidactica(
            id=(meta or {}).get("id", path.stem),
            titulo=(meta or {}).get("titulo", path.stem),
            midi_path=str(path),
            tempo=tempo_bpm,
            compas=(meta or {}).get("compas", "4/4"),
            notas=notas,
            duracion_ms=int(duracion_ms),
            ppq=ppq,
        )

    def _parse_track(self, trk: bytes):
        idx = 0
        tick = 0
        running = None
        eventos = []
        while idx < len(trk):
            delta, idx = leer_varlen(trk, idx)
            tick += delta
            if idx >= len(trk):
                break
            status = trk[idx]
            if status < 0x80:
                if running is None:
                    break
                status = running
            else:
                idx += 1
                running = status

            if status == 0xFF:
                if idx >= len(trk):
                    break
                meta_tipo = trk[idx]; idx += 1
                ln, idx = leer_varlen(trk, idx)
                payload = trk[idx:idx+ln]; idx += ln
                if meta_tipo == 0x51 and len(payload) == 3:
                    eventos.append((tick, "tempo", int.from_bytes(payload, "big")))
                elif meta_tipo == 0x2F:
                    break
                continue

            if status in (0xF0, 0xF7):
                ln, idx = leer_varlen(trk, idx)
                idx += ln
                continue

            tipo = status & 0xF0
            canal = status & 0x0F
            if tipo in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                if idx + 2 > len(trk):
                    break
                a = trk[idx]; b = trk[idx+1]; idx += 2
                if tipo == 0x90:
                    eventos.append((tick, "on" if b > 0 else "off", int(a), int(b), int(canal)))
                elif tipo == 0x80:
                    eventos.append((tick, "off", int(a), int(b), int(canal)))
            elif tipo in (0xC0, 0xD0):
                idx += 1
            else:
                break
        return eventos

    def _construir_notas(self, eventos, ms_por_tick: float, ppq: int, meta: dict) -> list[NotaMidiDidactica]:
        activos: dict[tuple[int, int], tuple[int, int]] = {}
        notas = []
        compas = str(meta.get("compas", "4/4"))
        try:
            num, den = [int(x) for x in compas.split("/", 1)]
        except Exception:
            num, den = 4, 4
        ticks_por_pulso = ppq * (4 / max(1, den))
        ticks_por_compas = ticks_por_pulso * max(1, num)

        for e in sorted(eventos, key=lambda x: x[0]):
            tick = e[0]
            tipo = e[1]
            if tipo == "on":
                _, _, midi, vel, canal = e
                activos[(midi, canal)] = (tick, vel)
            elif tipo == "off":
                _, _, midi, _vel, canal = e
                clave = (midi, canal)
                if clave not in activos:
                    continue
                inicio_tick, vel = activos.pop(clave)
                dur_ticks = max(1, tick - inicio_tick)
                inicio_ms = int(round(inicio_tick * ms_por_tick))
                dur_ms = int(round(dur_ticks * ms_por_tick))
                pulso = int((inicio_tick // max(1, int(ticks_por_pulso))) % max(1, num)) + 1
                comp = int(inicio_tick // max(1, int(ticks_por_compas))) + 1
                nota = nota_midi_a_nombre(midi)
                mano = "izquierda" if midi < 60 else "derecha"
                notas.append(NotaMidiDidactica(
                    nota=nota, midi=int(midi), inicio_ms=inicio_ms, duracion_ms=dur_ms,
                    velocity=int(vel), canal=int(canal), pulso=pulso, compas=comp, mano=mano
                ))
        return sorted(notas, key=lambda n: (n.inicio_ms, n.midi))


class GestorMidiDidactico:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else DATA_DIR.parent
        self.parser = MidiDidacticoParser()
        self.repertorio = self._cargar_repertorio()
        self.pieza: PiezaMidiDidactica | None = None
        self.indice = 0

    def _cargar_repertorio(self) -> list[dict]:
        repertorio: list[dict] = []
        vistos: set[str] = set()

        for ruta in [REPERTORIO_N1_PATH, *CATALOGOS_MIDI_DIDACTICO]:
            try:
                data = json.loads(ruta.read_text(encoding="utf-8"))
            except Exception:
                continue
            nivel = str(data.get("nivel") or "").strip()
            for item in data.get("items", []):
                meta = self._normalizar_meta(item, nivel=nivel)
                midi_path = meta.get("midi_path")
                if not midi_path:
                    continue
                clave = str(meta.get("id") or midi_path)
                if clave in vistos:
                    continue
                vistos.add(clave)
                repertorio.append(meta)
        return repertorio

    def _normalizar_meta(self, meta: dict | None, nivel: str = "") -> dict:
        meta = dict(meta or {})
        midi_path = meta.get("midi_path") or meta.get("archivo") or meta.get("archivo_midi")
        if midi_path:
            meta["midi_path"] = str(midi_path)
        if nivel and not meta.get("nivel"):
            meta["nivel"] = nivel
        if meta.get("clase_id") and not meta.get("id"):
            meta["id"] = f"{meta.get('clase_id')}_midi"
        if meta.get("id") and not meta.get("titulo"):
            meta["titulo"] = str(meta.get("id"))
        return meta

    def listar_piezas(self) -> list[dict]:
        return list(self.repertorio)

    def cargar_por_indice(self, indice: int) -> PiezaMidiDidactica:
        if not self.repertorio:
            raise ValueError("No hay piezas MIDI internas en el repertorio.")
        indice = max(0, min(int(indice), len(self.repertorio) - 1))
        meta = self.repertorio[indice]
        self.pieza = self.cargar_por_archivo(str(meta.get("midi_path", "")), meta)
        self.indice = 0
        return self.pieza

    def cargar_por_id(self, pieza_id: str) -> PiezaMidiDidactica:
        for i, item in enumerate(self.repertorio):
            if item.get("id") == pieza_id:
                return self.cargar_por_indice(i)
        raise ValueError(f"No existe la pieza MIDI didáctica: {pieza_id}")

    def cargar_por_archivo(self, midi_path: str | Path, meta: dict | None = None) -> PiezaMidiDidactica:
        meta = self._normalizar_meta(meta)
        ruta = Path(midi_path)
        if not ruta.is_absolute():
            ruta = self.base_dir / ruta
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo MIDI interno: {ruta}")
        if not meta.get("id"):
            meta["id"] = ruta.stem
        if not meta.get("titulo"):
            meta["titulo"] = ruta.stem.replace("_", " ").title()
        meta["midi_path"] = str(ruta)
        self.pieza = self.parser.parse_file(ruta, meta)
        return self.pieza

    def evento_actual(self, tiempo_ms: int) -> NotaMidiDidactica | None:
        if not self.pieza or not self.pieza.notas:
            return None
        actual = None
        for n in self.pieza.notas:
            if n.inicio_ms <= tiempo_ms:
                actual = n
            else:
                break
        return actual

    def notas_activas(self, tiempo_ms: int) -> list[NotaMidiDidactica]:
        if not self.pieza or not self.pieza.notas:
            return []
        return [n for n in self.pieza.notas if n.inicio_ms <= tiempo_ms < n.fin_ms()]

    def siguiente_nota(self, tiempo_ms: int) -> NotaMidiDidactica | None:
        if not self.pieza or not self.pieza.notas:
            return None
        for n in self.pieza.notas:
            if n.inicio_ms > tiempo_ms:
                return n
        return None

    def objetivo_desde_tiempo(self, tiempo_ms: int) -> list[str]:
        activas = self.notas_activas(tiempo_ms)
        if activas:
            return [n.nota for n in activas]
        sig = self.siguiente_nota(tiempo_ms)
        return [sig.nota] if sig else []
