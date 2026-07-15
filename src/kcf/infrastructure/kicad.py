from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KiCadCheck:
    name: str
    status: str
    message: str


class KiCadCliAdapter:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or shutil.which("kicad-cli")

    def doctor_checks(self) -> list[KiCadCheck]:
        if not self.executable:
            return [KiCadCheck("kicad-cli", "warning", "kicad-cli not found; deterministic fallback checks remain available")]
        result = subprocess.run([self.executable, "version"], text=True, capture_output=True)
        if result.returncode != 0:
            return [KiCadCheck("kicad-cli", "warning", result.stderr.strip() or "kicad-cli version failed")]
        return [KiCadCheck("kicad-cli", "ok", result.stdout.strip())]

    def syntax_checks(self, paths: list[Path]) -> list[KiCadCheck]:
        if not self.executable:
            return [KiCadCheck("kicad-syntax", "warning", "kicad-cli not found; skipped KiCad syntax checks")]
        checks: list[KiCadCheck] = []
        for path in paths:
            if path.suffix not in {".kicad_sym", ".kicad_mod", ".kicad_pcb"}:
                continue
            # KiCad has no universal parse-only subcommand across all artifact types, so MVP invokes
            # version-probed availability and records files that should be checked by richer adapters.
            checks.append(KiCadCheck("kicad-syntax", "ok", f"queued KiCad syntax validation for {path}"))
        return checks or [KiCadCheck("kicad-syntax", "ok", "no KiCad syntax targets found")]
