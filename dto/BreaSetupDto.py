from typing import NamedTuple

class BreaSetupDto(NamedTuple):
    n: int
    t: int
    g: int
    p: int
    R: int
    q: int
    theta: int
    index: int
    data: dict
    weights: dict