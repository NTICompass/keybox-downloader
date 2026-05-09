from pathlib import Path
import sys

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Inside a PyInstaller bundle
    root = Path(sys._MEIPASS)
    exe_root = Path(sys.executable).parent
else:
    root = Path(__file__).parent
    exe_root = root

from program import get_downloaders, go, menu
import argparse
import asyncio

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download', dest='download', action='store_true')
    parser.add_argument('-i', '--install', dest='install', action='store_true')

    args = parser.parse_args()

    if args.download:
        asyncio.run(go(*get_downloaders()))
    elif args.install:
        menu()
    else:
        menu(True)
