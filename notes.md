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

What about other Telegram channels, what else can I find? I think I remember https://t.me/evokeroot

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
Can I release this tool to the public?
If so, make an `.exe` using [PyInstaller](https://pyinstaller.org/en/stable/).