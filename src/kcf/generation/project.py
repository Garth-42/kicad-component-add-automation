from __future__ import annotations

from kcf.domain.component import ComponentSpec


def generate_test_project(spec: ComponentSpec) -> dict[str, str]:
    key = spec.component_key
    return {
        "component-test.kicad_pro": '{"meta":{"version":1},"project":{"name":"' + key + '"}}\n',
        "component-test.kicad_sch": f'(kicad_sch (version 20240100) (generator "kicad-component-factory") (uuid "{key}-schematic"))\n',
        "component-test.kicad_pcb": f'(kicad_pcb (version 20240100) (generator "kicad-component-factory"))\n',
    }
