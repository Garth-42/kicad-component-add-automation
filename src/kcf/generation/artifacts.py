from __future__ import annotations

import json
from pathlib import Path

from kcf.domain.component import ComponentSpec
from kcf.generation.footprint import generate_footprint
from kcf.generation.project import generate_test_project
from kcf.generation.source_manifest import render_source_manifest
from kcf.generation.symbol import generate_symbol_library
from kcf.rendering.svg import render_footprint_layers_svg, render_footprint_svg, render_model_3d_svg, render_symbol_svg
from kcf.validation.core import validate_component


def artifact_map(spec: ComponentSpec) -> dict[str, str]:
    manufacturer = spec.component_key.rsplit("-", 1)[0]
    base = f"components/{manufacturer}/{spec.component_key}"
    report = validate_component(spec).to_dict()
    files = {
        f"libraries/{spec.identity.library_name}.kicad_sym": generate_symbol_library(spec),
        f"libraries/{spec.identity.library_name}.pretty/{spec.identity.footprint_name}.kicad_mod": generate_footprint(spec),
        f"{base}/review/symbol.svg": render_symbol_svg(spec),
        f"{base}/review/footprint.svg": render_footprint_svg(spec),
        f"{base}/review/footprint-layers.svg": render_footprint_layers_svg(spec),
        f"{base}/review/validation-report.json": json.dumps(report, indent=2, sort_keys=True) + "\n",
        f"{base}/sources/source-manifest.json": render_source_manifest(spec),
    }
    if spec.model_3d.path:
        files[f"{base}/review/model-3d.svg"] = render_model_3d_svg(spec)
    for name, content in generate_test_project(spec).items():
        files[f"test-projects/{spec.component_key}/{name}"] = content
    return files


def write_artifacts(spec: ComponentSpec, output_root: Path) -> list[Path]:
    written: list[Path] = []
    for relative, content in artifact_map(spec).items():
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
