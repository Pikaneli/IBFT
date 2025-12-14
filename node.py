# node.py
import threading
import time
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import pickle

class IBFTNode:
    """Complete IBFT node implementation as per Algorithm 1"""
    
    def __init__(self, node_id: int, total_nodes: int, private_key, public_keys):
        # Node identification
        self.node_id = node_id
        self.n = total_nodes
        self.f = (total_nodes - 1) // 3  # Max faulty nodes
        
        # Cryptographic keys
        self.private_key = private_key
        self.public_keys = public_keys  # Map node_id -> public_key
        
        # State variables (Algorithm 1)
        self.λ = 0  # Consensus instance identifier
        self.r = 0  # Current round
        self.pr = -1  # Round at which prepared
        self.pv = None  # Value prepared
        self.lock_round = -1  # Highest round locked
        self.lock_value = None  # Value locked
        
        # Message stores
        self.preprepare_msgs = defaultdict(dict)  # (view, sequence) -> message
        self.prepare_msgs = defaultdict(lambda: defaultdict(set))  # (view, sequence) -> {sender}
        self.commit_msgs = defaultdict(lambda: defaultdict(set))  # (view, sequence) -> {sender}
        self.round_change_msgs = defaultdict(lambda: defaultdict(set))  # view -> {sender}
        self.new_round_msgs = defaultdict(dict)  # view -> message
        
        # Decision state
        self.decided = False
        self.decision = None
        self.decisions = {}  # sequence -> value
        
        # Message digests for deduplication
        self.seen_messages = set()
        
        # Timeout management
        self.timeout_handle = None
        self.round_timer = None
        self.timeout_duration = 10.0  # seconds
        
        # Locks for thread safety
        self.lock = threading.RLock()
        self.message_queue = []
        self.queue_lock = threading.Lock()
        self.queue_condition = threading.Condition(self.queue_lock)
        
        # Callbacks
        self.on_decision_callback = None
        self.network_send_callback = None
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'view_changes': 0,
            'decisions': 0
        }
    
    def set_network_callback(self, callback):
        """Set callback for sending messages to network"""
        self.network_send_callback = callback
    
    def set_decision_callback(self, callback):
        """Set callback for when decision is made"""
        self.on_decision_callback = callback
    
    def broadcast(self, message):
        """Broadcast message to all nodes"""
        with self.lock:
            if self.network_send_callback:
                serialized = pickle.dumps(message)
                for node_id in range(self.n):
                    if node_id != self.node_id:  # Don't send to self (will be delivered separately)
                        self.network_send_callback(node_id, serialized)
                self.stats['messages_sent'] += self.n - 1
            
            # Also deliver to self for processing
            self.receive_message(message)
    
    def receive_message(self, message):
        """Receive and queue a message for processing"""
        with self.queue_lock:
            message_hash = message.hash()
            if message_hash not in self.seen_messages:
                self.seen_messages.add(message_hash)
                self.message_queue.append(message)
                self.queue_condition.notify()
                self.stats['messages_received'] += 1
    
    def process_messages(self):
        """Main message processing loop"""
        while True:
            with self.queue_lock:
                while not self.message_queue:
                    self.queue_condition.wait()
                message = self.message_queue.pop(0)
            
            try:
                self._process_message(message)
            except Exception as e:
                print(f"Node {self.node_id} error processing message: {e}")
    
    def _process_message(self, message):
        """Process a single message"""
        with self.lock:
            # Verify message signature
            if not message.verify(self.public_keys[message.sender]):
                print(f"Node {self.node_id}: Invalid signature from {message.sender}")
                return
            
            # Verify message is for current or future consensus instance
            if message.sequence < self.λ:
                return  # Old consensus instance
            
            # Route to appropriate handler
            handlers = {
                MessageType.PREPREPARE: self._handle_preprepare,
                MessageType.PREPARE: self._handle_prepare,
                MessageType.COMMIT: self._handle_commit,
                MessageType.ROUND_CHANGE: self._handle_round_change,
                MessageType.NEW_ROUND: self._handle_new_round,
            }
            
            if message.msg_type in handlers:
                handlers[message.msg_type](message)
    
    def _handle_preprepare(self, msg):
        """Handle PREPREPARE message (Algorithm 2 lines 1-7)"""
        # Verify sender is primary for this view
        if (msg.view % self.n) != msg.sender:
            print(f"Node {self.node_id}: PREPREPARE from non-primary {msg.sender}")
            return
        
        # Check if we're in the same view
        if msg.view != self.r:
            print(f"Node {self.node_id}: PREPREPARE for wrong view {msg.view}, current {self.r}")
            return
        
        # Store preprepare
        key = (msg.view, msg.sequence)
        self.preprepare_msgs[key] = msg
        
        # Verify external validity
        if not self._is_valid_value(msg.value):
            print(f"Node {self.node_id}: Invalid value in PREPREPARE")
            return
        
        # Send PREPARE
        self._send_prepare(msg.value, msg.view, msg.sequence)
        
        # Reset round timer
        self._reset_round_timer()
    
    def _handle_prepare(self, msg):
        """Handle PREPARE message"""
        # Store prepare
        key = (msg.view, msg.sequence)
        self.prepare_msgs[key][msg.value].add(msg.sender)
        
        # Check for prepare quorum
        if len(self.prepare_msgs[key][msg.value]) >= 2 * self.f + 1:
            # Update lock if needed
            if msg.view > self.lock_round:
                self.lock_round = msg.view
                self.lock_value = msg.value
            
            # Send COMMIT
            self._send_commit(msg.value, msg.view, msg.sequence)
    
    def _handle_commit(self, msg):
        """Handle COMMIT message"""
        key = (msg.view, msg.sequence)
        self.commit_msgs[key][msg.value].add(msg.sender)
        
        # Check for commit quorum
        if len(self.commit_msgs[key][msg.value]) >= 2 * self.f + 1:
            # Decision reached!
            self._decide(msg.value, msg.sequence)
    
    def _decide(self, value, sequence):
        """Record decision and notify"""
        self.decided = True
        self.decision = value
        self.decisions[sequence] = value
        self.λ = sequence + 1  # Move to next consensus instance
        
        if self.on_decision_callback:
            self.on_decision_callback(self.node_id, sequence, value)
        
        print(f"Node {self.node_id}: DECIDED value {value} for sequence {sequence}")
        self.stats['decisions'] += 1
    
    def _send_prepare(self, value, view, sequence):
        """Send PREPARE message (Algorithm 2 lines 8-11)"""
        prepare_msg = IBFTMessage(
            msg_type=MessageType.PREPARE,
            view=view,
            sequence=sequence,
            sender=self.node_id,
            value=value
        )
        prepare_msg.sign(self.private_key)
        self.broadcast(prepare_msg)
    
    def _send_commit(self, value, view, sequence):
        """Send COMMIT message"""
        commit_msg = IBFTMessage(
            msg_type=MessageType.COMMIT,
            view=view,
            sequence=sequence,
            sender=self.node_id,
            value=value
        )
        commit_msg.sign(self.private_key)
        self.broadcast(commit_msg)
    
    def _is_valid_value(self, value):
        """External validity check (β predicate) - can be customized"""
        # Default implementation: accept any non-None value
        return value is not None
    
    def _reset_round_timer(self):
        """Reset the round timer"""
        if self.round_timer:
            self.round_timer.cancel()
        
        self.round_timer = threading.Timer(self.timeout_duration, self._on_round_timeout)
        self.round_timer.start()
    
    def _on_round_timeout(self):
        """Handle round timeout - trigger view change"""
        print(f"Node {self.node_id}: Round {self.r} timeout, starting view change")
        self._start_round_change()
    
    def _start_round_change(self):
        """Start round change to next view"""
        with self.lock:
            new_view = self.r + 1
            self.r = new_view
            self.stats['view_changes'] += 1
            
            # Collect justification
            justification = self._collect_round_change_justification()
            
            # Send ROUND_CHANGE message
            round_change_msg = IBFTMessage(
                msg_type=MessageType.ROUND_CHANGE,
                view=new_view,
                sequence=self.λ,
                sender=self.node_id,
                justification=justification
            )
            round_change_msg.sign(self.private_key)
            self.broadcast(round_change_msg)
    
    def _collect_round_change_justification(self):
        """Collect justification for round change"""
        justification = set()
        
        # Include highest prepared value if exists
        if self.lock_round >= 0:
            # Create a dummy prepare message digest for justification
            if self.lock_value:
                dummy_msg = IBFTMessage(
                    msg_type=MessageType.PREPARE,
                    view=self.lock_round,
                    sequence=self.λ,
                    sender=self.node_id,
                    value=self.lock_value
                )
                justification.add(dummy_msg.hash())
        
        return justification
    
    def _handle_round_change(self, msg):
        """Handle ROUND_CHANGE message"""
        self.round_change_msgs[msg.view][msg.sender].add(msg.hash())
        
        # Check for quorum of ROUND_CHANGE messages
        if len(self.round_change_msgs[msg.view]) >= 2 * self.f + 1:
            # If I'm the primary for this new view, send NEW_ROUND
            if (msg.view % self.n) == self.node_id:
                self._send_new_round(msg.view)
    
    def _send_new_round(self, view):
        """Send NEW_ROUND message as primary"""
        # Determine safe value to propose
        safe_value = self._determine_safe_value(view)
        
        if safe_value is None:
            safe_value = f"Block for view {view}"  # Default value
        
        # Create NEW_ROUND message
        justification = set()
        for sender in self.round_change_msgs[view]:
            justification.update(self.round_change_msgs[view][sender])
        
        new_round_msg = IBFTMessage(
            msg_type=MessageType.NEW_ROUND,
            view=view,
            sequence=self.λ,
            sender=self.node_id,
            value=safe_value,
            justification=justification
        )
        new_round_msg.sign(self.private_key)
        self.broadcast(new_round_msg)
    
    def _handle_new_round(self, msg):
        """Handle NEW_ROUND message"""
        # Verify sender is primary for this view
        if (msg.view % self.n) != msg.sender:
            return
        
        # Store NEW_ROUND message
        self.new_round_msgs[msg.view] = msg
        
        # Accept new view
        self.r = msg.view
        
        # Reset state for new view
        self.pr = -1
        self.pv = None
        
        # Process the proposed value as if it was a PREPREPARE
        preprepare_msg = IBFTMessage(
            msg_type=MessageType.PREPREPARE,
            view=msg.view,
            sequence=self.λ,
            sender=msg.sender,
            value=msg.value
        )
        self._handle_preprepare(preprepare_msg)
    
    def _determine_safe_value(self, new_view):
        """Determine safe value to propose (Algorithm 4)"""
        # Check if any value is locked
        if self.lock_round >= 0:
            return self.lock_value
        
        # Check for highest prepared certificate
        highest_prepared = -1
        highest_value = None
        
        for (view, seq), value_senders in self.prepare_msgs.items():
            for value, senders in value_senders.items():
                if len(senders) >= 2 * self.f + 1 and view > highest_prepared:
                    highest_prepared = view
                    highest_value = value
        
        return highest_value
    
    def propose_value(self, value):
        """Start a new consensus instance with given value"""
        with self.lock:
            if self.decided:
                return False
            
            sequence = self.λ
            
            # If I'm primary, send PREPREPARE
            if (self.r % self.n) == self.node_id:
                preprepare_msg = IBFTMessage(
                    msg_type=MessageType.PREPREPARE,
                    view=self.r,
                    sequence=sequence,
                    sender=self.node_id,
                    value=value
                )
                preprepare_msg.sign(self.private_key)
                self.broadcast(preprepare_msg)
                return True
            
            return False
    
    def get_stats(self):
        """Get node statistics"""
        with self.lock:
            return self.stats.copy()
    
    def get_state(self):
        """Get current node state"""
        with self.lock:
            return {
                'node_id': self.node_id,
                'λ': self.λ,
                'r': self.r,
                'pr': self.pr,
                'pv': self.pv,
                'lock_round': self.lock_round,
                'lock_value': self.lock_value,
                'decided': self.decided,
                'decision': self.decision,
                'stats': self.stats
            }