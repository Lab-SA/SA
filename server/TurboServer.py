import os, sys, copy
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from MainServer import MainServer
from TurboBaseServer import TurboBaseServer
from BasicSA import getCommonValues
from CommonValue import TurboRound

usersNum = 0
threshold = 0
R = 0
groups = []

# send common values and index, group of each user
def setUp():
    global usersNum, threshold, R, groups

    tag = TurboRound.SetUp.name
    port = TurboRound.SetUp.value
    server = MainServer(tag, port)
    server.start()

    commonValues = getCommonValues()
    usersNum = commonValues["n"]
    threshold = commonValues["t"]
    R = commonValues["R"]

    usersNow = len(server.requests)
    response = []
    for i in range(usersNow):
        response_i = copy.deepcopy(commonValues)
        response_i["group"] = i # TODO: grouping
        response_i["index"] = 0 # TODO
        response.append(response_i)
    server.foreachIndex(response)

def turbo():
    global groups, usersNum

    tag = TurboRound.Turbo.name
    tag_value = TurboRound.TurboValue.name
    tag_final = TurboRound.TurboFinal.name
    port = TurboRound.Turbo.value
    
    server = TurboBaseServer(tag, tag_value, tag_final, port, 3, usersNum) # len(groups)
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
