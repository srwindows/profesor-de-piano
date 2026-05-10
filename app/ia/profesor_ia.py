class ProfesorIA:
    """Capa pedagógica local para explicar aciertos, fallos, repasos y exámenes.

    No depende de internet. Más adelante se podrá conectar a un modelo IA externo/local,
    pero esta clase ya centraliza la lógica de profesor.
    """

    def explicar_fallo(self, ejercicio: dict, respuesta: str) -> str:
        return (
            "Vamos a corregirlo sin avanzar todavía.\n\n"
            f"Tu respuesta: {respuesta or '(vacía)'}\n"
            f"Pista: {ejercicio.get('pista', '')}\n\n"
            f"Recordatorio: {ejercicio.get('teoria', '')}"
        )

    def explicar_acierto(self, ejercicio: dict) -> str:
        return (
            "Correcto. Has superado este punto y puedes avanzar.\n\n"
            f"Idea clave: {ejercicio.get('objetivo', '')}"
        )

    def decidir_repaso(self, racha: int, fallos: int) -> bool:
        return fallos > 0 and (racha == 0 or fallos % 3 == 0)

    def responder_interactivo(self, pregunta: str, contexto: str = "", perfil=None, pantalla: str = "") -> str:
        """Respuesta local en tiempo real para el profesor virtual.

        Es una IA pedagógica local basada en contexto: interpreta la pregunta,
        recuerda la pantalla activa y responde como profesor. No requiere internet.
        Más adelante esta función puede conectarse a un modelo externo/local.
        """
        pregunta_l = (pregunta or "").strip().lower()
        nombre = getattr(perfil, "nombre", "alumno") or "alumno"
        alumno = getattr(perfil, "alumno_o_alumna", "alumno") if perfil is not None else "alumno"
        preparado = getattr(perfil, "preparado_o_preparada", "preparado/a") if perfil is not None else "preparado/a"
        contexto = (contexto or "").strip()

        if pregunta_l in {"si", "sí", "s", "lo entiendo", "entendido", "vale", "ok", "correcto"}:
            return self.confirmar_comprension(contexto, nombre, alumno, preparado)
        if pregunta_l in {"no", "n", "no entiendo", "no lo entiendo", "repitemelo", "repítemelo", "otra vez"}:
            return self.reforzar_explicacion(contexto, nombre, alumno)
        if "ejemplo" in pregunta_l:
            return self.dar_ejemplo(contexto, nombre)
        if "para qué" in pregunta_l or "para que" in pregunta_l or "sirve" in pregunta_l:
            return self.explicar_utilidad(contexto, nombre)
        if "siguiente" in pregunta_l or "continuar" in pregunta_l:
            return self.preparar_siguiente_paso(contexto, nombre, preparado)
        if "imagen" in pregunta_l or "gif" in pregunta_l or "foto" in pregunta_l:
            return self.explicar_material_visual(contexto, nombre)
        if "mano" in pregunta_l or "muñeca" in pregunta_l or "muneca" in pregunta_l or "postura" in pregunta_l:
            return (
                f"{nombre}, en piano la postura es una base técnica, no un detalle estético. Empieza por el cuerpo: siéntate al borde del banco, espalda recta, hombros relajados y pies apoyados. "
                "Después mira los brazos: los codos deben quedar a la altura aproximada del teclado para que el antebrazo no tire de la muñeca hacia abajo ni hacia arriba. "
                "Por último mira la mano: muñeca relajada y dedos curvados para que la yema contacte la tecla. "
                "Ejemplo: si te encorvas, los hombros se cierran y la mano pierde libertad; si te colocas bien, los dedos pueden moverse con menos esfuerzo. ¿Quieres que lo practiquemos paso a paso?"
            )
        if "digit" in pregunta_l or "dedo" in pregunta_l or "dedos" in pregunta_l:
            return (
                f"{nombre}, la digitación es el sistema que convierte los dedos en números: 1 pulgar, 2 índice, 3 corazón, 4 anular y 5 meñique. "
                "Sirve para decidir con qué dedo se toca cada nota. Esto evita movimientos torpes y prepara la mano para frases más largas. "
                "Ejemplo: si un ejercicio marca 2 sobre una nota, debes pensar índice, no cualquier dedo. Si marca 5, debes pensar meñique. "
                "Ahora quiero comprobarlo: dime qué dedo es el número 3."
            )
        if "teclado" in pregunta_l or "negras" in pregunta_l or "blancas" in pregunta_l or "do" in pregunta_l:
            return (
                f"{nombre}, el teclado se aprende por patrones. Las teclas negras forman grupos de dos y de tres. Ese patrón es tu mapa. "
                "Para encontrar DO, busca dos teclas negras juntas y mira la tecla blanca inmediatamente anterior. Esa es DO. "
                "Después las blancas siguen DO, RE, MI, FA, SOL, LA y SI. Ejemplo: desde DO, si subes una tecla blanca llegas a RE; si subes otra, llegas a MI. "
                "¿Quieres que te lo vuelva a explicar usando el patrón de dos teclas negras?"
            )

        base = contexto if contexto else "Estamos en una clase guiada de piano desde cero."
        return (
            f"{nombre}, voy a responder usando lo que estamos viendo ahora.\n\n"
            f"Contexto de la pantalla:\n{base}\n\n"
            "Mi recomendación como profesor es esta: primero identifica el concepto visual, después dime con tus palabras para qué sirve, y solo después lo llevamos al teclado. "
            "Si algo no está claro, escríbeme 'no' y te lo vuelvo a explicar con otro ejemplo."
        )

    def confirmar_comprension(self, contexto: str, nombre: str, alumno: str, preparado: str) -> str:
        return (
            f"Perfecto, {nombre}. Entonces no avanzamos a ciegas: has confirmado que lo entiendes.\n\n"
            "Antes de pasar al siguiente paso, haz una comprobación rápida: intenta decirlo con tus palabras. "
            "Por ejemplo: 'el dedo 1 es el pulgar', o 'DO está antes del grupo de dos teclas negras'.\n\n"
            f"Si puedes explicarlo así, estás {preparado} para continuar. El siguiente paso lógico es llevarlo a una práctica corta, sin evaluación, para que tu mano lo asimile."
        )

    def reforzar_explicacion(self, contexto: str, nombre: str, alumno: str) -> str:
        c = (contexto or "").lower()
        if "postura" in c or "espalda" in c or "hombros" in c or "codos" in c or "pies" in c or "muñeca" in c or "muneca" in c:
            return (
                f"Lo repetimos desde cero, {nombre}. Antes de tocar, haz esta comprobación en cinco pasos:\n\n"
                "1. Banco: siéntate cerca del borde, no hundido hacia atrás.\n"
                "2. Espalda: recta, pero sin ponerte rígido.\n"
                "3. Hombros: relajados y bajos, no subidos.\n"
                "4. Codos: aproximadamente a nivel del teclado.\n"
                "5. Pies: apoyados para que el cuerpo esté estable.\n\n"
                "Después revisa muñecas y dedos. Si esos cinco puntos están bien, la mano trabajará mejor. Cuando lo tengas, dime 'sí'."
            )
        if "digit" in c or "dedo" in c:
            return (
                f"No pasa nada, {nombre}. Lo repetimos más claro.\n\n"
                "Piensa en cada mano como una lista de cinco herramientas:\n"
                "1 = pulgar, el dedo más corto y fuerte.\n"
                "2 = índice, el dedo con el que normalmente señalas.\n"
                "3 = corazón, el dedo central.\n"
                "4 = anular, el que suele costar más mover de forma independiente.\n"
                "5 = meñique, el dedo pequeño.\n\n"
                "Ejercicio: mira tu mano derecha y toca con el pulgar la mesa: di 'uno'. Luego índice: 'dos'. Repite despacio. "
                "Cuando lo tengas, dime 'sí'."
            )
        if "teclado" in c or "teclas negras" in c or "do" in c:
            return (
                f"Lo repetimos, {nombre}. El teclado no se memoriza tecla por tecla. Se busca el dibujo.\n\n"
                "Paso 1: busca dos teclas negras juntas.\n"
                "Paso 2: mira la tecla blanca que está justo a la izquierda de esas dos negras.\n"
                "Paso 3: esa tecla blanca es DO.\n\n"
                "Ahora hazlo visualmente en la imagen. No mires todas las teclas: busca solo el grupo de dos negras. Cuando lo veas, dime 'sí'."
            )
        return (
            f"Lo repetimos con calma, {nombre}. Primero mira el elemento destacado de la imagen. Segundo, dime qué representa. Tercero, piensa para qué sirve al tocar.\n\n"
            "No necesitas entender todo de golpe. Necesitas entender el paso actual. Si quieres, pregúntame 'ejemplo' y te doy un caso concreto."
        )

    def dar_ejemplo(self, contexto: str, nombre: str) -> str:
        c = (contexto or "").lower()
        if "postura" in c or "espalda" in c or "hombros" in c or "codos" in c or "pies" in c or "muñeca" in c or "muneca" in c:
            return (
                f"Ejemplo concreto, {nombre}: si te sientas muy atrás en el banco, normalmente te inclinas hacia delante para llegar al teclado. "
                "Eso encorva la espalda y bloquea los hombros. En cambio, si te sientas cerca del borde, con pies apoyados y espalda larga, "
                "los brazos llegan al teclado de forma natural y la muñeca puede quedar relajada."
            )
        if "digit" in c or "dedo" in c:
            return (
                f"Ejemplo concreto, {nombre}: imagina que el ejercicio dice 'toca MI con el dedo 3'. "
                "No significa tocar cualquier MI de cualquier manera. Significa localizar MI y usar el dedo corazón, porque el 3 es el corazón. "
                "Así la mano aprende un recorrido ordenado."
            )
        if "teclado" in c or "do" in c:
            return (
                f"Ejemplo concreto, {nombre}: mira un grupo de dos teclas negras. La tecla blanca justo antes de ese grupo es DO. "
                "Si subes una tecla blanca desde DO, llegas a RE. Si subes otra, llegas a MI. Ese pequeño recorrido ya te permite tocar tus primeras notas."
            )
        return (
            f"Ejemplo concreto, {nombre}: si ves una imagen con un dedo iluminado, no la mires solo como dibujo. Pregúntate: qué dedo es, qué número tiene y qué tecla debe tocar. "
            "Ese proceso transforma la imagen en práctica real."
        )

    def explicar_utilidad(self, contexto: str, nombre: str) -> str:
        return (
            f"Sirve para que aprendas con estructura, {nombre}. La teoría visual reduce confusión antes de tocar. "
            "La digitación ordena los dedos. La postura evita tensión. El patrón de teclas negras te orienta en el teclado. "
            "Y las prácticas convierten todo eso en movimiento. Esa es la diferencia entre pulsar teclas al azar y estudiar piano de forma profesional."
        )

    def explicar_material_visual(self, contexto: str, nombre: str) -> str:
        return (
            f"{nombre}, el material visual se estudia en tres pasadas. Primera pasada: mirar sin tocar, solo identificar qué aparece. "
            "Segunda pasada: entender para qué sirve. Tercera pasada: repetirlo físicamente en el teclado. "
            "Cuando pulses una imagen, la ampliamos para que no estudies con detalles pequeños. Después te pregunto si lo entendiste."
        )

    def preparar_siguiente_paso(self, contexto: str, nombre: str, preparado: str) -> str:
        return (
            f"Para continuar de forma profesional, {nombre}, no saltamos directamente. Primero confirmamos comprensión; después hacemos una práctica corta; "
            "y solo al final hacemos un ejercicio evaluable.\n\n"
            f"Si ya estás {preparado}, pulsa Práctica o dime 'sí'. Si dudas, dime 'no' y vuelvo a explicarlo con otro ejemplo."
        )

