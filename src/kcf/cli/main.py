from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from kcf.application.bootstrap import doctor_findings, init_private_library
from kcf.application.workflow_actions import WorkflowActionError, answer_question, approve_release, approve_spec, reconcile_stale_approvals, reject_candidate, request_changes
from kcf.application.release_workflow import create_job, generate_candidate
from kcf.application.workflow_status import JsonWorkflowJobStore, format_status_table, workflow_statuses
from kcf.domain.schema import dump_component_schema
from kcf.domain.serialization import load_component
from kcf.generation.artifacts import artifact_map, write_artifacts
from kcf.infrastructure.kicad import KiCadCliAdapter
from kcf.validation.core import validate_component


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kcf", description="KiCad Component Factory")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_p = sub.add_parser("doctor")
    doctor_p.add_argument("--repo-root", type=Path, default=Path("."))
    init_p = sub.add_parser("init-library")
    init_p.add_argument("path", type=Path)
    init_p.add_argument("--private", action="store_true", dest="private", help="Initialize a secret-safe private component library repository")
    schema_p = sub.add_parser("schema")
    schema_p.add_argument("--output", "-o", type=Path)
    val_p = sub.add_parser("validate")
    val_p.add_argument("spec_path", type=Path)
    gen_p = sub.add_parser("generate")
    gen_p.add_argument("spec_path", type=Path)
    gen_p.add_argument("--output-root", type=Path, default=Path("."))
    check_p = sub.add_parser("check")
    check_p.add_argument("spec_path", type=Path)
    check_p.add_argument("--output-root", type=Path, default=Path("."))
    ci_p = sub.add_parser("ci")
    ci_sub = ci_p.add_subparsers(dest="ci_command", required=True)
    ci_component_p = ci_sub.add_parser("component-check")
    ci_component_p.add_argument("spec_path", type=Path)
    ci_component_p.add_argument("--output-root", type=Path, default=Path("."))
    ci_library_p = ci_sub.add_parser("library-check")
    ci_library_p.add_argument("--repo-root", type=Path, default=Path("."))
    ci_secret_p = ci_sub.add_parser("secret-check")
    ci_secret_p.add_argument("--repo-root", type=Path, default=Path("."))
    jobs_p = sub.add_parser("jobs")
    jobs_sub = jobs_p.add_subparsers(dest="jobs_command", required=True)
    create_p = jobs_sub.add_parser("create")
    create_p.add_argument("spec_path", type=Path)
    create_p.add_argument("--repo-root", type=Path, default=Path("."))
    create_p.add_argument("--job-id")
    generate_p = jobs_sub.add_parser("generate-candidate")
    generate_p.add_argument("job_id")
    generate_p.add_argument("spec_path", type=Path)
    generate_p.add_argument("--repo-root", type=Path, default=Path("."))
    generate_p.add_argument("--output-root", type=Path)
    generate_p.add_argument("--actor", default="kcf")
    generate_p.add_argument("--commit", action="store_true")
    status_p = jobs_sub.add_parser("status")
    status_p.add_argument("job_id", nargs="?")
    status_p.add_argument("--repo-root", type=Path, default=Path("."))
    status_p.add_argument("--json", action="store_true", dest="json_output")
    answer_p = jobs_sub.add_parser("answer-question")
    answer_p.add_argument("job_id")
    answer_p.add_argument("question_id")
    answer_p.add_argument("--answer", required=True)
    answer_p.add_argument("--actor", default="local-user")
    answer_p.add_argument("--repo-root", type=Path, default=Path("."))
    approve_spec_p = jobs_sub.add_parser("approve-spec")
    approve_spec_p.add_argument("job_id")
    approve_spec_p.add_argument("--spec-hash", required=True)
    approve_spec_p.add_argument("--actor", default="local-user")
    approve_spec_p.add_argument("--repo-root", type=Path, default=Path("."))
    approve_release_p = jobs_sub.add_parser("approve-release")
    approve_release_p.add_argument("job_id")
    approve_release_p.add_argument("--candidate-hash", required=True)
    approve_release_p.add_argument("--actor", default="local-user")
    approve_release_p.add_argument("--repo-root", type=Path, default=Path("."))
    reject_p = jobs_sub.add_parser("reject-candidate")
    reject_p.add_argument("job_id")
    reject_p.add_argument("--candidate-hash", required=True)
    reject_p.add_argument("--reason", required=True)
    reject_p.add_argument("--actor", default="local-user")
    reject_p.add_argument("--repo-root", type=Path, default=Path("."))
    changes_p = jobs_sub.add_parser("request-changes")
    changes_p.add_argument("job_id")
    changes_p.add_argument("--reason", required=True)
    changes_p.add_argument("--actor", default="local-user")
    changes_p.add_argument("--repo-root", type=Path, default=Path("."))
    reconcile_p = jobs_sub.add_parser("reconcile")
    reconcile_p.add_argument("job_id")
    reconcile_p.add_argument("--actor", default="kcf")
    reconcile_p.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print("KCF doctor")
        print(f"KiCad CLI: {shutil.which('kicad-cli') or 'not found'}")
        findings = doctor_findings(args.repo_root)
        for check in KiCadCliAdapter().doctor_checks():
            print(f"{check.status}: {check.name}: {check.message}")
        for finding in findings:
            print(f"{finding.severity}: {finding.message}")
        return 1 if any(finding.severity == "error" for finding in findings) else 0
    if args.command == "init-library":
        if not args.private:
            parser.error("init-library currently requires --private")
        result = init_private_library(args.path)
        print(f"initialized private library at {result.root}")
        print(f"created {len(result.created)} paths")
        if result.skipped:
            print(f"skipped {len(result.skipped)} existing files")
        return 0
    if args.command == "schema":
        text = dump_component_schema()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    if args.command == "validate":
        spec = load_component(args.spec_path)
        report = validate_component(spec)
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.passed else 1
    if args.command == "generate":
        spec = load_component(args.spec_path)
        for path in write_artifacts(spec, args.output_root):
            print(path)
        return 0
    if args.command == "check":
        spec = load_component(args.spec_path)
        report = validate_component(spec)
        if not report.passed:
            print(json.dumps(report.to_dict(), indent=2))
            return 1
        mismatches = []
        for relative, content in artifact_map(spec).items():
            path = args.output_root / relative
            if not path.exists():
                mismatches.append(f"missing {relative}")
            elif path.read_text(encoding="utf-8") != content:
                mismatches.append(f"drift {relative}")
        if mismatches:
            print("\n".join(mismatches))
            return 1
        print("passed")
        return 0
    if args.command == "ci" and args.ci_command == "component-check":
        rc = run(["validate", str(args.spec_path)])
        if rc != 0:
            return rc
        output_root = args.output_root
        write_artifacts(load_component(args.spec_path), output_root)
        rc = run(["check", str(args.spec_path), "--output-root", str(output_root)])
        for check in KiCadCliAdapter().syntax_checks([path for path in output_root.rglob("*.kicad_*")]):
            print(f"{check.status}: {check.name}: {check.message}")
        return rc
    if args.command == "ci" and args.ci_command == "library-check":
        specs = sorted(args.repo_root.glob("components/*/*/component.yaml"))
        failed = 0
        for spec_path in specs:
            failed += run(["check", str(spec_path), "--output-root", str(args.repo_root)]) != 0
        print(f"checked {len(specs)} component specification(s)")
        return 1 if failed else 0
    if args.command == "ci" and args.ci_command == "secret-check":
        findings = doctor_findings(args.repo_root)
        for finding in findings:
            print(f"{finding.severity}: {finding.message}")
        return 1 if any(finding.severity == "error" for finding in findings) else 0
    if args.command == "jobs" and args.jobs_command == "create":
        job = create_job(JsonWorkflowJobStore(args.repo_root), args.spec_path, args.job_id)
        print(json.dumps(job.to_dict(), indent=2))
        return 0
    if args.command == "jobs" and args.jobs_command == "generate-candidate":
        try:
            job, git_result = generate_candidate(JsonWorkflowJobStore(args.repo_root), args.job_id, args.spec_path, args.output_root or args.repo_root, args.actor, args.commit)
        except Exception as exc:
            print(f"error: {exc}")
            return 1
        payload = job.to_dict()
        if git_result is not None:
            payload["git"] = {"branch": git_result.branch, "commit": git_result.commit, "staged_paths": git_result.staged_paths}
        print(json.dumps(payload, indent=2))
        return 0
    if args.command == "jobs" and args.jobs_command == "status":
        statuses = workflow_statuses(JsonWorkflowJobStore(args.repo_root), args.job_id)
        if args.json_output:
            print(json.dumps([status.to_dict() for status in statuses], indent=2))
        else:
            print(format_status_table(statuses))
        return 1 if args.job_id and not statuses else 0
    if args.command == "jobs":
        store = JsonWorkflowJobStore(args.repo_root)
        try:
            if args.jobs_command == "answer-question":
                job = answer_question(store, args.job_id, args.question_id, args.answer, args.actor)
            elif args.jobs_command == "approve-spec":
                job = approve_spec(store, args.job_id, args.spec_hash, args.actor)
            elif args.jobs_command == "approve-release":
                job = approve_release(store, args.job_id, args.candidate_hash, args.actor)
            elif args.jobs_command == "reject-candidate":
                job = reject_candidate(store, args.job_id, args.candidate_hash, args.actor, args.reason)
            elif args.jobs_command == "request-changes":
                job = request_changes(store, args.job_id, args.actor, args.reason)
            elif args.jobs_command == "reconcile":
                job = reconcile_stale_approvals(store, args.job_id, args.actor)
            else:
                return 2
        except WorkflowActionError as exc:
            print(f"error: {exc}")
            return 1
        print(json.dumps(job.to_dict(), indent=2))
        return 0
    return 2


def main() -> None:
    raise SystemExit(run())

if __name__ == "__main__":
    main()
