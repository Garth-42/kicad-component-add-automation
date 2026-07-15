from __future__ import annotations

import json
from typing import Any

from kcf.domain.component import ComponentSpec
from kcf.domain.workflow import WorkflowJob
from kcf.generation.hashing import artifact_bundle_hash, sha256_text, spec_hash
from kcf.generation.source_manifest import source_manifest
from kcf.validation.core import validate_component

GENERATOR_VERSION = "0.1.0"
KICAD_TARGET_VERSION = "10"


def release_manifest(spec: ComponentSpec, artifacts: dict[str, str], job: WorkflowJob | None = None) -> dict[str, Any]:
    validation_report = json.dumps(validate_component(spec).to_dict(), sort_keys=True, separators=(",", ":"))
    source_payload = source_manifest(spec)
    approvers = []
    if job is not None:
        approvers = [approval.to_dict() for approval in job.approvals]
    payload: dict[str, Any] = {
        "manifest_version": "1.0",
        "component_key": spec.component_key,
        "spec_hash": spec_hash(spec),
        "candidate_hash": artifact_bundle_hash({path: content for path, content in artifacts.items() if not path.endswith("release.json")}),
        "generator_version": GENERATOR_VERSION,
        "kicad_target_version": KICAD_TARGET_VERSION,
        "source_manifest_hash": source_payload["manifest_hash"],
        "validation_report_hash": sha256_text(validation_report),
        "style_policy_hash": spec.policies.get("style_policy_hash", "sha256:unconfigured"),
        "known_limitations": [],
        "review_retention": {
            "mode": spec.policies.get("review_response_retention", "summary_only"),
            "limitations": "Full discussion history is not retained unless policy opts in.",
        },
        "approvals": approvers,
    }
    payload["release_manifest_hash"] = sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return payload


def render_release_manifest(spec: ComponentSpec, artifacts: dict[str, str], job: WorkflowJob | None = None) -> str:
    return json.dumps(release_manifest(spec, artifacts, job), indent=2, sort_keys=True) + "\n"
