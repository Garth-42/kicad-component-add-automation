from pathlib import Path

import pytest

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
