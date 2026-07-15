from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(data: Any) -> str:
    return sha256_text(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items() if item is not None and item != [] and item != {}}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class PartLookupQuery:
    manufacturer_part_number: str
    manufacturer: str | None = None
    source_part_number: str | None = None

    def fingerprint(self) -> str:
        return sha256_json(_plain(self))


@dataclass
class PriceBreak:
    quantity: int
    unit_price: str
    currency: str | None = None


@dataclass
class TechnicalParameter:
    name: str
    value: str
    unit: str | None = None
    source_field: str | None = None


@dataclass
class SourceLink:
    title: str
    kind: str
    url: str | None = None
    revision: str | None = None
    retrieved_at: str | None = None
    retention_mode: str = "external_reference"


@dataclass
class CadAsset:
    kind: str
    url_or_ref: str | None = None
    format: str | None = None
    retention_mode: str = "external_reference"


@dataclass
class NormalizedPart:
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    distributor_part_numbers: list[str] = field(default_factory=list)
    product_url: str | None = None
    datasheet_url: str | None = None
    image_url: str | None = None
    description: str | None = None
    lifecycle_status: str | None = None
    availability: int | None = None
    price_breaks: list[PriceBreak] = field(default_factory=list)
    minimum_order_quantity: int | None = None
    packaging: str | None = None
    rohs: str | None = None
    reach: str | None = None
    approvals: list[str] = field(default_factory=list)
    declarations: list[str] = field(default_factory=list)
    distributor_category: str | None = None
    manufacturer_family: str | None = None
    keywords: list[str] = field(default_factory=list)
    technical_parameters: list[TechnicalParameter] = field(default_factory=list)
    documents: list[SourceLink] = field(default_factory=list)
    cad_assets: list[CadAsset] = field(default_factory=list)


@dataclass
class SourceFetchResult:
    source_name: str
    retrieved_at: str
    request_fingerprint: str
    raw_payload_sha256: str
    normalized: NormalizedPart
    raw_payload_ref: str | None = None
    license_notes: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"
