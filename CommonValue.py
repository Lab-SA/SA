from enum import Enum

class BasicSARound(Enum):
    SetUp = 1
    AdvertiseKeys = 2
    ShareKeys = 3
    MaskedInputCollection = 4
    Unmasking = 5

class TurboRound(Enum):
    SetUp = 7000
    Turbo = 7010
    TurboValue = 7011
    TurboFinal = 7012
    Final = 7020

class CSARound(Enum):
    SetUp = 1
    ShareMasks = 2
    Aggregation = 3
    RemoveMasks = 4

class BreaRound(Enum):
    SetUp = 1
    ShareKeys = 2
    ComputeDistance = 3
    Unmasking = 4
