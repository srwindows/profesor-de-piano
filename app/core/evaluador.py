class Evaluador:
    def evaluar_respuesta_texto(self, respuesta: str, solucion: str) -> tuple[bool, str]:
        normalizada = respuesta.strip().lower()
        solucion_normalizada = solucion.strip().lower()
        if normalizada == solucion_normalizada:
            return True, "Correcto. Puedes avanzar."
        return False, f"No está superado todavía. Respuesta esperada: {solucion}. Repasa y vuelve a intentarlo."

    def evaluar_prueba_inicial(self, aciertos: int) -> str:
        if aciertos <= 3:
            return "nivel_0"
        if aciertos <= 6:
            return "nivel_1"
        return "nivel_2"
