from typing import NamedTuple

class BreaSetupDto(NamedTuple):
    n: int
    t: int
    g: int
    p: int
    R: int
    index: int
    data: dict
    weights: dict