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

From [Specter](https://github.com/dpejoh/specter/commit/784fbc71aa4cc93484226f754b5be75cf97ae778):

```bash
RKA_HOST="rp.mhmrdd.me"
RKA_TCP=59416
RKA_TOKEN="${RKA_TOKEN:-yurikey-5b70e270d6d69cd399c59ca3d62ccf6e}"
```

See also: https://github.com/dpejoh/specter/blob/v1.4.2/src/features/rka.sh

Even more info: https://github.com/vocolboy/RemoteKeyAttestation

Also: https://t.me/meetstrong/132
> Public RKA Server is determined to close on June 21, 2026
> No new tokens will be issued.

Is that `rp.mhmrdd.me` or another server? How can I set up my own server?
Is this at all legit?

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

The file `LICENSE.2` references "Oh My Keymint"!
That could be this: https://github.com/qwq233/OhMyKeymint

The `injector.toml` file matches the one in that repo.

So yeah, it seems the "Play-IntegrityFix" modules just re-packages "OhMyKeymint" and assumes that's good enough.
Yep, even the `README.md` is exactly the same, except they _tried_ to replace the names.

It's just "OhMyKeymint" with a sketchy `fateh7_enc_armv7` ELF added as well as `autopif4.sh` from PlayIntregityFork.

I would never use Fateh7's module, but what does "OhMyKeymint" do? Can I use that to get "strong integrity"?

Even more info about "OhMyKeymint" from Citra (https://t.me/s/citraintegritytrick)

- https://t.me/CitraIntegrityTrick/1049
- https://t.me/CitraIntegrityTrick/1050

> OhMyKeymint distinguishes itself from TrickyStore by functioning as a comprehensive KeyMint simulator rather than a
> mere patcher.
>
> However, this simulation involves a significant security trade-off by shifting the root of trust from immutable
> hardware
> chips to software-based files.
>
> Consequently, any application [...] will perceive a completely new security environment,
> which will likely trigger a requirement for you to re-login and re-bind your device to the account.

---
I found a "fork" of the "original" YuriKey called "Specter":
https://github.com/dpejoh/specter

Need to figure out where this gets its keyboxes from, it wants a file called `kb_provider.val`.
Or it falls back to `$CATALOG_URL`, which is in `https://github.com/dpejoh/specter/blob/main/src/lib/urls.sh`

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

---
Add "options" panel to toggle on/off downloaders (via `overrides.py`)
Add "description" for each downloader to be shown here.

Also show program version:

```python
from importlib.metadata import version

APP_VERSION = version("keybox-downloader")
```

Needs `pyinstaller --copy-metadata` during build.