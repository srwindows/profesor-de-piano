# Voz Piper del avatar

Desde la versión 1.7.3 la voz robótica queda eliminada. El avatar habla solo con **Piper TTS**.

Si Piper o el modelo del avatar seleccionado no están configurados, el programa mostrará un aviso y no usará espeak como respaldo.

## Instalar Piper en Debian con `--break-system-packages`

```bash
python3 -m pip install --user piper-tts --break-system-packages
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Comprueba:

```bash
piper --help
```

## Rutas esperadas por defecto

Voz chica:

```text
voices/piper/laura/es_MX-laura-high.onnx
voices/piper/laura/es_MX-laura-high.onnx.json
```

Voz chico:

```text
voices/piper/es_ES-carlfm-high.onnx
voices/piper/es_ES-carlfm-high.onnx.json
```

También puedes elegir cualquier `.onnx` desde:

```text
Configuración > Avatar y voz
```

Al pulsar **Guardar configuración**, las rutas se guardan en:

```text
data/ajustes_usuario.json
```

## Configurar automáticamente voces ya descargadas

Si ya descargaste las voces en otra carpeta del proyecto, ejecuta:

```bash
python3 configurar_voz_piper.py
```

El script buscará `es_MX-laura-high.onnx` y `es_ES-carlfm-high.onnx` dentro de `~/Escritorio/profesor_de_piano` y guardará las rutas encontradas.

## Probar voz fuera del programa

```bash
python3 probar_voz.py
```

## Probar voz chica manualmente

```bash
echo "Hola, soy tu profesora de piano." | \
piper \
--model "$PWD/voices/piper/laura/es_MX-laura-high.onnx" \
--config "$PWD/voices/piper/laura/es_MX-laura-high.onnx.json" \
--output_file prueba_chica_piper.wav

aplay prueba_chica_piper.wav
```
