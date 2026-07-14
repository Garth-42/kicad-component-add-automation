from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from kcf.application.bootstrap import doctor_findings, init_private_library
from kcf.domain.schema import dump_component_schema
from kcf.domain.serialization import load_component
from kcf.generation.artifacts import artifact_map, write_artifacts
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
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print("KCF doctor")
        print(f"KiCad CLI: {shutil.which('kicad-cli') or 'not found'}")
        findings = doctor_findings(args.repo_root)
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
    return 2


def main() -> None:
    raise SystemExit(run())

if __name__ == "__main__":
    main()
