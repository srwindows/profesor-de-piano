class ProfesorVirtual:
    def bienvenida(self, nivel: str) -> str:
        if nivel == "sin_evaluar":
            return "Bienvenido. Primero haremos una pequeña evaluación para ubicar tu nivel."
        return f"Continuamos desde tu nivel actual: {nivel}."

    def explicar_ejercicio(self, ejercicio: dict | None) -> str:
        if not ejercicio:
            return "No hay ejercicios disponibles para este nivel todavía."
        return (
            f"Ejercicio: {ejercicio.get('titulo', 'Sin título')}\n\n"
            f"Objetivo: {ejercicio.get('objetivo', '')}\n\n"
            f"Instrucción: {ejercicio.get('instruccion', '')}"
        )

    def recomendar(self, superado: bool) -> str:
        if superado:
            return "Buen trabajo. El sistema permite avanzar porque el ejercicio está superado."
        return "Antes de avanzar conviene repetir este ejercicio. El progreso queda bloqueado hasta superarlo."
