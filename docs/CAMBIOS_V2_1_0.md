# Cambios v2.1.0 — Ruta curricular multinivel

## Paso grande

Esta versión añade el mapa general del curso. Ya no trabajamos solo por pantallas sueltas: ahora el programa tiene una ruta curricular visible.

## Añadido

- Nuevo archivo de datos:

```text
data/ruta_curso.json
```

- Nuevo gestor:

```text
app/core/ruta_curso.py
```

- Nuevo diálogo:

```text
app/ui/dialogo_ruta_curso.py
```

## Nueva función

- Botón **Ruta curso** en el panel del avatar.
- Botón **Ruta** en la pantalla de estudio.
- Mapa de niveles:
  - Nivel 0 — Base absoluta;
  - Nivel Inicial;
  - Nivel Básico;
  - Nivel Intermedio;
  - Nivel Avanzado.

## La ruta muestra

- estado del nivel:
  - actual;
  - disponible;
  - completado;
  - bloqueado;
- objetivo;
- módulos;
- qué desbloquea;
- conexión con el plan personalizado.

## Desde la ruta se puede

- abrir teoría;
- abrir Plan alumno;
- continuar la práctica del nivel recomendado.

## Entrega

ZIP sin carpeta `voices`.
