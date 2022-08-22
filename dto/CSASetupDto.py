from typing import NamedTuple

class CSASetupDto(NamedTuple):
    n: int
    g: int
    p: int
    R: int
    encrypted_ri: int
    Ri: int
    cluster: int    # cluster index
    clusterN: int   # number of nodes in cluster
    cluster_keys: dict
    index: int
    data: dict
    weights: dict
