# Subir videos a Facebook

Herramienta para publicar en tu perfil de Facebook, **uno detrás del otro**, los videos que vas juntando en el
celular. La PC maneja el celular por **adb inalámbrico**; no usa la API de Facebook sino la app oficial.

## Cómo funciona

1. **En el celular (Termux)** `vigilar_videos.sh` vigila una carpeta (por defecto `~/Videos`) y muestra el listado cada
   30 s. Cuando pasan 10 minutos sin cambios (ni videos nuevos ni videos que sigan creciendo), copia los videos a
   `/sdcard/Movies/SubirFacebook` y deja `LISTO.txt` con la lista (`nombre<TAB>tamaño`).
2. **En la PC** `Subir_videos_Facebook.bat`:
   - ejecuta `conectar_celular.py`: si el celular no aparece por adb, lo busca en la red y, si hace falta, muestra
     un **código QR en la consola** para vincularlo (*Opciones de desarrollador → Depuración inalámbrica →
     Vincular dispositivo con código QR*);
   - ejecuta `subir_facebook.py`: espera `LISTO.txt` y sube los videos de a uno abriendo el editor de Facebook,
     verifica que los destinatarios sean **Público**, toca *Publicar* y confirma que el editor se cerró.
3. **Sin repetir:** cada video se identifica por **nombre + tamaño**. Lo publicado se anota en `subidos.txt` (en el
   celular), así que si se corta y se vuelve a ejecutar, no sube dos veces el mismo video.
4. **Para frenar:** cerrar la ventana o, en Termux, `touch /sdcard/Movies/SubirFacebook/PARAR`.

`python subir_facebook.py --prueba` recorre el primer video hasta el botón *Publicar* y lo descarta sin publicar.

## Requisitos

- PC con Windows y Python 3.10+ (`pip install qrcode`).
- `adb` (Android platform-tools). Se toma de la variable de entorno `ADB`; si no está definida se usa la ruta por
  defecto del script o el `adb` del PATH.
- Celular Android con la app de Facebook con sesión iniciada, depuración inalámbrica activada, en la misma Wi-Fi
  que la PC, y desbloqueado mientras sube (el script nunca lo desbloquea: si está bloqueado, espera).
- Termux en el celular (`termux-setup-storage`). `instalar_alias_termux.sh` instala los alias `vigilar` y `vigilar0`.

### Avisos al celular (opcional)

Si definís la variable de entorno `NTFY_TOPICO` o creás un archivo `ntfy_topico.txt` junto al script con el nombre
de tu tópico de [ntfy](https://ntfy.sh), recibís avisos cuando empieza, se frena o termina la subida. Ese archivo
está en `.gitignore`. Sin tópico, no se envía ningún aviso.

## Advertencia

Automatizar la app de Facebook **puede violar sus Condiciones de uso** y llevar a restricciones o al bloqueo de la
cuenta. Usalo bajo tu propia responsabilidad, con moderación, y **subí solo contenido propio** o sobre el que tengas
los derechos.

Las coordenadas del camino rápido (`SIGUIENTE_XY`, `PUBLICAR_XY`) se midieron en un celular concreto; en otra
pantalla el script detecta que no coinciden y usa el camino completo (lectura de la interfaz con uiautomator).
