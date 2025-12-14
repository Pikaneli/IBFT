from node import IBFTNode
from messages import IBFTMessage, MessageType

# Algoritam 2 (Normal case operation)

class IBFTConsensus:
    def __init__(self, node: IBFTNode):
        self.node = node
        
    def is_primary(self, round_num: int = None) -> bool:
        # Provera da li je trenutni čvor primarni za datu rundu
        if round_num is None:
            round_num = self.node.r
        return (round_num % self.node.n) == self.node.node_id
    
    def quorum_size(self) -> int:
        # Vraća veličinu kvora 2f + 1
        return (2 * self.node.f) + 1
    
    def on_preprepare(self, msg: IBFTMessage):
        # Obrada PREPREPARE poruke
        # Validate: mora biti od primarnog čvora i za trenutnu rundu i instancu
        if not self.is_primary(msg.view):
            return  False # Ignoriši ako nije od primarnog
        
        # Proveri obrazlozenje za promenu runde
        if msg.view > 0 and not self.has_valid_justification(msg):
            return False  # Ignoriši ako nema validno obrazloženje
        
        # Proveri eksternu validnost vrednosti
        if not self.is_valid_value(msg.value):
            return False  # Ignoriši ako vrednost nije validna
        
        # Sacuvaj preprepare poruku
        key = (msg.view, msg.sequence)
        self.node.preprepare_msgs[key] = msg
        
        # Posalji prepare poruku
        if self.should_prepare(msg):
            self.send_prepare(msg.value, msg.view, msg.sequence)
            
        return True
    
    def send_prepare(self, value, view, sequence):
        # Kreiraj i posalji PREPARE poruku
        prepare_msg = IBFTMessage(
            msg_type=MessageType.PREPARE,
            view=view,
            sequence=sequence,
            sender=self.node.node_id,
            value=value
        )
        self.node.broadcast(prepare_msg)
        
        # Sacuvaj prepared stanje
        if view > self.node.pr:
            self.node.pr = view
            self.node.pv = value
            
# Algoritam 4

class IBFTValidator:
    @staticmethod
    def is_safe_proposal(value, justification, current_round, lock_round, lock_value) -> bool:
        # Provera se da li je vrednost bezbedna ya predlog u novoj rundi
        if justification is None:
            return False
        
        # Proveri kvora sertifikat
        if not IBFTValidator.has_quorum_prepare(justification, current_round-1):
            return False
        
        # Proveri zakljucavanje
        if lock_round == -1:
            # Mora se predloziti yakljucana vrednost ako postoji
            return value == lock_value
        
        return True
    
    @staticmethod
    def has_quorum_prepare(messages, round_num) -> bool:
        # Proveri kvorum ya PREPARE poruku (2f+1)
        unique_senders = {msg.sender for msg in messages
                          if msg.msg_type == MessageType.PREPARE
                          and msg.view == round_num}
        return len(unique_senders) >= (2 * (len(messages) // 3)) + 1
    