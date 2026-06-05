from abc import ABC
from dataclasses import dataclass, field, fields
from json import JSONDecodeError
from pathlib import Path
from typing import ClassVar
import __main__
import json


@dataclass
class BaseData(ABC):
    _loaded = False

    _root: ClassVar[Path] = __main__.exe_root
    _manifest_path: ClassVar[Path] = _root / 'cache'
    _manifest_json = 'manifest.json'
    _manifest_file: Path = field(init=False)

    def __post_init__(self):
        self._manifest_file = self._manifest_path / self._manifest_json

        self._manifest_path.mkdir(exist_ok=True)
        self._manifest_file.touch(exist_ok=True)

        with open(self._manifest_file, 'r') as file:
            try:
                for k, v in json.load(file).items():
                    object.__setattr__(self, k, v)
            except JSONDecodeError:
                pass
            finally:
                self._loaded = True

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

        if not name.startswith('_') and self._loaded:
            self.save()

    def save(self):
        with open(self._manifest_file, 'w') as file:
            json.dump(
                {
                    f.name: getattr(self, f.name)
                    for f in fields(self)
                    if not f.name.startswith('_')
                },
                file,
            )
