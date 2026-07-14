import json
from pathlib import Path

import pytest

from kcf.cli.main import run
from kcf.domain.component import ComponentSpec, ComponentValidationError
from kcf.domain.serialization import dump_component_yaml, load_component, component_to_dict
from kcf.validation.core import validate_component

FIXTURE = Path("tests/fixtures/terminal_block.yaml")


def test_loads_terminal_block_fixture() -> None:
    spec = load_component(FIXTURE)
    assert spec.component_key == "example-manufacturer-abc123-03"
    assert str(spec.footprint.pads[1].x_mm) == "5.08"


def test_stable_yaml_round_trip() -> None:
    spec = load_component(FIXTURE)
    dumped = dump_component_yaml(spec)
    assert '"schema_version": "1.0"' in dumped
    assert '"component_key": "example-manufacturer-abc123-03"' in dumped


def test_pin_pad_mismatch_is_error() -> None:
    spec = load_component(FIXTURE)
    spec.footprint.pads.pop()
    report = validate_component(spec)
    assert not report.passed
    assert any(f.code == "PIN_PAD_MISMATCH" for f in report.findings)


def test_invalid_component_key_rejected() -> None:
    data = component_to_dict(load_component(FIXTURE))
    data["component_key"] = "Bad Key"
    with pytest.raises(ComponentValidationError):
        ComponentSpec.from_dict(data)


def test_component_schema_file_matches_cli_output(tmp_path: Path) -> None:
    schema_path = tmp_path / "component.schema.json"
    assert run(["schema", "--output", str(schema_path)]) == 0
    assert schema_path.read_text(encoding="utf-8") == Path("schemas/component.schema.json").read_text(encoding="utf-8")


def test_component_schema_documents_core_constraints() -> None:
    schema = json.loads(Path("schemas/component.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["properties"]["component_key"]["pattern"] == "^[a-z0-9-]+$"
    assert schema["$defs"]["classification"]["properties"]["risk_level"]["enum"] == ["low", "medium", "high"]
    assert schema["$defs"]["footprint_pad"]["properties"]["shape"]["enum"] == ["rect", "circle", "oval"]


def test_source_manifest_metadata_round_trips_and_validates() -> None:
    spec = load_component(FIXTURE)

    assert spec.sources[0].source_id == "datasheet"
    assert spec.sources[0].document_revision == "A"
    assert spec.sources[0].retrieval_date == "2026-07-14"
    assert validate_component(spec).passed


def test_source_validation_rejects_bad_sha256() -> None:
    data = component_to_dict(load_component(FIXTURE))
    data["sources"][0]["sha256"] = "not-a-sha"

    with pytest.raises(ComponentValidationError):
        ComponentSpec.from_dict(data)


def test_source_validation_flags_missing_external_reference() -> None:
    data = component_to_dict(load_component(FIXTURE))
    del data["sources"][0]["uri"]
    spec = ComponentSpec.from_dict(data)

    report = validate_component(spec)

    assert not report.passed
    assert any(f.code == "SOURCE_REFERENCE_MISSING" for f in report.findings)
