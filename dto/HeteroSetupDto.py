from typing import NamedTuple

class HeteroSetupDto(NamedTuple):
    n: int
    t: int
    g: int
    p: int
    R: int
    group: int
    index: int
    B: list
    G: int
    quantization_levels: list
    data: dict
    weights: dict
    weights_interval: list

class HeteroKeysRequestDto(NamedTuple):
    group: int
    index: int
    c_pk: int
    s_pk: int

class HeteroMaskedInputRequestDto(NamedTuple):
    group: int
    index: int
    encodedx: list # [group, index, segment, encodecx]
