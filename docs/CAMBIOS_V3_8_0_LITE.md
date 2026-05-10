# v3.8.0 — Lite con retos de comprensión

Esta versión añade una comprobación real antes de marcar un punto como superado.

## Cambio principal

El botón `✓ Punto superado` pasa a funcionar como `Comprobar`.

Ahora el flujo es:

```text
Leer punto actual
↓
Comprobar
↓
Reto breve de comprensión
↓
Si acierta: punto superado
↓
Se desbloquea la flecha →
```

## Sin IA pesada

Los retos se generan mediante reglas docentes rápidas, sin Qwen, sin nube y sin modelos pesados.

## Archivos añadidos

```text
app/core/comprobacion_docente.py
app/ui/dialogo_reto_comprension.py
```

## Objetivo

Evitar que el alumno avance pulsando botones sin haber entendido el punto.
