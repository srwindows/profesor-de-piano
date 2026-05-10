class CameraManager:
    """Gestor opcional de cámara.

    En Linux intenta usar OpenCV si está instalado. Si no está instalado, el proyecto sigue
    arrancando y deja claro qué falta.
    """

    def __init__(self):
        self.error = ""
        self.cap = None
        self.indice = 0

    def disponible(self) -> bool:
        try:
            import cv2  # noqa
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def abrir(self, indice: int = 0) -> bool:
        try:
            import cv2
            self.cerrar()
            self.indice = indice
            self.cap = cv2.VideoCapture(indice)
            if not self.cap or not self.cap.isOpened():
                self.error = f"No se pudo abrir la cámara {indice}"
                return False
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    def leer_frame(self):
        if not self.cap:
            return None
        ok, frame = self.cap.read()
        return frame if ok else None

    def cerrar(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
