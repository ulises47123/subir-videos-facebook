"""Conecta el celular por adb inalámbrico. Si no lo encuentra, muestra un QR EN LA CONSOLA para vincularlo.

En el celular: Ajustes > Opciones de desarrollador > Depuración inalámbrica > "Vincular dispositivo con código QR"
y escanear el QR que aparece acá. Sale con código 0 si quedó conectado y 1 si no.
"""
import os, random, re, string, subprocess, sys, time

# Ruta del adb: variable de entorno ADB (por defecto la de esta PC; si no existe, se usa el "adb" del PATH).
ADB = os.environ.get("ADB") or r"C:\Users\Usuario\Documents\Mi música\proyectos\app-mando-facil\.tools\android-sdk\platform-tools\adb.exe"
if not os.path.exists(ADB):
    ADB = "adb"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def adb(*args, timeout=20):
    try:
        return subprocess.run([ADB, *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def conectado():
    return any(l.endswith("\tdevice") for l in adb("devices").splitlines()[1:])


def servicios(tipo):
    """[(nombre, ip:puerto)] de los servicios mDNS de adb de ese tipo."""
    out = []
    for l in adb("mdns", "services").splitlines():
        partes = l.split("\t")
        if len(partes) >= 3 and tipo in partes[1]:
            out.append((partes[0].strip(), partes[2].strip()))
    return out


def probar_conexion():
    for _, ep in servicios("_adb-tls-connect"):
        adb("connect", ep)
    time.sleep(1.5)
    return conectado()


def mostrar_qr(texto):
    import qrcode
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(texto)
    qr.make(fit=True)
    qr.print_ascii(invert=True)     # consola con fondo oscuro: módulos oscuros sobre fondo claro


def vincular_con_qr(minutos=3):
    nombre = "pc-subirfb-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    clave = "".join(random.choices(string.digits, k=8))
    print()
    print("No encuentro el celular. Vinculalo con este QR:")
    print("  Celular: Ajustes > Opciones de desarrollador > Depuración inalámbrica")
    print("           > Vincular dispositivo con código QR  (y escaneá esto)")
    print()
    mostrar_qr(f"WIFI:T:ADB;S:{nombre};P:{clave};;")
    print()
    print(f"Esperando que lo escanees (hasta {minutos} min)...", flush=True)
    fin = time.time() + minutos * 60
    while time.time() < fin:
        for n, ep in servicios("_adb-tls-pairing"):
            if n == nombre:
                r = adb("pair", ep, clave, timeout=30)
                print("  " + r.strip().splitlines()[-1] if r.strip() else "  (sin respuesta al vincular)")
                if "Successfully" in r or "exitosamente" in r.lower():
                    # El celular publica el servicio de conexión unos segundos después
                    for _ in range(20):
                        if probar_conexion():
                            return True
                        time.sleep(2)
                return conectado()
        time.sleep(2)
    print("Se acabó el tiempo sin escanear el QR.")
    return False


def main():
    if conectado():
        print("Celular conectado.")
        return 0
    print("No veo el celular por adb. Buscándolo en la red...", flush=True)
    if probar_conexion():
        print("Celular conectado.")
        return 0
    if vincular_con_qr():
        print("Celular vinculado y conectado.")
        return 0
    print("No se pudo conectar. Revisá que el celu y la PC estén en la misma Wi-Fi.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
