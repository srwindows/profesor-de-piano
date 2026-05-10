import os
import sys
import faulthandler

# Arranque defensivo para Debian/Xfce/equipos con gráfica integrada.
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")

# v4.1.6: salida defensiva para evitar finalizadores tardíos de PortAudio/ALSA.
# Se puede desactivar con:
# PROFESOR_SALIDA_OS_EXIT=0 python3 main.py
os.environ.setdefault("PROFESOR_SALIDA_OS_EXIT", "1")

try:
    faulthandler.enable()
except Exception:
    pass

from PySide6.QtWidgets import QApplication
from app.ui.ventana_principal import VentanaPrincipal


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Profesor de Piano IA")
    ventana = VentanaPrincipal()
    ventana.show()
    codigo = app.exec()
    try:
        ventana.close()
    except Exception:
        pass
    if os.environ.get("PROFESOR_SALIDA_OS_EXIT", "1") == "1":
        os._exit(int(codigo))
    sys.exit(codigo)


if __name__ == "__main__":
    main()
