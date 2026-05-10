from app.voice.voz_avatar import VozAvatar
from app.core.ajustes import GestorAjustes
import time

ajustes = GestorAjustes().ajustes
ajustes.voz_motor = "piper"
voz = VozAvatar()
print("Diagnóstico de voz Piper:")
for k, v in voz.diagnostico(
    "piper",
    avatar_tipo=ajustes.avatar_tipo,
    modelo_chica=ajustes.voz_piper_modelo_chica,
    modelo_chico=ajustes.voz_piper_modelo_chico,
).items():
    print(f"  {k}: {v}")

tipo = ajustes.avatar_tipo
texto = (
    "Hola Javi. Soy tu profesora de piano. Esta es una prueba de voz Piper sincronizada con el avatar."
    if tipo == "chica"
    else "Hola Javi. Soy tu profesor de piano. Esta es una prueba de voz Piper sincronizada con el avatar."
)

ok = voz.hablar(
    texto,
    avatar_tipo=tipo,
    velocidad=ajustes.voz_velocidad,
    volumen=ajustes.voz_volumen,
    motor="piper",
    modelo_chica=ajustes.voz_piper_modelo_chica,
    modelo_chico=ajustes.voz_piper_modelo_chico,
    on_start=lambda: print("Reproducción iniciada"),
    on_end=lambda: print("Reproducción finalizada"),
    on_error=lambda e: print("Error de voz:", e),
)
print("Voz lanzada:", ok)
if ok:
    time.sleep(8)
print("Último error:", voz.ultimo_error or "ninguno")
