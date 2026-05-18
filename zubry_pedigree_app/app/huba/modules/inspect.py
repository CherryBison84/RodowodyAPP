"""Alias wsteczny — preferowany moduł: ``dataset_inspect`` (unika kolizji ze ``inspect`` stdlib)."""

from app.huba.modules.dataset_inspect import (  # noqa: F401
    InspectedDataset,
    inspect_dataframe,
    inspect_dataset_from_bytes,
    inspect_dataset_from_path,
)

__all__ = [
    "InspectedDataset",
    "inspect_dataframe",
    "inspect_dataset_from_bytes",
    "inspect_dataset_from_path",
]
