from node import IBFTNode
from messages import IBFTMessage, MessageType

# Algoritam 3

class IBFTViewChange:
    def __init__(self, node: IBFTNode):
        self.node = node
        self.view_change_timeout = 10.0
        
        def start_round_change(self, new_round: int):
            # Pokretanje promene runde
            justification = self.collect_round_change_justification(new_round-1)
            
            round_change_msg = IBFTMessage(
                msg_type=MessageType.ROUND_CHANGE,
                view=new_round,
                sequence=self.node.lambdaa,
                sender=self.node.node_id,
                justification=justification
            )
            self.node.broadcast(round_change_msg)
            
        def on_new_round(self, msg: IBFTMessage):
            # Obrada NEW_ROUND poruke od novog primarnog čvora
            if not self.has_quorum_round_change(msg.view):
                return False
            
            if not self.is_safe_proposal(msg.value, msg.justification):
                return False
            
            # Prihvati novu rundu i vrednost
            self.node.r = msg.view
            return True