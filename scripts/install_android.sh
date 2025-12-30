#!/system/bin/sh

if [ $# -ne 1 ]; then
  echo "Usage $0 my_keybox.xml"
  exit 0
fi

KEY_FILE="$1"
KEY_BOX=/data/adb/tricky_store/keybox.xml
PIF_SCRIPT=/data/adb/modules/playintegrityfix/autopif4.sh

if [ -e "$KEY_FILE" ]; then
  cp "$KEY_FILE" "$KEY_BOX"
  chmod 644 "$KEY_BOX"
  chown root:root "$KEY_BOX"
fi

if [ -e "$PIF_SCRIPT" ]; then
  sh "$PIF_SCRIPT" -m
fi
