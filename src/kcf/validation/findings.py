from __future__ import annotations

from dataclasses import asdict, dataclass


class Severity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    artifact: str
    path: str | None = None
    validator: str = "unknown"
    validator_version: str = "1.0.0"
    waivable: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ValidationReport:
    component_key: str
    findings: list[Finding]

    @property
    def passed(self) -> bool:
        return not any(f.severity == Severity.ERROR for f in self.findings)

    def to_dict(self) -> dict[str, object]:
        return {"component_key": self.component_key, "findings": [f.to_dict() for f in self.findings], "passed": self.passed}
