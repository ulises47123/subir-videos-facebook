#!/data/data/com.termux/files/usr/bin/bash
# Vigila la carpeta de videos de Termux y actualiza el listado cada 30 s.
# Si pasan 10 minutos sin ningun cambio (ni videos nuevos ni videos que sigan creciendo),
# copia los videos a /sdcard/Movies/SubirFacebook, deja LISTO.txt con la lista y termina.
# Uso:  bash vigilar_videos.sh              (vigila ~/Videos, 10 min)
#       bash vigilar_videos.sh ~/otra 5     (otra carpeta, 5 min)
#       bash vigilar_videos.sh ~/Videos 0   (sin esperar: copia ya)

CARPETA="${1:-$HOME/Videos}"
DESTINO=/sdcard/Movies/SubirFacebook
INTERVALO=30                       # segundos entre revisiones
QUIETO_MAX=$(( ${2:-10} * 60 ))    # minutos sin cambios para terminar (2do parametro; 0 = ya)

if [ ! -d "$CARPETA" ]; then echo "No existe la carpeta $CARPETA"; exit 1; fi

firma() {
  # nombre <tab> tamaño de cada video (los .part de descargas a medias no cuentan)
  find "$CARPETA" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.mkv' \
       -o -iname '*.webm' -o -iname '*.3gp' \) -printf '%f\t%s\n' | sort
}

ultima=""; cambio=$(date +%s)
while true; do
  actual=$(firma); ahora=$(date +%s)
  if [ "$actual" != "$ultima" ]; then ultima="$actual"; cambio=$ahora; fi
  quieto=$((ahora - cambio))
  n=$(printf '%s' "$actual" | grep -c .)
  clear
  echo "Vigilando ${CARPETA/#$HOME/~}  $(date +%H:%M:%S)"
  echo "$n videos | quieto $((quieto / 60))m $((quieto % 60))s de $((QUIETO_MAX / 60))m"
  echo "----------------------------------------"
  [ "$n" -gt 15 ] && echo "(ultimos 15 de $n)"
  printf '%s\n' "$actual" | tail -n 15 | awk -F'\t' 'NF { printf "%5.1fMB %s\n", $2 / 1048576, $1 }'
  [ "$quieto" -ge "$QUIETO_MAX" ] && break
  sleep "$INTERVALO"
done

echo
echo "$((QUIETO_MAX / 60)) minutos sin cambios: listado final de $n videos."
mkdir -p "$DESTINO"
rm -f "$DESTINO/LISTO.txt"
printf '%s\n' "$actual" | grep . | while IFS=$'\t' read -r v tam; do
  # mismo nombre y mismo tamaño = mismo video: no se vuelve a copiar
  if [ -f "$DESTINO/$v" ] && [ "$(stat -c %s "$DESTINO/$v")" = "$tam" ]; then continue; fi
  cp -f "$CARPETA/$v" "$DESTINO/$v" && echo "  copiado: $v"
done
# LISTO.txt: nombre <tab> tamaño (la PC no sube dos veces el mismo nombre con el mismo tamaño)
printf '%s\n' "$actual" | grep . > "$DESTINO/LISTO.txt.tmp" && mv "$DESTINO/LISTO.txt.tmp" "$DESTINO/LISTO.txt"
echo
echo "Listo: $n videos en $DESTINO (LISTO.txt creado). La PC empieza a subirlos a Facebook."
echo "Para frenar la subida en cualquier momento:  touch $DESTINO/PARAR"
