from __future__ import annotations

from typing import Protocol

from kcf.ingestion.normalized import PartLookupQuery, SourceFetchResult


class SourceAdapter(Protocol):
    source_name: str

    def lookup_part(self, query: PartLookupQuery) -> SourceFetchResult:
        ...
