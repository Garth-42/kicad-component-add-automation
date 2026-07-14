from __future__ import annotations

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

    if spec.assumptions:
        for assumption in spec.assumptions:
            if assumption.approval_required and not assumption.approved_by:
                findings.append(Finding(code="UNAPPROVED_ASSUMPTION", severity=Severity.WARNING, message=f"Assumption {assumption.assumption_id} requires approval.", artifact=artifact, path="assumptions", validator="assumptions", waivable=True))

    return ValidationReport(component_key=spec.component_key, findings=findings)
