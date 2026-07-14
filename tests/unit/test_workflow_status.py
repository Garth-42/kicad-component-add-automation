import json
from pathlib import Path

from kcf.application.workflow_status import JsonWorkflowJobStore, format_status_table, workflow_statuses
from kcf.cli.main import run
from kcf.domain.workflow import RequiredActionCode, WorkflowJob, WorkflowState, WorkflowStatus


def _write_job(repo_root: Path, data: dict) -> None:
    jobs_dir = repo_root / ".kcf" / "runtime" / "jobs"
    jobs_dir.mkdir(parents=True)
    (jobs_dir / f"{data['job_id']}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_workflow_status_for_draft_job_recommends_source_work() -> None:
    job = WorkflowJob(job_id="job-1", component_key="example-part")

    status = WorkflowStatus.from_job(job)

    assert status.state == WorkflowState.DRAFT
    assert status.required_actions[0].code == RequiredActionCode.ATTACH_SOURCES
    assert "source evidence" in status.required_actions[0].message


def test_blocking_open_question_makes_status_blocked() -> None:
    job = WorkflowJob.from_dict(
        {
            "job_id": "job-2",
            "component_key": "example-part",
            "state": "SPEC_READY",
            "questions": [
                {
                    "question_id": "q-1",
                    "text": "Confirm pin 1 orientation.",
                    "blocking": True,
                    "answered": False,
                }
            ],
        }
    )

    status = WorkflowStatus.from_job(job)

    assert status.state == WorkflowState.BLOCKED
    assert status.required_actions[0].code == RequiredActionCode.RESOLVE_QUESTIONS
    assert len(status.open_questions) == 1


def test_json_store_reads_jobs_and_formats_table(tmp_path: Path) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-3",
            "component_key": "example-part",
            "state": "SPEC_APPROVED",
            "branch": "parts/example-part",
            "updated_at": "2026-07-14T00:00:00Z",
        },
    )

    statuses = workflow_statuses(JsonWorkflowJobStore(tmp_path))
    table = format_status_table(statuses)

    assert len(statuses) == 1
    assert statuses[0].required_actions[0].code == RequiredActionCode.GENERATE_CANDIDATE
    assert "job-3" in table
    assert "OPEN QUESTIONS" in table
    assert "FINDINGS" in table
    assert "parts/example-part" in table
    assert "GENERATE" in table or "Generate" in table


def test_cli_jobs_status_reports_empty_repo(tmp_path: Path, capsys) -> None:
    assert run(["jobs", "status", "--repo-root", str(tmp_path)]) == 0

    captured = capsys.readouterr()
    assert "No workflow jobs found." in captured.out


def test_cli_jobs_status_json_for_specific_job(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-4",
            "component_key": "example-part",
            "state": "CANDIDATE_GENERATED",
            "review_bundle_path": "components/example-part/review",
        },
    )

    assert run(["jobs", "status", "job-4", "--repo-root", str(tmp_path), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["job_id"] == "job-4"
    assert payload[0]["state"] == "CANDIDATE_GENERATED"
    assert payload[0]["required_actions"][0]["code"] == "APPROVE_RELEASE"


def test_cli_answer_question_persists_answer_and_event(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-5",
            "component_key": "example-part",
            "state": "SPEC_READY",
            "questions": [{"question_id": "q-1", "text": "Confirm pin 1.", "blocking": True, "answered": False}],
        },
    )

    assert run(["jobs", "answer-question", "job-5", "q-1", "--answer", "Pin 1 is square.", "--actor", "reviewer", "--repo-root", str(tmp_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["questions"][0]["answered"] is True
    assert payload["questions"][0]["answer"] == "Pin 1 is square."
    assert payload["questions"][0]["answered_by"] == "reviewer"
    assert payload["events"][0]["event_type"] == "QUESTION_ANSWERED"


def test_cli_approve_spec_is_hash_bound(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-6",
            "component_key": "example-part",
            "state": "SPEC_READY",
            "spec_hash": "sha256:abc",
        },
    )

    assert run(["jobs", "approve-spec", "job-6", "--spec-hash", "sha256:wrong", "--repo-root", str(tmp_path)]) == 1
    assert "spec hash mismatch" in capsys.readouterr().out

    assert run(["jobs", "approve-spec", "job-6", "--spec-hash", "sha256:abc", "--actor", "reviewer", "--repo-root", str(tmp_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "SPEC_APPROVED"
    assert payload["events"][0]["event_type"] == "SPEC_APPROVED"
    assert payload["events"][0]["data"]["spec_hash"] == "sha256:abc"
    assert payload["events"][0]["data"]["approval_id"] == payload["approvals"][0]["approval_id"]
    assert payload["approvals"][0]["scope"] == "SPECIFICATION"
    assert payload["approvals"][0]["subject_hash"] == "sha256:abc"
    assert payload["approvals"][0]["subject_hash_type"] == "spec_hash"
    assert payload["approvals"][0]["actor"] == "reviewer"


def test_cli_release_decisions_are_hash_bound(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-7",
            "component_key": "example-part",
            "state": "CANDIDATE_GENERATED",
            "candidate_hash": "sha256:def",
        },
    )

    assert run(["jobs", "reject-candidate", "job-7", "--candidate-hash", "sha256:def", "--reason", "Courtyard too tight.", "--repo-root", str(tmp_path)]) == 0
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["state"] == "CHANGES_REQUESTED"
    assert rejected["events"][0]["event_type"] == "RELEASE_REJECTED"
    assert rejected["events"][0]["data"]["reason"] == "Courtyard too tight."

    assert run(["jobs", "approve-release", "job-7", "--candidate-hash", "sha256:wrong", "--repo-root", str(tmp_path)]) == 1
    assert "candidate hash mismatch" in capsys.readouterr().out

    assert run(["jobs", "approve-release", "job-7", "--candidate-hash", "sha256:def", "--actor", "reviewer", "--repo-root", str(tmp_path)]) == 0
    approved = json.loads(capsys.readouterr().out)
    assert approved["state"] == "RELEASED"
    assert approved["events"][-1]["event_type"] == "RELEASE_APPROVED"
    assert approved["events"][-1]["data"]["approval_id"] == approved["approvals"][0]["approval_id"]
    assert approved["approvals"][0]["scope"] == "RELEASE_CANDIDATE"
    assert approved["approvals"][0]["subject_hash"] == "sha256:def"
    assert approved["approvals"][0]["subject_hash_type"] == "candidate_hash"


def test_workflow_job_round_trips_dedicated_approval_records() -> None:
    job = WorkflowJob.from_dict(
        {
            "job_id": "job-8",
            "component_key": "example-part",
            "approvals": [
                {
                    "approval_id": "approval-1",
                    "job_id": "job-8",
                    "scope": "SPECIFICATION",
                    "actor": "reviewer",
                    "timestamp": "2026-07-14T00:00:00Z",
                    "subject_hash": "sha256:abc",
                    "subject_hash_type": "spec_hash",
                    "event_id": "event-1",
                }
            ],
        }
    )

    payload = job.to_dict()

    assert payload["approvals"][0]["approval_id"] == "approval-1"
    assert payload["approvals"][0]["scope"] == "SPECIFICATION"
    assert payload["approvals"][0]["event_id"] == "event-1"


def test_cli_reconcile_invalidates_candidate_when_approved_inputs_change(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-9",
            "component_key": "example-part",
            "state": "CANDIDATE_GENERATED",
            "spec_hash": "sha256:spec",
            "candidate_hash": "sha256:candidate",
            "source_manifest_hash": "sha256:new-sources",
            "generator_version": "0.2.0",
            "style_policy_hash": "sha256:style-a",
            "approved_source_manifest_hash": "sha256:old-sources",
            "approved_generator_version": "0.2.0",
            "approved_style_policy_hash": "sha256:style-a",
            "approvals": [
                {
                    "approval_id": "approval-spec",
                    "job_id": "job-9",
                    "scope": "SPECIFICATION",
                    "actor": "reviewer",
                    "timestamp": "2026-07-14T00:00:00Z",
                    "subject_hash": "sha256:spec",
                    "subject_hash_type": "spec_hash",
                    "event_id": "event-spec",
                },
                {
                    "approval_id": "approval-release",
                    "job_id": "job-9",
                    "scope": "RELEASE_CANDIDATE",
                    "actor": "reviewer",
                    "timestamp": "2026-07-14T00:01:00Z",
                    "subject_hash": "sha256:candidate",
                    "subject_hash_type": "candidate_hash",
                    "event_id": "event-release",
                },
            ],
        },
    )

    assert run(["jobs", "reconcile", "job-9", "--actor", "bot", "--repo-root", str(tmp_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "CHANGES_REQUESTED"
    assert "candidate_hash" not in payload
    assert payload["invalidation_reasons"] == ["source_manifest_hash changed from sha256:old-sources to sha256:new-sources"]
    assert payload["events"][-1]["event_type"] == "WORKFLOW_INVALIDATED"
    assert payload["events"][-1]["actor"] == "bot"
    assert [approval["scope"] for approval in payload["approvals"]] == ["SPECIFICATION"]


def test_cli_approve_release_blocks_stale_approved_inputs(tmp_path: Path, capsys) -> None:
    _write_job(
        tmp_path,
        {
            "job_id": "job-10",
            "component_key": "example-part",
            "state": "CANDIDATE_GENERATED",
            "candidate_hash": "sha256:candidate",
            "generator_version": "0.3.0",
            "approved_generator_version": "0.2.0",
        },
    )

    assert run(["jobs", "approve-release", "job-10", "--candidate-hash", "sha256:candidate", "--repo-root", str(tmp_path)]) == 1

    assert "release approval requires spec re-approval" in capsys.readouterr().out
