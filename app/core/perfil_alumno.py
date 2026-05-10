import json
from dataclasses import dataclass, asdict
from pathlib import Path
from app.config import PERFIL_ALUMNO_PATH, DATA_DIR


@dataclass
class PerfilAlumno:
    nombre: str = ""
    tratamiento: str = "masculino"  # masculino, femenino, neutro

    @property
    def valido(self) -> bool:
        return bool((self.nombre or "").strip()) and self.tratamiento in {"masculino", "femenino", "neutro"}

    @property
    def saludo(self) -> str:
        nombre = (self.nombre or "alumno").strip()
        if self.tratamiento == "femenino":
            return f"Hola, {nombre}. Seré tu profesora virtual y te trataré como alumna."
        if self.tratamiento == "masculino":
            return f"Hola, {nombre}. Seré tu profesor virtual y te trataré como alumno."
        return f"Hola, {nombre}. Seré tu profesor virtual y usaré un trato neutro."

    @property
    def alumno_o_alumna(self) -> str:
        if self.tratamiento == "femenino":
            return "alumna"
        if self.tratamiento == "masculino":
            return "alumno"
        return "estudiante"

    @property
    def preparado_o_preparada(self) -> str:
        if self.tratamiento == "femenino":
            return "preparada"
        if self.tratamiento == "masculino":
            return "preparado"
        return "preparado/a"


class GestorPerfilAlumno:
    def __init__(self, ruta: Path = PERFIL_ALUMNO_PATH):
        self.ruta = Path(ruta)
        self.perfil = PerfilAlumno()
        self.cargar()

    def cargar(self) -> PerfilAlumno:
        try:
            if self.ruta.exists():
                datos = json.loads(self.ruta.read_text(encoding="utf-8"))
                self.perfil = PerfilAlumno(
                    nombre=str(datos.get("nombre", "")).strip(),
                    tratamiento=str(datos.get("tratamiento", "masculino")).strip().lower(),
                )
                if self.perfil.tratamiento not in {"masculino", "femenino", "neutro"}:
                    self.perfil.tratamiento = "masculino"
        except Exception:
            self.perfil = PerfilAlumno()
        return self.perfil

    def guardar(self, nombre: str, tratamiento: str) -> PerfilAlumno:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tratamiento = (tratamiento or "masculino").strip().lower()
        if tratamiento not in {"masculino", "femenino", "neutro"}:
            tratamiento = "masculino"
        self.perfil = PerfilAlumno(nombre=(nombre or "").strip(), tratamiento=tratamiento)
        self.ruta.write_text(json.dumps(asdict(self.perfil), ensure_ascii=False, indent=2), encoding="utf-8")
        return self.perfil
