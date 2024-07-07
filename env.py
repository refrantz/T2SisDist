import pickle
import socket
import os, signal, sys, time
from acceptor import Acceptor
from leader import Leader
from message import RequestMessage
from process import Process
from replica import Replica
from utils import *

NACCEPTORS = 3
NREPLICAS = 2
NLEADERS = 2
NREQUESTS = 10
NCONFIGS = 2

class Env:
  def __init__(self):
    self.available_addresses =  self.generate_ports('localhost', 10000, 11111)
    self.procs = {}
    self.proc_addresses = {}

  def get_network_address(self):
    return self.available_addresses.pop(0) if self.available_addresses else None
  
  def generate_ports(self, host, start_port, end_port):
    return [(host, port) for port in range(start_port, end_port + 1)]


  def release_network_address(self, address):
      self.available_addresses.append(address)

  def sendMessage(self, dst, msg):
    if dst in self.proc_addresses:
      host, port = self.proc_addresses[dst]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))  # You need to define `host` and `port` properly
        s.sendall(pickle.dumps(msg))
    except Exception as e:
        print("Failed to send message:", e)
    finally:
        s.close()  # Ensure the socket is closed regardless of the above results

  def addProc(self, proc):
    self.procs[proc.id] = proc
    self.proc_addresses[proc.id] = (proc.host, proc.port)
    proc.start()

  def removeProc(self, pid):
    if pid in self.procs:
      del self.procs[pid]
      del self.proc_addresses[pid]

  def run(self):
    initialconfig = Config([], [], [])
    c = 0

    for i in range(NREPLICAS):
      host, port = self.get_network_address()
      pid = "replica %d" % i
      Replica(self, pid, initialconfig, host, port)
      initialconfig.replicas.append(pid)

    for i in range(NACCEPTORS):
      host, port = self.get_network_address()
      pid = "acceptor %d.%d" % (c, i)
      Acceptor(self, pid, host, port)
      initialconfig.acceptors.append(pid)

    for i in range(NLEADERS):
      host, port = self.get_network_address()
      pid = "leader %d.%d" % (c, i)
      Leader(self, pid, initialconfig, host, port)
      initialconfig.leaders.append(pid)
      
    for i in range(NREQUESTS):
      pid = "client %d.%d" % (c,i)
      for r in initialconfig.replicas:
        cmd = Command(pid,0,"operation %d.%d" % (c,i))
        self.sendMessage(r,RequestMessage(pid,cmd))
        time.sleep(1)

    for c in range(1, NCONFIGS):
      # Create new configuration
      config = Config(initialconfig.replicas, [], [])
      for i in range(NACCEPTORS):
        host, port = self.get_network_address()
        pid = "acceptor %d.%d" % (c, i)
        Acceptor(self, pid, host, port)

        initialconfig.acceptors.append(pid)
      for i in range(NLEADERS):
        host, port = self.get_network_address()
        pid = "leader %d.%d" % (c, i)
        Leader(self, pid, initialconfig, host, port)

        initialconfig.leaders.append(pid)
      # Send reconfiguration request
      for r in config.replicas:
        pid = "master %d.%d" % (c,i)
        cmd = ReconfigCommand(pid,0,str(config))
        self.sendMessage(r, RequestMessage(pid, cmd))
        time.sleep(1)
      for i in range(WINDOW-1):
        pid = "master %d.%d" % (c,i)
        for r in config.replicas:
          cmd = Command(pid,0,"operation noop")
          self.sendMessage(r, RequestMessage(pid, cmd))
          time.sleep(1)
      for i in range(NREQUESTS):
        pid = "client %d.%d" % (c,i)
        for r in config.replicas:
          cmd = Command(pid,0,"operation %d.%d"%(c,i))
          self.sendMessage(r, RequestMessage(pid, cmd))
          time.sleep(1)

  def terminate_handler(self, signal, frame):
    self._graceexit()

  def _graceexit(self, exitcode=0):
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitcode)

def main():
  e = Env()
  e.run()
  signal.signal(signal.SIGINT, e.terminate_handler)
  signal.signal(signal.SIGTERM, e.terminate_handler)
  signal.pause()


if __name__=='__main__':
  main()
