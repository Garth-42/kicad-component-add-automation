from __future__ import annotations

from decimal import Decimal

from kcf.domain.component import ComponentSpec
from kcf.generation.formatting import mm


def render_footprint_svg(spec: ComponentSpec) -> str:
    scale = Decimal("10")
    body = spec.footprint.body
    width = (body.width_mm + Decimal("4")) * scale
    height = (body.depth_mm + Decimal("4")) * scale
    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{mm(width,0)}" height="{mm(height,0)}" viewBox="-20 -20 {mm(width,0)} {mm(height,0)}">',
        f'<rect x="0" y="0" width="{mm(body.width_mm * scale)}" height="{mm(body.depth_mm * scale)}" fill="none" stroke="black"/>',
    ]
    for pad in spec.footprint.pads:
        x = pad.x_mm * scale
        y = pad.y_mm * scale
        r = max(pad.size_x_mm, pad.size_y_mm) * scale / Decimal("2")
        items.append(f'<circle cx="{mm(x)}" cy="{mm(y)}" r="{mm(r)}" fill="none" stroke="blue"/>')
        items.append(f'<text x="{mm(x)}" y="{mm(y)}" font-size="8" text-anchor="middle">{pad.number}</text>')
    items.append("</svg>\n")
    return "\n".join(items)


def render_symbol_svg(spec: ComponentSpec) -> str:
    height = max(80, 24 * len(spec.symbol.pins))
    items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="180" height="{height}">', '<rect x="70" y="10" width="70" height="60" fill="none" stroke="black"/>']
    y = 25
    for pin in spec.symbol.pins:
        items.append(f'<line x1="20" y1="{y}" x2="70" y2="{y}" stroke="black"/>')
        items.append(f'<text x="25" y="{y - 3}" font-size="10">{pin.number}</text>')
        items.append(f'<text x="78" y="{y - 3}" font-size="10">{pin.name}</text>')
        y += 18
    items.append("</svg>\n")
    return "\n".join(items)
