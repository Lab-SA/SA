import threading

from BasicSAClient import BasicSAClient, sendRequest
from TurboClient import TurboClient
from BreaClient import BreaClient
from HeteroSAClient import HeteroSAClient
from CSAClient import CSAClient
from CSAClientV2 import CSAClientV2

def runOneClient(mode, k, dropout = False):
    if mode == 0: # BasicSA
        client = BasicSAClient()
        for _ in range(k):
            client.setUp()
            client.advertiseKeys()
            client.shareKeys()
            client.maskedInputCollection()
            client.unmasking()

    elif mode == 1: # Turbo
        client = TurboClient()
        for _ in range(k):
            group = client.setUp()
            if group != 0:
                client.turbo()
            client.turbo_value()
            client.turbo_final()

    elif mode == 2: # BREA
        client = BreaClient()
        for i in range(k):
            client.setUp()
            client.ShareKeys()
            client.ShareCommitmentsVerifyShares()
            client.ComputeDistance()
            client.unMasking()

    elif mode == 3: # HeteroSA
        client = HeteroSAClient()
        for _ in range(k):
            client.setUp()
            client.advertiseKeys()
            client.shareKeys()
            client.maskedInputCollection()
            client.unmasking()

    elif mode == 4: # BasicCSA
        client = CSAClient(isBasic = True)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode == 5: # FullCSA
        client = CSAClient(isBasic = False)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode == 6: # BasicCSA V2
        client = CSAClientV2(isBasic = True)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

    elif mode == 7: # FullCSA V2
        client = CSAClientV2(isBasic = False)
        for _ in range(k):
            client.setUp()
            if not client.shareRandomMasks():
                continue
            if not dropout:
                client.sendSecureWeight()

if __name__ == "__main__":
    # args
    k = 101       # rounds
    n = 25       # number of users
    mode = 6
    """ mode
    0: BasicSA Client
    1: Turbo Client
    2: BREA Client
    3: HeteroSA Client
    4: BasicCSA Client
    5: FullCSA Client
    6: BasicCSA Client V2
    """

    host = 'localhost'
    port = 6000
    quantization_levels = [20, 30, 60, 80, 100]
    args = {'t': int(n/2), 'perGroup': 2, 'G': 2, 'qLevel': 30, 'quantization_levels': quantization_levels}
    #sendRequest(host, port, mode, {'n': n, 'k': k, 'args': args})

    # thread
    dropout = n #int(n/2)
    for i in range(n):
        if i >= dropout:
            threading.Thread(target=runOneClient, args=(mode, k, True)).start()
        else:
            threading.Thread(target=runOneClient, args=(mode, k, False)).start()
        #thread = threading.Thread(target=runOneClient, args=(mode, k))
        #thread.start()