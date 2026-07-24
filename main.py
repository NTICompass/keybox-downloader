# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Keybox-Downloader main launcher."""

import sys
from pathlib import Path as SysPath

from anyio import Path

# https://nuitka.net/user-documentation/common-issue-solutions.html#onefile-finding-files
is_nuitka = '__compiled__' in globals()

# https://pyinstaller.org/en/stable/runtime-information.html
is_pyinstaller = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# `root` is where "internal files" are, like the "scripts" directory
root = (
    Path(sys._MEIPASS)  # ruff: ignore[private-member-access]
    if is_pyinstaller
    else Path(SysPath(__file__).resolve().parent)
)

# `exe_root` is where the program was run from, where "keyboxes" and such go
exe_root = Path(sys.executable).parent if is_pyinstaller else (Path(sys.argv[0]).parent if is_nuitka else root)

# ruff: disable[module-import-not-at-top-of-file]
import argparse

import anyio

from downloaders import Downloader
from program.action import get_downloaders, go
from program.install import main_menu

# ruff: enable[module-import-not-at-top-of-file]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-d', '--download', dest='download', action='store_true')
    group.add_argument('-i', '--install', dest='install', action='store_true')

    args = parser.parse_args()

    async def main() -> None:
        """Select which entrypoint to run."""
        async with Downloader.start():
            if args.download:
                await go(*get_downloaders())
            elif args.install:
                await main_menu()
            else:
                await main_menu(ignore_empty=True)

    anyio.run(main, backend='asyncio')
