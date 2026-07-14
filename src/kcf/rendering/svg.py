from __future__ import annotations

from decimal import Decimal
from html import escape

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


def render_footprint_layers_svg(spec: ComponentSpec) -> str:
    scale = Decimal("10")
    body = spec.footprint.body
    clearance = spec.footprint.courtyard.clearance_mm
    width = (body.width_mm + (clearance * 2) + Decimal("4")) * scale
    height = (body.depth_mm + (clearance * 2) + Decimal("4")) * scale
    x0 = -clearance * scale
    y0 = -clearance * scale
    x1 = (body.width_mm + clearance) * scale
    y1 = (body.depth_mm + clearance) * scale
    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{mm(width,0)}" height="{mm(height,0)}" viewBox="-30 -30 {mm(width,0)} {mm(height,0)}">',
        "<style>",
        ".fab { fill: none; stroke: #222; stroke-width: 1.2; }",
        ".courtyard { fill: none; stroke: #b000b0; stroke-width: 0.8; stroke-dasharray: 4 3; }",
        ".copper { fill: rgba(190, 120, 30, 0.35); stroke: #be781e; stroke-width: 1.2; }",
        ".mask { fill: none; stroke: #008000; stroke-width: 1; stroke-dasharray: 2 2; }",
        ".paste { fill: none; stroke: #666; stroke-width: 1; stroke-dasharray: 1 3; }",
        ".drill { fill: white; stroke: #333; stroke-width: 1; }",
        "text { font-family: sans-serif; font-size: 8px; }",
        "</style>",
        f'<rect class="fab" x="0" y="0" width="{mm(body.width_mm * scale)}" height="{mm(body.depth_mm * scale)}"/>',
        f'<rect class="courtyard" x="{mm(x0)}" y="{mm(y0)}" width="{mm(x1 - x0)}" height="{mm(y1 - y0)}"/>',
    ]
    for pad in spec.footprint.pads:
        x = pad.x_mm * scale
        y = pad.y_mm * scale
        width_px = pad.size_x_mm * scale
        height_px = pad.size_y_mm * scale
        rx = width_px / Decimal("2")
        ry = height_px / Decimal("2")
        classes = "copper mask" if spec.footprint.technology == "through_hole" else "copper mask paste"
        if pad.shape == "rect":
            items.append(f'<rect class="{classes}" x="{mm(x - rx)}" y="{mm(y - ry)}" width="{mm(width_px)}" height="{mm(height_px)}"/>')
        else:
            items.append(f'<ellipse class="{classes}" cx="{mm(x)}" cy="{mm(y)}" rx="{mm(rx)}" ry="{mm(ry)}"/>')
        if pad.drill_mm is not None:
            items.append(f'<circle class="drill" cx="{mm(x)}" cy="{mm(y)}" r="{mm(pad.drill_mm * scale / Decimal("2"))}"/>')
        items.append(f'<text x="{mm(x)}" y="{mm(y - ry - Decimal("4"))}" text-anchor="middle">Pad {pad.number}</text>')
    legend_y = body.depth_mm * scale + Decimal("18")
    items.append(f'<text x="0" y="{mm(legend_y)}">Layers: F.Fab body, F.CrtYd clearance, copper/mask/paste pads, drills where present</text>')
    items.append("</svg>\n")
    return "\n".join(items)


def render_model_3d_svg(spec: ComponentSpec) -> str:
    model_path = escape(spec.model_3d.path or "No 3D model path provided")
    body = spec.footprint.body
    height = body.height_mm or Decimal("4")
    items = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="170" viewBox="0 0 240 170">',
        "<style>text { font-family: sans-serif; font-size: 10px; } .edge { fill: none; stroke: #333; } .top { fill: #dceeff; } .front { fill: #b9d7f0; } .side { fill: #91bddc; }</style>",
        '<polygon class="top" points="55,45 165,45 205,75 95,75"/>',
        '<polygon class="side" points="165,45 205,75 205,120 165,90"/>',
        '<polygon class="front" points="55,45 95,75 95,120 55,90"/>',
        '<polygon class="edge" points="55,45 165,45 205,75 205,120 95,120 55,90"/>',
        '<line class="edge" x1="95" y1="75" x2="205" y2="75"/>',
        '<line class="edge" x1="95" y1="75" x2="95" y2="120"/>',
        '<line class="edge" x1="165" y1="45" x2="165" y2="90"/>',
        f'<text x="20" y="145">3D model: {model_path}</text>',
        f'<text x="20" y="160">Body: {mm(body.width_mm)} mm × {mm(body.depth_mm)} mm × {mm(height)} mm</text>',
        "</svg>\n",
    ]
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
