from __future__ import annotations

from decimal import Decimal

from kcf.domain.component import ComponentSpec
from kcf.validation.findings import Finding, Severity, ValidationReport


def validate_component(spec: ComponentSpec) -> ValidationReport:
    findings: list[Finding] = []
    artifact = spec.component_key

    pin_numbers = [pin.number for pin in spec.symbol.pins]
    pad_numbers = [pad.number for pad in spec.footprint.pads]

    for number in sorted(set(pin_numbers)):
        if pin_numbers.count(number) > 1:
            findings.append(Finding(code="DUPLICATE_PIN", severity=Severity.ERROR, message=f"Symbol pin {number} is duplicated.", artifact=artifact, path="symbol.pins", validator="semantic"))
    for number in sorted(set(pad_numbers)):
        if pad_numbers.count(number) > 1:
            findings.append(Finding(code="DUPLICATE_PAD", severity=Severity.ERROR, message=f"Footprint pad {number} is duplicated.", artifact=artifact, path="footprint.pads", validator="semantic"))

    for number in sorted(set(pin_numbers) - set(pad_numbers)):
        findings.append(Finding(code="PIN_PAD_MISMATCH", severity=Severity.ERROR, message=f"Symbol pin {number} has no connectable footprint pad.", artifact=artifact, path="symbol.pins", validator="pin_pad_parity"))
    for number in sorted(set(pad_numbers) - set(pin_numbers)):
        findings.append(Finding(code="PIN_PAD_MISMATCH", severity=Severity.ERROR, message=f"Footprint pad {number} has no symbol pin.", artifact=artifact, path="footprint.pads", validator="pin_pad_parity"))

    if spec.schema_version != "1.0":
        findings.append(Finding(code="UNSUPPORTED_SCHEMA_VERSION", severity=Severity.ERROR, message=f"Unsupported schema version {spec.schema_version}.", artifact=artifact, path="schema_version", validator="schema"))

    if not spec.sources:
        findings.append(Finding(code="MISSING_SOURCE_EVIDENCE", severity=Severity.ERROR, message="At least one source document is required for MVP release.", artifact=artifact, path="sources", validator="sources"))

    evidence_facts = spec.evidence.get("facts", []) if isinstance(spec.evidence, dict) else []
    if not evidence_facts:
        findings.append(Finding(code="MISSING_EVIDENCE_FACTS", severity=Severity.WARNING, message="Evidence facts are not recorded for pins, dimensions, or model metadata.", artifact=artifact, path="evidence.facts", validator="evidence", waivable=True))

    if spec.classification.risk_level == "high" or spec.classification.safety_related or spec.classification.mains_rated:
        if not spec.release_constraints.required_human_roles:
            findings.append(Finding(code="MISSING_RISK_REVIEW_ROLE", severity=Severity.ERROR, message="High-risk, safety-related, or mains-rated components require at least one human reviewer role.", artifact=artifact, path="release_constraints.required_human_roles", validator="release_constraints"))

    if spec.footprint.body.width_mm <= 0 or spec.footprint.body.depth_mm <= 0:
        findings.append(Finding(code="INVALID_BODY_DIMENSIONS", severity=Severity.ERROR, message="Footprint body width and depth must be positive.", artifact=artifact, path="footprint.body", validator="geometry"))
    if spec.footprint.courtyard.clearance_mm < Decimal("0"):
        findings.append(Finding(code="INVALID_COURTYARD", severity=Severity.ERROR, message="Courtyard clearance must not be negative.", artifact=artifact, path="footprint.courtyard.clearance_mm", validator="geometry"))

    supported_families = {"terminal_block", "through_hole_connector", "smd_passive", "ic_package"}
    if spec.classification.family not in supported_families:
        findings.append(Finding(code="UNSUPPORTED_GENERATOR_FAMILY", severity=Severity.WARNING, message=f"Generator family {spec.classification.family} is not one of the MVP-supported templates.", artifact=artifact, path="classification.family", validator="generator_coverage", waivable=True))

    if spec.footprint.technology == "through_hole":
        for index, pad in enumerate(spec.footprint.pads):
            if pad.drill_mm is None:
                findings.append(Finding(code="MISSING_DRILL", severity=Severity.ERROR, message=f"Through-hole pad {pad.number} is missing drill_mm.", artifact=artifact, path=f"footprint.pads[{index}].drill_mm", validator="geometry"))

    source_ids = [source.source_id for source in spec.sources]
    for source_id in sorted(set(source_ids)):
        if source_ids.count(source_id) > 1:
            findings.append(Finding(code="DUPLICATE_SOURCE", severity=Severity.ERROR, message=f"Source {source_id} is duplicated.", artifact=artifact, path="sources", validator="sources"))

    for index, source in enumerate(spec.sources):
        if source.retention_mode == "external_reference" and not (source.uri or source.external_reference):
            findings.append(Finding(code="SOURCE_REFERENCE_MISSING", severity=Severity.ERROR, message=f"Source {source.source_id} requires uri or external_reference.", artifact=artifact, path=f"sources[{index}]", validator="sources"))
        if source.retention_mode in {"embedded", "local_only"} and not source.local_path:
            findings.append(Finding(code="SOURCE_LOCAL_PATH_MISSING", severity=Severity.WARNING, message=f"Source {source.source_id} should record local_path for retained source files.", artifact=artifact, path=f"sources[{index}].local_path", validator="sources", waivable=True))

    if spec.footprint.technology == "smd":
        for index, pad in enumerate(spec.footprint.pads):
            if pad.drill_mm is not None:
                findings.append(Finding(code="SMD_PAD_HAS_DRILL", severity=Severity.ERROR, message=f"SMD pad {pad.number} must not define drill_mm.", artifact=artifact, path=f"footprint.pads[{index}].drill_mm", validator="geometry"))

    if spec.model_3d.path and spec.model_3d.status in {"unknown", "not_provided"}:
        findings.append(Finding(code="MODEL_3D_STATUS_MISMATCH", severity=Severity.WARNING, message="3D model path is set but model_3d.status does not indicate a provided/referenced model.", artifact=artifact, path="model_3d.status", validator="model_3d", waivable=True))

    if spec.assumptions:
        for assumption in spec.assumptions:
            if assumption.approval_required and not assumption.approved_by:
                findings.append(Finding(code="UNAPPROVED_ASSUMPTION", severity=Severity.WARNING, message=f"Assumption {assumption.assumption_id} requires approval.", artifact=artifact, path="assumptions", validator="assumptions", waivable=True))

    blocked_warning_codes = set(spec.release_constraints.block_on_warning_codes)
    for finding in list(findings):
        if finding.severity == Severity.WARNING and finding.code in blocked_warning_codes:
            findings.append(Finding(code="BLOCKED_WARNING", severity=Severity.ERROR, message=f"Release constraints block warning {finding.code}.", artifact=artifact, path="release_constraints.block_on_warning_codes", validator="release_constraints"))

    return ValidationReport(component_key=spec.component_key, findings=findings)
