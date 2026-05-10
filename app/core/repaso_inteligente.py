class RepasoInteligente:
    """Selecciona ejercicios de repaso a partir de fallos reales del alumno.

    No usa internet. Trabaja con el historial local y con la lista de ejercicios
    del proyecto. La idea es que el profesor no avance sin atender los puntos
    débiles detectados.
    """

    def __init__(self, repo):
        self.repo = repo

    def _mapa_ejercicios(self):
        return {e.get("id"): e for e in getattr(self.repo, "ejercicios", []) if e.get("id")}

    def ejercicio_por_id(self, ejercicio_id: str):
        return self._mapa_ejercicios().get(ejercicio_id)

    def indice_en_nivel(self, ejercicio: dict) -> int:
        nivel = ejercicio.get("nivel", "inicial")
        lista = [e for e in getattr(self.repo, "ejercicios", []) if e.get("nivel") == nivel]
        for i, item in enumerate(lista):
            if item.get("id") == ejercicio.get("id"):
                return i
        return 0

    def seleccionar(self, estado, nivel_actual: str = "inicial"):
        """Devuelve el mejor ejercicio de repaso o None."""
        mapa = self._mapa_ejercicios()

        # 1. Prioridad: cola de repasos pendientes, de más reciente a más antiguo.
        for eid in list(getattr(estado, "repasos_pendientes", []) or []):
            ejercicio = mapa.get(eid)
            if ejercicio:
                return ejercicio, "repaso pendiente por fallo reciente"

        # 2. Si no hay cola, buscar el ejercicio con más fallos acumulados.
        fallos = getattr(estado, "mapa_fallos", {}) or {}
        if fallos:
            candidatos = sorted(fallos.items(), key=lambda kv: int(kv[1]), reverse=True)
            for eid, _ in candidatos:
                ejercicio = mapa.get(eid)
                if ejercicio:
                    return ejercicio, "ejercicio con más fallos acumulados"

        # 3. Si no hay fallos, usar el ejercicio anterior del nivel actual.
        lista = [e for e in getattr(self.repo, "ejercicios", []) if e.get("nivel") == nivel_actual]
        if lista:
            indice = max(0, min(int(getattr(estado, "indice_ejercicio", 0) or 0), len(lista) - 1))
            return lista[max(0, indice - 1)], "repaso preventivo del ejercicio anterior"

        return None, "sin ejercicios disponibles"

    def plan_texto(self, estado, nivel_actual: str = "inicial") -> str:
        total_fallos = sum(int(v) for v in (getattr(estado, "mapa_fallos", {}) or {}).values())
        total_aciertos = sum(int(v) for v in (getattr(estado, "mapa_aciertos", {}) or {}).values())
        cola = list(getattr(estado, "repasos_pendientes", []) or [])
        seleccion, motivo = self.seleccionar(estado, nivel_actual)
        titulo = seleccion.get("titulo", "Sin ejercicio") if seleccion else "No hay repaso pendiente"

        lineas = [
            "REPASO INTELIGENTE",
            "",
            f"Nivel actual: {nivel_actual}",
            f"Aciertos registrados: {total_aciertos}",
            f"Fallos registrados: {total_fallos}",
            f"Repasos pendientes: {len(cola)}",
            "",
            f"Siguiente repaso recomendado: {titulo}",
            f"Motivo: {motivo}.",
        ]

        if seleccion:
            lineas.extend([
                "",
                "Qué hará el profesor:",
                "1. Volverá a explicar la idea clave.",
                "2. Mostrará un ejemplo.",
                "3. Permitirá práctica sin penalización.",
                "4. Solo contará el resultado cuando pulses 'Hacer ejercicio'.",
            ])
        else:
            lineas.extend([
                "",
                "No hay errores pendientes. El profesor recomienda continuar con la clase actual y mantener la práctica diaria.",
            ])

        return "\n".join(lineas)
