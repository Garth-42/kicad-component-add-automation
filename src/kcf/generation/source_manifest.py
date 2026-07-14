from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from kcf.domain.component import ComponentSpec, SourceDocument


def source_document_to_manifest_entry(source: SourceDocument) -> dict[str, str]:
    data = asdict(source)
    return {key: value for key, value in data.items() if value is not None}


def source_manifest(spec: ComponentSpec) -> dict[str, Any]:
    sources = sorted((source_document_to_manifest_entry(source) for source in spec.sources), key=lambda item: item["source_id"])
    payload: dict[str, Any] = {
        "manifest_version": "1.0",
        "component_key": spec.component_key,
        "source_count": len(sources),
        "sources": sources,
    }
    payload["manifest_hash"] = source_manifest_hash(payload)
    return payload


def source_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_source_manifest(spec: ComponentSpec) -> str:
    return json.dumps(source_manifest(spec), indent=2, sort_keys=True) + "\n"
