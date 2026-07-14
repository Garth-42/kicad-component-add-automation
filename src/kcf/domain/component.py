from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


class ComponentValidationError(ValueError):
    pass


def dec(value: Any) -> Decimal:
    return Decimal(str(value))


def require_keys(data: dict[str, Any], keys: list[str], path: str) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise ComponentValidationError(f"{path} missing required keys: {', '.join(missing)}")


@dataclass
class Identity:
    manufacturer: str
    manufacturer_part_number: str
    library_name: str
    symbol_name: str
    footprint_name: str
    description: str
    datasheet_description: str | None = None
    keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Identity:
        require_keys(data, ["manufacturer", "manufacturer_part_number", "library_name", "symbol_name", "footprint_name", "description"], "identity")
        return cls(**data)


@dataclass
class Classification:
    family: str
    risk_level: str = "medium"
    safety_related: bool = False
    mains_rated: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Classification:
        require_keys(data, ["family"], "classification")
        if data.get("risk_level", "medium") not in {"low", "medium", "high"}:
            raise ComponentValidationError("classification.risk_level must be low, medium, or high")
        return cls(**data)


@dataclass
class SymbolBody:
    width_grid_units: int
    height_grid_units: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SymbolBody:
        return cls(int(data["width_grid_units"]), int(data["height_grid_units"]))


@dataclass
class SymbolPin:
    number: str
    name: str
    electrical_type: str = "passive"
    orientation: str = "right"
    group: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SymbolPin:
        require_keys(data, ["number", "name"], "symbol.pins[]")
        return cls(**data)


@dataclass
class SymbolSpec:
    reference_prefix: str
    representation: str
    body: SymbolBody
    pins: list[SymbolPin]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SymbolSpec:
        require_keys(data, ["reference_prefix", "body", "pins"], "symbol")
        return cls(data["reference_prefix"], data.get("representation", "single_unit"), SymbolBody.from_dict(data["body"]), [SymbolPin.from_dict(item) for item in data["pins"]])


@dataclass
class FootprintBody:
    width_mm: Decimal
    depth_mm: Decimal
    height_mm: Decimal | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FootprintBody:
        return cls(dec(data["width_mm"]), dec(data["depth_mm"]), dec(data["height_mm"]) if data.get("height_mm") is not None else None)


@dataclass
class FootprintPad:
    number: str
    x_mm: Decimal
    y_mm: Decimal
    shape: str
    size_x_mm: Decimal
    size_y_mm: Decimal
    drill_mm: Decimal | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FootprintPad:
        require_keys(data, ["number", "x_mm", "y_mm", "shape", "size_x_mm", "size_y_mm"], "footprint.pads[]")
        pad = cls(data["number"], dec(data["x_mm"]), dec(data["y_mm"]), data["shape"], dec(data["size_x_mm"]), dec(data["size_y_mm"]), dec(data["drill_mm"]) if data.get("drill_mm") is not None else None)
        if pad.shape not in {"rect", "circle", "oval"}:
            raise ComponentValidationError("pad shape must be rect, circle, or oval")
        if pad.drill_mm is not None and pad.drill_mm >= min(pad.size_x_mm, pad.size_y_mm):
            raise ComponentValidationError("drill_mm must be smaller than pad size")
        return pad


@dataclass
class CourtyardSpec:
    method: str = "body_plus_clearance"
    clearance_mm: Decimal = Decimal("0.50")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CourtyardSpec:
        return cls(data.get("method", "body_plus_clearance"), dec(data["clearance_mm"]))


@dataclass
class FootprintSpec:
    technology: str
    origin_strategy: str
    pitch_mm: Decimal | None
    body: FootprintBody
    pads: list[FootprintPad]
    courtyard: CourtyardSpec

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FootprintSpec:
        require_keys(data, ["technology", "body", "pads", "courtyard"], "footprint")
        return cls(data["technology"], data.get("origin_strategy", "pad_1"), dec(data["pitch_mm"]) if data.get("pitch_mm") is not None else None, FootprintBody.from_dict(data["body"]), [FootprintPad.from_dict(item) for item in data["pads"]], CourtyardSpec.from_dict(data["courtyard"]))


@dataclass
class Model3D:
    status: str = "unknown"
    path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Model3D:
        return cls(**(data or {}))


@dataclass
class Assumption:
    assumption_id: str
    field: str
    value: str
    reason: str
    unit: str | None = None
    approved_by: str | None = None
    approval_required: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Assumption:
        return cls(**data)


@dataclass
class ReleaseConstraints:
    required_human_roles: list[str] = field(default_factory=list)
    block_on_warning_codes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ReleaseConstraints:
        return cls(**(data or {}))


@dataclass
class ComponentSpec:
    schema_version: str
    component_key: str
    identity: Identity
    classification: Classification
    symbol: SymbolSpec
    footprint: FootprintSpec
    model_3d: Model3D = field(default_factory=Model3D)
    sources: list[dict[str, str]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    assumptions: list[Assumption] = field(default_factory=list)
    policies: dict[str, str] = field(default_factory=dict)
    release_constraints: ReleaseConstraints = field(default_factory=ReleaseConstraints)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComponentSpec:
        require_keys(data, ["schema_version", "component_key", "identity", "classification", "symbol", "footprint"], "component")
        key = data["component_key"]
        if any(ch for ch in key if not (ch.islower() or ch.isdigit() or ch == "-")):
            raise ComponentValidationError("component_key must be a lowercase slug")
        return cls(
            data["schema_version"], key, Identity.from_dict(data["identity"]), Classification.from_dict(data["classification"]), SymbolSpec.from_dict(data["symbol"]), FootprintSpec.from_dict(data["footprint"]), Model3D.from_dict(data.get("model_3d")), data.get("sources", []), data.get("evidence", {}), [Assumption.from_dict(item) for item in data.get("assumptions", [])], data.get("policies", {}), ReleaseConstraints.from_dict(data.get("release_constraints")),
        )
