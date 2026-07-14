from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from kcf.domain.component import ComponentSpec


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def component_to_dict(spec: ComponentSpec) -> dict[str, Any]:
    return _plain(spec)


def dump_component_yaml(spec: ComponentSpec) -> str:
    # JSON is a valid YAML 1.2 subset and is deterministic here.
    return json.dumps(component_to_dict(spec), indent=2, sort_keys=False) + "\n"


def load_component(path: Path) -> ComponentSpec:
    return ComponentSpec.from_dict(json.loads(path.read_text(encoding="utf-8")))
