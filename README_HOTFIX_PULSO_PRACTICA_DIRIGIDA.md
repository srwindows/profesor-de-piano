# Hotfix: Pulso con práctica dirigida y corregida

Este hotfix convierte el botón **Práctica** de la pestaña **Pulso** en una práctica real, no en una vuelta genérica a la pantalla de clase.

## Cambios principales

- Nuevo panel `DialogoPulsoPractica`.
- El botón **Práctica** de Pulso abre ejercicios prácticos específicos.
- Se añadieron prácticas funcionales a los 25 ejercicios de Pulso.
- Cada práctica incluye:
  - metrónomo visual/sonoro;
  - compás de entrada;
  - BPM modificable;
  - tolerancia temporal modificable;
  - demo guiada;
  - secuencia de notas esperadas;
  - corrección por nota;
  - corrección por pulso;
  - corrección si se toca durante un silencio;
  - registro en historial pedagógico MIDI;
  - avance al completar con precisión suficiente.

## Cinco niveles prácticos

1. Pulso básico.
2. Compás y acento.
3. Corcheas y subdivisión.
4. Síncopas y patrones.
5. Ritmo musical avanzado.

## Archivos modificados

```text
app/ui/ventana_principal.py
app/ui/dialogo_pulso_practica.py
data/pulso_ritmo.json
```

## Comprobación realizada

```bash
python3 -m py_compile app/ui/dialogo_pulso_practica.py app/ui/dialogo_pulso_ritmo.py app/ui/ventana_principal.py app/core/pulso_ritmo.py
python3 -m compileall -q app
```

La práctica usa el piano interactivo global y también acepta entrada MIDI externa si está conectada.
