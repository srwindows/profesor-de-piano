# Cambios v2.5.0 — Partitura integrada y metrónomo con sonido opcional

## Paso grande

Se integra la lectura de partitura dentro de la arquitectura nueva de paneles centrales. El piano virtual queda visible mientras se trabaja la partitura, preparando el programa para lectura real y ejercicios con pentagrama.

## Añadido

- Nuevo botón **Partitura** en la barra superior.
- Nuevo botón **Partitura** en el panel del profesor.
- Nuevo panel integrado de lectura de partitura.
- Nuevo gestor:

```text
app/core/lectura_partitura.py
```

- Nuevo diálogo/panel:

```text
app/ui/dialogo_lectura_partitura.py
```

- Nuevos datos:

```text
data/lectura_partitura.json
data/progreso_lectura_partitura.json
```

## Metrónomo

- El panel **Pulso** ahora tiene una casilla **Sonido**.
- Si está activada, el metrónomo hace beep.
- Si está desactivada, el metrónomo funciona solo de forma visual.

## Integración

- Partitura queda añadida a la Ruta curso.
- Partitura queda añadida a la Sesión diaria.
- Partitura se abre en el hueco central, no como ventana flotante.
- El profesor permanece fijo a la derecha y el piano permanece visible.

## Entrega

ZIP sin carpeta `voices`.
