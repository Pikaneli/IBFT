from messages import IBFTMessage

class IBFTNode:
    def __init__(self, node_id: int, total_nodes: int, fault_tolerance: int = 1):
        self.node_id = node_id
        self.n = total_nodes
        self.f = fault_tolerance

        # Algoritam 1 stanja
        self.lambdaa = 0  # Trenutni broj konsenzus instance
        self.r = 0  # Trenutni broj runde
        self.pv = None  # Predlozena runda
        self.pr = -1  # Broj runde za koju je predlozena vrednost
        self.lock_round = -1
        self.lock_value = None
        
        # Log poruke
        self.prepare_msgs = {}  
        self.prepare_msgs = {}
        self.commit_msgs = {}
        self.round_change_msgs = {}
        
        # Odluke stanja
        self.decided = False
        self.decision = None
        
    def broadcast(self, message: IBFTMessage):
        # Slanje poruke svim ostalim čvorovima
        pass