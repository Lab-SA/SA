import os, sys, copy, random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from TurboBaseServer import TurboBaseServer
from BasicSA import getCommonValues
from Turbo import generateRandomVectorSet, reconstruct, computeFinalOutput
from CommonValue import TurboRound
import learning.federated_main as fl
import learning.models_helper as mhelper

model = {}
groupNum = 0
perGroup = 0
usersNum = 0
threshold = 0
R = 0
mask_u_dic = {}
drop_out = {}
alpha = beta = []

# send common values and index, group of each user
def setUp():
    global groupNum, usersNum, threshold, R, perGroup, mask_u_dic, alpha, beta, model

    commonValues = getCommonValues()
    R = commonValues["R"]
    commonValues["n"] = usersNum = 4
    commonValues["t"] = threshold = 2

    tag = TurboRound.SetUp.name
    port = TurboRound.SetUp.value
    server = MainServer(tag, port, usersNum)
    server.start()

    perGroup = 2 # temp
    commonValues["perGroup"] = perGroup

    # generate common alpha/beta
    commonValues["alpha"], commonValues["beta"] = alpha, beta = generateRandomVectorSet(perGroup, commonValues["p"])

    usersNow = len(server.requests) # MUST be multiple of perGroup
    groupNum = int(usersNow / perGroup)
    response = []
    mask_u_dic = {i:{} for i in range(groupNum)}

    if model == {}:
        model = fl.setup()
    model_weights_list = mhelper.weights_to_dic_of_list(model.state_dict())
    user_groups = fl.get_user_dataset(usersNow)

    for i in range(groupNum):
        for j in range(perGroup):
            response_ij = copy.deepcopy(commonValues)
            response_ij["group"] = i
            response_ij["index"] = j
            mask_u = random.randrange(1, R) # 1~R
            mask_u_dic[i][j] = mask_u
            response_ij["mask_u"] = mask_u
            response_ij["data"] = [int(k) for k in user_groups[i*perGroup+j]]
            response_ij["weights"] = model_weights_list
            response.append(response_ij)
    server.foreachIndex(response)

def turbo():
    global groupNum, usersNum, perGroup, drop_out

    tag = TurboRound.Turbo.name
    tag_value = TurboRound.TurboValue.name
    tag_final = TurboRound.TurboFinal.name
    port = TurboRound.Turbo.value

    print(groupNum, usersNum, perGroup, drop_out)
    server = TurboBaseServer(tag, tag_value, tag_final, port, groupNum, usersNum, perGroup)
    server.start()
    drop_out = server.drop_out


def final():
    global mask_u_dic, drop_out, groupNum, alpha, beta, perGroup, model

    tag = TurboRound.Final.name
    port = TurboRound.Final.value

    server = MainServer(tag, port, perGroup)
    server.start()
    final_tildeS = {}
    final_barS = {}

    for request in server.requests:
        requestData = request[1]  # (socket, data)
        index = int(requestData["index"])
        final_tildeS[index] = requestData["final_tildeS"]
        final_barS[index] = requestData["final_barS"]
        drop_out[groupNum-1] = requestData["drop_out"] # last group
    
    # reconstruct
    reconstruct(alpha, beta, final_tildeS, final_barS)
    server.broadcast({})

    # calculate sum of surviving user's mask_u
    for group, item in drop_out.items():
        group = int(group)
        for i in item: # drop out
            i = int(i)
            del mask_u_dic[group][i]
    
    # final value (sum_xu)
    sum_xu = computeFinalOutput(final_tildeS, mask_u_dic)
    restored_xu = mhelper.restore_weights_tensor(mhelper.default_weights_info, sum_xu)
    print(f"restored_xu={restored_xu}")
    # update global model
    model = fl.update_globalmodel(model, restored_xu)

    # End
    server.broadcast("[Server] End protocol")
    fl.test_model(model)

if __name__ == "__main__":
    setUp()
    turbo()
    final_value = final()
    #print(f'final value: {final_value}')
