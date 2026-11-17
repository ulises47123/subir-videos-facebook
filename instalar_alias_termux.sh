#!/data/data/com.termux/files/usr/bin/bash
# Guarda vigilar_videos.sh en ~/.scripts (carpeta oculta, protegido contra borrado accidental)
# y crea los alias "vigilar" y "vigilar0" en ~/.bashrc.
set -e
mkdir -p ~/.scripts
chmod 755 ~/.scripts
if [ -f ~/vigilar_videos.sh ]; then
  [ -f ~/.scripts/vigilar_videos.sh ] && chmod 644 ~/.scripts/vigilar_videos.sh
  mv -f ~/vigilar_videos.sh ~/.scripts/vigilar_videos.sh
elif [ ! -f ~/.scripts/vigilar_videos.sh ]; then
  cp ~/storage/downloads/vigilar_videos.sh ~/.scripts/vigilar_videos.sh
fi
# Solo lectura: si alguien hace rm, bash pregunta antes de borrarlo
chmod 555 ~/.scripts/vigilar_videos.sh
chmod 555 ~/.scripts

touch ~/.bashrc
sed -i '/# alias-vigilar-videos/d' ~/.bashrc
cat >> ~/.bashrc <<'EOF'
alias vigilar='bash ~/.scripts/vigilar_videos.sh'   # alias-vigilar-videos
alias vigilar0='bash ~/.scripts/vigilar_videos.sh ~/Videos 0'   # alias-vigilar-videos
EOF
# Si existe .bash_profile y no carga .bashrc, se agrega para que los alias anden al abrir Termux
if [ -f ~/.bash_profile ] && ! grep -q bashrc ~/.bash_profile; then
  echo '[ -f ~/.bashrc ] && . ~/.bashrc' >> ~/.bash_profile
fi

echo
echo "Listo:"
ls -l ~/.scripts/vigilar_videos.sh
grep alias-vigilar-videos ~/.bashrc
echo
echo "Uso:  vigilar            (vigila ~/Videos, corta a los 10 min sin cambios)"
echo "      vigilar0           (no espera: copia ya para subir)"
echo "      vigilar ~/otra 5   (otra carpeta, 5 min)"
