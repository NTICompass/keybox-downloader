from pathlib import Path
from program import get_downloaders, go, menu
import argparse
import asyncio
import sys

if __name__ == '__main__':
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Inside a PyInstaller bundle
        root = Path(sys._MEIPASS)
    else:
        root = Path(__file__).parent
        
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
