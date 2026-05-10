class ProfesorDidactico:
    """Genera clase, ejemplo, práctica guiada y corrección antes de evaluar.

    v1.8.6: auditoría de redacción didáctica para que texto visible y narración
    tengan pausas claras. Se evitan frases ambiguas como "Toca Do" en cabeceras
    habladas, porque algunos modelos Piper pueden unirlo como "tocado".
    """

    def clase(self, ejercicio: dict | None, nivel: str) -> str:
        if not ejercicio:
            return "No hay una lección cargada."
        titulo = self._titulo_humano(ejercicio.get("titulo", "Lección"))
        objetivo = self._frase_corta(ejercicio.get("objetivo", ""))
        teoria = self._frase_corta(ejercicio.get("teoria", ""))
        instruccion = self._frase_corta(ejercicio.get("instruccion", ""))
        tipo = ejercicio.get("tipo", "texto")
        pauta = self._pauta_especifica(ejercicio)
        modo = (
            "Esta lección se practicará tocando el teclado MIDI, o usando el piano de la pantalla."
            if tipo in {"midi_nota", "midi_acorde", "midi_secuencia"}
            else "Esta lección se practicará respondiendo por escrito."
        )
        return (
            "MODO CLASE\n"
            f"{titulo}\n\n"
            "Nivel\n"
            f"{self._nivel_humano(nivel)}\n\n"
            "1. ¿Qué vamos a aprender?\n"
            f"{objetivo}\n\n"
            "2. Explicación del profesor\n"
            f"{teoria}\n\n"
            "3. Cómo debes pensarlo\n"
            f"{pauta}\n\n"
            "4. Qué haremos después\n"
            "Primero, verás un ejemplo. Después, practicarás sin que cuente como fallo. "
            "Solo al pulsar 'Hacer ejercicio', se evaluará la respuesta.\n\n"
            "Ejercicio que haremos al final\n"
            f"{instruccion}\n\n"
            f"{modo}"
        )

    def ejemplo(self, ejercicio: dict | None) -> str:
        if not ejercicio:
            return "No hay ejemplo disponible."
        tipo = ejercicio.get("tipo", "texto")
        solucion = self._frase_corta(ejercicio.get("solucion", ""), punto=False)
        titulo = self._titulo_humano(ejercicio.get("titulo", ""))
        if tipo == "midi_nota":
            return (
                "EJEMPLO GUIADO\n"
                f"{titulo}\n\n"
                f"La nota correcta, para este ejercicio, es: {solucion}.\n\n"
                "Escucha la demostración, y mira el teclado. Después, intenta localizar esa misma nota.\n"
                "No pasa nada si fallas durante la práctica. Aquí todavía estamos aprendiendo."
            )
        if tipo == "midi_acorde":
            return (
                "EJEMPLO GUIADO\n"
                f"{titulo}\n\n"
                f"El acorde correcto contiene estas notas: {solucion}.\n\n"
                "Escucha cómo suena el acorde. Después, intenta mantener las notas juntas.\n"
                "El profesor valorará si falta alguna nota, o si has añadido una nota que no corresponde."
            )
        if tipo == "midi_secuencia":
            return (
                "EJEMPLO GUIADO\n"
                f"{titulo}\n\n"
                f"La secuencia correcta es: {solucion}.\n\n"
                "Escucha las notas una detrás de otra. Después, intenta repetirlas con calma, sin correr. "
                "El profesor irá mostrando la secuencia detectada para que veas si vas en orden."
            )
        return (
            "EJEMPLO GUIADO\n"
            f"{titulo}\n\n"
            f"Una respuesta válida sería: {solucion}.\n\n"
            "Antes de contestar, entiende la razón. La respuesta no debe memorizarse sin sentido. "
            "Debe salir de la explicación anterior."
        )

    def practica(self, ejercicio: dict | None) -> str:
        if not ejercicio:
            return "No hay práctica disponible."
        tipo = ejercicio.get("tipo", "texto")
        if tipo == "midi_nota":
            return (
                "PRÁCTICA GUIADA\n"
                "Sin nota de evaluación\n\n"
                "Toca ahora la nota que hemos explicado.\n"
                "Si tocas otra nota, el profesor te dirá cuál ha detectado, y cómo corregirlo.\n\n"
                "Cuando la localices con seguridad, pulsa 'Hacer ejercicio'."
            )
        if tipo == "midi_acorde":
            return (
                "PRÁCTICA GUIADA\n"
                "Sin nota de evaluación\n\n"
                "Mantén pulsadas las notas del acorde.\n"
                "El profesor te dirá qué acorde está detectando, y qué nota falta si la respuesta no está completa.\n\n"
                "Cuando puedas tocarlo de forma estable, pulsa 'Hacer ejercicio'."
            )
        if tipo == "midi_secuencia":
            return (
                "PRÁCTICA GUIADA\n"
                "Sin nota de evaluación\n\n"
                "Toca la secuencia despacio, una nota cada vez.\n"
                "Si vas bien, el profesor te dirá que continúes. Si te equivocas, borrará la secuencia para empezar limpio.\n\n"
                "Cuando la puedas tocar completa, pulsa 'Hacer ejercicio'."
            )
        return (
            "PRÁCTICA GUIADA\n"
            "Sin nota de evaluación\n\n"
            "Piensa la respuesta antes de escribirla. Usa la pista, si lo necesitas.\n"
            "Cuando estés preparado, pulsa 'Hacer ejercicio', y entonces se comprobará oficialmente."
        )

    def ejercicio(self, ejercicio: dict | None) -> str:
        if not ejercicio:
            return "No hay ejercicio cargado."
        instruccion = self._frase_corta(ejercicio.get("instruccion", ""))
        return (
            "EJERCICIO EVALUABLE\n\n"
            f"{instruccion}\n\n"
            "Ahora sí cuenta el resultado.\n"
            "Si aciertas, avanzas. Si fallas, no avanzas todavía: el profesor vuelve a explicar, y te deja repetir."
        )

    def fallo_guiado(self, ejercicio: dict, respuesta: str) -> str:
        solucion = self._frase_corta(ejercicio.get("solucion", ""), punto=False)
        pista = self._frase_corta(ejercicio.get("pista", ""))
        teoria = self._frase_corta(ejercicio.get("teoria", ""))
        return (
            "No avanzamos todavía, pero esto forma parte de la clase.\n\n"
            f"Has respondido, o tocado: {respuesta or '(nada)'}.\n"
            f"Lo que buscábamos era: {solucion}.\n\n"
            f"Vuelve a fijarte en esta idea:\n{teoria}\n\n"
            f"Pista concreta:\n{pista}\n\n"
            "Usa el botón Play del narrador si quieres repetir la explicación. También puedes volver a practicar antes del ejercicio."
        )

    def practica_correcta(self, ejercicio: dict, respuesta: str) -> str:
        solucion = self._frase_corta(ejercicio.get("solucion", ""), punto=False)
        return (
            "Bien. En práctica, lo has localizado correctamente.\n\n"
            f"Detectado: {respuesta}.\n"
            f"Objetivo: {solucion}.\n\n"
            "Ahora pulsa 'Hacer ejercicio', para que cuente oficialmente y puedas avanzar."
        )

    def practica_incorrecta(self, ejercicio: dict, respuesta: str) -> str:
        solucion = self._frase_corta(ejercicio.get("solucion", ""), punto=False)
        pista = self._frase_corta(ejercicio.get("pista", ""))
        return (
            "Todavía no. No cuenta como fallo, porque estás en práctica.\n\n"
            f"Detectado: {respuesta or '(nada)'}.\n"
            f"Objetivo: {solucion}.\n\n"
            f"Pista: {pista}\n\n"
            "Corrige con calma, y vuelve a intentarlo."
        )

    def _pauta_especifica(self, ejercicio: dict) -> str:
        titulo = ejercicio.get("titulo", "").lower()
        solucion = str(ejercicio.get("solucion", ""))
        if "do" in titulo or solucion.lower() == "do":
            return (
                "Busca un grupo de dos teclas negras. Después, mira la tecla blanca que queda justo a la izquierda. "
                "Esa tecla es Do. Este patrón se repite por todo el teclado."
            )
        if "re" in titulo or solucion.lower() == "re":
            return (
                "Busca el grupo de dos teclas negras. Re es la tecla blanca que queda en medio de esas dos teclas negras. "
                "Primero localiza el grupo. Después, coloca el dedo en el centro."
            )
        if "mi" in titulo or solucion.lower() == "mi":
            return (
                "Busca el grupo de dos teclas negras. Mi es la tecla blanca que queda justo a la derecha de ese grupo. "
                "Piensa: izquierda, Do; centro, Re; derecha, Mi."
            )
        if "fa" in titulo or solucion.lower() == "fa":
            return (
                "Busca el grupo de tres teclas negras. Fa está justo antes de ese grupo. "
                "Es la tecla blanca que prepara la entrada al grupo grande."
            )
        if "sol" in titulo or solucion.lower() == "sol":
            return (
                "Busca el grupo de tres teclas negras. Sol queda dentro de esa zona, entre Fa y La. "
                "Localiza primero el grupo grande, y después sitúa la nota con calma."
            )
        if "si" in titulo or solucion.lower() == "si":
            return (
                "Si está justo antes del Do siguiente. Si encuentras un Do, la tecla blanca inmediatamente anterior es Si."
            )
        if "teclas negras" in titulo:
            return (
                "Las teclas negras no están repartidas al azar. Aparecen en grupos de dos, y en grupos de tres. "
                "Ese patrón es el mapa del teclado."
            )
        if "acorde" in titulo:
            return (
                "Un acorde no se toca nota por nota, como una melodía. Sus notas deben sonar juntas, y mantenerse estables."
            )
        if "pulso" in titulo:
            return (
                "El pulso es como el latido de la música. Antes de correr, hay que poder mantenerlo constante."
            )
        if "función" in titulo or "dominante" in titulo:
            return (
                "La función armónica no pregunta solo el nombre del acorde. También pregunta qué papel cumple dentro de la tonalidad."
            )
        return "Primero, entiende el patrón. Después, practica despacio. La velocidad llega cuando el concepto está claro."

    def _frase_corta(self, texto, punto: bool = True) -> str:
        texto = str(texto or "").strip()
        if not texto:
            return texto
        texto = self._normalizar_notas_en_frase(texto)
        if punto and texto[-1] not in ".!?:;":
            texto += "."
        return texto

    def _titulo_humano(self, texto) -> str:
        texto = str(texto or "").strip()
        mapa = {
            "Toca Do": "Toca el Do.",
            "Toca Re": "Toca el Re.",
            "Toca Mi": "Toca el Mi.",
            "Toca Fa": "Toca el Fa.",
            "Toca Sol": "Toca el Sol.",
            "Toca La": "Toca el La.",
            "Toca Si": "Toca el Si.",
        }
        texto = mapa.get(texto, texto)
        texto = self._normalizar_notas_en_frase(texto)
        if texto and texto[-1] not in ".!?:;":
            texto += "."
        return texto

    def _nivel_humano(self, nivel) -> str:
        texto = str(nivel or "").strip().replace("_", " ")
        if not texto:
            return "inicial."
        texto = texto[0].upper() + texto[1:]
        if texto[-1] not in ".!?:;":
            texto += "."
        return texto

    def _normalizar_notas_en_frase(self, texto: str) -> str:
        # Quita comas falsas en expresiones como "Localizar Do, en tu teclado".
        texto = texto.replace("Localizar Do, en tu teclado", "Localizar el Do en tu teclado")
        texto = texto.replace("Localizar Re,", "Localizar el Re,")
        texto = texto.replace("Localizar Mi,", "Localizar el Mi,")
        texto = texto.replace("Localizar Fa,", "Localizar el Fa,")
        texto = texto.replace("Localizar Sol,", "Localizar el Sol,")
        texto = texto.replace("Localizar Si,", "Localizar el Si,")
        texto = texto.replace("Toca Do en", "Toca el Do en")
        return texto
