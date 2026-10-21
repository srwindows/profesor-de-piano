# Piano Booster — versión educativa modificada (2026)

**Este programa está basado en [PianoBooster](https://github.com/pianobooster/PianoBooster)**. Es una versión derivada independiente, no oficial, y **no está patrocinada ni aprobada** por los autores originales.

## Autoría y licencias originales

Las menciones de copyright que contiene el original se mantienen, especialmente:

- Copyright © 2008–2021 **Louis James Barman**.
- Copyright © 2018–2019 **Fabien Givors**.
- Copyright © 2021–2022 **Marius Kittler**.
- Otros colaboradores figuran en `license.txt` y en los avisos de los archivos individuales.

El código original se distribuye bajo **GNU GPL versión 3 o cualquier versión posterior**, según `license.txt`, `README.md` y los encabezados del código. Esta versión derivada sigue bajo la **misma opción GPLv3-or-later**. Se conserva íntegro `gplv3.txt`; no se retiran avisos previos ni se sustituye su autoría.

## Modificaciones propias del proyecto educativo, 2026

Mantenedor del trabajo derivado: **srwindows (proyecto profesor-de-piano)**.

Esta rama contiene modificaciones sustanciales posteriores al PianoBooster original:

- Interfaz y adaptación educativa en español.
- Selector de pistas, partes, acompañamiento y claves.
- Modo Sigue estricto, detección de fallos y estadísticas de aprendizaje.
- Entrada y salida MIDI multicanal CH1–CH16, indicación de actividad y protección contra duplicación de MIDI.
- Partitura MusicXML/PDF generada con MuseScore, lectura interactiva y navegación por páginas.
- Representación de duraciones de notas, ligaduras y pedal cuando hay CC64.
- Adaptaciones del código C++ y motor auxiliar Python para compilar en Windows y macOS.

El proyecto se ofrece **sin garantías**, como permite la GPL. No se atribuye a los autores originales la responsabilidad sobre cambios, errores o soporte de esta versión.

## Obtención del código fuente correspondiente

El código fuente modificable, herramientas de compilación y scripts para crear los binarios Windows/macOS se publican con las compilaciones en el repositorio:

<https://github.com/srwindows/profesor-de-piano/tree/pianobooster-desktop-build>

Quien reciba un binario deberá tener acceso al **código fuente correspondiente a esa versión concreta** bajo las condiciones de la GPLv3 (véase sección 6), incluidos scripts relevantes para compilar e instalar. No basta con un enlace que posteriormente se modifique o desaparezca: conservar el código de cada versión distribuida y acompañarlo con la información necesaria.

## Contenidos multimedia

El archivo original `license.txt` declara que la **documentación y música** de PianoBooster tienen licencia **Creative Commons Attribution (CC-BY)**. Se preserva atribución y procedencia de [BoosterMusic](https://github.com/pianobooster/BoosterMusic). Los usuarios deben consultar también los créditos concretos que pudieran figurar en el material musical incluido.

## Bibliotecas y aplicaciones de terceros

- **Qt**: bibliotecas dinámicas bajo licencias aplicables (habitualmente LGPL/GPL por módulo). Deben conservarse los avisos, permisos para sustituir/revincular las bibliotecas LGPL y documentación de licencias al distribuirlas.
- **FluidSynth**: biblioteca de síntesis, sujeta a su propia licencia LGPL y avisos.
- **RtMidi**: biblioteca MIDI, copyright y permisos según los encabezados originales.
- **MuseScore**: aplicación externa que el usuario instala por separado para generar la notación profesional. No se incluye ni se reclama su autoría.
- **Python, mido, NumPy, Pillow y pypdfium2/PDFium**: componentes del motor auxiliar, con sus respectivas licencias; los paquetes binarios deben contener los avisos de terceros aplicables.
- **SoundFonts**: no se incluyen bibliotecas sonoras de terceros sin verificar sus derechos de redistribución.

Este documento es un aviso de atribución y cumplimiento, no reemplaza los textos de licencia que acompañan cada componente.
