import json
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, date

from app.config import DATA_DIR


ALUMNOS_DIR = DATA_DIR / "alumnos"


def _slug(texto: str) -> str:
    texto = (texto or "alumno_principal").strip().lower()
    texto = re.sub(r"[^a-z0-9áéíóúüñ]+", "_", texto, flags=re.IGNORECASE)
    texto = texto.strip("_")
    return texto or "alumno_principal"


@dataclass
class DiagnosticoDocente:
    severidad: str
    mensaje: str
    recomendacion: str


class HistorialAlumno:
    """Expediente pedagógico vivo del alumno.

    Guarda datos que el profesor debe consultar para adaptar explicaciones:
    progreso, clases, errores, MIDI, pulso, velocity, recomendaciones y sesiones.
    """

    def __init__(self, alumno_nombre: str = "alumno_principal", base_dir: Path = ALUMNOS_DIR):
        self.alumno_nombre = (alumno_nombre or "alumno_principal").strip() or "alumno_principal"
        self.alumno_id = _slug(self.alumno_nombre)
        self.base_dir = Path(base_dir) / self.alumno_id
        self.sesiones_dir = self.base_dir / "sesiones"
        self.perfil_path = self.base_dir / "perfil.json"
        self.progreso_path = self.base_dir / "progreso.json"
        self.historial_clases_path = self.base_dir / "historial_clases.json"
        self.historial_midi_path = self.base_dir / "historial_midi.json"
        self.errores_path = self.base_dir / "errores_recurrentes.json"
        self.recomendaciones_path = self.base_dir / "recomendaciones.json"
        self._asegurar()

    def _asegurar(self):
        self.sesiones_dir.mkdir(parents=True, exist_ok=True)
        defaults = {
            self.perfil_path: {
                "alumno_id": self.alumno_id,
                "nombre": self.alumno_nombre,
                "creado": datetime.now().isoformat(timespec="seconds"),
                "modo": "pro",
            },
            self.progreso_path: {
                "nivel_actual": 0,
                "clase_actual": "",
                "clases_superadas": [],
                "ejercicios_superados": [],
                "examenes_clase_superados": [],
                "examenes_globales_superados": [],
                "tiempo_total_estudio_segundos": 0,
                "ultima_actualizacion": datetime.now().isoformat(timespec="seconds"),
            },
            self.historial_clases_path: {"eventos": []},
            self.historial_midi_path: {
                "eventos": [],
                "estadisticas": {
                    "notas_total": 0,
                    "aciertos": 0,
                    "errores": 0,
                    "velocity_media": 0.0,
                    "fuera_de_pulso": 0,
                    "a_tiempo": 0,
                    "acordes_total": 0,
                    "acordes_correctos": 0,
                    "acordes_incompletos": 0,
                    "tiempo_reaccion_media_ms": 0.0,
                    "simultaneidad_media_ms": 0.0,
                    "notas_simultaneas": 0,
                    "notas_sobrantes": 0,
                    "notas_faltantes": 0,
                }
            },
            self.errores_path: {
                "notas_falladas": {},
                "errores_por_tipo": {},
                "errores_por_clase": {},
                "observaciones": []
            },
            self.recomendaciones_path: {
                "actuales": [],
                "historico": []
            },
        }
        for path, data in defaults.items():
            if not path.exists():
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _leer(self, path: Path, defecto):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return defecto

    def _guardar(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _sesion_path(self) -> Path:
        return self.sesiones_dir / f"{date.today().isoformat()}.json"

    def registrar_evento_sesion(self, tipo: str, detalle: dict):
        path = self._sesion_path()
        data = self._leer(path, {"fecha": date.today().isoformat(), "eventos": []})
        data.setdefault("eventos", []).append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tipo": tipo,
            "detalle": detalle or {}
        })
        data["eventos"] = data["eventos"][-1000:]
        self._guardar(path, data)

    def registrar_clase(self, clase_id: str, titulo: str = "", evento: str = "clase", correcto: bool | None = None, detalle: dict | None = None):
        data = self._leer(self.historial_clases_path, {"eventos": []})
        item = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "clase_id": clase_id,
            "titulo": titulo,
            "evento": evento,
            "correcto": correcto,
            "detalle": detalle or {}
        }
        data.setdefault("eventos", []).append(item)
        data["eventos"] = data["eventos"][-1000:]
        self._guardar(self.historial_clases_path, data)
        self.registrar_evento_sesion("clase", item)

        progreso = self._leer(self.progreso_path, {})
        progreso["clase_actual"] = clase_id or progreso.get("clase_actual", "")
        if evento in {"examen_clase_superado", "clase_superada"} and clase_id:
            lista = list(progreso.get("clases_superadas", []))
            if clase_id not in lista:
                lista.append(clase_id)
            progreso["clases_superadas"] = lista
            examenes = list(progreso.get("examenes_clase_superados", []))
            if clase_id not in examenes:
                examenes.append(clase_id)
            progreso["examenes_clase_superados"] = examenes
        progreso["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
        self._guardar(self.progreso_path, progreso)

    def registrar_ejercicio(self, ejercicio_id: str, clase_id: str = "", correcto: bool = False, tipo: str = "", detalle: dict | None = None):
        progreso = self._leer(self.progreso_path, {})
        if correcto and ejercicio_id:
            lista = list(progreso.get("ejercicios_superados", []))
            if ejercicio_id not in lista:
                lista.append(ejercicio_id)
            progreso["ejercicios_superados"] = lista
        progreso["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
        self._guardar(self.progreso_path, progreso)

        self.registrar_clase(
            clase_id=clase_id,
            titulo="",
            evento="ejercicio_superado" if correcto else "ejercicio_fallado",
            correcto=correcto,
            detalle={"ejercicio_id": ejercicio_id, "tipo": tipo, **(detalle or {})}
        )

    def registrar_midi_evento(
        self,
        nota: str = "",
        velocity: int | None = None,
        canal: int | None = None,
        origen: str = "midi",
        esperado: str | list[str] | None = None,
        correcto: bool | None = None,
        diferencia_ms: float | None = None,
        en_pulso: bool | None = None,
        tipo: str = "nota",
        mensaje: str = "",
        contexto: dict | None = None,
    ):
        data = self._leer(self.historial_midi_path, {"eventos": [], "estadisticas": {}})
        stats = data.setdefault("estadisticas", {})
        evento = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "tipo": tipo,
            "origen": origen,
            "nota": nota,
            "velocity": velocity,
            "canal": canal,
            "esperado": esperado,
            "correcto": correcto,
            "diferencia_ms": diferencia_ms,
            "en_pulso": en_pulso,
            "mensaje": mensaje,
            "contexto": contexto or {}
        }
        data.setdefault("eventos", []).append(evento)
        data["eventos"] = data["eventos"][-2000:]

        if tipo == "acorde":
            stats["acordes_total"] = int(stats.get("acordes_total", 0)) + 1
            if correcto is True:
                stats["acordes_correctos"] = int(stats.get("acordes_correctos", 0)) + 1
            elif correcto is False:
                stats["acordes_incompletos"] = int(stats.get("acordes_incompletos", 0)) + 1
        else:
            stats["notas_total"] = int(stats.get("notas_total", 0)) + 1
            if correcto is True:
                stats["aciertos"] = int(stats.get("aciertos", 0)) + 1
            elif correcto is False:
                stats["errores"] = int(stats.get("errores", 0)) + 1
            if en_pulso is True:
                stats["a_tiempo"] = int(stats.get("a_tiempo", 0)) + 1
            elif en_pulso is False:
                stats["fuera_de_pulso"] = int(stats.get("fuera_de_pulso", 0)) + 1

        if velocity is not None:
            total_prev = max(0, int(stats.get("notas_total", 1)) - 1)
            media_prev = float(stats.get("velocity_media", 0.0))
            stats["velocity_media"] = round(((media_prev * total_prev) + int(velocity)) / max(1, total_prev + 1), 2)

        contexto = contexto or {}
        tiempo_reaccion = contexto.get("tiempo_reaccion_ms")
        if tiempo_reaccion is not None:
            total_prev = max(0, int(stats.get("notas_total", 1)) - 1)
            media_prev = float(stats.get("tiempo_reaccion_media_ms", 0.0))
            stats["tiempo_reaccion_media_ms"] = round(((media_prev * total_prev) + float(tiempo_reaccion)) / max(1, total_prev + 1), 2)

        simultaneidad = contexto.get("simultaneidad_ms")
        if simultaneidad is not None:
            total_sim = int(stats.get("notas_simultaneas", 0)) + 1
            media_prev = float(stats.get("simultaneidad_media_ms", 0.0))
            stats["simultaneidad_media_ms"] = round(((media_prev * (total_sim - 1)) + float(simultaneidad)) / max(1, total_sim), 2)
            stats["notas_simultaneas"] = total_sim

        if contexto.get("notas_sobrantes"):
            stats["notas_sobrantes"] = int(stats.get("notas_sobrantes", 0)) + len(contexto.get("notas_sobrantes", []))
        if contexto.get("notas_faltantes"):
            stats["notas_faltantes"] = int(stats.get("notas_faltantes", 0)) + len(contexto.get("notas_faltantes", []))

        self._guardar(self.historial_midi_path, data)
        self.registrar_evento_sesion("midi", evento)

        if correcto is False:
            self.registrar_error(
                tipo="midi_" + tipo,
                clave=str(nota or "desconocida"),
                detalle={"esperado": esperado, "velocity": velocity, "diferencia_ms": diferencia_ms, "mensaje": mensaje}
            )

        self._actualizar_recomendaciones()

    def registrar_error(self, tipo: str, clave: str, detalle: dict | None = None):
        data = self._leer(self.errores_path, {"notas_falladas": {}, "errores_por_tipo": {}, "errores_por_clase": {}, "observaciones": []})
        data.setdefault("errores_por_tipo", {})
        data["errores_por_tipo"][tipo] = int(data["errores_por_tipo"].get(tipo, 0)) + 1

        if clave:
            data.setdefault("notas_falladas", {})
            data["notas_falladas"][clave] = int(data["notas_falladas"].get(clave, 0)) + 1

        data.setdefault("observaciones", []).append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tipo": tipo,
            "clave": clave,
            "detalle": detalle or {}
        })
        data["observaciones"] = data["observaciones"][-500:]
        self._guardar(self.errores_path, data)
        self.registrar_evento_sesion("error", {"tipo": tipo, "clave": clave, "detalle": detalle or {}})

    def _actualizar_recomendaciones(self):
        midi = self._leer(self.historial_midi_path, {"estadisticas": {}})
        errores = self._leer(self.errores_path, {})
        stats = midi.get("estadisticas", {})
        actuales = []

        if int(stats.get("fuera_de_pulso", 0)) >= 3:
            actuales.append({
                "tipo": "pulso",
                "prioridad": "alta",
                "texto": "Reforzar pulso con metrónomo lento antes de avanzar."
            })
        if int(stats.get("errores", 0)) >= 3:
            actuales.append({
                "tipo": "lectura",
                "prioridad": "media",
                "texto": "Repetir lectura en pizarra antes de pedir velocidad."
            })
        if float(stats.get("velocity_media", 0.0)) >= 105:
            actuales.append({
                "tipo": "velocity",
                "prioridad": "media",
                "texto": "Trabajar pulsación más suave y controlada."
            })

        notas = errores.get("notas_falladas", {})
        if notas:
            peor = sorted(notas.items(), key=lambda x: x[1], reverse=True)[0]
            if peor[1] >= 2:
                actuales.append({
                    "tipo": "nota_recurrente",
                    "prioridad": "media",
                    "texto": f"Repasar la nota {peor[0]}: aparece como fallo recurrente."
                })

        rec = self._leer(self.recomendaciones_path, {"actuales": [], "historico": []})
        rec["actuales"] = actuales
        if actuales:
            rec.setdefault("historico", []).append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "actuales": actuales
            })
            rec["historico"] = rec["historico"][-200:]
        self._guardar(self.recomendaciones_path, rec)

    def registrar_observacion_pro(self, entrada: str, observacion: str, detalle: dict | None = None):
        """Guarda observaciones didácticas de cámara/sonido sin guardar vídeo/audio."""
        data = self._leer(self.errores_path, {"notas_falladas": {}, "errores_por_tipo": {}, "errores_por_clase": {}, "observaciones": []})
        item = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tipo": f"observacion_{entrada}",
            "clave": entrada,
            "detalle": {
                "observacion": observacion,
                "sin_grabacion": True,
                **(detalle or {})
            }
        }
        data.setdefault("observaciones", []).append(item)
        data["observaciones"] = data["observaciones"][-500:]
        self._guardar(self.errores_path, data)
        self.registrar_evento_sesion("observacion_pro", item)

    def registrar_hanon(self, resultado: dict):
        """Guarda un resultado Hanon completo en el expediente del alumno."""
        item = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            **(resultado or {}),
        }
        progreso = self._leer(self.progreso_path, {})
        hanon = progreso.setdefault("hanon", {"superados": [], "historial": []})
        hanon.setdefault("historial", []).append(item)
        hanon["historial"] = hanon["historial"][-500:]
        if item.get("aprobado") and item.get("hanon_id"):
            superados = list(hanon.get("superados", []))
            if item["hanon_id"] not in superados:
                superados.append(item["hanon_id"])
            hanon["superados"] = superados
        progreso["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
        self._guardar(self.progreso_path, progreso)
        self.registrar_evento_sesion("hanon", item)

    def resumen_docente(self) -> str:
        progreso = self._leer(self.progreso_path, {})
        midi = self._leer(self.historial_midi_path, {"estadisticas": {}})
        errores = self._leer(self.errores_path, {})
        rec = self._leer(self.recomendaciones_path, {"actuales": []})

        stats = midi.get("estadisticas", {})
        clases = len(progreso.get("clases_superadas", []))
        ejercicios = len(progreso.get("ejercicios_superados", []))
        notas_total = int(stats.get("notas_total", 0))
        aciertos = int(stats.get("aciertos", 0))
        errores_n = int(stats.get("errores", 0))
        fuera = int(stats.get("fuera_de_pulso", 0))
        velocity_media = float(stats.get("velocity_media", 0.0) or 0.0)

        notas_falladas = errores.get("notas_falladas", {})
        peor_nota = ""
        if notas_falladas:
            peor_nota = sorted(notas_falladas.items(), key=lambda x: x[1], reverse=True)[0][0]

        lineas = [
            f"Expediente de {self.alumno_nombre}: {clases} clases superadas, {ejercicios} ejercicios superados.",
            f"MIDI registrado: {notas_total} notas, {aciertos} aciertos, {errores_n} errores.",
        ]
        if fuera:
            lineas.append(f"Pulso: {fuera} entradas fuera de pulso registradas.")
        if velocity_media:
            lineas.append(f"Velocity media: {velocity_media:.1f}.")
        tiempo_reaccion = float(stats.get("tiempo_reaccion_media_ms", 0.0) or 0.0)
        if tiempo_reaccion:
            lineas.append(f"Tiempo de reacción medio: {tiempo_reaccion:.1f} ms.")
        simultaneidad = float(stats.get("simultaneidad_media_ms", 0.0) or 0.0)
        if simultaneidad:
            lineas.append(f"Simultaneidad media en acordes/notas múltiples: {simultaneidad:.1f} ms.")
        if peor_nota:
            lineas.append(f"Nota a reforzar: {peor_nota}.")
        observaciones = errores.get("observaciones", [])
        obs_pro = [o for o in observaciones if str(o.get("tipo", "")).startswith("observacion_")]
        if obs_pro:
            ultima = obs_pro[-1].get("detalle", {}).get("observacion", "")
            if ultima:
                lineas.append(f"Última observación Pro: {ultima}")
        actuales = rec.get("actuales", [])
        if actuales:
            lineas.append("Recomendación actual: " + actuales[0].get("texto", "repasar con calma."))
        else:
            lineas.append("Recomendación actual: continuar con calma y registrar más datos.")
        return "\n".join(lineas)

    def expediente_completo(self) -> dict:
        return {
            "perfil": self._leer(self.perfil_path, {}),
            "progreso": self._leer(self.progreso_path, {}),
            "historial_clases": self._leer(self.historial_clases_path, {}),
            "historial_midi": self._leer(self.historial_midi_path, {}),
            "errores_recurrentes": self._leer(self.errores_path, {}),
            "recomendaciones": self._leer(self.recomendaciones_path, {}),
        }
