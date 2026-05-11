from typing import TypedDict


class CacheManifest(TypedDict, total=False):
    last_checked: int | float
    attestation_date: int | float
