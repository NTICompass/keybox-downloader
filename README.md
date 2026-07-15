# Keybox Downloader

Download `keybox.xml` files from various Magisk modules / GitHub projects.
Also install them on your phone.

Runs on PC or even on Android (via termux).

## Android Instructions

```bash
pkg install uv python python-cryptography
git checkout ...
cd keybox-downloader
uv venv --system-site-packages
uv run main.py
```

If you DO need to compile wheels, then run `export ANDROID_API_LEVEL=24`.