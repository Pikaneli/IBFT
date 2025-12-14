from consensus import IBFTConsensus
from view_change import IBFTViewChange
from node import IBFTNode
from messages import IBFTMessage, MessageType

class IBFTProtocol:
    def __init__(self, node_id: int, total_nodas: int):
        self.node = IBFTNode(node_id, total_nodes)
        self.consensus = IBFTConsensus(self.node)
        self.view_change = IBFTViewChange(self.node)
        
    def start_consensus(self, value):
        # Pokretanje algoritma 1
        self.lambdaa += 1
        
        if self.consensus.is_primary():
            # Primarni cvor predstavlja vrednost
            preprepare = IBFTMessage(
                msg_type=MessageType.PREPREPARE,
                view=self.node.r,
                sequence=self.node.lambdaa,
                sender=self.node.node_id,
                value=value
            )
            self.node.broadcast(preprepare)
            
    def handle_message(self, msg: IBFTMessage):
        # Rukovanje dolaznim porukama
        handlers = {
            MessageType.PREPREPARE: self.consensus.on_preprepare,
            MessageType.ROUND_CHANGE: self.view_change.on_round_change,
            MessageType.NEW_ROUND: self.view_change.on_new_round,
            MessageType.PREPARE: self.consensus.on_prepare,
            MessageType.COMMIT: self.consensus.on_commit
        }
        
        if msg.msg_type in handlers:
            handlers[msg.msg_type](msg)
            
        # Provera donosenja odluke
        self.check_decision()
        
    def check_decision(self):
        # Provera da li je kvorum commit poruka dostignut
        key = (self.node.r, self.node.lambdaa)
        if key in self.node.commit_msgs:
            commits = self.node.commit_msgs[key]
            if len(commits) >= self.consensus.quorum_size():
                # Donesena odluka
                self.node.decided = True