import os, sys, copy, random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from TurboBaseServer import TurboBaseServer
from BasicSA import getCommonValues
from CommonValue import TurboRound

groupNum = 0
perGroup = 0
usersNum = 0
threshold = 0
R = 0
groups = []

# send common values and index, group of each user
def setUp():
    global groupNum, usersNum, threshold, R, groups, perGroup

    tag = TurboRound.SetUp.name
    port = TurboRound.SetUp.value
    server = MainServer(tag, port)
    server.start()

    commonValues = getCommonValues()
    usersNum = commonValues["n"]
    threshold = commonValues["t"]
    R = commonValues["R"]

    perGroup = 2 # temp
    commonValues["perGroup"] = perGroup

    usersNow = len(server.requests) # MUST be multiple of perGroup
    groupNum = int(usersNow / perGroup)
    response = []
    for i in range(groupNum):
        for j in range(perGroup):
            response_ij = copy.deepcopy(commonValues)
            response_ij["group"] = i
            response_ij["index"] = j
            response_ij["mask_u"] = random.randrange(1, R) # 1~R
            response.append(response_ij)
    server.foreachIndex(response)

def turbo():
    global groups, usersNum, perGroup

    tag = TurboRound.Turbo.name
    tag_value = TurboRound.TurboValue.name
    tag_final = TurboRound.TurboFinal.name
    port = TurboRound.Turbo.value
    
    server = TurboBaseServer(tag, tag_value, tag_final, port, 3, usersNum, perGroup) # len(groups)
    server.start()

def final():
    tag = TurboRound.Final.name
    port = TurboRound.Final.value

    server = MainServer(tag, port)
    server.start()
    final_tildeS = []
    final_barS = []

    for request in server.requests:
        requestData = request[1]  # (socket, data)
        final_tildeS.append(int(requestData["final_tildeS"]))
        final_barS.append(int(requestData["final_barS"]))
    server.broadcast({})

    print(final_tildeS)
    print(final_barS)

if __name__ == "__main__":
    setUp()
    turbo()
    final()
