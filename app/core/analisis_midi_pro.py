from __future__ import annotations

import time
from dataclasses import dataclass, field


ES_BASE = {
    "C": "do", "D": "re", "E": "mi", "F": "fa", "G": "sol", "A": "la", "B": "si",
    "DO": "do", "RE": "re", "MI": "mi", "FA": "fa", "SOL": "sol", "LA": "la", "SI": "si",
}


def normalizar_nota(nota: str) -> str:
    return str(nota or "").strip()


def nota_base(nota: str) -> str:
    n = normalizar_nota(nota).upper()
    if not n:
        return ""
    base = ""
    for ch in n:
        if ch.isdigit() or ch == "-":
            break
        base += ch
    return ES_BASE.get(base, base.lower())


def coinciden_notas(tocada: str, esperada: str) -> bool:
    tocada = normalizar_nota(tocada)
    esperada = normalizar_nota(esperada)
    if not tocada or not esperada:
        return False
    if tocada.upper() == esperada.upper():
        return True
    return nota_base(tocada) == nota_base(esperada)


def clasificar_velocity(velocity: int | None) -> str:
    if velocity is None:
        return "sin_velocity"
    v = int(velocity)
    if v <= 32:
        return "muy_suave"
    if v <= 55:
        return "suave"
    if v <= 88:
        return "equilibrada"
    if v <= 112:
        return "fuerte"
    return "demasiado_fuerte"


def clasificar_pulso(diferencia_ms: float | None, tolerancia_ms: float = 340.0) -> str:
    if diferencia_ms is None:
        return "sin_pulso"
    d = float(diferencia_ms)
    if d <= tolerancia_ms * 0.45:
        return "a_tiempo"
    if d <= tolerancia_ms:
        return "cerca_del_pulso"
    return "fuera_de_pulso"


@dataclass
class ObjetivoMidiPro:
    tipo: str = "libre"  # libre, nota, secuencia, acorde, pulso
    esperado: list[str] = field(default_factory=list)
    indice: int = 0
    creado_ts: float = field(default_factory=time.monotonic)
    permite_simultaneas: bool = True
    requiere_simultaneo: bool = False
    tolerancia_simultaneidad_ms: float = 90.0

    def esperado_actual(self) -> str:
        if not self.esperado:
            return ""
        if self.tipo in {"secuencia", "pulso"}:
            idx = max(0, min(self.indice, len(self.esperado) - 1))
            return self.esperado[idx]
        if self.tipo == "nota":
            return self.esperado[0]
        return ""

    def avanzar(self):
        if self.tipo in {"secuencia", "pulso"}:
            self.indice += 1

    def completado(self) -> bool:
        return self.tipo in {"secuencia", "pulso"} and self.indice >= len(self.esperado)


@dataclass
class DiagnosticoMidiPro:
    tipo: str
    nota: str = ""
    velocity: int | None = None
    canal: int | None = None
    esperado: str | list[str] | None = None
    correcto: bool | None = None
    velocity_clase: str = "sin_velocity"
    tiempo_reaccion_ms: float | None = None
    diferencia_pulso_ms: float | None = None
    pulso_clase: str = "sin_pulso"
    notas_activas: list[str] = field(default_factory=list)
    notas_sobrantes: list[str] = field(default_factory=list)
    notas_faltantes: list[str] = field(default_factory=list)
    simultaneidad_ms: float | None = None
    acorde_completo: bool | None = None
    permite_simultaneas: bool = True
    mensaje_docente: str = ""

    def contexto_historial(self) -> dict:
        return {
            "velocity_clase": self.velocity_clase,
            "tiempo_reaccion_ms": self.tiempo_reaccion_ms,
            "diferencia_pulso_ms": self.diferencia_pulso_ms,
            "pulso_clase": self.pulso_clase,
            "notas_activas": self.notas_activas,
            "notas_sobrantes": self.notas_sobrantes,
            "notas_faltantes": self.notas_faltantes,
            "simultaneidad_ms": self.simultaneidad_ms,
            "acorde_completo": self.acorde_completo,
            "permite_simultaneas": self.permite_simultaneas,
        }


class AnalizadorMidiPro:
    """Analizador determinista y ligero para modo Pro.

    No usa IA pesada. Mide y clasifica:
    - nota correcta;
    - secuencia;
    - acordes;
    - velocity;
    - tiempo de reacción;
    - pulso frente al metrónomo;
    - simultaneidad;
    - notas sobrantes/faltantes.
    """

    def __init__(self):
        self.objetivo = ObjetivoMidiPro()
        self.notas_activas: dict[str, float] = {}
        self.velocity_activas: dict[str, int] = {}
        self.historial: list[DiagnosticoMidiPro] = []
        self.max_historial = 2000

    def configurar_objetivo(
        self,
        tipo: str = "libre",
        esperado: str | list[str] | None = None,
        permite_simultaneas: bool = True,
        requiere_simultaneo: bool = False,
        tolerancia_simultaneidad_ms: float = 90.0,
    ):
        if esperado is None:
            lista = []
        elif isinstance(esperado, str):
            lista = [p for p in esperado.replace(",", "-").replace("+", "-").split("-") if p.strip()]
        else:
            lista = [str(x).strip() for x in esperado if str(x).strip()]
        self.objetivo = ObjetivoMidiPro(
            tipo=str(tipo or "libre"),
            esperado=lista,
            indice=0,
            creado_ts=time.monotonic(),
            permite_simultaneas=bool(permite_simultaneas),
            requiere_simultaneo=bool(requiere_simultaneo),
            tolerancia_simultaneidad_ms=float(tolerancia_simultaneidad_ms),
        )

    def limpiar_objetivo(self):
        self.objetivo = ObjetivoMidiPro()

    def avanzar_objetivo(self):
        self.objetivo.avanzar()

    def note_on(
        self,
        nota: str,
        velocity: int | None = None,
        canal: int | None = None,
        origen: str = "midi",
        ultimo_pulso_ts: float | None = None,
        tolerancia_pulso_ms: float = 340.0,
        momento: float | None = None,
    ) -> DiagnosticoMidiPro:
        ahora = time.monotonic() if momento is None else float(momento)
        nota = normalizar_nota(nota)
        self.notas_activas[nota] = ahora
        if velocity is not None:
            self.velocity_activas[nota] = int(velocity)

        esperado_actual = self.objetivo.esperado_actual()
        esperado = self.objetivo.esperado if self.objetivo.tipo == "acorde" else esperado_actual

        tiempo_reaccion_ms = round((ahora - self.objetivo.creado_ts) * 1000.0, 1) if self.objetivo.tipo != "libre" else None
        diferencia_pulso_ms = None
        if ultimo_pulso_ts:
            diferencia_pulso_ms = round(abs(ahora - float(ultimo_pulso_ts)) * 1000.0, 1)

        notas_activas = sorted(self.notas_activas.keys())
        simultaneidad_ms = None
        if len(notas_activas) >= 2:
            tiempos = [self.notas_activas[n] for n in notas_activas]
            simultaneidad_ms = round((max(tiempos) - min(tiempos)) * 1000.0, 1)

        correcto = None
        faltantes: list[str] = []
        sobrantes: list[str] = []
        acorde_completo = None

        if self.objetivo.tipo in {"nota", "secuencia", "pulso"} and esperado_actual:
            correcto = coinciden_notas(nota, esperado_actual)
            if not self.objetivo.permite_simultaneas and len(notas_activas) > 1:
                correcto = False
                sobrantes = [n for n in notas_activas if not coinciden_notas(n, esperado_actual)]
        elif self.objetivo.tipo == "acorde" and self.objetivo.esperado:
            esperadas = self.objetivo.esperado
            faltantes = [e for e in esperadas if not any(coinciden_notas(n, e) for n in notas_activas)]
            sobrantes = [n for n in notas_activas if not any(coinciden_notas(n, e) for e in esperadas)]
            acorde_completo = not faltantes and not sobrantes
            correcto = acorde_completo
            if self.objetivo.requiere_simultaneo and simultaneidad_ms is not None:
                if simultaneidad_ms > self.objetivo.tolerancia_simultaneidad_ms:
                    correcto = False

        diag = DiagnosticoMidiPro(
            tipo=self.objetivo.tipo if self.objetivo.tipo != "libre" else "nota_libre",
            nota=nota,
            velocity=velocity,
            canal=canal,
            esperado=esperado,
            correcto=correcto,
            velocity_clase=clasificar_velocity(velocity),
            tiempo_reaccion_ms=tiempo_reaccion_ms,
            diferencia_pulso_ms=diferencia_pulso_ms,
            pulso_clase=clasificar_pulso(diferencia_pulso_ms, tolerancia_pulso_ms),
            notas_activas=notas_activas,
            notas_sobrantes=sobrantes,
            notas_faltantes=faltantes,
            simultaneidad_ms=simultaneidad_ms,
            acorde_completo=acorde_completo,
            permite_simultaneas=self.objetivo.permite_simultaneas,
            mensaje_docente=self._mensaje_docente(nota, esperado, correcto, velocity, diferencia_pulso_ms, faltantes, sobrantes, simultaneidad_ms),
        )
        self.historial.append(diag)
        self.historial = self.historial[-self.max_historial:]
        return diag

    def note_off(self, nota: str, momento: float | None = None) -> float | None:
        ahora = time.monotonic() if momento is None else float(momento)
        nota = normalizar_nota(nota)
        inicio = self.notas_activas.pop(nota, None)
        self.velocity_activas.pop(nota, None)
        if inicio is None:
            return None
        return round((ahora - inicio) * 1000.0, 1)

    def _mensaje_docente(
        self,
        nota: str,
        esperado,
        correcto,
        velocity,
        diferencia_pulso_ms,
        faltantes,
        sobrantes,
        simultaneidad_ms,
    ) -> str:
        partes = []
        if correcto is True:
            partes.append("Correcto.")
        elif correcto is False:
            partes.append("No está correcto todavía.")
        else:
            partes.append("Nota registrada.")

        if esperado:
            partes.append(f"Esperaba {esperado} y has tocado {nota}.")
        else:
            partes.append(f"Has tocado {nota}.")

        vclase = clasificar_velocity(velocity)
        if vclase == "demasiado_fuerte":
            partes.append("La pulsación es demasiado fuerte; intenta tocar con menos peso.")
        elif vclase == "muy_suave":
            partes.append("La pulsación es muy suave; procura que la tecla baje con seguridad.")
        elif vclase in {"suave", "equilibrada", "fuerte"}:
            partes.append(f"Velocity: {vclase}.")

        if diferencia_pulso_ms is not None:
            if clasificar_pulso(diferencia_pulso_ms) == "fuera_de_pulso":
                partes.append(f"Has caído fuera del pulso por unos {diferencia_pulso_ms} ms.")
            else:
                partes.append(f"Pulso aceptable: diferencia aproximada {diferencia_pulso_ms} ms.")

        if faltantes:
            partes.append("Faltan notas: " + ", ".join(faltantes) + ".")
        if sobrantes:
            partes.append("Sobran notas: " + ", ".join(sobrantes) + ".")
        if simultaneidad_ms is not None:
            partes.append(f"Simultaneidad aproximada: {simultaneidad_ms} ms.")
        return " ".join(partes)
