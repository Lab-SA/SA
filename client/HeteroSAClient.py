import os, sys, json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from CommonValue import BasicSARound
from BasicSAClient import sendRequestAndReceive
from dto.HeteroSetupDto import HeteroSetupDto

SIZE = 2048
ENCODING = 'utf-8'

class HeteroSAClient:
    HOST = 'localhost'
    xu = 0  # temp. local model of this client

    u = 0  # u = user index
    n = t = g = p = R = 0 # common values
    group = 0
    index = 0
    B = []

    perGroup  = 0
    
    my_keys = {}  # c_pk, c_sk, s_pk, s_sk of this client
    others_keys = {}  # other users' public key dic

    def setUp(self):
        tag = BasicSARound.SetUp.name
        PORT = BasicSARound.SetUp.value

        # response: HeteroSetupDto
        response = sendRequestAndReceive(self.HOST, PORT, tag, {})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: HeteroSetupDto(**d)) #
        print(setupDto)
        
        self.n = setupDto.n
        self.t = setupDto.t
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        self.group = self.perGroup = setupDto.group
        self.index = setupDto.index
        self.B = setupDto.B

if __name__ == "__main__":
    client = HeteroSAClient()
    client.setUp()
