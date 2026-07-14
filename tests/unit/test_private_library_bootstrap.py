from pathlib import Path

from kcf.application.bootstrap import doctor_findings
from kcf.cli.main import run


def test_init_library_private_creates_secret_safe_layout(tmp_path: Path) -> None:
    library = tmp_path / "library"

    assert run(["init-library", str(library), "--private"]) == 0

    assert (library / ".kcf" / "config.yaml").exists()
    assert (library / ".kcf" / "config.example.yaml").exists()
    assert (library / ".kcf" / "config.local.yaml").exists()
    assert (library / ".kcf" / "slack.example.yaml").exists()
    assert (library / ".env.example").exists()
    assert (library / "components").is_dir()
    assert (library / "libraries" / "Company_Electrical.pretty").is_dir()

    gitignore = (library / ".gitignore").read_text(encoding="utf-8")
    assert ".kcf/config.local.yaml" in gitignore
    assert ".kcf/secrets/" in gitignore
    assert ".env" in gitignore
    assert "*.sqlite" in gitignore

    config = (library / ".kcf" / "config.yaml").read_text(encoding="utf-8")
    assert "KCF_SLACK_BOT_TOKEN" in config
    assert "xoxb-" not in config
    assert doctor_findings(library) == []


def test_init_library_private_is_idempotent(tmp_path: Path) -> None:
    library = tmp_path / "library"
    assert run(["init-library", str(library), "--private"]) == 0
    config = library / ".kcf" / "config.yaml"
    config.write_text("custom: true\n", encoding="utf-8")

    assert run(["init-library", str(library), "--private"]) == 0

    assert config.read_text(encoding="utf-8") == "custom: true\n"


def test_doctor_fails_on_committed_secret_pattern(tmp_path: Path) -> None:
    library = tmp_path / "library"
    assert run(["init-library", str(library), "--private"]) == 0
    (library / ".kcf" / "config.yaml").write_text("slack_bot_token: xoxb-secret\n", encoding="utf-8")

    findings = doctor_findings(library)

    assert any(finding.severity == "error" and "possible committed secret" in finding.message for finding in findings)
    assert run(["doctor", "--repo-root", str(library)]) == 1
