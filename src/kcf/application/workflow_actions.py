from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from kcf.application.workflow_status import WorkflowJobStore
from kcf.domain.workflow import ApprovalRecord, ApprovalScope, ReviewQuestion, WorkflowEvent, WorkflowJob, WorkflowState


class WorkflowActionError(ValueError):
    pass


def answer_question(store: WorkflowJobStore, job_id: str, question_id: str, answer: str, actor: str) -> WorkflowJob:
    job = _require_job(store, job_id)
    now = _now()
    updated_questions: list[ReviewQuestion] = []
    matched = False
    for question in job.questions:
        if question.question_id != question_id:
            updated_questions.append(question)
            continue
        matched = True
        if question.answered:
            raise WorkflowActionError(f"question {question_id} is already answered")
        updated_questions.append(replace(question, answered=True, answer=answer, answered_by=actor, answered_at=now))
    if not matched:
        raise WorkflowActionError(f"question {question_id} was not found")
    updated = _append_event(
        replace(job, questions=updated_questions, updated_at=now),
        "QUESTION_ANSWERED",
        actor,
        f"Answered review question {question_id}.",
        {"question_id": question_id},
        now,
    )
    store.save_job(updated)
    return updated


def approve_spec(store: WorkflowJobStore, job_id: str, spec_hash: str, actor: str) -> WorkflowJob:
    job = _require_job(store, job_id)
    _require_hash_match("spec", job.spec_hash, spec_hash)
    now = _now()
    updated = _append_approval_event(
        replace(job, state=WorkflowState.SPEC_APPROVED, spec_hash=spec_hash, updated_at=now),
        scope=ApprovalScope.SPECIFICATION,
        subject_hash=spec_hash,
        subject_hash_type="spec_hash",
        event_type="SPEC_APPROVED",
        actor=actor,
        message="Approved canonical specification hash.",
        timestamp=now,
    )
    store.save_job(updated)
    return updated


def approve_release(store: WorkflowJobStore, job_id: str, candidate_hash: str, actor: str) -> WorkflowJob:
    job = _require_job(store, job_id)
    _require_hash_match("candidate", job.candidate_hash, candidate_hash)
    now = _now()
    updated = _append_approval_event(
        replace(job, state=WorkflowState.RELEASED, candidate_hash=candidate_hash, updated_at=now),
        scope=ApprovalScope.RELEASE_CANDIDATE,
        subject_hash=candidate_hash,
        subject_hash_type="candidate_hash",
        event_type="RELEASE_APPROVED",
        actor=actor,
        message="Approved release candidate hash.",
        timestamp=now,
    )
    store.save_job(updated)
    return updated


def reject_candidate(store: WorkflowJobStore, job_id: str, candidate_hash: str, actor: str, reason: str) -> WorkflowJob:
    job = _require_job(store, job_id)
    _require_hash_match("candidate", job.candidate_hash, candidate_hash)
    now = _now()
    updated = _append_event(
        replace(job, state=WorkflowState.CHANGES_REQUESTED, candidate_hash=candidate_hash, updated_at=now),
        "RELEASE_REJECTED",
        actor,
        "Rejected release candidate hash.",
        {"candidate_hash": candidate_hash, "reason": reason},
        now,
    )
    store.save_job(updated)
    return updated


def request_changes(store: WorkflowJobStore, job_id: str, actor: str, reason: str) -> WorkflowJob:
    job = _require_job(store, job_id)
    now = _now()
    updated = _append_event(
        replace(job, state=WorkflowState.CHANGES_REQUESTED, updated_at=now),
        "CHANGES_REQUESTED",
        actor,
        "Recorded requested workflow changes.",
        {"reason": reason},
        now,
    )
    store.save_job(updated)
    return updated


def _require_job(store: WorkflowJobStore, job_id: str) -> WorkflowJob:
    job = store.get_job(job_id)
    if job is None:
        raise WorkflowActionError(f"job {job_id} was not found")
    return job


def _require_hash_match(kind: str, recorded_hash: str | None, provided_hash: str) -> None:
    if not provided_hash:
        raise WorkflowActionError(f"{kind} hash is required")
    if recorded_hash is not None and recorded_hash != provided_hash:
        raise WorkflowActionError(f"{kind} hash mismatch: expected {recorded_hash}, got {provided_hash}")


def _append_approval_event(
    job: WorkflowJob,
    *,
    scope: ApprovalScope,
    subject_hash: str,
    subject_hash_type: str,
    event_type: str,
    actor: str,
    message: str,
    timestamp: str,
) -> WorkflowJob:
    approval_id = str(uuid4())
    event_id = str(uuid4())
    approval = ApprovalRecord(
        approval_id=approval_id,
        job_id=job.job_id,
        scope=scope,
        actor=actor,
        timestamp=timestamp,
        subject_hash=subject_hash,
        subject_hash_type=subject_hash_type,
        event_id=event_id,
    )
    event = WorkflowEvent(
        event_id=event_id,
        job_id=job.job_id,
        event_type=event_type,
        timestamp=timestamp,
        actor=actor,
        message=message,
        data={subject_hash_type: subject_hash, "approval_id": approval_id, "approval_scope": scope.value},
    )
    return replace(job, approvals=[*job.approvals, approval], events=[*job.events, event])


def _append_event(
    job: WorkflowJob,
    event_type: str,
    actor: str,
    message: str,
    data: dict[str, str],
    timestamp: str,
) -> WorkflowJob:
    event = WorkflowEvent(
        event_id=str(uuid4()),
        job_id=job.job_id,
        event_type=event_type,
        timestamp=timestamp,
        actor=actor,
        message=message,
        data=data,
    )
    return replace(job, events=[*job.events, event])


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
