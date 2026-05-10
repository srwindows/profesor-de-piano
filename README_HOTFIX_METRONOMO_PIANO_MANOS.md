# Hotfix: metrónomo Hanon, piano global y manos de digitación

Cambios aplicados sobre la versión anterior:

- El botón `Pulso` interno de la pizarra Hanon ya no dispara también el metrónomo genérico de la pizarra. Ahora solo ejecuta la acción Hanon correspondiente.
- El metrónomo de la demo Hanon empieza con la reproducción y se detiene cuando termina la demo.
- La demo Hanon se detiene correctamente al llegar al final de la pieza. Antes el reloj quedaba clavado en el final y el temporizador seguía vivo.
- En `Práctica MIDI` y `Examen` se añade control directo de metrónomo:
  - casilla `Metrónomo` para encender/apagar el clic sonoro;
  - selector `BPM` de 30 a 220, modificable en directo.
- El piano interactivo queda como teclado global inferior; se evita el mini piano dentro de la pizarra Hanon, porque tapaba las manos.
- La pizarra Hanon vuelve a mostrar las dos manos de digitación y resalta el dedo correcto para la nota activa.
- Se aumenta ligeramente la altura útil del piano global para que no quede testimonial.

Archivos modificados:

- `app/ui/ventana_principal.py`
- `app/ui/pizarra_musical.py` *(sin cambios estructurales en este hotfix, se conserva para validación del paquete)*

Comprobación realizada:

```bash
python3 -m py_compile app/ui/ventana_principal.py app/ui/pizarra_musical.py app/ui/piano_virtual.py
```
