from typing import NamedTuple

class BalancedSetupDto(NamedTuple):
    n: int
    g: int
    p: int
    R: int
    encrypted_ri: int
    cluster: int    # cluster index
    clusterN: int   # number of nodes in cluster
    index: int
    data: dict
    weights: dict
