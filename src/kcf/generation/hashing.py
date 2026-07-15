from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from kcf.domain.component import ComponentSpec
from kcf.domain.serialization import component_to_dict


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def spec_hash(spec: ComponentSpec) -> str:
    return sha256_json(component_to_dict(spec))


def artifact_bundle_hash(artifacts: Mapping[str, str]) -> str:
    payload = {path: sha256_text(content) for path, content in sorted(artifacts.items())}
    return sha256_json(payload)
