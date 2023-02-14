import os, sys, json, random, socket

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import CSA
from CommonValue import CSARound
from BasicSA import stochasticQuantization
from common import sendRequestAndReceiveV2, sendRequestV2
import learning.federated_main as fl
import learning.models_helper as mhelper
from dto.CSASetupDto import CSASetupDto
from ast import literal_eval

SIZE = 2048
ENCODING = 'utf-8'


class CSAClient:  # no training weights
    HOST = 'localhost'
    PORT = 8000
    verifyRound = 'verify'
    isBasic = True  # true if BCSA, else FCSA

    n = g = p = R = 0   # number of users and secure parameters
    quantizationLevel = 30
    cluster = clusterN = 0  # cluster index
    index = 0   # my index
    ri = 0      # random integer that the FL server assigns to Ci
    PS = 0      # processing score
    GPS_i = 0   # GPS information of gird
    GPS_j = 0   # GPS information of grid

    my_sk = my_pk = 0   # my secret key and public key
    others_keys = {}    # other users' public key dic
    weight = {}         # model weights
    model = {}

    isFirst = True      # setup model at first

    def __init__(self, isBasic):
        # init client socket
        self.isBasic = isBasic  # isBasic = Ture: BCSA / False: FCSA
        self.mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mysocket.connect((self.HOST, self.PORT))
        self.mysocket.settimeout(10)
        self.isFirst = True  # for setup step (run once)

    def setUp(self):
        tag = CSARound.SetUp.name
        print("Start New Round")

        global_weights = {}

        if self.isFirst:
            self.isFirst = False

            self.my_sk, self.my_pk = CSA.generateECCKey()  # generate ECC key
            self.PS = random.randrange(0, 3)  # set PS level
            self.GPS_i = random.randrange(1, 6)  # set GPS info
            self.GPS_j = random.randrange(1, 8)

            # request with my public key (pk)
            # response: CSASetupDto
            response = sendRequestAndReceiveV2(self.mysocket, tag,
                                               {'pk': self.my_pk.hex(), 'PS': self.PS, 'GPS_i': self.GPS_i,
                                                'GPS_j': self.GPS_j}, self.PS)
            setupDto = json.loads(json.dumps(response), object_hook=lambda d: CSASetupDto(**d))

            self.n = setupDto.n
            self.g = setupDto.g
            self.p = setupDto.p
            self.R = setupDto.R
            self.cluster = setupDto.cluster
            self.clusterN = setupDto.clusterN  # deprecated
            self.cluster_indexes = setupDto.cluster_indexes
            self.index = setupDto.index  # my index
            self.quantizationLevel = setupDto.qLevel
            self.others_keys = {int(key): value for key, value in literal_eval(setupDto.cluster_keys).items()}
            self.others_keys.pop(self.index)
            # self.PS = 3

            self.cluster_indexes.remove(self.index)  # remove my index for future processing

            # decrypt ri and verity Ri = (g ** ri) mod p
            self.ri = int(bytes.decode(CSA.decrypt(self.my_sk, bytes.fromhex(setupDto.encrypted_ri)), 'ascii'))
            self.Ri = int(setupDto.Ri)
            if self.Ri != (self.g ** self.ri) % self.p:  # verify ri and Ri
                print("Invalid Ri and ri.")

            self.data = setupDto.data  # data set for learning
            global_weights = mhelper.dic_of_list_to_weights(literal_eval(setupDto.weights))

            self.model = fl.setup()  # setup initial model at first

        else:  # just get weights of global model
            response = sendRequestAndReceiveV2(self.mysocket, tag, {}, self.PS)
            global_weights = mhelper.dic_of_list_to_weights(literal_eval(response['weights']))

        self.model.load_state_dict(global_weights)  # set to weights of global model
        local_model, local_weight, local_loss = fl.local_update(self.model, self.data, 0)  # update local model
        self.weights_info, self.weight = mhelper.flatten_tensor(local_weight)  # flatten tensor to 1d list
        # no training weight!
        self.weight = stochasticQuantization(self.weight, self.quantizationLevel, self.p)  # do quantization

    def shareRandomMasks(self):
        # generate and share random masks with other users
        tag = CSARound.ShareMasks.name

        while True:  # repeat until all member share valid masks
            # generate random masks
            self.my_mask, encrypted_mask, public_mask = CSA.generateMasks(self.index, self.cluster_indexes, self.ri,
                                                                          self.others_keys, self.g, self.p)
            request = {'cluster': self.cluster, 'index': self.index, 'emask': encrypted_mask, 'pmask': public_mask}
            response = sendRequestAndReceiveV2(self.mysocket, tag, request, self.PS)
            if response.get('process') is not None:  # this cluster is end
                return False

            prev_survived = len(self.cluster_indexes) + 1  # include my index
            if len(response['survived']) != prev_survived:  # drop out in shareRandomMasks stage!
                self.cluster_indexes = response['survived']
                self.cluster_indexes.remove(self.index)
                continue

            # get encrypted masks and public masks
            emask = {int(key): value for key, value in response['emask'].items()}
            pmask = {int(key): value for key, value in response['pmask'].items()}
            # print(self.ri, self.Ri, self.index)

            # verify others masks
            self.nowN = len(pmask)
            self.others_mask = CSA.verifyMasks(self.index, self.ri, emask, pmask, self.my_sk, self.g, self.p)
            if self.others_mask != {}:  # successfully verified
                request = {'cluster': self.cluster, 'index': self.index}
                sendRequestV2(self.mysocket, self.verifyRound, request, self.PS)
                break
        return True  # successfully verified

    def sendSecureWeight(self):  # send secure weight S
        tag = CSARound.Aggregation.name

        if self.isBasic:  # BCSA
            self.a = 0
        else:  # FCSA: need extra value: alpha
            self.a = random.randrange(1, self.p)

        # generate secure weight S with ri, others mask, a
        S = CSA.generateSecureWeight(self.weight, self.ri, self.others_mask, self.p, self.a)

        # send S
        request = {'cluster': self.cluster, 'index': self.index, 'S': S}
        response = sendRequestAndReceiveV2(self.mysocket, tag, request, self.PS)

        # if dropout occurs or this is FCSA, do recovery step
        self.survived = response['survived']
        if not self.isBasic or len(self.survived) != self.nowN:
            self.sendMasksOfDropout()

    def sendMasksOfDropout(self):  # send the masks of drop-out users
        tag = CSARound.RemoveMasks.name

        request = {'cluster': self.cluster, 'index': self.index}
        if not self.isBasic:  # FCSA
            request['a'] = self.a
        while True:  # repeat until all drop out users are handled
            # generate and send RS value
            RS = CSA.computeReconstructionValue(self.survived, self.my_mask, self.others_mask, self.cluster_indexes)
            request['RS'] = RS
            response = sendRequestAndReceiveV2(self.mysocket, tag, request, self.PS)
            self.survived = response['survived']
            if len(self.survived) == 0:  # successfully recovered
                break


if __name__ == "__main__":
    client = CSAClient(isBasic=True)  # BCSA
    # client = CSAClient(isBasic = False) # FCSA
    for _ in range(3):
        client.setUp()
        if not client.shareRandomMasks():
            continue
        client.sendSecureWeight()
