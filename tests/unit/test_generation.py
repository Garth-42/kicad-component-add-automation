from pathlib import Path

from kcf.cli.main import run
from kcf.domain.serialization import load_component
from kcf.generation.artifacts import artifact_map, write_artifacts

FIXTURE = Path("tests/fixtures/terminal_block.yaml")


def test_artifact_map_contains_first_vertical_slice_files() -> None:
    spec = load_component(FIXTURE)
    artifacts = artifact_map(spec)
    assert "libraries/Company_Electrical.kicad_sym" in artifacts
    assert "libraries/Company_Electrical.pretty/TerminalBlock_ABC123-03_1x03_P5.08mm.kicad_mod" in artifacts
    assert f"test-projects/{spec.component_key}/component-test.kicad_pro" in artifacts
    assert any(path.endswith("review/validation-report.json") for path in artifacts)
    assert '(symbol "ABC123-03"' in artifacts["libraries/Company_Electrical.kicad_sym"]
    assert '(pad "1" thru_hole rect' in artifacts["libraries/Company_Electrical.pretty/TerminalBlock_ABC123-03_1x03_P5.08mm.kicad_mod"]


def test_write_artifacts_and_cli_check(tmp_path: Path) -> None:
    spec = load_component(FIXTURE)
    write_artifacts(spec, tmp_path)
    assert run(["check", str(FIXTURE), "--output-root", str(tmp_path)]) == 0


def test_cli_validate_passes() -> None:
    assert run(["validate", str(FIXTURE)]) == 0
