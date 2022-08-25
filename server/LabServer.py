import socket, json, time, threading

from BasicSAServerV2 import BasicSAServerV2
from TurboBaseServer import TurboServer
from HeteroSAServer import HeteroSAServer
from CSAServer import CSAServer

def runServer(mode, k, n):
    if mode == 0: # BasicSA
        server = BasicSAServerV2(n=n, k=k)
        server.start()

    elif mode == 1: # Turbo
        server = TurboServer(n=n, k=k)
        server.start()

    #elif mode == 2: # BREA

    elif mode == 3: # HeteroSA
        server = HeteroSAServer(n=n, k=k)
        server.start()

    elif mode == 4: # BasicCSA
        server = CSAServer(n=n, k=k, isBasic = True)
        server.start()

    elif mode == 5: # FullCSA
        server = CSAServer(n=n, k=k, isBasic = False)
        server.start()


class LabServer:
    host = 'localhost'
    port = 6000
    SIZE = 2048
    ENCODING = 'utf-8'

    def start(self):
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.bind((self.host, self.port))
        serverSocket.listen()
        print(f'[SERVER] Server started')

        while True:
            currentClient = socket
            try:
                clientSocket, addr = serverSocket.accept()
                currentClient = clientSocket

                # receive client data
                # client request must ends with "\r\n"
                request = ''
                while True:
                    received = str(clientSocket.recv(self.SIZE), self.ENCODING)
                    if received.endswith("\r\n"):
                        received = received.replace("\r\n", "")
                        request = request + received
                        break
                    request = request + received

                requestData = json.loads(request)
                k = int(requestData['k'])    # rounds
                n = int(requestData['n'])    # number of users
                mode = int(requestData['request'])
                """ mode
                0: BasicSA Client
                1: Turbo Client
                2: BREA Client
                3: HeteroSA Client
                4: BasicCSA Client
                5: FullCSA Client
                """
                if mode < 0 or mode > 5:
                    raise AttributeError

                print(f'[SERVER] Client: {addr}, request: {request}')
                thread = threading.Thread(target=runServer, args=(mode, k, n))
                thread.start()

            except socket.timeout:
                pass
            except AttributeError:
                print(f'[SERVER] Exception: invalid request')
                currentClient.sendall(bytes(f'Exception: invalid request', self.ENCODING))
                pass
            except:
                print(f'[SERVER] Exception: invalid request or unknown server error')
                currentClient.sendall(bytes('Exception: invalid request or unknown server error\r\n', self.ENCODING))
                pass



if __name__ == "__main__":
    server = LabServer()
    server.start()
