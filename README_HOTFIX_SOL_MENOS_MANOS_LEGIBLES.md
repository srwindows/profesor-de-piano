# Hotfix: sostenidos visibles y digitación Hanon legible

Cambios aplicados sobre la versión anterior:

1. **Pentagrama y piano sincronizados visualmente**
   - Si la nota activa es sostenida (por ejemplo `G#4` / `Sol#4`), ahora se dibuja el símbolo `♯` delante de la nota en el pentagrama.
   - La posición de la nota en el pentagrama sigue siendo la correcta: un sostenido se coloca en la línea/espacio de la nota natural, pero con accidental visible.
   - Esto evita que parezca que el pentagrama pide `Sol` natural mientras el piano marca `Sol#`.

2. **Manos Hanon más grandes y legibles**
   - Se reserva más altura del lienzo para las manos.
   - Se recorta visualmente la parte baja de la imagen de referencia al dibujarla, sin modificar los PNG originales, para que dedos y numeración ocupen más espacio.
   - El marcador de dedo sigue sincronizado con la nota activa.

3. **Limpieza entre manos y piano global**
   - La información de paso ya no se dibuja en la parte inferior de la pizarra, entre las manos y el piano.
   - En MIDI/Hanon se coloca como etiqueta compacta arriba.
   - Se elimina la barra interna inferior de la pizarra porque ya existe la barra de progreso Hanon superior.

Archivos modificados:

- `app/ui/pizarra_musical.py`
- `app/ui/ventana_principal.py`

Comprobación realizada:

```bash
python3 -m py_compile app/ui/pizarra_musical.py app/ui/ventana_principal.py app/ui/piano_virtual.py
```
