from app.core.datos import RepositorioDatos

NIVELES_ORDEN = ["nivel_0", "nivel_1", "nivel_2"]

class MotorEjercicios:
    def __init__(self, repo: RepositorioDatos):
        self.repo = repo
        self.ejercicio_actual = None
        self.lista_actual = []
        self.modo_examen = False

    def ejercicios_de_nivel(self, nivel_id: str):
        return [e for e in self.repo.ejercicios if e.get("nivel") == nivel_id]

    def ejercicios_por_ids(self, ids: list[str]):
        mapa = {e.get("id"): e for e in self.repo.ejercicios}
        return [mapa[i] for i in ids if i in mapa]

    def cargar_examen(self, ids: list[str], indice: int = 0):
        self.modo_examen = True
        self.lista_actual = self.ejercicios_por_ids(ids)
        if not self.lista_actual:
            self.ejercicio_actual = {"titulo":"Examen vacío", "instruccion":"No hay ejercicios en este examen.", "solucion":""}
            return self.ejercicio_actual, 0, 0
        indice = max(0, min(indice, len(self.lista_actual)-1))
        self.ejercicio_actual = self.lista_actual[indice]
        return self.ejercicio_actual, indice, len(self.lista_actual)

    def cargar_ejercicio(self, nivel_id: str, indice: int = 0):
        self.modo_examen = False
        self.lista_actual = self.ejercicios_de_nivel(nivel_id)
        if not self.lista_actual:
            self.ejercicio_actual = {"titulo":"Sin ejercicios", "instruccion":"No hay ejercicios para este nivel.", "solucion":""}
            return self.ejercicio_actual, nivel_id, 0, 0
        if indice >= len(self.lista_actual):
            nivel_id, indice = self._siguiente_nivel(nivel_id)
            self.lista_actual = self.ejercicios_de_nivel(nivel_id)
        indice = max(0, min(indice, len(self.lista_actual)-1))
        self.ejercicio_actual = self.lista_actual[indice]
        return self.ejercicio_actual, nivel_id, indice, len(self.lista_actual)

    def _siguiente_nivel(self, nivel_id: str):
        try:
            pos = NIVELES_ORDEN.index(nivel_id)
        except ValueError:
            return "inicial", 0
        if pos < len(NIVELES_ORDEN)-1:
            return NIVELES_ORDEN[pos+1], 0
        return nivel_id, 0

    def progreso_nivel_porcentaje(self, indice: int):
        total = max(1, len(self.lista_actual))
        return int((min(indice, total) / total) * 100)
