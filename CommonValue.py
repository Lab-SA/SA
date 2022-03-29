from enum import Enum

class BasicSARound(Enum):
    SetUp = 7000
    AdvertiseKeys = 7010
    ShareKeys = 7020
    MaskedInputCollection = 7030
    Unmasking = 7040

class TurboRound(Enum):
    SetUp = 7000
    Turbo = 7010
    TurboValue = 7011
    TurboFinal = 7012
    Final = 7020

class BreaRound(Enum):
    SetUp = 7000
    SecretSharing = 7010
    SelectUsers = 7020
    Unmasking = 7030
