import argparse
from program import go, menu

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download', dest='download', action='store_true')
    parser.add_argument('-i', '--install', dest='install', action='store_true')

    args = parser.parse_args()

    if args.download:
        go()
    elif args.install:
        menu()