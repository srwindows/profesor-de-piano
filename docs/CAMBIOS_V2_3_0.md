# Cambios v2.3.0 — Pulso y metrónomo guiado

## Paso serio

Se añade un entrenador de pulso. Esto es fundamental porque un alumno puede tocar las notas correctas y aun así tocar mal si no mantiene el tiempo.

## Añadido

- Nuevo archivo de datos:

```text
data/pulso_ritmo.json
```

- Nuevo progreso:

```text
data/progreso_pulso_ritmo.json
```

- Nuevo gestor:

```text
app/core/pulso_ritmo.py
```

- Nuevo diálogo:

```text
app/ui/dialogo_pulso_ritmo.py
```

## Botones nuevos

- **Pulso** en el panel del avatar.
- **Pulso** en la pantalla de estudio.

## Funciones

- Metrónomo visual.
- Metrónomo sonoro mediante beep del sistema.
- BPM ajustable de 40 a 220.
- Compás ajustable de 2 a 7.
- Ejercicios progresivos de pulso:
  - contar 4 pulsos;
  - tocar DO en el tiempo 1;
  - negras lentas;
  - blancas;
  - acento del primer pulso.
- Guardado de progreso.
- Celebración al completar ejercicio de pulso.

## Integración

- Añadido a la ruta curricular.
- Añadido a la sesión diaria.
- Puede abrir práctica desde el entrenador.

## Entrega

ZIP sin carpeta `voices`.
