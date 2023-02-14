import threading

from BasicSAClient import BasicSAClient
from TurboClient import TurboClient
from BreaClient import BreaClient
from HeteroSAClient import HeteroSAClient
from CSAClient import CSAClient
from CSAClientV2 import CSAClientV2


def runOneClient(mode, k, dropout = False):
    if mode == 0:  # BasicSA
        client = BasicSAClient()
        for _ in range(k):
            client.setUp()
            client.advertiseKeys()
            client.shareKeys()
            client.maskedInputCollection()
            client.unmasking()

    elif mode == 1:  # Turbo
        client = TurboClient()
        for _ in range(k):
            group = client.setUp()
            if group != 0:
                client.turbo()
            client.turbo_value()
            client.turbo_final()

    elif mode == 2:  # BREA
        client = BreaClient()
        for i in range(k):
            client.setUp()
            client.ShareKeys()
            client.ComputeDistance()
            client.unMasking()

    elif mode == 3:  # HeteroSA
        client = HeteroSAClient()
        for _ in range(k):
            client.setUp()
            client.advertiseKeys()
            client.shareKeys()
            client.maskedInputCollection()
            client.unmasking()

    elif mode == 4:  # BCSA
        client = CSAClient(isBasic = True)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode ==  5: # FCSA
        client = CSAClient(isBasic = False)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode == 6:  # BCSA V2
        client = CSAClientV2(isBasic = True)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode == 7:  # FCSA V2
        client = CSAClientV2(isBasic = False)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()


if __name__ == "__main__":
    """ Run clients with thread, depending on the mode
    [mode]
    0: BasicSA Client
    1: Turbo Client
    2: BREA Client
    3: HeteroSA Client
    4: BCSA Client
    5: FCSA Client
    6: BCSA Client V2
    7: FCSA Client V2
    """

    # args
    k = 101     # rounds
    n = 25      # number of users
    mode = 6

    # thread
    survived = n  # = no drop-out
    for i in range(n):
        if i >= survived:  # drop out
            threading.Thread(target=runOneClient, args=(mode, k, True)).start()
        else:
            threading.Thread(target=runOneClient, args=(mode, k, False)).start()
