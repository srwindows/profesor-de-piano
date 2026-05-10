# Profesor de Piano v3.7.0 Lite estable

Esta es la rama ligera y estable del proyecto.

## Objetivo

Crear una versión que pueda llegar a más usuarios:

- portátiles modestos;
- Debian/Linux;
- futura versión Android Lite;
- futura versión iPad Lite;
- equipos sin GPU dedicada;
- equipos sin IA local.

## Enfoque

El profesor enseña mediante:

- reglas docentes rápidas;
- textos estructurados;
- puntos de clase;
- preguntas de comprobación futuras;
- lectura guiada;
- voz local opcional.

La IA pesada no forma parte del corazón de esta versión.

## No incluido

```text
voices/
modelos_ia/
*.gguf
*.bin
*.safetensors
*.onnx
```

## Ejecución

```bash
python3 main.py
```

## Voces

La carpeta `voices` debe añadirse manualmente, como ya venías haciendo.

## Próximo camino recomendado

Construir sobre esta rama Lite:

1. estabilizar curso;
2. mejorar ejercicios;
3. mejorar teoría y partitura;
4. mejorar evaluación y repasos;
5. después añadir IA opcional como módulo externo.
