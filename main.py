from pathlib import Path
import sys

# https://nuitka.net/user-documentation/common-issue-solutions.html#onefile-finding-files
is_nuitka = '__compiled__' in globals()

# https://pyinstaller.org/en/stable/runtime-information.html
is_pyinstaller = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# `root` is where "internal files" are, like the "scripts" directory
root = Path(sys._MEIPASS) if is_pyinstaller else Path(__file__).resolve().parent

# `exe_root` is where the program was run from, where "keyboxes" and such go
exe_root = (
    Path(sys.executable).parent
    if is_pyinstaller
    else (Path(sys.argv[0]).parent if is_nuitka else root)
)

# ruff: disable[E402]
from downloaders import Downloader
from program.action import get_downloaders, go
from program.install import menu
import argparse
import asyncio
# ruff: enable[E402]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-d', '--download', dest='download', action='store_true')
    group.add_argument('-i', '--install', dest='install', action='store_true')

    args = parser.parse_args()
    context = Downloader.start()

    async def run_dl():
        async with context:
            await go(*get_downloaders())

    if args.download:
        asyncio.run(run_dl())
    elif args.install:
        menu(context)
    else:
        menu(context, True)
