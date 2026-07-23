from dataclasses import dataclass, field

from .basedata import BaseData


@dataclass
class Overrides[T: type](BaseData):
    # Override Downloader.ENABLED
    enabled: dict[str, bool] = field(default_factory=dict)
    _manifest_json = 'overrides.json'

    def toggle(self, cls: T, value: bool, save=True):
        self.enabled[cls.__name__] = value

        if save:
            self.save()

    def is_enabled(self, cls: T) -> bool | None:
        return self.enabled.get(cls.__name__, None)
