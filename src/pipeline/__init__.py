"""Data collection pipeline modules for M5."""

from .data_collection import collect_data
from .types import CollectionRequest, RawCollectionResult

__all__ = ["collect_data", "CollectionRequest", "RawCollectionResult"]
