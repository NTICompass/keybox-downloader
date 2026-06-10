from pathlib import Path
import sys

root = (
    Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).resolve().parent
)
exe_root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else root

# ruff: disable[E402]
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

    if args.download:
        asyncio.run(go(*get_downloaders()))
    elif args.install:
        menu()
    else:
        menu(True)
