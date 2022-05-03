import os, sys, copy
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from BasicSA import getCommonValues
from CommonValue import BreaRound
import learning.federated_main as fl
import Brea as br

class BreaServer():
    users_keys = {}
    n = 4
    t = 1
    R = 0
    perGroup = 2
    usersNow = 0
    segment_yu = {}
    surviving_users = []

    def __init__(self, n, k):
        super().__init__(n, k)
        

    def setUp(self, requests):
        global usersNum, threshold, R, model
        usersNow = len(requests)
        tag = BreaRound.SetUp.name
        port = BreaRound.SetUp.value
        server = MainServer(tag, port)
        server.start()

        commonValues = getCommonValues()
        usersNum = commonValues["n"]

        if model == {}:
            model = fl.setup()
        model_weights_list = fl.weights_to_dic_of_list(model.state_dict())
        user_groups = fl.get_user_dataset(usersNow)

        response =[]
        for i in range(usersNow):
            response_i = copy.deepcopy(commonValues)
            response_i["index"] = i
            response_i["data"] = [int(k) for k in user_groups[i]]
            response_i["weights"] = model_weights_list
            response.append(response_i)
        server.foreachIndex(response)


    def secretSharing():
        global usersNum



    def SelectUsers():
        global usersNum



    def unmasking():
        global usersNum

