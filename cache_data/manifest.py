from dataclasses import dataclass

from .basedata import BaseData


@dataclass
class Manifest(BaseData):
    last_checked: int | float = 0  # Keybox downloading
    attestation_date: int | float = 0  # Google attestation status
