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
    cluster_indexes: list # list of index in cluster
    cluster_keys: dict # node's id and public key
    index: int # user's index
    qLevel: int # quantization level
    data: dict # user's data set for learning
    weights: dict # weights of global model
    training_weight: int # user's training weight
