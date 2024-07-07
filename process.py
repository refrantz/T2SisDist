import socket
import pickle
from threading import Thread
from Queue import Queue

class Process(Thread):
  def __init__(self, env, id, host, port):
    super(Process, self).__init__()
    self.env = env
    self.id = id
    self.host = host
    self.port = port
    self.inbox = Queue()
    self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server_socket.bind((self.host, self.port))
    self.server_socket.listen(5)
    self.listener_thread = Thread(target=self.listen_for_messages)
    self.listener_thread.daemon = True
    self.listener_thread.start()
  
  def listen_for_messages(self):
    while True:
        client_socket, addr = self.server_socket.accept()
        data = client_socket.recv(1024)
        if data:
            msg = pickle.loads(data)
            self.inbox.put(msg)
        client_socket.close()

  def run(self):
    try:
        self.body()
        self.env.removeProc(self.id)
    except EOFError:
        print("Exiting..")

  def getNextMessage(self):
    return self.inbox.get()

  def deliver(self, msg):
    self.inbox.put(msg)

  def sendMessage(self, dst_id, msg):
    self.env.sendMessage(dst_id, msg)
