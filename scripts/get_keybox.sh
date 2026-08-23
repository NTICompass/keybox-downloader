#!/system/bin/sh
KEY_FILE=/data/local/tmp/current_keybox.xml
KEY_BOX=''
KEY_MOD=''

get_keybox_path() {
  # TrickyStore, TEESimulator (<= 3), and other forks
  if [ -d "/data/adb/tricky_store" ]; then
    KEY_BOX=/data/adb/tricky_store/keybox.xml

    if [ -f /data/adb/modules/tricky_store/libTEESimulator.so ]; then
      KEY_MOD='TEESimulator 3.x'
    elif [ -f /data/adb/modules/tricky_store/libTrickyStoreOSS.so ]; then
      KEY_MOD='TrickyStore OSS'
    else
      KEY_MOD='TrickyStore'
    fi
  # TEESimulator >= 4
  elif [ -d "/data/adb/teesim/" ]; then
    KEY_BOX=/data/adb/teesim/keybox.xml
    KEY_MOD='TEESimulator 4.x'
  # OhMyKeymint
  elif [ -d "/data/misc/keystore/omk" ]; then
    KEY_BOX=/data/misc/keystore/omk/keybox.xml
    KEY_MOD='OhMyKeymint'
  fi
}

get_keybox_path

if [ -n "$KEY_BOX" ] && [ -e "$KEY_BOX" ]; then
  cp "$KEY_BOX" "$KEY_FILE"
  chmod 666 "$KEY_FILE"
  chown shell:shell "$KEY_FILE"
fi

echo "$KEY_MOD"