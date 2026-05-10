from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from app.core.politica_midi_externo import PoliticaMidiExterno


@dataclass
class PlanPistasMidiExterno:
    permitido: bool
    nivel: int
    ruta: str
    max_pistas: int
    pistas_activas: list[int]
    pista_alumno: int | None
    pista_ritmo: int | None
    pistas_silenciadas: list[int]
    mensaje_profesor: str
    analisis: dict

    def dict(self) -> dict:
        return asdict(self)


class SelectorPistasMidiExterno:
    def __init__(self, ruta_planes: Path | None = None):
        self.ruta_planes = Path(ruta_planes) if ruta_planes else Path("data/midi_externo")
        self.ruta_planes.mkdir(parents=True, exist_ok=True)
        self.politica = PoliticaMidiExterno()

    def crear_plan(self, ruta: str | Path, nivel: int) -> PlanPistasMidiExterno:
        resultado = self.politica.evaluar(ruta, nivel)
        analisis = resultado.analisis.dict() if resultado.analisis else {}
        if not resultado.permitido:
            return PlanPistasMidiExterno(False, int(nivel), str(ruta), resultado.max_pistas, [], None, None, [], resultado.mensaje_profesor, analisis)

        canales = analisis.get("canales_usados", []) or []
        pistas_con_notas = int(analisis.get("pistas_con_notas", 0) or 0)
        max_pistas = int(resultado.max_pistas)
        pista_ritmo = 0 if 10 in canales else None
        pista_alumno = 1 if pista_ritmo == 0 and pistas_con_notas > 1 else 0 if pistas_con_notas else None

        activas = []
        if pista_ritmo is not None:
            activas.append(pista_ritmo)
        if pista_alumno is not None and pista_alumno not in activas:
            activas.append(pista_alumno)
        for i in range(pistas_con_notas):
            if len(activas) >= max_pistas:
                break
            if i not in activas:
                activas.append(i)
        silenciadas = [i for i in range(pistas_con_notas) if i not in activas]

        if int(nivel) == 3:
            msg = "Plan Nivel 3 creado: base rítmica + una pista musical para el alumno."
        elif int(nivel) == 4:
            msg = "Plan Nivel 4 creado: hasta cuatro pistas activas para trabajar por capas."
        else:
            msg = "Plan Nivel 5+ creado: MIDI completo disponible. El alumno podrá elegir qué pista toca."
        return PlanPistasMidiExterno(True, int(nivel), str(ruta), max_pistas, sorted(activas), pista_alumno, pista_ritmo, sorted(silenciadas), msg, analisis)

    def guardar_plan(self, plan: PlanPistasMidiExterno, nombre: str = "ultimo_plan_pistas.json") -> Path:
        self.ruta_planes.mkdir(parents=True, exist_ok=True)
        path = self.ruta_planes / nombre
        data = plan.dict()
        data["guardado"] = datetime.now().isoformat(timespec="seconds")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def resumen_humano(self, plan: PlanPistasMidiExterno) -> str:
        if not plan.permitido:
            return plan.mensaje_profesor
        partes = [plan.mensaje_profesor]
        if plan.pista_ritmo is not None:
            partes.append(f"Ritmo: pista {plan.pista_ritmo + 1}.")
        if plan.pista_alumno is not None:
            partes.append(f"Alumno toca: pista {plan.pista_alumno + 1}.")
        partes.append("Activas: " + ", ".join(str(i + 1) for i in plan.pistas_activas) + ".")
        if plan.pistas_silenciadas:
            partes.append("Silenciadas por ahora: " + ", ".join(str(i + 1) for i in plan.pistas_silenciadas) + ".")
        return " ".join(partes)
