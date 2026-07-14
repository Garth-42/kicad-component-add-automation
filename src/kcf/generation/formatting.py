from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def mm(value: Decimal, places: int = 2) -> str:
    quant = Decimal(1).scaleb(-places)
    return format(value.quantize(quant, rounding=ROUND_HALF_UP), "f")
