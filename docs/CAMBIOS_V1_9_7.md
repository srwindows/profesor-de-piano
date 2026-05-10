# Cambios v1.9.7 — Repaso inteligente

## Objetivo

Esta versión añade una capa de profesor más realista: cuando el alumno falla un ejercicio,
el sistema no solo bloquea el avance, sino que guarda ese punto como repaso pendiente.

## Añadido

- Botón **Repaso IA** en la pantalla de estudio.
- Cola de ejercicios pendientes de repaso.
- Registro local de fallos por ejercicio.
- Registro local de aciertos por ejercicio.
- Limpieza automática de la cola cuando un ejercicio pendiente se supera.
- El panel de estado ahora muestra cuántos repasos quedan.
- El **Plan completo** muestra un informe de repaso inteligente.

## Funcionamiento

1. Si el alumno falla, el ejercicio entra en `repasos_pendientes`.
2. Si pulsa **Repaso IA**, el profesor carga primero el fallo más reciente.
3. Si no hay cola pendiente, repasa el ejercicio con más fallos acumulados.
4. Si no hay fallos, propone un repaso preventivo del ejercicio anterior.
5. Al acertar, ese ejercicio se retira de la cola de repaso.

## Archivos principales modificados

- `app/core/progreso.py`
- `app/core/repaso_inteligente.py`
- `app/ui/ventana_principal.py`
- `app/config.py`

## Nota

El ZIP sigue entregándose sin carpeta de voces.
