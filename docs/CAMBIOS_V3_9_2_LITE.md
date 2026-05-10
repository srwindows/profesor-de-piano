# v3.9.2 — Fix pizarra musical visible

## Problema corregido

Al pulsar `Leer punto actual`, el profesor leía el punto, pero la pizarra musical no aparecía.

## Causa

En la pestaña Partitura, el texto superior (`txt_profesor`) está dentro de un `QFrame`.
La función que insertaba la pizarra buscaba el QTextEdit solo en layouts directos y no encontraba el layout real del padre.

## Corrección

`_asegurar_pizarra_musical_panel()` ahora:

1. localiza el widget de texto superior;
2. entra en el layout de su `parentWidget()`;
3. inserta ahí `PizarraMusicalProfesor`;
4. oculta el texto original;
5. fuerza actualización visual del panel.

## Resultado esperado

Al pulsar `Leer punto actual`, la zona superior encima del metrónomo debe cambiar y mostrar la pizarra musical.
