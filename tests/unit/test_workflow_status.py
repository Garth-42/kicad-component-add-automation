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
