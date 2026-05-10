from __future__ import annotations

import re


NOTAS_ANGLO = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTAS_ES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
BASE_A_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ES_A_ANGLO = {
    "DO": "C", "RE": "D", "MI": "E", "FA": "F", "SOL": "G", "LA": "A", "SI": "B",
    "DO#": "C#", "RE#": "D#", "FA#": "F#", "SOL#": "G#", "LA#": "A#",
}


def midi_a_nombre(midi: int) -> str:
    """Convención única del proyecto: MIDI 60 = C4 / Do4."""
    midi = int(midi)
    return f"{NOTAS_ANGLO[midi % 12]}{(midi // 12) - 1}"


def midi_a_info(midi: int) -> dict:
    midi = int(midi)
    pc = midi % 12
    octava = (midi // 12) - 1
    return {
        "midi": midi,
        "midi_number": midi,
        "note_name": NOTAS_ANGLO[pc],
        "nombre": NOTAS_ES[pc],
        "octave": octava,
        "octava": octava,
        "nombre_completo": f"{NOTAS_ES[pc]}{octava}",
        "nota": f"{NOTAS_ANGLO[pc]}{octava}",
    }


def nombre_a_midi(nota: str) -> int | None:
    texto = str(nota or "").strip()
    if not texto:
        return None
    texto = texto.replace("♯", "#").replace("＃", "#").replace("♭", "b")
    texto = texto.replace("Sib", "Bb").replace("Mib", "Eb").replace("Lab", "Ab").replace("Reb", "Db").replace("Solb", "Gb")
    upper = texto.upper().replace(" ", "")
    for es in sorted(ES_A_ANGLO, key=len, reverse=True):
        if upper.startswith(es):
            upper = ES_A_ANGLO[es] + upper[len(es):]
            break
    m = re.match(r"^([A-G])([#B]?)(-?\d+)$", upper)
    if not m:
        return None
    base, acc, octava_txt = m.groups()
    pc = BASE_A_PC.get(base)
    if pc is None:
        return None
    if acc == "#":
        pc += 1
    elif acc == "B":
        pc -= 1
    pc %= 12
    return (int(octava_txt) + 1) * 12 + pc


def normalizar_nota(valor, midi: int | None = None) -> dict:
    if midi is None:
        try:
            if isinstance(valor, int):
                midi = int(valor)
            else:
                midi = nombre_a_midi(str(valor))
        except Exception:
            midi = None
    if midi is None:
        return {
            "midi": None,
            "midi_number": None,
            "note_name": str(valor or ""),
            "nombre": str(valor or ""),
            "octave": None,
            "octava": None,
            "nombre_completo": str(valor or ""),
            "nota": str(valor or ""),
        }
    return midi_a_info(int(midi))
