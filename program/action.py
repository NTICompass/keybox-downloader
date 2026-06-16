from .keybox import Keybox, KeyType
from asyncstdlib import enumerate as a_enumerate
from cache_data import Manifest
from collections.abc import Generator
from datetime import datetime, timedelta
from downloaders import Downloader
from pathlib import Path
from shutil import make_archive, rmtree
from time import time
from tqdm.asyncio import tqdm_asyncio
import __main__
import logging


root: Path = __main__.exe_root
path = root / 'keyboxes'
log_path = root / 'logs'
backup_path = root / 'backups'
logger = logging.getLogger(__name__)
manifest: Manifest


def can_run() -> bool:
    global manifest
    manifest = Manifest()

    # Only download once every 24hrs
    if manifest.last_checked > 0:
        time_diff = datetime.now() - datetime.fromtimestamp(manifest.last_checked)
        return (time_diff / timedelta(hours=1)) >= 24

    return True


def force_run():
    global manifest

    logger.info('Forcing downloads...')
    manifest.last_checked = 0


def make_folders():
    path.mkdir(exist_ok=True)

    for key_type in KeyType:
        (path / key_type).mkdir()


def init():
    log_path.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=f'{log_path}/keybox-downloader-{time():.0f}.log', level=logging.INFO
    )
    logger.info('Starting Keybox Downloader')

    if not can_run():
        raise RuntimeError(
            f'Last download was less than 24hrs ago: {manifest.last_checked}'
        )

    if not path.exists():
        make_folders()
    else:
        logger.info('Backing up existing keyboxes')

        backup_path.mkdir(exist_ok=True)
        make_archive(f'{backup_path}/keyboxes-{time():.0f}', 'zip', path)
        rmtree(path)
        make_folders()


async def run(dl: Downloader) -> list[tuple[Path, Keybox]]:
    files: list[tuple[Path, Keybox]] = []

    async for idx, keybox_file in a_enumerate(dl()):
        keybox_idx = idx + 1

        if keybox_file is None:
            logger.info(f'Skipping empty keybox #{keybox_idx:d}')
            continue

        logger.info(f'Checking/Saving keybox #{keybox_idx:d}')
        files.append((path / keybox_file.key_type, keybox_file))

    return files


async def go(*downloaders: Downloader):
    try:
        init()
    except RuntimeError as e:
        logger.info(e)
    else:
        await Keybox.init_attestation(Downloader.client)
        keyboxes: list[Keybox] = []

        for task in tqdm_asyncio.as_completed([run(dl) for dl in downloaders]):
            for folder, xml_file in await task:
                xml_file.save(folder)
                keyboxes.append(xml_file)

        logger.info('All keyboxes downloaded, comparing to find duplicates')

        groups = Keybox.group(*keyboxes)
        logger.info(groups)

        manifest.last_checked = datetime.now().timestamp()


def get_downloaders() -> Generator[Downloader]:
    return (cls() for cls in Downloader.enabled)
