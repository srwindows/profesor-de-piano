# Auditoría curricular — Niveles 1 y 2

Versión generada: `4.1.15-lite-hotfix-niveles-1-2-completos`

## Resultado de la auditoría

Antes de esta corrección:

- Nivel 1 tenía 30 entradas, pero solo la clase 1 estaba completa. Las clases 2–30 estaban como `pendiente_desarrollo` / `placeholder_funcional`.
- Nivel 2 tenía 30 entradas, pero todas estaban como esqueleto pendiente.
- `evaluaciones.json`, `teoria_visual.json`, `pizarra.json`, `midi.json`, `partituras.json`, `tecnica.json`, `ritmo_metronomo.json`, `repasos.json` y `documentacion.json` estaban vacíos o sin contenido funcional en los niveles 1 y 2.

## Corrección aplicada

- Nivel 1 completado con 30 clases funcionales.
- Nivel 2 completado con 30 clases funcionales.
- Cada clase contiene:
  - clase teórica;
  - guion del profesor;
  - pizarra/pentagrama;
  - secuencia docente;
  - archivo MIDI generado;
  - partitura MusicXML generada;
  - 4 ejercicios asociados;
  - examen final de clase;
  - regla de avance;
  - enlace a la siguiente clase.
- Cada nivel contiene examen global.

## Archivos principales actualizados

- `data/colecciones/nivel_1/clases.json`
- `data/colecciones/nivel_2/clases.json`
- `data/flujo_docente_nivel_1.json`
- `data/flujo_docente_nivel_2.json`
- `data/lecciones_nivel_1.json`
- `data/lecciones_nivel_2.json`
- `data/colecciones/nivel_1/evaluaciones.json`
- `data/colecciones/nivel_2/evaluaciones.json`
- `assets/midi/nivel_1/clases/`
- `assets/midi/nivel_2/clases/`
- `assets/partituras/nivel_1/`
- `assets/partituras/nivel_2/`
- `docs/curriculo/nivel_1/`
- `docs/curriculo/nivel_2/`

## Nota

La carpeta `voices/` no se incluye en la entrega. Debe añadirse manualmente en la raíz del proyecto, como ya estaba acordado para evitar ZIPs pesados.
