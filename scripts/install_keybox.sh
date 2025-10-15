#!/system/bin/sh
KEY_FILE=/data/local/tmp/my_keybox.xml
KEY_BOX=/data/adb/tricky_store/keybox.xml
PIF_SCRIPT=/data/adb/modules/playintegrityfix/autopif2.sh

if [ -e "$KEY_FILE" ]; then
  mv "$KEY_FILE" "$KEY_BOX"
  chmod 644 "$KEY_BOX"
  chown root:root "$KEY_BOX"
fi

if [ -e "$PIF_SCRIPT" ]; then
  sh "$PIF_SCRIPT" -s -m -p
fi