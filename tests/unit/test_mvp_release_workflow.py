import json
from pathlib import Path

from kcf.application.workflow_status import JsonWorkflowJobStore
from kcf.cli.main import run
from kcf.domain.serialization import component_to_dict, load_component
from kcf.domain.component import ComponentSpec
from kcf.generation.artifacts import artifact_map, write_artifacts
from kcf.generation.hashing import artifact_bundle_hash, spec_hash
from kcf.validation.core import validate_component

FIXTURE = Path("tests/fixtures/terminal_block.yaml")


def test_release_manifest_records_mvp_release_metadata() -> None:
    spec = load_component(FIXTURE)
    artifacts = artifact_map(spec)
    release_path = f"components/example-manufacturer-abc123/{spec.component_key}/release.json"

    manifest = json.loads(artifacts[release_path])

    assert manifest["spec_hash"] == spec_hash(spec)
    assert manifest["candidate_hash"] == artifact_bundle_hash({path: content for path, content in artifacts.items() if not path.endswith("release.json")})
    assert manifest["generator_version"] == "0.1.0"
    assert manifest["kicad_target_version"] == "10"
    assert manifest["source_manifest_hash"].startswith("sha256:")
    assert manifest["validation_report_hash"].startswith("sha256:")
    assert manifest["review_retention"]["mode"] == "summary_only"


def test_stricter_mvp_validation_blocks_missing_sources_and_bad_smd_drills() -> None:
    data = component_to_dict(load_component(FIXTURE))
    data["sources"] = []
    no_sources = ComponentSpec.from_dict(data)
    report = validate_component(no_sources)
    assert not report.passed
    assert any(f.code == "MISSING_SOURCE_EVIDENCE" for f in report.findings)

    data = component_to_dict(load_component(FIXTURE))
    data["classification"]["family"] = "smd_passive"
    data["footprint"]["technology"] = "smd"
    smd_with_drill = ComponentSpec.from_dict(data)
    report = validate_component(smd_with_drill)
    assert not report.passed
    assert any(f.code == "SMD_PAD_HAS_DRILL" for f in report.findings)


def test_cli_job_create_and_generate_candidate_updates_hashes(tmp_path: Path, capsys) -> None:
    assert run(["jobs", "create", str(FIXTURE), "--repo-root", str(tmp_path), "--job-id", "job-mvp"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["state"] == "SPEC_READY"
    assert created["spec_hash"].startswith("sha256:")

    assert run(["jobs", "generate-candidate", "job-mvp", str(FIXTURE), "--repo-root", str(tmp_path)]) == 0
    generated = json.loads(capsys.readouterr().out)
    assert generated["state"] == "CANDIDATE_GENERATED"
    assert generated["candidate_hash"].startswith("sha256:")
    assert generated["review_bundle_path"].endswith("/review")
    assert (tmp_path / "components" / "example-manufacturer-abc123" / "example-manufacturer-abc123-03" / "release.json").exists()


def test_ci_component_check_regenerates_and_checks_artifacts(tmp_path: Path) -> None:
    assert run(["ci", "component-check", str(FIXTURE), "--output-root", str(tmp_path)]) == 0


def test_git_commit_release_candidate(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "KCF Tests")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "kcf@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "KCF Tests")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "kcf@example.invalid")
    store = JsonWorkflowJobStore(tmp_path)
    assert run(["jobs", "create", str(FIXTURE), "--repo-root", str(tmp_path), "--job-id", "job-git"]) == 0
    capsys.readouterr()

    assert run(["jobs", "generate-candidate", "job-git", str(FIXTURE), "--repo-root", str(tmp_path), "--commit"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["git"]["branch"] == "parts/example-manufacturer-abc123-03"
    assert payload["git"]["commit"]
    assert "components/example-manufacturer-abc123/example-manufacturer-abc123-03/release.json" in payload["git"]["staged_paths"]
    assert store.get_job("job-git").candidate_hash == payload["candidate_hash"]
