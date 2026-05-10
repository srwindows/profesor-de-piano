from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR
from app.core.midi_didactico import MidiDidacticoParser, PiezaMidiDidactica


HANON_DIR = DATA_DIR / "hanon"
INDICE_HANON_PATH = HANON_DIR / "indice_hanon.json"
CURSO_HANON_PATH = HANON_DIR / "curso_hanon_completo.json"
PROGRESO_HANON_PATH = HANON_DIR / "progreso_hanon.json"


@dataclass
class ResultadoHanon:
    hanon_id: str
    puntuacion: int
    aprobado: bool
    notas_correctas_pct: int
    pulso_pct: int
    velocity_score: int
    duracion_score: int
    errores_recurrentes: list[str]
    recomendacion: str


class GestorHanon:
    """Carga y evalúa el paquete Hanon sin interferir con el curso principal."""

    def __init__(self, base_dir: Path | None = None, progreso_path: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else DATA_DIR.parent
        self.hanon_dir = self.base_dir / "data" / "hanon"
        self.indice_path = self.hanon_dir / "indice_hanon.json"
        self.curso_path = self.hanon_dir / "curso_hanon_completo.json"
        self.progreso_path = progreso_path or (self.hanon_dir / "progreso_hanon.json")
        self.parser = MidiDidacticoParser()
        self._indice_cache: dict | None = None
        self._curso_cache: dict | None = None

    def _leer_json(self, ruta: Path, defecto):
        try:
            if ruta.exists():
                return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            pass
        return defecto

    def _resolver(self, ruta: str | Path | None) -> Path:
        p = Path(str(ruta or ""))
        return p if p.is_absolute() else self.base_dir / p

    def disponible(self) -> tuple[bool, str]:
        faltan = []
        if not self.indice_path.exists():
            faltan.append(str(self.indice_path))
        if not self.curso_path.exists():
            faltan.append(str(self.curso_path))
        if faltan:
            return False, "Faltan archivos Hanon: " + "; ".join(faltan)
        return True, ""

    def cargar_indice(self) -> dict:
        ok, msg = self.disponible()
        if not ok:
            return {"error": msg, "niveles": [], "ejercicios": []}
        if self._indice_cache is None:
            self._indice_cache = self._leer_json(self.indice_path, {"niveles": [], "ejercicios": []})
        return self._indice_cache

    def cargar_curso(self) -> dict:
        ok, msg = self.disponible()
        if not ok:
            return {"error": msg, "clases": []}
        if self._curso_cache is None:
            self._curso_cache = self._leer_json(self.curso_path, {"clases": []})
        return self._curso_cache

    def cargar_progreso(self) -> dict:
        datos = self._leer_json(self.progreso_path, {})
        datos.setdefault("superados", [])
        datos.setdefault("resultados", {})
        datos.setdefault("examenes_nivel", {})
        datos.setdefault("historial", [])
        return datos

    def guardar_progreso(self, datos: dict):
        self.progreso_path.parent.mkdir(parents=True, exist_ok=True)
        datos["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
        self.progreso_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    def clases(self) -> list[dict]:
        clases = list((self.cargar_curso() or {}).get("clases", []) or [])
        return sorted([c for c in clases if isinstance(c, dict)], key=lambda x: int(x.get("orden", 9999) or 9999))

    def niveles(self) -> list[dict]:
        return list((self.cargar_indice() or {}).get("niveles", []) or [])

    def clase_por_id(self, hanon_id: str) -> dict | None:
        hanon_id = str(hanon_id or "")
        return next((c for c in self.clases() if c.get("id") == hanon_id), None)

    def estado_clase(self, clase: dict, progreso: dict | None = None) -> str:
        progreso = progreso or self.cargar_progreso()
        hanon_id = str(clase.get("id", ""))
        orden = int(clase.get("orden", 0) or 0)
        superados = set(progreso.get("superados", []))
        resultados = progreso.get("resultados", {})
        if hanon_id in superados:
            return "superado"
        if resultados.get(hanon_id, {}).get("en_practica"):
            return "en práctica"
        if orden <= 1:
            return "disponible"
        previo = f"hanon_{orden - 1:02d}"
        return "disponible" if previo in superados else "bloqueado"

    def estado_por_niveles(self) -> list[dict]:
        progreso = self.cargar_progreso()
        clases = {c.get("id"): c for c in self.clases()}
        salida = []
        for nivel in self.niveles():
            item = dict(nivel)
            ejercicios = []
            for hid in nivel.get("ejercicios", []) or []:
                clase = dict(clases.get(hid, {"id": hid, "titulo": hid, "objetivo": ""}))
                clase["estado_hanon"] = self.estado_clase(clase, progreso)
                ejercicios.append(clase)
            item["ejercicios_detalle"] = ejercicios
            salida.append(item)
        return salida

    def cargar_modelo(self, hanon_id: str) -> dict:
        clase = self.clase_por_id(hanon_id)
        if not clase:
            raise ValueError(f"No existe {hanon_id} en curso_hanon_completo.json")
        ruta = self._resolver(clase.get("modelo"))
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el modelo Hanon: {ruta}")
        modelo = self._leer_json(ruta, {})
        modelo["_clase"] = clase
        modelo["_modelo_path"] = str(ruta)
        return modelo

    def cargar_recurso_json(self, modelo: dict, clave: str, defecto=None):
        ruta = self._resolver((modelo.get("archivos") or {}).get(clave))
        if not ruta.exists():
            return defecto if defecto is not None else {}
        return self._leer_json(ruta, defecto if defecto is not None else {})

    def cargar_pieza_demo(self, modelo: dict) -> PiezaMidiDidactica:
        ruta = self._resolver((modelo.get("archivos") or {}).get("midi_demo"))
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el MIDI demo Hanon: {ruta}")
        meta = {
            "id": modelo.get("id", ruta.stem),
            "titulo": modelo.get("titulo", ruta.stem),
            "tempo": (modelo.get("tempo") or {}).get("bpm_inicial", 60),
            "compas": (modelo.get("datos_musicales") or {}).get("compas", "4/4"),
        }
        return self.parser.parse_file(ruta, meta)

    def notas_fallback(self, modelo: dict) -> list[dict]:
        try:
            pieza = self.cargar_pieza_demo(modelo)
            return [n for n in pieza.notas_dict()]
        except Exception:
            datos = modelo.get("datos_musicales") or {}
            notas = datos.get("patron_mano_derecha_primer_compas") or []
            return [
                {"nota": self._nota_es_a_audio(n), "inicio_ms": i * 500, "duracion_ms": 420, "velocity": 80, "pulso": (i % 4) + 1, "compas": i // 4 + 1}
                for i, n in enumerate(notas)
            ]

    def _nota_es_a_audio(self, nota: str) -> str:
        mapa = {"Do": "C", "Re": "D", "Mi": "E", "Fa": "F", "Sol": "G", "La": "A", "Si": "B"}
        texto = str(nota or "")
        for es, en in mapa.items():
            texto = texto.replace(es, en)
        return texto

    def iniciar_practica(self, hanon_id: str):
        progreso = self.cargar_progreso()
        progreso.setdefault("resultados", {}).setdefault(hanon_id, {})["en_practica"] = True
        self.guardar_progreso(progreso)

    def registrar_resultado(self, resultado: ResultadoHanon, bpm: int = 60):
        progreso = self.cargar_progreso()
        item = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "hanon_id": resultado.hanon_id,
            "bpm": bpm,
            "nota_final": resultado.puntuacion,
            "notas_correctas": resultado.notas_correctas_pct,
            "pulso": resultado.pulso_pct,
            "velocity": resultado.velocity_score,
            "duracion": resultado.duracion_score,
            "errores_recurrentes": resultado.errores_recurrentes,
            "recomendacion": resultado.recomendacion,
            "aprobado": resultado.aprobado,
        }
        progreso.setdefault("resultados", {})[resultado.hanon_id] = item
        progreso.setdefault("historial", []).append(item)
        progreso["historial"] = progreso["historial"][-500:]
        if resultado.aprobado and resultado.hanon_id not in progreso.setdefault("superados", []):
            progreso["superados"].append(resultado.hanon_id)
        self._actualizar_examen_nivel(progreso, resultado.hanon_id)
        self.guardar_progreso(progreso)
        return item

    def _actualizar_examen_nivel(self, progreso: dict, hanon_id: str):
        clase = self.clase_por_id(hanon_id) or {}
        nivel = int(clase.get("nivel", 0) or 0)
        if not nivel:
            return
        ids = [c.get("id") for c in self.clases() if int(c.get("nivel", 0) or 0) == nivel]
        if ids and all(h in set(progreso.get("superados", [])) for h in ids):
            progreso.setdefault("examenes_nivel", {})[str(nivel)] = {
                "estado": "disponible",
                "fecha_desbloqueo": datetime.now().isoformat(timespec="seconds"),
            }

    def evaluar_eventos(self, hanon_id: str, eventos: list[dict], notas_objetivo: list[dict], rubrica: dict | None = None) -> ResultadoHanon:
        rubrica = rubrica or {}
        ventana = 120
        for c in rubrica.get("criterios", []) or []:
            if c.get("id") == "pulso":
                ventana = int(c.get("ventana_ms", ventana) or ventana)

        # La práctica Hanon puede corregirse antes de terminar todos los eventos.
        # Antes se calculaba total con min(len(objetivo), len(eventos)) y después
        # se forzaba a 1; si eventos estaba vacío o era más corto, se hacía
        # eventos[0] / eventos[i] y PyQt lanzaba IndexError.
        # Ahora se evalúa la secuencia completa: los eventos que faltan cuentan
        # como "sin_nota" y las notas de más cuentan como error, sin romper la app.
        eventos = [e for e in (eventos or []) if isinstance(e, dict)]
        notas_objetivo = [n for n in (notas_objetivo or []) if isinstance(n, dict)]
        total = max(1, max(len(notas_objetivo), len(eventos)))

        correctas = 0
        en_pulso = 0
        velocidades = []
        duraciones = []
        errores = {}
        for i in range(total):
            esperado_item = notas_objetivo[i] if i < len(notas_objetivo) else {}
            ev = eventos[i] if i < len(eventos) else {}
            esperado = str((esperado_item or {}).get("nota", "")).upper()
            recibido = str((ev or {}).get("nota", "")).upper()
            diff = abs(float((ev or {}).get("diferencia_ms", 9999) or 9999))

            if esperado and recibido and recibido == esperado:
                correctas += 1
            else:
                if esperado and not recibido:
                    clave_error = "sin_nota"
                elif recibido and not esperado:
                    clave_error = f"nota_extra:{recibido}"
                else:
                    clave_error = recibido or "sin_nota"
                errores[clave_error] = errores.get(clave_error, 0) + 1

            if ev and diff <= ventana:
                en_pulso += 1
            if ev.get("velocity") is not None:
                velocidades.append(int(ev.get("velocity") or 0))
            if ev.get("duracion_ms") is not None:
                duraciones.append(float(ev.get("duracion_ms") or 0))

        notas_pct = int(round(correctas * 100 / total))
        pulso_pct = int(round(en_pulso * 100 / total))
        if len(velocidades) >= 2:
            desv = statistics.pstdev(velocidades)
            velocity_score = max(0, min(100, int(round(100 - (desv * 3)))))
        else:
            velocity_score = 70 if velocidades else 50
        if len(duraciones) >= 2:
            media = max(1.0, statistics.mean(duraciones))
            duracion_score = max(0, min(100, int(round(100 - (statistics.pstdev(duraciones) / media) * 100))))
        else:
            duracion_score = 70
        puntuacion = int(round(notas_pct * 0.35 + pulso_pct * 0.25 + velocity_score * 0.20 + duracion_score * 0.10 + 10))
        aprobado_desde = int(rubrica.get("aprobado_desde", 80) or 80)
        recurrentes = [k for k, _v in sorted(errores.items(), key=lambda x: x[1], reverse=True)[:5]]
        recomendacion = self.recomendacion(notas_pct, pulso_pct, velocity_score, duracion_score, rubrica)
        return ResultadoHanon(hanon_id, puntuacion, puntuacion >= aprobado_desde, notas_pct, pulso_pct, velocity_score, duracion_score, recurrentes, recomendacion)

    def recomendacion(self, notas_pct: int, pulso_pct: int, velocity_score: int, duracion_score: int, rubrica: dict | None = None) -> str:
        fb = (rubrica or {}).get("feedback", {}) if isinstance(rubrica, dict) else {}
        if notas_pct < 90:
            return fb.get("nota_incorrecta", "Repetir lento mirando la nota activa.")
        if pulso_pct < 80:
            return fb.get("fuera_de_pulso", "Trabajar con metrónomo más lento.")
        if velocity_score < 75:
            return fb.get("velocity_irregular", "Trabajar relajación e igualdad de ataque.")
        if duracion_score < 75:
            return "Tocar más ligado y controlar la duración de cada nota."
        return fb.get("aprobado", "Ejercicio superado. Puedes avanzar.")
