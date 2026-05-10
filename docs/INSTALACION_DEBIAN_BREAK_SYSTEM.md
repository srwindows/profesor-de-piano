# Instalación en Debian usando `--break-system-packages`

Desde la carpeta del proyecto:

```bash
cd ~/Escritorio/profesor_de_piano/profesor_piano_python_v1_7_3_piper_config_guardada
```

Instala dependencias de sistema:

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev build-essential portaudio19-dev libasound2-dev libsndfile1 libgl1 libglib2.0-0 v4l-utils pulseaudio-utils alsa-utils
```

Instala paquetes Python sin entorno virtual:

```bash
python3 -m pip install --upgrade pip setuptools wheel --break-system-packages
python3 -m pip install -r requirements.txt --break-system-packages
```

Si el comando `piper` no aparece:

```bash
python3 -m pip install --user piper-tts --break-system-packages
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Configura voces Piper ya descargadas:

```bash
python3 configurar_voz_piper.py
python3 probar_voz.py
```

Arranca:

```bash
python3 main.py
```

Comprueba OpenCV:

```bash
python3 -c "import cv2; print(cv2.__version__)"
```

Comprueba cámaras disponibles:

```bash
v4l2-ctl --list-devices
```

La cámara se configura desde:

```text
Configuración > Cámara
```

La voz se configura desde:

```text
Configuración > Avatar y voz
```
