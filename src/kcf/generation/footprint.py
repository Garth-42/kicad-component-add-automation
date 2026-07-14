from __future__ import annotations

from decimal import Decimal

from kcf.domain.component import ComponentSpec
from kcf.generation.formatting import mm


def generate_footprint(spec: ComponentSpec) -> str:
    fp = spec.identity.footprint_name
    body = spec.footprint.body
    cx = body.width_mm / Decimal("2")
    clearance = spec.footprint.courtyard.clearance_mm
    x0 = -clearance
    y0 = -clearance
    x1 = body.width_mm + clearance
    y1 = body.depth_mm + clearance
    lines = [
        f'(footprint "{fp}"',
        '  (version 20240100)',
        '  (generator "kicad-component-factory")',
        '  (layer "F.Cu")',
        f'  (descr "{spec.identity.description}")',
        f'  (fp_text reference "REF**" (at {mm(cx)} {mm(-Decimal("2.00"))} 0) (layer "F.SilkS"))',
        f'  (fp_text value "{fp}" (at {mm(cx)} {mm(body.depth_mm + Decimal("2.00"))} 0) (layer "F.Fab"))',
        f'  (fp_rect (start 0 0) (end {mm(body.width_mm)} {mm(body.depth_mm)}) (stroke (width 0.10) (type solid)) (fill none) (layer "F.Fab"))',
        f'  (fp_rect (start {mm(x0)} {mm(y0)}) (end {mm(x1)} {mm(y1)}) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
    ]
    for pad in spec.footprint.pads:
        drill = f' (drill {mm(pad.drill_mm)})' if pad.drill_mm is not None else ""
        pad_type = "thru_hole" if spec.footprint.technology == "through_hole" else "smd"
        layers = '"*.Cu" "*.Mask"' if pad_type == "thru_hole" else '"F.Cu" "F.Paste" "F.Mask"'
        lines.append(
            f'  (pad "{pad.number}" {pad_type} {pad.shape} (at {mm(pad.x_mm)} {mm(pad.y_mm)}) '
            f'(size {mm(pad.size_x_mm)} {mm(pad.size_y_mm)}){drill} (layers {layers}))'
        )
    lines += [")", ""]
    return "\n".join(lines)
