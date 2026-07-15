from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from kcf.application.workflow_status import WorkflowJobStore
from kcf.domain.serialization import load_component
from kcf.domain.workflow import WorkflowEvent, WorkflowJob, WorkflowState
from kcf.generation.artifacts import artifact_map, write_artifacts
from kcf.generation.hashing import artifact_bundle_hash, spec_hash
from kcf.generation.release_manifest import GENERATOR_VERSION
from kcf.generation.source_manifest import source_manifest
from kcf.infrastructure.git.adapter import GitAdapter, GitAdapterError, GitResult
from kcf.validation.core import validate_component


def create_job(store: WorkflowJobStore, spec_path: Path, job_id: str | None = None, branch: str | None = None) -> WorkflowJob:
    spec = load_component(spec_path)
    report = validate_component(spec)
    now = _now()
    source_hash = source_manifest(spec)["manifest_hash"]
    state = WorkflowState.SPEC_READY if report.passed else WorkflowState.BLOCKED
    job = WorkflowJob(
        job_id=job_id or f"job-{uuid4()}",
        component_key=spec.component_key,
        state=state,
        branch=branch or f"parts/{spec.component_key}",
        created_at=now,
        updated_at=now,
        spec_hash=spec_hash(spec),
        source_manifest_hash=source_hash,
        generator_version=GENERATOR_VERSION,
        style_policy_hash=spec.policies.get("style_policy_hash", "sha256:unconfigured"),
        findings=[finding.to_dict() for finding in report.findings],
        events=[WorkflowEvent(str(uuid4()), job_id or "pending", "JOB_CREATED", now, "kcf", "Created component workflow job.", {"spec_path": str(spec_path)} )],
    )
    # Fix generated event job id after job id default is known.
    job = replace(job, events=[replace(event, job_id=job.job_id) for event in job.events])
    store.save_job(job)
    return job


def generate_candidate(store: WorkflowJobStore, job_id: str, spec_path: Path, output_root: Path, actor: str = "kcf", commit: bool = False) -> tuple[WorkflowJob, GitResult | None]:
    job = store.get_job(job_id)
    if job is None:
        raise ValueError(f"job {job_id} was not found")
    spec = load_component(spec_path)
    report = validate_component(spec)
    if not report.passed:
        raise ValueError("cannot generate release candidate for invalid spec")
    written = write_artifacts(spec, output_root)
    artifacts = artifact_map(spec)
    candidate_hash = artifact_bundle_hash({path: content for path, content in artifacts.items() if not path.endswith("release.json")})
    now = _now()
    updated = replace(
        job,
        state=WorkflowState.CANDIDATE_GENERATED,
        spec_hash=spec_hash(spec),
        candidate_hash=candidate_hash,
        source_manifest_hash=source_manifest(spec)["manifest_hash"],
        generator_version=GENERATOR_VERSION,
        style_policy_hash=spec.policies.get("style_policy_hash", "sha256:unconfigured"),
        review_bundle_path=f"components/{spec.component_key.rsplit('-', 1)[0]}/{spec.component_key}/review",
        findings=[finding.to_dict() for finding in report.findings],
        updated_at=now,
        events=[*job.events, WorkflowEvent(str(uuid4()), job.job_id, "CANDIDATE_GENERATED", now, actor, "Generated deterministic KiCad release candidate.", {"candidate_hash": candidate_hash})],
    )
    git_result = None
    if commit:
        adapter = GitAdapter(output_root)
        adapter.init_if_needed()
        branch = updated.branch or f"parts/{spec.component_key}"
        adapter.checkout_branch(branch)
        staged_paths = adapter.stage(written)
        adapter.ensure_no_unstaged_changes()
        try:
            commit_hash = adapter.commit(f"Add {spec.component_key} release candidate")
        except GitAdapterError:
            raise
        git_result = GitResult(branch=branch, commit=commit_hash, staged_paths=staged_paths)
    store.save_job(updated)
    return updated, git_result


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
