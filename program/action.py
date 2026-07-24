# SPDX-FileCopyrightText: Copyright 2026 gen\Eric Computers
# SPDX-License-Identifier: MIT

"""Script to gather the enabled `Downloader` modules and run them."""

import asyncio
import logging
from asyncio import Future
from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import make_archive, rmtree
from time import time
from typing import TYPE_CHECKING

from asyncstdlib import enumerate as a_enumerate
from tqdm.asyncio import tqdm_asyncio

import __main__
from cache_data import Manifest
from downloaders import Downloader

from .keybox import Keybox, KeyType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Iterator

root: Path = __main__.exe_root
path = root / 'keyboxes'
log_path = root / 'logs'
backup_path = root / 'backups'
logger = logging.getLogger(__name__)
manifest: Manifest
dl_hours = 24
local_tz = datetime.now(UTC).astimezone().tzinfo


def can_run() -> bool:
    """Return whether the downloaders can be run.

    Returns:
        If the downloaders have been run in the lat 24 hours

    """
    global manifest
    manifest = Manifest()

    # Only download once every 24hrs
    if manifest.last_checked > 0:
        time_diff = datetime.now(tz=local_tz) - datetime.fromtimestamp(manifest.last_checked, tz=local_tz)
        return (time_diff / timedelta(hours=1)) >= dl_hours

    return True


def force_run() -> None:
    """Force downloaders to run even if it's been less than 24 hours since the last run."""
    logger.info('Forcing downloads...')
    manifest.last_checked = 0


def make_folders() -> None:
    """Create the folders needed for keybox downloads."""
    path.mkdir(exist_ok=True)

    for key_type in KeyType:
        (path / key_type).mkdir()


def init() -> None:
    """Initialize the app, checking the last download time and creating needed folders.

    Raises:
        RuntimeError: If downloaders were ran in the last 24 hours

    """
    log_path.mkdir(exist_ok=True)
    logging.basicConfig(filename=f'{log_path}/keybox-downloader-{time():.0f}.log', level=logging.INFO)
    logger.info('Starting Keybox Downloader')

    if not can_run():
        msg = f'Last download was less than 24hrs ago: {manifest.last_checked}'
        raise RuntimeError(msg)

    if not path.exists():
        make_folders()
    else:
        logger.info('Backing up existing keyboxes')

        backup_path.mkdir(exist_ok=True)
        make_archive(f'{backup_path}/keyboxes-{time():.0f}', 'zip', path)
        rmtree(path)
        make_folders()


type KeyPath = tuple[Path, Keybox]


async def run(dl: Downloader) -> tuple[list[KeyPath], str]:
    """Coroutine to run the `Downloader` and get its keybox files.

    Args:
        dl: `Downloader` object to run

    Returns:
        A tuple containing a list of keybox files and the downloader name (for progress tracking)

    """
    files: list[KeyPath] = []

    async for idx, keybox_file in a_enumerate(dl()):
        keybox_idx = idx + 1

        if keybox_file is None:
            logger.info(f'Skipping empty keybox #{keybox_idx:d}')
            continue

        logger.info(f'Checking/Saving keybox #{keybox_idx:d}')
        files.append((path / keybox_file.key_type, keybox_file))

    return files, type(dl).__name__


async def go(*downloaders: Downloader, progress: Callable[[int, int, str], Awaitable[None]] | None = None) -> None:
    """Run the passed `Downloader` objects and save their keybox files (main entry point).

    Args:
         downloaders: A collection of `Downloader` objects to run
         progress: A callback to send the download progress to (if `None`, then `tqdm` is used)

    """
    try:
        init()
    except RuntimeError as e:
        logger.info(e)
    else:
        await Keybox.init_attestation(Downloader.client)
        keyboxes: list[Keybox] = []

        def as_completed[T](fs: Iterable[Awaitable[T]]) -> Iterator[Future[T]]:
            func = tqdm_asyncio.as_completed if progress is None else asyncio.as_completed
            return func(fs)

        tasks = [run(dl) for dl in downloaders]
        total = len(tasks)

        for idx, task in enumerate(as_completed(tasks), start=1):
            dl_info, dl_complete = await task
            dl_count = 0

            for folder, xml_file in dl_info:
                xml_file.save(folder)
                keyboxes.append(xml_file)
                dl_count += 1

            if progress is not None:
                await progress(idx, total, f'{dl_complete} ({dl_count})')

        logger.info('All keyboxes downloaded, comparing to find duplicates')

        groups = Keybox.group(*keyboxes)
        logger.info(groups)

        manifest.last_checked = datetime.now(tz=local_tz).timestamp()


def get_downloaders() -> list[Downloader]:
    """Collect the enabled `Downloader` modules to run.

    Returns:
        List of `Downloader` objects

    """
    return [cls() for cls in Downloader.enabled]