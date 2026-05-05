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
