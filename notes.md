There's something called "PlayStrong" that uses RKA (Remote Key Attestation?) or RSP tokens.

- https://t.me/s/meetstrong
    - also https://t.me/remotesp

> This was found via YuriKey: https://t.me/s/who_is_yuri

Info (via https://t.me/s/arcintalknotes):
> In short, playstrong is a method to obtain integrity from another device's integrity that is channeled through a
> server. The advantage is that it can last a long time. However, there are several drawbacks, including:
>1. It cannot lock the spoofing to the bootloader, so a keybox is still required to perform bootloader spoofing.
>2. It is highly dependent on the server of the device owner used for attestation. If the server errors out,
    disconnects, or reaches its limit, you won't be able to get integrity.
---

New "page" for IntegrityBox:  https://integritybox2.vercel.app/

No keybox download, just links to Telegram: https://t.me/s/IntegrityBox

---
How can I download files from Telegram? They have an API, but then I'd need to make an account.
Maybe use something like telegram@totallysecure.email?

Use: https://codeberg.org/Lonami/Telethon

What about other Telegram channels, what else can I find? I think I remember https://t.me/evokeroot

Also, I just found https://t.me/s/HidingRootDetections

---
I found another project that's basically doing the same thing as mine, but with only 3 sources.
https://github.com/purainity/keybox-tools

Though they do have public keys for the "hardware attestation root", which could be interesting to try to check against.

---
Can I generate my own keybox?
https://github.com/KOWX712/Tricky-Addon-Update-Target-List/blob/main/webui/scripts/keygen.js

It seems to generate a self-signed one, will that work? Is there any other way to get the signing cert?

https://github.com/LRFP-Team/keyboxGenerator
This lets you get "device" integrity, is that good enough?

---
In https://github.com/FBIVIP/Play-IntegrityFix/releases, there is no longer just a `keybox.xml` (well, there is, but
it's an AOSP keybox).
What there is... is 3 ELF files:

- fateh7_enc_armv7
- libs/arm64-v8a/inject
- libs/arm64-v8a/keymint

What are these doing?

It's not generating a keybox, is it? The module purposely removes Tricky Store and
PlayIntegrityFork, so what could it be doing?

I think `inject` does something with the built-in keystore and `keymint` may create a key, but's just gonna be
self-signed.

---
Can I release this tool to the public?
If so, make an `.exe` using [PyInstaller](https://pyinstaller.org/en/stable/).

```
pyinstaller.exe --add-data "scripts:scripts" --onefile --noupx .\main.py
```

This works on Android..... kind of.

`/sdcard/` is `noexec`, so the binary needs to be in `/data/local/tmp`
I also need to include the following libs from termux:

- `/data/data/com.termux/files/usr/lib/libz.so.1.3.2` (`ln -s libz.so.1 libz.so.1.3.2`)
- `/data/data/com.termux/files/usr/lib/libandroid-support.so`

Then you can run with:
`LD_LIBRARY_PATH=$PWD ./main`

This works over `adb shell`, but not in Termius. It works in Termux.
What other local terminal emulators could I try?

---
With `uv`: `uv sync`

With `pip` (Android): `pip install .[build]`