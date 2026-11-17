@echo off
chcp 65001 >nul
title Subir videos a Facebook
cd /d "%~dp0"

echo ==========================================================
echo   Subir videos a Facebook (perfil, Publico)
echo ==========================================================
echo   Antes de seguir:
echo    - Celular en la misma Wi-Fi y con Depuracion inalambrica
echo    - Celular desbloqueado y sin usar mientras sube
echo    - En Termux:  vigilar   (o vigilar0 para no esperar)
echo.
echo   Para frenar:  cerrar esta ventana  o  en Termux:
echo     touch /sdcard/Movies/SubirFacebook/PARAR
echo ==========================================================
echo.

set "PY=python"
where python >nul 2>nul || set "PY=py"

rem Conecta el celular; si no lo encuentra muestra un QR en la consola para vincularlo
%PY% conectar_celular.py
if errorlevel 1 (
  echo.
  pause
  exit /b 1
)
echo.

%PY% subir_facebook.py %*

echo.
echo Termino. El detalle queda en registro_subida.txt
pause
