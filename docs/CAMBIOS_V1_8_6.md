# Cambios v1.8.6 — narrador estable y diagnosticable

- Se invalida la caché antigua de voz para no reutilizar audios defectuosos de versiones previas.
- Se separa texto visual y texto hablado: la pantalla puede mostrar títulos, números y saltos de línea, pero Piper recibe bloques limpios.
- Se añade diagnóstico de texto narrado en Configuración > Avatar y voz > Ver texto narrado.
- Se corrige la lectura de `Nivel` e `Inicial` para evitar pronunciaciones tipo `nivelo` o `inicialo`.
- Se refuerza la cola de reproducción para que un bloque fallido no corte toda la narración.
- Se aíslan los procesos Piper de precaché/precalentamiento para que no interfieran con la reproducción real.
- Se mantiene el ZIP sin carpeta `voices/` para que el usuario la añada manualmente.
