from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowState(StrEnum):
    DRAFT = "DRAFT"
    SOURCES_ATTACHED = "SOURCES_ATTACHED"
    SPEC_READY = "SPEC_READY"
    SPEC_APPROVED = "SPEC_APPROVED"
    CANDIDATE_GENERATED = "CANDIDATE_GENERATED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    BLOCKED = "BLOCKED"
    RELEASED = "RELEASED"


class ApprovalScope(StrEnum):
    SPECIFICATION = "SPECIFICATION"
    RELEASE_CANDIDATE = "RELEASE_CANDIDATE"


class RequiredActionCode(StrEnum):
    ATTACH_SOURCES = "ATTACH_SOURCES"
    RESOLVE_QUESTIONS = "RESOLVE_QUESTIONS"
    APPROVE_SPEC = "APPROVE_SPEC"
    GENERATE_CANDIDATE = "GENERATE_CANDIDATE"
    APPROVE_RELEASE = "APPROVE_RELEASE"
    NONE = "NONE"


@dataclass(frozen=True)
class WorkflowEvent:
    event_id: str
    job_id: str
    event_type: str
    timestamp: str
    actor: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowEvent:
        return cls(
            event_id=data["event_id"],
            job_id=data["job_id"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            actor=data["actor"],
            message=data["message"],
            data=data.get("data", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "job_id": self.job_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "message": self.message,
            "data": self.data,
        }


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    job_id: str
    scope: ApprovalScope
    actor: str
    timestamp: str
    subject_hash: str
    subject_hash_type: str
    event_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRecord:
        return cls(
            approval_id=data["approval_id"],
            job_id=data["job_id"],
            scope=ApprovalScope(data["scope"]),
            actor=data["actor"],
            timestamp=data["timestamp"],
            subject_hash=data["subject_hash"],
            subject_hash_type=data["subject_hash_type"],
            event_id=data.get("event_id"),
        )

    def to_dict(self) -> dict[str, str]:
        result = {
            "approval_id": self.approval_id,
            "job_id": self.job_id,
            "scope": self.scope.value,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "subject_hash": self.subject_hash,
            "subject_hash_type": self.subject_hash_type,
        }
        if self.event_id is not None:
            result["event_id"] = self.event_id
        return result


@dataclass(frozen=True)
class ReviewQuestion:
    question_id: str
    text: str
    blocking: bool = True
    answered: bool = False
    required_role: str | None = None
    answer: str | None = None
    answered_by: str | None = None
    answered_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewQuestion:
        return cls(
            question_id=data["question_id"],
            text=data["text"],
            blocking=bool(data.get("blocking", True)),
            answered=bool(data.get("answered", False)),
            required_role=data.get("required_role"),
            answer=data.get("answer"),
            answered_by=data.get("answered_by"),
            answered_at=data.get("answered_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "question_id": self.question_id,
            "text": self.text,
            "blocking": self.blocking,
            "answered": self.answered,
        }
        if self.required_role is not None:
            result["required_role"] = self.required_role
        for key in ("answer", "answered_by", "answered_at"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result


@dataclass(frozen=True)
class RequiredAction:
    code: RequiredActionCode
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "message": self.message}


@dataclass(frozen=True)
class WorkflowJob:
    job_id: str
    component_key: str
    state: WorkflowState = WorkflowState.DRAFT
    branch: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    spec_hash: str | None = None
    candidate_hash: str | None = None
    review_bundle_path: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    questions: list[ReviewQuestion] = field(default_factory=list)
    events: list[WorkflowEvent] = field(default_factory=list)
    approvals: list[ApprovalRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowJob:
        return cls(
            job_id=data["job_id"],
            component_key=data["component_key"],
            state=WorkflowState(data.get("state", WorkflowState.DRAFT.value)),
            branch=data.get("branch"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            spec_hash=data.get("spec_hash"),
            candidate_hash=data.get("candidate_hash"),
            review_bundle_path=data.get("review_bundle_path"),
            findings=data.get("findings", []),
            questions=[ReviewQuestion.from_dict(item) for item in data.get("questions", [])],
            events=[WorkflowEvent.from_dict(item) for item in data.get("events", [])],
            approvals=[ApprovalRecord.from_dict(item) for item in data.get("approvals", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "job_id": self.job_id,
            "component_key": self.component_key,
            "state": self.state.value,
            "findings": self.findings,
            "questions": [question.to_dict() for question in self.questions],
            "events": [event.to_dict() for event in self.events],
            "approvals": [approval.to_dict() for approval in self.approvals],
        }
        for key in ("branch", "created_at", "updated_at", "spec_hash", "candidate_hash", "review_bundle_path"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        return result

    @property
    def open_questions(self) -> list[ReviewQuestion]:
        return [question for question in self.questions if not question.answered]

    @property
    def blocking_open_questions(self) -> list[ReviewQuestion]:
        return [question for question in self.open_questions if question.blocking]

    @property
    def effective_state(self) -> WorkflowState:
        if self.blocking_open_questions and self.state != WorkflowState.RELEASED:
            return WorkflowState.BLOCKED
        return self.state

    def required_actions(self) -> list[RequiredAction]:
        if self.blocking_open_questions:
            return [
                RequiredAction(
                    RequiredActionCode.RESOLVE_QUESTIONS,
                    f"Answer {len(self.blocking_open_questions)} blocking review question(s).",
                )
            ]
        if self.state == WorkflowState.DRAFT:
            return [RequiredAction(RequiredActionCode.ATTACH_SOURCES, "Attach source evidence and prepare the canonical specification.")]
        if self.state in {WorkflowState.SOURCES_ATTACHED, WorkflowState.SPEC_READY}:
            return [RequiredAction(RequiredActionCode.APPROVE_SPEC, "Review and approve the canonical specification hash.")]
        if self.state == WorkflowState.SPEC_APPROVED:
            return [RequiredAction(RequiredActionCode.GENERATE_CANDIDATE, "Generate deterministic KiCad candidate artifacts.")]
        if self.state == WorkflowState.CANDIDATE_GENERATED:
            return [RequiredAction(RequiredActionCode.APPROVE_RELEASE, "Review generated artifacts and approve or reject the release candidate.")]
        if self.state == WorkflowState.CHANGES_REQUESTED:
            return [RequiredAction(RequiredActionCode.GENERATE_CANDIDATE, "Address requested changes and regenerate deterministic KiCad candidate artifacts.")]
        return [RequiredAction(RequiredActionCode.NONE, "No action required.")]


@dataclass(frozen=True)
class WorkflowStatus:
    job_id: str
    component_key: str
    state: WorkflowState
    branch: str | None
    open_questions: list[ReviewQuestion]
    required_actions: list[RequiredAction]
    review_bundle_path: str | None = None
    finding_count: int = 0

    @classmethod
    def from_job(cls, job: WorkflowJob) -> WorkflowStatus:
        return cls(
            job_id=job.job_id,
            component_key=job.component_key,
            state=job.effective_state,
            branch=job.branch,
            open_questions=job.open_questions,
            required_actions=job.required_actions(),
            review_bundle_path=job.review_bundle_path,
            finding_count=len(job.findings),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "job_id": self.job_id,
            "component_key": self.component_key,
            "state": self.state.value,
            "open_questions": [question.to_dict() for question in self.open_questions],
            "required_actions": [action.to_dict() for action in self.required_actions],
            "finding_count": self.finding_count,
        }
        if self.branch is not None:
            result["branch"] = self.branch
        if self.review_bundle_path is not None:
            result["review_bundle_path"] = self.review_bundle_path
        return result
