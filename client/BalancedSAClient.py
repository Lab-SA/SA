import os, sys, json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import BalancedSA
from CommonValue import BalancedSARound
from BasicSAClient import sendRequestAndReceive
import learning.federated_main as fl
import learning.models_helper as mhelper
from dto.BalancedSetupDto import BalancedSetupDto
from ast import literal_eval

SIZE = 2048
ENCODING = 'utf-8'

class BalancedSAClient:
    HOST = 'localhost'
    PORT = 7000

    n = g = p = R = 0 # common values
    cluster = clusterN = 0
    index = 0
    ri = 0

    my_sk = my_pk = 0
    others_keys = {}  # other users' public key dic
    weight = {}
    model = {}

    def setUp(self):
        tag = BalancedSARound.SetUp.name

        self.my_sk, self.my_pk = BalancedSA.generateECCKey()

        # request with my public key (pk)
        # response: BalancedSetupDto
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {'pk': self.my_pk})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: BalancedSetupDto(**d)) #
        
        self.n = setupDto.n
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        # TODO self.ri = 
        self.cluster = setupDto.cluster
        self.clusterN = setupDto.clusterN
        self.index = setupDto.index

        self.data = setupDto.data
        global_weights = mhelper.dic_of_list_to_weights(literal_eval(setupDto.weights))

        self.weight = 1 # temp

        #if self.model == {}:
        #    self.model = fl.setup()
        #fl.update_model(self.model, global_weights)
        #local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0) # epoch 0 (temp)
        #self.weight = local_weight
    
    def shareRandomMasks(self): # send random masks
        tag = BalancedSARound.ShareMasks.name


    def sendSecureWeight(self): # send secure weight S
        tag = BalancedSARound.Aggregation.name


    def sendMasksOfDropout(self): # send the masks of drop-out users
        tag = BalancedSARound.RemoveMasks.name
    

if __name__ == "__main__":
    client = BalancedSAClient()  # test
    client.setUp()
    while not client.shareRandomMasks(): # repeat step 2 until all member share valid mask
        continue
    client.sendSecureWeight()
    client.sendMasksOfDropout()
