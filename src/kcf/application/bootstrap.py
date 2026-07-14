from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_EXAMPLE = """# KiCad Component Factory private library configuration template
library:
  name: "Company_Electrical"
  visibility: "private"

secrets:
  # Store real credentials in environment variables or a secret manager, never in Git.
  slack_bot_token_env: "KCF_SLACK_BOT_TOKEN"
  slack_signing_secret_env: "KCF_SLACK_SIGNING_SECRET"
  model_api_key_env: "KCF_MODEL_API_KEY"

collaboration:
  slack:
    enabled: false
    workspace_id: "T00000000"
    review_channel: "#component-review"
    approver_map: {}
"""

SLACK_EXAMPLE = """# Copy values into .kcf/config.local.yaml or your secret manager.
# Do not commit real Slack credentials.
slack:
  enabled: true
  workspace_id: "T00000000"
  review_channel: "#component-review"
  signing_secret_env: "KCF_SLACK_SIGNING_SECRET"
  bot_token_env: "KCF_SLACK_BOT_TOKEN"
  approver_map:
    U00000000:
      actor: "engineer@example.com"
      roles:
        - "electrical_reviewer"
"""

CONFIG_LOCAL = """# Local private overrides. This file is intentionally gitignored.
# Uncomment and customize when enabling integrations.
# collaboration:
#   slack:
#     enabled: true
#     workspace_id: "T00000000"
#     review_channel: "#component-review"
"""

ENV_EXAMPLE = """# Runtime secrets for local development.
# Copy to .env or export in your shell. Never commit real values.
KCF_SLACK_BOT_TOKEN=
KCF_SLACK_SIGNING_SECRET=
KCF_MODEL_API_KEY=
"""

GITIGNORE = """# KCF local-only configuration and secrets
.kcf/config.local.yaml
.kcf/secrets/
.kcf/runtime/
.env
.env.*
!.env.example
*.sqlite
*.sqlite3

# Generated local build output
build/
"""

README = """# Private KiCad Component Library

This repository was initialized by `kcf init-library --private`.

## Secret-safe setup

1. Review `.kcf/config.example.yaml` and `.kcf/slack.example.yaml`.
2. Put local private overrides in `.kcf/config.local.yaml`.
3. Export real secrets in your shell, load them from `.env`, or use a secret manager.
4. Run `kcf doctor --repo-root .` before committing configuration changes.

Real Slack/model-provider credentials must never be committed to Git.
"""

POLICY_LIBRARY_STYLE = """# Library style policy placeholder
schema_version: "1.0"
"""

POLICY_RISK_RULES = """# Risk rules policy placeholder
schema_version: "1.0"
"""

POLICY_SOURCE_RETENTION = """# Source and review retention policy placeholder
schema_version: "1.0"
default_source_storage_mode: "external"
default_review_response_storage_mode: "summary_only"
"""

SECRET_PATTERNS = [
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "slack_bot_token:",
    "slack_signing_secret:",
    "signing_secret:",
    "model_api_key:",
    "api_key:",
]


@dataclass(frozen=True)
class DoctorFinding:
    severity: str
    message: str


@dataclass(frozen=True)
class InitResult:
    root: Path
    created: list[Path]
    skipped: list[Path]


def _write_if_missing(root: Path, relative: str, content: str) -> tuple[Path, bool]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path, False
    path.write_text(content, encoding="utf-8")
    return path, True


def init_private_library(root: Path) -> InitResult:
    root = root.resolve()
    created: list[Path] = []
    skipped: list[Path] = []
    root.mkdir(parents=True, exist_ok=True)

    directories = [
        ".kcf/policies",
        ".kcf/secrets",
        ".kcf/runtime",
        "components",
        "libraries/Company_Electrical.pretty",
        "libraries/Company_Electrical.3dshapes",
        "schemas",
        "test-projects",
        "tools",
    ]
    for relative in directories:
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)

    files = {
        ".kcf/config.yaml": CONFIG_EXAMPLE,
        ".kcf/config.example.yaml": CONFIG_EXAMPLE,
        ".kcf/config.local.yaml": CONFIG_LOCAL,
        ".kcf/slack.example.yaml": SLACK_EXAMPLE,
        ".kcf/schema-version": "1.0\n",
        ".kcf/policies/library-style.yaml": POLICY_LIBRARY_STYLE,
        ".kcf/policies/risk-rules.yaml": POLICY_RISK_RULES,
        ".kcf/policies/source-retention.yaml": POLICY_SOURCE_RETENTION,
        ".env.example": ENV_EXAMPLE,
        ".gitignore": GITIGNORE,
        "README.md": README,
    }
    for relative, content in files.items():
        path, did_create = _write_if_missing(root, relative, content)
        if did_create:
            created.append(path)
        else:
            skipped.append(path)

    return InitResult(root, created, skipped)


def doctor_findings(repo_root: Path) -> list[DoctorFinding]:
    root = repo_root.resolve()
    findings: list[DoctorFinding] = []
    config_path = root / ".kcf" / "config.yaml"
    local_config_path = root / ".kcf" / "config.local.yaml"
    gitignore_path = root / ".gitignore"

    if not (root / ".kcf").exists():
        findings.append(DoctorFinding("warning", f"{root} does not contain a .kcf directory; run kcf init-library --private for a private library repo"))
        return findings

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8").lower()
        for pattern in SECRET_PATTERNS:
            if pattern in text:
                findings.append(DoctorFinding("error", f"possible committed secret pattern '{pattern}' found in {config_path}"))
    else:
        findings.append(DoctorFinding("warning", f"missing committed config template {config_path}"))

    if local_config_path.exists() and gitignore_path.exists():
        gitignore = gitignore_path.read_text(encoding="utf-8")
        if ".kcf/config.local.yaml" not in gitignore:
            findings.append(DoctorFinding("warning", ".kcf/config.local.yaml exists but is not listed in .gitignore"))

    if config_path.exists():
        text = config_path.read_text(encoding="utf-8").lower()
        slack_enabled = "enabled: true" in text and "slack" in text
        if slack_enabled:
            for env_name in ("KCF_SLACK_BOT_TOKEN", "KCF_SLACK_SIGNING_SECRET"):
                if not os.environ.get(env_name):
                    findings.append(DoctorFinding("warning", f"Slack appears enabled but {env_name} is not set"))

    return findings
