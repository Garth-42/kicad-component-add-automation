from __future__ import annotations

import json
from pathlib import Path

from kcf.domain.workflow import WorkflowJob, WorkflowStatus


class WorkflowJobStore:
    def list_jobs(self) -> list[WorkflowJob]:
        raise NotImplementedError

    def get_job(self, job_id: str) -> WorkflowJob | None:
        raise NotImplementedError

    def save_job(self, job: WorkflowJob) -> None:
        raise NotImplementedError


class JsonWorkflowJobStore(WorkflowJobStore):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.jobs_dir = self.repo_root / ".kcf" / "runtime" / "jobs"

    def list_jobs(self) -> list[WorkflowJob]:
        if not self.jobs_dir.exists():
            return []
        jobs = [self._load(path) for path in sorted(self.jobs_dir.glob("*.json"))]
        return sorted(jobs, key=lambda job: (job.updated_at or job.created_at or "", job.job_id))

    def get_job(self, job_id: str) -> WorkflowJob | None:
        path = self.jobs_dir / f"{job_id}.json"
        if not path.exists():
            return None
        return self._load(path)

    def save_job(self, job: WorkflowJob) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        path = self.jobs_dir / f"{job.job_id}.json"
        path.write_text(json.dumps(job.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _load(self, path: Path) -> WorkflowJob:
        return WorkflowJob.from_dict(json.loads(path.read_text(encoding="utf-8")))


def workflow_statuses(store: WorkflowJobStore, job_id: str | None = None) -> list[WorkflowStatus]:
    if job_id is not None:
        job = store.get_job(job_id)
        return [] if job is None else [WorkflowStatus.from_job(job)]
    return [WorkflowStatus.from_job(job) for job in store.list_jobs()]


def format_status_table(statuses: list[WorkflowStatus]) -> str:
    if not statuses:
        return "No workflow jobs found."

    lines = ["JOB ID  COMPONENT  STATE  OPEN QUESTIONS  FINDINGS  BRANCH  REVIEW BUNDLE  NEXT ACTION"]
    for status in statuses:
        action = status.required_actions[0].message if status.required_actions else "No action required."
        branch = status.branch or "-"
        review_bundle = status.review_bundle_path or "-"
        lines.append(
            f"{status.job_id}  {status.component_key}  {status.state.value}  "
            f"{len(status.open_questions)}  {status.finding_count}  {branch}  {review_bundle}  {action}"
        )
    return "\n".join(lines)
