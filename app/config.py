from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"
VOICES_DIR = BASE_DIR / "voices"
PIPER_VOICES_DIR = VOICES_DIR / "piper"

PROGRESO_PATH = DATA_DIR / "progreso_usuario.json"
NIVELES_PATH = DATA_DIR / "niveles.json"
EJERCICIOS_PATH = DATA_DIR / "ejercicios.json"
AJUSTES_PATH = DATA_DIR / "ajustes_usuario.json"
PERFIL_ALUMNO_PATH = DATA_DIR / "perfil_alumno.json"
LECCIONES_PATH = DATA_DIR / "lecciones.json"
EXAMENES_PATH = DATA_DIR / "examenes.json"

APP_NOMBRE = "Profesor de Piano IA"
APP_VERSION = "4.1.15-lite-hotfix-niveles-1-2-completos"

LECCIONES_NIVEL_0_PATH = DATA_DIR / "lecciones_nivel_0.json"
PROGRESO_ALUMNO_PATH = DATA_DIR / "progreso_alumno.json"
