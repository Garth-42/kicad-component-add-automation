from __future__ import annotations

from kcf.domain.component import ComponentSpec


def _pin_orientation(orientation: str) -> str:
    return {"right": "R", "left": "L", "up": "U", "down": "D"}[orientation]


def generate_symbol_library(spec: ComponentSpec) -> str:
    lines = [
        "(kicad_symbol_lib",
        '  (version 20240100)',
        '  (generator "kicad-component-factory")',
        f'  (symbol "{spec.identity.symbol_name}"',
        f'    (property "Reference" "{spec.symbol.reference_prefix}" (at 0 0 0))',
        f'    (property "Value" "{spec.identity.manufacturer_part_number}" (at 0 -2.54 0))',
        f'    (property "Footprint" "{spec.identity.library_name}:{spec.identity.footprint_name}" (at 0 -5.08 0))',
    ]
    y = 0.0
    for pin in spec.symbol.pins:
        lines.append(
            f'    (pin {pin.electrical_type} line (at -7.62 {y:.2f} 0) (length 2.54) '
            f'(name "{pin.name}") (number "{pin.number}") (orientation {_pin_orientation(pin.orientation)}))'
        )
        y -= 2.54
    lines += ["  )", ")", ""]
    return "\n".join(lines)
