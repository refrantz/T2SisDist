from utils import BallotNumber
from process import Process
from commander import Commander
from scout import Scout
from message import ProposeMessage,AdoptedMessage,PreemptedMessage

class Leader(Process):
  def __init__(self, env, id, config, host, port):
    Process.__init__(self, env, id, host, port)
    self.ballot_number = BallotNumber(0, self.id)
    self.active = False
    self.proposals = {}
    self.config = config
    self.env.addProc(self)

  def create_scout(self):
    address = self.env.get_network_address()
    if address:
      host, port = address
      scout_id = "scout:{}:{}".format(self.id, self.ballot_number)
      scout = Scout(self.env, scout_id,
                    self.id, self.config.acceptors, self.ballot_number, host, port)

  def create_commander(self, slot_number, command):
    address = self.env.get_network_address()
    if address:
      host, port = address
      commander_id = "commander:{}:{}:{}".format(self.id, self.ballot_number, slot_number)
      commander = Commander(self.env,
                            commander_id,
                            self.id, self.config.acceptors, self.config.replicas,
                            self.ballot_number, slot_number, command, host, port)

  def body(self):
    print "Here I am: ", self.id
    self.create_scout()
    while True:
      msg = self.getNextMessage()
      if isinstance(msg, ProposeMessage):
        if msg.slot_number not in self.proposals:
          self.proposals[msg.slot_number] = msg.command
          if self.active:
            self.create_commander(msg.slot_number, msg.command)
      elif isinstance(msg, AdoptedMessage):
        if self.ballot_number == msg.ballot_number:
          pmax = {}
          for pv in msg.accepted:
            if pv.slot_number not in pmax or \
                  pmax[pv.slot_number] < pv.ballot_number:
              pmax[pv.slot_number] = pv.ballot_number
              self.proposals[pv.slot_number] = pv.command
          for sn in self.proposals:
            self.create_commander(sn, self.proposals[sn])
          self.active = True
      elif isinstance(msg, PreemptedMessage):
        if msg.ballot_number > self.ballot_number:
          self.active = False
          self.ballot_number = BallotNumber(msg.ballot_number.round+1,
                                            self.id)
          self.create_scout()
      else:
        print "Leader: unknown msg type"
