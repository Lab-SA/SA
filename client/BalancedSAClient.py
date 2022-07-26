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
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, {'pk': self.my_pk.hex()})
        setupDto = json.loads(json.dumps(response), object_hook=lambda d: BalancedSetupDto(**d))
        
        self.n = setupDto.n
        self.g = setupDto.g
        self.p = setupDto.p
        self.R = setupDto.R
        self.cluster = setupDto.cluster
        self.clusterN = setupDto.clusterN
        self.index = setupDto.index
        self.others_keys = {int(key): value for key, value in literal_eval(setupDto.cluster_keys).items()}
        self.others_keys.pop(self.index)

        # decrypt ri and verity Ri = (g ** ri) mod p
        self.ri = int(bytes.decode(BalancedSA.decrypt(self.my_sk, bytes.fromhex(setupDto.encrypted_ri)), 'ascii'))
        self.Ri = int(setupDto.Ri)
        if self.Ri != (self.g ** self.ri) % self.p:
            print("Invalid Ri and ri.")

        # print(self.cluster, self.clusterN, self.index, self.ri, self.Ri)
        # print(self.others_keys)

        self.data = setupDto.data
        global_weights = mhelper.dic_of_list_to_weights(literal_eval(setupDto.weights))

        self.weight = [1] # temp

        #if self.model == {}:
        #    self.model = fl.setup()
        #fl.update_model(self.model, global_weights)
        #local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0) # epoch 0 (temp)
        #self.weight = local_weight
    
    def shareRandomMasks(self): # send random masks
        tag = BalancedSARound.ShareMasks.name

        self.my_mask, encrypted_mask, public_mask = BalancedSA.generateMasks(self.index, self.clusterN, self.ri, self.others_keys, self.g, self.p, self.R)
        request = {'cluster': self.cluster, 'index': self.index, 'emask': encrypted_mask, 'pmask': public_mask}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

        return True # TODO

    def sendSecureWeight(self): # send secure weight S
        tag = BalancedSARound.Aggregation.name

        request = {'cluster': self.cluster, 'index': self.index}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

    def sendMasksOfDropout(self): # send the masks of drop-out users
        tag = BalancedSARound.RemoveMasks.name

        request = {'cluster': self.cluster, 'index': self.index}
        response = sendRequestAndReceive(self.HOST, self.PORT, tag, request)

if __name__ == "__main__":
    client = BalancedSAClient()
    client.setUp()
    while not client.shareRandomMasks(): # repeat step 2 until all member share valid mask
        continue
    client.sendSecureWeight()
    client.sendMasksOfDropout()
