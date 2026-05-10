import random
import re


class ComprobacionDocente:
    """Genera retos de comprensión sin IA pesada.

    La finalidad no es examinar de forma dura, sino evitar avanzar
    mecánicamente sin entender el punto de clase.
    """

    def __init__(self):
        self._contador = 0

    def generar_reto(self, texto_punto: str) -> dict:
        texto = str(texto_punto or "")
        t = texto.lower()

        reglas = [
            (
                ["clave de sol", "sol"],
                "¿Por qué se llama clave de Sol?",
                "Porque señala la línea donde se coloca la nota SOL.",
                [
                    "Porque señala la línea donde se coloca la nota SOL.",
                    "Porque siempre se toca con el dedo sol.",
                    "Porque indica tocar más fuerte.",
                    "Porque marca el final del pentagrama."
                ],
                "La clave de Sol organiza el pentagrama alrededor de la nota SOL. Desde esa referencia nombramos las demás líneas y espacios."
            ),
            (
                ["clave de fa", "fa"],
                "¿Por qué se llama clave de Fa?",
                "Porque sus dos puntos señalan la línea donde se coloca la nota FA.",
                [
                    "Porque sus dos puntos señalan la línea donde se coloca la nota FA.",
                    "Porque obliga a tocar con la mano derecha.",
                    "Porque indica tocar más rápido.",
                    "Porque marca una pausa."
                ],
                "La clave de Fa señala la línea de FA con sus dos puntos. Desde esa referencia se leen las demás notas del pentagrama inferior."
            ),
            (
                ["pentagrama superior", "mano derecha"],
                "¿Qué suele representar el pentagrama superior en una partitura de piano?",
                "Normalmente la mano derecha.",
                [
                    "Normalmente la mano derecha.",
                    "Normalmente el pedal.",
                    "Normalmente la dinámica.",
                    "Normalmente el tempo."
                ],
                "En piano, el pentagrama superior suele corresponder a la mano derecha, aunque puede haber excepciones según la obra."
            ),
            (
                ["pentagrama inferior", "mano izquierda"],
                "¿Qué suele representar el pentagrama inferior en una partitura de piano?",
                "Normalmente la mano izquierda.",
                [
                    "Normalmente la mano izquierda.",
                    "Normalmente el pedal.",
                    "Normalmente la melodía cantada.",
                    "Normalmente el metrónomo."
                ],
                "En piano, el pentagrama inferior suele corresponder a la mano izquierda, normalmente en clave de fa."
            ),
            (
                ["negra", "pulso"],
                "En una explicación básica de ritmo, ¿cuánto suele durar una negra?",
                "Un pulso.",
                ["Un pulso.", "Dos pulsos.", "Cuatro pulsos.", "Medio compás siempre."],
                "La negra se usa como referencia habitual de un pulso en muchos ejercicios iniciales."
            ),
            (
                ["blanca", "pulsos"],
                "¿Cuánto dura normalmente una blanca si la negra vale un pulso?",
                "Dos pulsos.",
                ["Dos pulsos.", "Un pulso.", "Cuatro pulsos.", "No se cuenta."],
                "La blanca dura dos tiempos cuando la negra es la unidad de pulso."
            ),
            (
                ["redonda", "pulsos"],
                "¿Cuánto dura normalmente una redonda si la negra vale un pulso?",
                "Cuatro pulsos.",
                ["Cuatro pulsos.", "Un pulso.", "Dos pulsos.", "Medio pulso."],
                "La redonda dura cuatro tiempos cuando la negra vale un pulso."
            ),
            (
                ["silencio", "no tocar"],
                "¿Qué significa un silencio en la lectura musical?",
                "No tocar, pero seguir contando el pulso.",
                [
                    "No tocar, pero seguir contando el pulso.",
                    "Parar el ejercicio completamente.",
                    "Tocar más fuerte.",
                    "Cambiar de mano."
                ],
                "El silencio no elimina el tiempo: se cuenta igual, pero no se toca una nota."
            ),
            (
                ["do central"],
                "¿Para qué sirve localizar el DO central?",
                "Para orientarse entre el teclado y la partitura.",
                [
                    "Para orientarse entre el teclado y la partitura.",
                    "Para tocar siempre con el dedo cinco.",
                    "Para subir el volumen.",
                    "Para cambiar el sonido del piano."
                ],
                "El DO central es una referencia fundamental porque conecta el centro del teclado con la lectura en partitura."
            ),
            (
                ["clave de sol"],
                "¿Con qué mano se relaciona normalmente la clave de sol en piano inicial?",
                "Con la mano derecha.",
                ["Con la mano derecha.", "Con el pedal.", "Con la mano izquierda siempre.", "Con el metrónomo."],
                "En piano inicial, la clave de sol suele aparecer en el pentagrama superior y se asocia normalmente a la mano derecha."
            ),
            (
                ["clave de fa"],
                "¿Con qué mano se relaciona normalmente la clave de fa en piano inicial?",
                "Con la mano izquierda.",
                ["Con la mano izquierda.", "Con la mano derecha siempre.", "Con el pedal.", "Con el tempo."],
                "En piano inicial, la clave de fa suele aparecer en el pentagrama inferior y se asocia normalmente a la mano izquierda."
            ),
            (
                ["metrónomo"],
                "¿Para qué usamos el metrónomo en una clase de piano?",
                "Para mantener un pulso regular.",
                [
                    "Para mantener un pulso regular.",
                    "Para cambiar la afinación del piano.",
                    "Para saber qué dedo usar siempre.",
                    "Para tocar más fuerte."
                ],
                "El metrónomo ayuda a mantener la regularidad del pulso, no sustituye la lectura ni la técnica."
            ),
            (
                ["digitación", "dedo"],
                "¿Para qué sirve la digitación?",
                "Para saber qué dedo conviene usar en cada nota o paso.",
                [
                    "Para saber qué dedo conviene usar en cada nota o paso.",
                    "Para cambiar el color del sonido.",
                    "Para elegir el tempo automáticamente.",
                    "Para evitar leer la partitura."
                ],
                "La digitación ordena los dedos para tocar con control, continuidad y menos tensión."
            ),
            (
                ["postura", "muñeca"],
                "¿Qué buscamos con una buena postura al piano?",
                "Tocar con control, comodidad y sin tensión innecesaria.",
                [
                    "Tocar con control, comodidad y sin tensión innecesaria.",
                    "Tocar siempre muy fuerte.",
                    "Mantener los hombros rígidos.",
                    "No mirar nunca el teclado."
                ],
                "La postura no es estética: evita tensión y permite tocar con más control."
            ),
        ]

        for claves, pregunta, correcta, opciones, explicacion in reglas:
            if all(c in t for c in claves):
                return self._reto(pregunta, correcta, opciones, explicacion)

        # Reglas más flexibles por palabra aislada.
        if "partitura" in t:
            return self._reto(
                "¿Qué nos indica una partitura de piano?",
                "Qué notas tocar, cuándo tocarlas y cómo organizarlas en el tiempo.",
                [
                    "Qué notas tocar, cuándo tocarlas y cómo organizarlas en el tiempo.",
                    "Solo el volumen del piano.",
                    "Solo el nombre de la canción.",
                    "La marca del instrumento."
                ],
                "La partitura es un mapa musical: indica notas, ritmo, organización y muchas señales de interpretación."
            )

        if "pulso" in t or "ritmo" in t:
            return self._reto(
                "¿Qué debe mantenerse estable cuando trabajamos el pulso?",
                "La regularidad del tiempo.",
                [
                    "La regularidad del tiempo.",
                    "El color de la pantalla.",
                    "El nombre de la nota.",
                    "La altura de la banqueta solamente."
                ],
                "El pulso es la base regular sobre la que colocamos notas, silencios y figuras."
            )

        if "mano derecha" in t:
            return self._reto(
                "Si el punto habla de mano derecha, ¿qué debemos comprobar?",
                "Qué notas o acciones debe realizar esa mano.",
                [
                    "Qué notas o acciones debe realizar esa mano.",
                    "Que el pedal esté siempre pisado.",
                    "Que la mano izquierda no exista.",
                    "Que el tempo cambie solo."
                ],
                "No basta con nombrar la mano: hay que saber qué hace y cuándo lo hace."
            )

        if "mano izquierda" in t:
            return self._reto(
                "Si el punto habla de mano izquierda, ¿qué debemos comprobar?",
                "Qué notas o acompañamiento debe realizar esa mano.",
                [
                    "Qué notas o acompañamiento debe realizar esa mano.",
                    "Que siempre toque la melodía principal.",
                    "Que no siga el pulso.",
                    "Que sustituya al metrónomo."
                ],
                "En piano, la mano izquierda suele llevar acompañamiento o registro grave, pero depende del ejercicio."
            )

        # Reto genérico para cualquier punto.
        return self._reto(
            "Antes de avanzar, ¿qué debes poder hacer con este punto?",
            "Explicarlo con tus palabras y aplicarlo en el piano o en la partitura.",
            [
                "Explicarlo con tus palabras y aplicarlo en el piano o en la partitura.",
                "Pasarlo sin leerlo.",
                "Memorizar solo el título.",
                "Pulsar siguiente sin comprobar nada."
            ],
            "Un punto se considera superado cuando puedes explicar la idea y aplicarla, aunque sea de forma sencilla."
        )

    def _reto(self, pregunta: str, correcta: str, opciones: list[str], explicacion: str) -> dict:
        opciones_limpias = []
        vistos = set()
        for op in opciones:
            op = str(op).strip()
            k = op.lower()
            if op and k not in vistos:
                vistos.add(k)
                opciones_limpias.append(op)

        if correcta not in opciones_limpias:
            opciones_limpias.insert(0, correcta)

        random.shuffle(opciones_limpias)
        return {
            "pregunta": pregunta,
            "correcta": correcta,
            "opciones": opciones_limpias,
            "explicacion": explicacion,
        }
