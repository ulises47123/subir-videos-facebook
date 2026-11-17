"""Sube a Facebook (perfil, Público), uno por uno, los videos que deja vigilar_videos.sh en Movies/SubirFacebook.

Se ejecuta en la PC y maneja el celular por adb (misma red Wi-Fi, depuración inalámbrica activa, celular desbloqueado).
  python subir_facebook.py            espera LISTO.txt y sube todo lo que falta
  python subir_facebook.py --prueba   recorre el primer video hasta el botón Publicar y descarta (no publica)

Por cada video: abre "Nueva publicación" de Facebook con el video, toca Siguiente, verifica que los destinatarios
sean "Público", toca Publicar y confirma que salió del editor. Anota lo subido en subidos.txt (en el celular), así
si se corta y se vuelve a ejecutar no repite. Entre video y video espera un rato al azar.
Para frenar: crear el archivo PARAR en la carpeta (en Termux: touch /sdcard/Movies/SubirFacebook/PARAR) o Ctrl+C.
"""
import html, os, pathlib, random, re, subprocess, sys, time, urllib.request

# Ruta del adb: variable de entorno ADB (por defecto la de esta PC; si no existe, se usa el "adb" del PATH).
ADB = os.environ.get("ADB") or r"C:\Users\Usuario\Documents\Mi música\proyectos\app-mando-facil\.tools\android-sdk\platform-tools\adb.exe"
if not os.path.exists(ADB):
    ADB = "adb"
DIR = "/sdcard/Movies/SubirFacebook"
REL = "Movies/SubirFacebook/"
COMPOSER = "com.facebook.katana/com.facebook.composer.shareintent.ImplicitShareIntentHandlerDefaultAlias"
PAUSA = (0, 1)             # segundos entre publicaciones (Facebook sube en segundo plano)
AQUI = pathlib.Path(__file__).resolve().parent
LOG = AQUI / "registro_subida.txt"
# Avisos por ntfy (opcional): variable de entorno NTFY_TOPICO o archivo ntfy_topico.txt junto al script
# (no se versiona). Si no hay ninguno de los dos, no se avisa.
TOPICO_ARCHIVO = AQUI / "ntfy_topico.txt"
PRUEBA = "--prueba" in sys.argv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(msg):
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(linea, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def elegir_dispositivo():
    out = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout.splitlines()[1:]
    serie = [l.split("\t")[0] for l in out if l.endswith("\tdevice")]
    serie.sort(key=lambda s: "(" in s)          # preferir el serial sin "(2)"
    if not serie:
        sys.exit("No hay celular conectado por adb.")
    return serie[0]


DEV = elegir_dispositivo()


def sh(cmd):
    return subprocess.run([ADB, "-s", DEV, "shell", cmd], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def dump():
    for _ in range(4):
        x = subprocess.run([ADB, "-s", DEV, "exec-out", "uiautomator", "dump", "/dev/tty"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace").stdout
        if "<hierarchy" in x:
            return x
        time.sleep(1.5)
    return ""


def nodos(xml):
    out = []
    for m in re.finditer(r"<node [^>]*>", xml):
        n = m.group(0)
        g = lambda k: html.unescape((re.search(k + r'="([^"]*)"', n) or [None, ""])[1])
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
        out.append({"text": g("text"), "desc": g("content-desc"), "cls": g("class"),
                    "c": ((int(b[1]) + int(b[3])) // 2, (int(b[2]) + int(b[4])) // 2) if b else None})
    return out


def buscar(xml, desc=None, text=None, empieza=None, boton=False):
    for n in nodos(xml):
        if boton and n["cls"] != "android.widget.Button":
            continue
        if desc is not None and n["desc"] != desc:
            continue
        if text is not None and n["text"] != text:
            continue
        if empieza is not None and not n["desc"].startswith(empieza):
            continue
        return n
    return None


def tocar(n):
    sh(f"input tap {n['c'][0]} {n['c'][1]}")


def esperar(fn, segundos):
    fin = time.time() + segundos
    while time.time() < fin:
        x = dump()
        r = fn(x)
        if r:
            return x, r
        time.sleep(0.3)
    return None, None


def foco():
    m = re.search(r"mCurrentFocus=Window\{\S+ \S+ ([^}]+)\}", sh("dumpsys window | grep -m1 mCurrentFocus"))
    return m.group(1) if m else ""


def avisar(titulo, texto):
    """Aviso al celular por ntfy (sin datos sensibles) y notificación local."""
    try:
        t = os.environ.get("NTFY_TOPICO", "").strip()
        if not t and TOPICO_ARCHIVO.exists():
            t = TOPICO_ARCHIVO.read_text(encoding="utf-8").strip()
        if not t:
            return
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{t}", data=texto.encode("utf-8"),
                                                      headers={"Title": titulo.encode("utf-8")}), timeout=15)
    except Exception:
        pass


def captura(nombre):
    p = AQUI / "capturas_error"
    p.mkdir(exist_ok=True)
    f = p / f"{time.strftime('%H%M%S')}_{nombre}.png"
    f.write_bytes(subprocess.run([ADB, "-s", DEV, "exec-out", "screencap", "-p"], capture_output=True).stdout)
    return f


def celular_listo():
    """Despierta la pantalla; si está bloqueado espera (no se desbloquea nunca)."""
    aviso = False
    while True:
        if "isKeyguardShowing=true" not in sh("input keyevent KEYCODE_WAKEUP; dumpsys window | grep -m1 isKeyguardShowing"):
            return
        if not aviso:
            log("El celular está bloqueado: espero a que lo desbloquees.")
            avisar("ProjectPilot: subida en pausa", "El celu esta bloqueado. Desbloquealo y sigo solo.")
            aviso = True
        time.sleep(20)


IDS = {}


def cargar_ids():
    """Una sola consulta al celular con los _id de todos los videos de la carpeta."""
    out = sh(f"content query --uri content://media/external/video/media --projection _id:_display_name "
             f"--where \"relative_path='{REL}'\"")
    for m in re.finditer(r"_id=(\d+), _display_name=(.+)", out):
        IDS[m.group(2).strip()] = m.group(1)


def id_video(nombre):
    if nombre in IDS:
        return IDS[nombre]
    q = (f"content query --uri content://media/external/video/media --projection _id "
         f"--where \"relative_path='{REL}' AND _display_name='{nombre}'\"")
    for _ in range(3):
        m = re.search(r"_id=(\d+)", sh(q))
        if m:
            return m.group(1)
        sh(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file://{DIR}/{nombre}'")
        time.sleep(3)
    return None


def salir_del_editor():
    for _ in range(4):
        if "com.facebook.composer" not in foco():
            return
        x = dump()
        d = buscar(x, text="DESCARTAR")
        if d:
            tocar(d); time.sleep(2); continue
        b = buscar(x, desc="Atrás", boton=True) or buscar(x, desc="Cerrar", boton=True)
        tocar(b) if b else sh("input keyevent 4")
        time.sleep(2)


CONTADOR = {"ok": 0}
SIGUIENTE_XY = (605, 148)      # botón "Siguiente" del editor (medido con uiautomator)
PUBLICAR_XY = (360, 1543)      # botón "Publicar" de la pantalla final


def subir_rapido(vid, nombre):
    """Camino rápido sin uiautomator (que tarda ~1 s por lectura): solo mira qué pantalla de Facebook está
    adelante. Si algo no es lo esperado devuelve None y se usa el camino completo."""
    sh("input keyevent KEYCODE_HOME")
    sh(f"am start -W --activity-multiple-task -a android.intent.action.SEND -t video/mp4 --eu android.intent.extra.STREAM "
       f"content://media/external/video/media/{vid} --grant-read-uri-permission -n {COMPOSER}")
    fin = time.time() + 15
    while time.time() < fin:                       # editor -> Siguiente hasta pasar a la pantalla final
        f = foco()
        if "ComposerPreviewActivity" in f:
            break
        if "composer.activity.ComposerActivity" in f:
            sh(f"input tap {SIGUIENTE_XY[0]} {SIGUIENTE_XY[1]}")
        time.sleep(0.5)
    else:
        return None
    time.sleep(0.4)
    sh(f"input tap {PUBLICAR_XY[0]} {PUBLICAR_XY[1]}")
    fin = time.time() + 15
    while time.time() < fin:
        time.sleep(0.3)
        if "com.facebook.composer" not in foco():
            return True
    return None


def subir(nombre):
    """Devuelve True si quedó publicado (o, en prueba, si llegó hasta Publicar)."""
    vid = id_video(nombre)
    if not vid:
        log(f"  ✗ {nombre}: el celular no lo encuentra en {REL}")
        return False
    # El 1º y cada 10 videos van por el camino completo, que vuelve a verificar "Público" leyendo la pantalla.
    if not PRUEBA and CONTADOR["ok"] % 10 != 0:
        r = subir_rapido(vid, nombre)
        if r:
            CONTADOR["ok"] += 1
            log(f"  ✓ publicado: {nombre} (rápido)")
            return True
        log(f"  (camino rápido no anduvo con {nombre}; uso el completo)")
        salir_del_editor()
    sig = None
    for intento in range(2):
        # Si Facebook está adelante, el pedido de compartir no abre el editor: se manda Facebook al fondo
        # con INICIO (no se cierra, la subida anterior sigue) y recién ahí se abre el editor.
        sh("input keyevent KEYCODE_HOME"); time.sleep(0.4)
        sh(f"am start --activity-multiple-task -a android.intent.action.SEND -t video/mp4 --eu android.intent.extra.STREAM "
           f"content://media/external/video/media/{vid} --grant-read-uri-permission -n {COMPOSER}")
        # Paso 1: editor con el video adjunto
        x, sig = esperar(lambda x: buscar(x, desc="Eliminar video") and buscar(x, desc="Siguiente", boton=True), 25)
        if sig:
            break
        salir_del_editor()
    if not sig:
        log(f"  ✗ {nombre}: no apareció el editor con el video ({captura('editor')})")
        salir_del_editor(); return False
    tocar(sig)

    # Paso 2: pantalla final, destinatarios Público y botón Publicar
    x, pub = esperar(lambda x: buscar(x, desc="Publicar", boton=True), 30)
    if not pub:
        log(f"  ✗ {nombre}: no apareció el botón Publicar ({captura('publicar')})")
        salir_del_editor(); return False
    dest = buscar(x, empieza="Destinatarios de la publicación")
    if not dest or "Público" not in dest["desc"]:
        log(f"  ✗ {nombre}: los destinatarios no son Público ({dest['desc'] if dest else 'no los encuentro'}). "
            "Freno todo para no publicar con otra privacidad.")
        salir_del_editor(); raise SystemExit(2)
    if PRUEBA:
        log(f"  ✓ PRUEBA {nombre}: llegó a Publicar con Público. Descarto sin publicar.")
        salir_del_editor(); return True

    # Confirmar que seguimos en el editor justo antes de tocar
    if "com.facebook.composer" not in foco():
        log(f"  ✗ {nombre}: la pantalla cambió antes de Publicar ({captura('cambio')})")
        salir_del_editor(); return False
    tocar(pub)
    fin = time.time() + 40
    while time.time() < fin:
        time.sleep(0.4)
        if "com.facebook.composer" not in foco():
            # Facebook sigue subiendo en segundo plano: no se espera, se pasa al siguiente.
            CONTADOR["ok"] += 1
            log(f"  ✓ publicado: {nombre}")
            return True
    log(f"  ✗ {nombre}: tocó Publicar pero el editor no se cerró ({captura('no_cerro')})")
    salir_del_editor(); return False


SUBIENDO = ("No cierres Facebook", "Finalizando", "Publicando", "Subiendo", "Procesando")


def esperar_subida(maximo=240):
    """Facebook queda abierto y muestra 'Finalizando... No cierres Facebook' mientras sube.
    Se espera a que ese aviso desaparezca para mandar el siguiente (uno detrás del otro, sin amontonar)."""
    time.sleep(2)
    fin = time.time() + maximo
    while time.time() < fin:
        x = dump()
        if not any(t in x for t in SUBIENDO):
            return True
        time.sleep(3)
    log(f"  (el aviso de subida sigue después de {maximo} s; sigo igual)")
    return False


def leer_lista(ruta):
    return [l.strip() for l in sh(f"cat '{ruta}' 2>/dev/null").splitlines() if l.strip()]


def main():
    log(f"Inicio ({'PRUEBA, no publica' if PRUEBA else 'subida real, Público'}) en {DEV}")
    avisado = False
    while not sh(f"ls '{DIR}/LISTO.txt' 2>/dev/null").strip():
        if not avisado:
            log("Esperando LISTO.txt (lo crea vigilar_videos.sh al terminar la vigilancia)...")
            avisado = True
        time.sleep(30)

    # Cada video se identifica por NOMBRE + TAMAÑO: si ya se subió uno igual, no se repite.
    lista = []
    for l in leer_lista(f"{DIR}/LISTO.txt"):
        nombre, _, tam = l.partition("\t")
        if not tam:                                   # LISTO viejo sin tamaño: se mide en el celular
            tam = sh(f"stat -c %s '{DIR}/{nombre}' 2>/dev/null").strip()
        lista.append((nombre, tam))
    hechos = set()
    for l in leer_lista(f"{DIR}/subidos.txt"):
        nombre, _, tam = l.partition("\t")
        hechos.add((nombre, tam))
    vistos, pendientes, repetidos = set(), [], 0
    for v in lista:
        if v in hechos or v in vistos:
            repetidos += 1; continue
        vistos.add(v)
        if "'" not in v[0]:
            pendientes.append(v)
    if PRUEBA:
        pendientes = pendientes[:1]
    log(f"{len(lista)} videos en la lista, {repetidos} ya subidos (mismo nombre y tamaño), {len(pendientes)} por subir.")
    if not PRUEBA and pendientes:
        avisar("ProjectPilot: subida a Facebook", f"Empiezo a subir {len(pendientes)} videos, uno detras del otro.")

    # Indexar de una vez todos los videos copiados (Facebook los recibe como content://media/...)
    cargar_ids()
    for v, _ in pendientes:
        if v not in IDS:
            sh(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d 'file://{DIR}/{v}' >/dev/null")

    # Sin notificaciones emergentes durante la subida (tapan los botones); se restaura al final
    hu = sh("settings get global heads_up_notifications_enabled").strip()
    sh("settings put global heads_up_notifications_enabled 0")
    ok = fallas_seguidas = 0
    try:
        for i, (v, tam) in enumerate(pendientes, 1):
            real = sh(f"ls '{DIR}/PARAR' 2>/dev/null; stat -c %s '{DIR}/{v}' 2>/dev/null").strip()
            if "PARAR" in real:
                log("Encontré PARAR: freno."); break
            if real != tam:
                log(f"  ✗ {v}: el tamaño en el celular ({real or 'no está'}) no coincide con la lista ({tam}); lo salteo.")
                continue
            celular_listo()
            log(f"[{i}/{len(pendientes)}] {v} ({int(tam) / 1048576:.1f} MB)")
            if subir(v):
                ok += 1; fallas_seguidas = 0
                if not PRUEBA:
                    sh(f"printf '%s\\t%s\\n' '{v}' '{tam}' >> '{DIR}/subidos.txt'")
            else:
                fallas_seguidas += 1
                if fallas_seguidas >= 2:
                    log("Dos fallas seguidas: freno para revisar.")
                    avisar("ProjectPilot: subida frenada", "Fallaron 2 videos seguidos. Revisa registro_subida.txt.")
                    break
            if i < len(pendientes) and not PRUEBA:
                espera = random.randint(*PAUSA)
                log(f"  sigo en {espera} s")
                time.sleep(espera)
    finally:
        sh(f"settings put global heads_up_notifications_enabled {hu if hu in ('0', '1') else 1}")
    log(f"Fin: {ok} de {len(pendientes)} {'probados' if PRUEBA else 'publicados'}.")
    if not PRUEBA and pendientes:
        avisar("ProjectPilot: subida terminada", f"Publicados {ok} de {len(pendientes)} videos.")


if __name__ == "__main__":
    main()
