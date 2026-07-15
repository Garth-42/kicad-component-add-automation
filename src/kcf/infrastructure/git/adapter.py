from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitResult:
    branch: str
    commit: str | None
    staged_paths: list[str]


class GitAdapterError(RuntimeError):
    pass


class GitAdapter:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def is_repo(self) -> bool:
        return (self.repo_root / ".git").exists()

    def init_if_needed(self) -> None:
        if not self.is_repo():
            self._git("init")

    def checkout_branch(self, branch: str) -> None:
        self._git("checkout", "-B", branch)

    def stage(self, paths: list[Path]) -> list[str]:
        rels = [path.relative_to(self.repo_root).as_posix() for path in paths]
        if rels:
            self._git("add", "--", *rels)
        return rels

    def ensure_no_unstaged_changes(self) -> None:
        status = self._git("status", "--porcelain", capture=True).stdout.strip().splitlines()
        unstaged = [line for line in status if line and line[1] != " " and not (line[3:].startswith(".kcf/runtime/") or line[3:] == ".kcf/")]
        if unstaged:
            raise GitAdapterError("candidate worktree has unstaged changes: " + "; ".join(unstaged))

    def commit(self, message: str) -> str | None:
        staged = self._git("diff", "--cached", "--name-only", capture=True).stdout.strip()
        if not staged:
            return None
        self._git("commit", "-m", message)
        return self._git("rev-parse", "HEAD", capture=True).stdout.strip()

    def _git(self, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["git", *args], cwd=self.repo_root, text=True, capture_output=True)
        if result.returncode != 0:
            raise GitAdapterError(result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed")
        return result
