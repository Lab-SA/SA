from threading import Lock
from collections import deque

class MessageQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = Lock()

    def put(self, clientSocket, requestData):
        with self.lock:
            self.queue.append([clientSocket, requestData])

    def get(self):
        with self.lock:
            return self.queue.popleft()

if __name__ == "__main__":
    mq = MessageQueue()
    mq.put(1, 2)
    mq.put(2,3)
    print(mq.get())
    print(mq.get())
    print(mq.get())