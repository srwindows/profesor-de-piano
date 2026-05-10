from dataclasses import dataclass, field
from time import time

NOMBRE_ES = {
    "C": "do", "C#": "do#", "DB": "reb", "D": "re", "D#": "re#", "EB": "mib",
    "E": "mi", "F": "fa", "F#": "fa#", "GB": "solb", "G": "sol", "G#": "sol#",
    "AB": "lab", "A": "la", "A#": "la#", "BB": "sib", "B": "si"
}
ORDEN = ["do", "do#", "re", "re#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si"]

@dataclass
class EventoNota:
    nota: str
    velocidad: int = 0
    canal: int = 1
    instante: float = field(default_factory=time)

class ReconocedorMusical:
    """Reconocimiento local de notas, acordes y secuencias MIDI.

    No sustituye a un motor IA externo: es la capa determinista para corregir
    si el alumno toca la nota/acorde esperado.
    """

    def __init__(self):
        self.notas_activas: dict[str, EventoNota] = {}
        self.historial: list[EventoNota] = []
        self.max_historial = 512

    def note_on(self, nota: str, velocidad: int = 0, canal: int = 1):
        ev = EventoNota(nota=nota, velocidad=velocidad, canal=canal)
        self.notas_activas[nota] = ev
        self.historial.append(ev)
        self.historial = self.historial[-self.max_historial:]

    def note_off(self, nota: str):
        self.notas_activas.pop(nota, None)

    def ultima_nota_base(self) -> str:
        if not self.historial:
            return ""
        return self.normalizar_nota(self.historial[-1].nota)

    def acorde_actual(self) -> list[str]:
        notas = {self.normalizar_nota(n) for n in self.notas_activas}
        return sorted(notas, key=lambda n: ORDEN.index(n) if n in ORDEN else 99)

    def acorde_actual_texto(self) -> str:
        return "-".join(self.acorde_actual())

    def secuencia_reciente(self, n=8) -> list[str]:
        return [self.normalizar_nota(ev.nota) for ev in self.historial[-n:]]

    def coincide_acorde(self, solucion: str) -> bool:
        esperado = self.normalizar_lista(solucion)
        actual = self.acorde_actual()
        return set(actual) == set(esperado) and len(actual) == len(esperado)

    def limpiar(self):
        self.notas_activas.clear()
        self.historial.clear()

    @classmethod
    def normalizar_lista(cls, texto: str) -> list[str]:
        bruto = texto.replace(",", "-").replace("+", "-").replace(" ", "-").lower()
        partes = [p for p in bruto.split("-") if p]
        return [cls.normalizar_nota(p) for p in partes]

    @staticmethod
    def normalizar_nota(nota: str) -> str:
        n = ''.join(ch for ch in str(nota).strip() if not ch.isdigit() and ch != '-').upper()
        if n in NOMBRE_ES:
            return NOMBRE_ES[n]
        n = n.lower()
        equivalencias = {"c":"do", "d":"re", "e":"mi", "f":"fa", "g":"sol", "a":"la", "b":"si"}
        return equivalencias.get(n, n)
