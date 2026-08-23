#!/system/bin/sh

if [ $# -ne 1 ]; then
  echo "Usage $0 my_keybox.xml"
  exit 0
fi

KEY_FILE="$1"
PIF_SCRIPT=/data/adb/modules/playintegrityfix/autopif4.sh
KEY_BOX=''

get_keybox_path() {
  # TrickyStore, TEESimulator (<= 3), and other forks
  if [ -d "/data/adb/tricky_store" ]; then
    KEY_BOX=/data/adb/tricky_store/keybox.xml
  # TEESimulator >= 4
  elif [ -d "/data/adb/teesim/" ]; then
    KEY_BOX=/data/adb/teesim/keybox.xml
  # OhMyKeymint
  elif [ -d "/data/misc/keystore/omk" ]; then
    KEY_BOX=/data/misc/keystore/omk/keybox.xml
  fi
}

if [ -e "$KEY_FILE" ]; then
  get_keybox_path

  if [ -n "$KEY_BOX" ]; then
    cp "$KEY_FILE" "$KEY_BOX"
    chmod 644 "$KEY_BOX"
    chown root:root "$KEY_BOX"
  fi
fi

if [ -e "$PIF_SCRIPT" ]; then
  sh "$PIF_SCRIPT" -m
fi
