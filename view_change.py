# ibft/view_change.py
"""
IBFT View Change Logic - Algorithm 3 from the paper
Handles leader rotation and recovery from faulty primaries
"""

import threading
import time
from typing import Dict, Set, List, Optional, Any
from collections import defaultdict
from .messages import IBFTMessage, MessageType

class IBFTViewChange:
    """Implements the view change protocol (Algorithm 3)"""
    
    def __init__(self, node):
        self.node = node
        self.round_change_msgs = defaultdict(lambda: defaultdict(set))  # view -> sender -> {msg_hashes}
        self.new_round_msgs = {}  # view -> message
        self.view_change_timeout = 10.0  # seconds
        self.round_timer = None
        self.pending_view_changes = defaultdict(list)  # view -> list of messages
        self.highest_prepared_certificates = {}  # sequence -> (view, value, certificate)
    
    def reset_round_timer(self):
        """Reset the round timer"""
        if self.round_timer:
            self.round_timer.cancel()
        
        self.round_timer = threading.Timer(
            self.view_change_timeout,
            self._on_round_timeout
        )
        self.round_timer.start()
    
    def _on_round_timeout(self):
        """Handle round timeout - initiate view change"""
        print(f"Node {self.node.node_id}: Round {self.node.r} timeout, starting view change")
        self.start_round_change()
    
    def start_round_change(self, new_view: Optional[int] = None):
        """
        Start round change to new view (Algorithm 3 lines 1-4)
        """
        if new_view is None:
            new_view = self.node.r + 1
        
        # Update current view
        self.node.r = new_view
        self.node.stats['view_changes'] += 1
        
        # Reset consensus state for new view
        self.node.pr = -1
        self.node.pv = None
        
        # Collect justification for round change
        justification = self._collect_round_change_justification()
        
        # Send ROUND_CHANGE message
        round_change_msg = IBFTMessage(
            msg_type=MessageType.ROUND_CHANGE,
            view=new_view,
            sequence=self.node.λ,
            sender=self.node.node_id,
            justification=justification
        )
        
        # Include highest prepared certificate if available
        if self.node.lock_round >= 0 and self.node.lock_value:
            # Create a proof of lock
            lock_proof = self._create_lock_proof()
            if lock_proof:
                round_change_msg.value = self.node.lock_value
                # Add lock proof to justification
                round_change_msg.justification.add(lock_proof)
        
        round_change_msg.sign(self.node.private_key)
        self.node.broadcast(round_change_msg)
        
        print(f"Node {self.node.node_id}: Sent ROUND_CHANGE for view {new_view}")
    
    def handle_round_change(self, msg: IBFTMessage) -> bool:
        """
        Handle ROUND_CHANGE message (Algorithm 3 lines 5-10)
        """
        # Verify message is for current or future view
        if msg.view < self.node.r:
            return False  # Old view
        
        # Store round change message
        self.round_change_msgs[msg.view][msg.sender].add(msg.hash())
        
        # Check for quorum of ROUND_CHANGE messages (2f + 1)
        if len(self.round_change_msgs[msg.view]) >= self.node.quorum_size():
            # If I'm the primary for this new view, send NEW_ROUND
            if self._is_primary_for_view(msg.view):
                self._send_new_round(msg.view)
        
        return True
    
    def handle_new_round(self, msg: IBFTMessage) -> bool:
        """
        Handle NEW_ROUND message (Algorithm 3 lines 11-15)
        """
        # Verify sender is primary for this view
        if not self._is_primary_for_view(msg.view, msg.sender):
            print(f"Node {self.node.node_id}: NEW_ROUND from non-primary {msg.sender}")
            return False
        
        # Verify we have quorum of ROUND_CHANGE messages for this view
        if not self._has_round_change_quorum(msg.view):
            print(f"Node {self.node.node_id}: No round change quorum for view {msg.view}")
            return False
        
        # Check if proposal is safe (Algorithm 4)
        if not self._is_safe_proposal(msg.value, msg.justification, msg.view):
            print(f"Node {self.node.node_id}: Unsafe proposal in NEW_ROUND")
            return False
        
        # Store NEW_ROUND message
        self.new_round_msgs[msg.view] = msg
        
        # Accept new view
        self.node.r = msg.view
        
        # Reset round timer
        self.reset_round_timer()
        
        print(f"Node {self.node.node_id}: Accepted NEW_ROUND for view {msg.view}")
        
        # Process the proposed value as if it was a PREPREPARE
        # This will be handled by the main message processor
        
        return True
    
    def _send_new_round(self, view: int):
        """
        Send NEW_ROUND message as primary (Algorithm 3 lines 16-20)
        """
        # Determine safe value to propose
        safe_value = self._determine_safe_value(view)
        
        if safe_value is None:
            # No safe value found, propose a default value
            safe_value = f"New block for view {view}"
        
        # Collect justification from round change messages
        justification = set()
        for sender in self.round_change_msgs[view]:
            justification.update(self.round_change_msgs[view][sender])
        
        # Create NEW_ROUND message
        new_round_msg = IBFTMessage(
            msg_type=MessageType.NEW_ROUND,
            view=view,
            sequence=self.node.λ,
            sender=self.node.node_id,
            value=safe_value,
            justification=justification
        )
        
        new_round_msg.sign(self.node.private_key)
        self.node.broadcast(new_round_msg)
        
        print(f"Node {self.node.node_id}: Sent NEW_ROUND for view {view} with value {safe_value}")
    
    def _collect_round_change_justification(self) -> Set[str]:
        """
        Collect justification for round change
        Returns set of message hashes that justify the round change
        """
        justification = set()
        
        # Include proof of highest prepared value if we have one
        if self.node.lock_round >= 0 and self.node.lock_value:
            # Create proof of lock (simplified - would be actual messages in production)
            lock_proof = f"lock_{self.node.lock_round}_{hash(str(self.node.lock_value))}"
            justification.add(lock_proof)
        
        return justification
    
    def _has_round_change_quorum(self, view: int) -> bool:
        """Check if we have quorum of ROUND_CHANGE messages for given view"""
        return len(self.round_change_msgs[view]) >= self.node.quorum_size()
    
    def _is_primary_for_view(self, view: int, node_id: Optional[int] = None) -> bool:
        """Check if node is primary for given view"""
        if node_id is None:
            node_id = self.node.node_id
        return (view % self.node.n) == node_id
    
    def _determine_safe_value(self, new_view: int) -> Optional[Any]:
        """
        Determine safe value to propose in NEW_ROUND (Algorithm 4)
        """
        # 1. Check if we have a locked value
        if self.node.lock_round >= 0:
            return self.node.lock_value
        
        # 2. Check for highest prepared certificate from round change messages
        highest_view = -1
        highest_value = None
        
        # Look for prepared certificates in round change justifications
        for sender in self.round_change_msgs[new_view]:
            # In real implementation, would extract prepared certificates
            # from round change message justifications
            pass
        
        # 3. If no prepared certificate found, check our own prepare messages
        # This is a simplification - real implementation would check all nodes' proofs
        if highest_value is None:
            # Return any valid value
            return "Default block"
        
        return highest_value
    
    def _is_safe_proposal(self, value: Any, justification: Set[str], view: int) -> bool:
        """
        Check if proposal is safe according to Algorithm 4
        """
        if not justification:
            return False
        
        # Simplified safety check
        # In full implementation, would verify:
        # 1. Quorum of round change messages
        # 2. If any node is locked, value must match locked value
        # 3. Otherwise, value must have prepare certificate from previous view
        
        # For now, accept if we have any justification
        return len(justification) > 0
    
    def _create_lock_proof(self) -> Optional[str]:
        """Create proof of locked value"""
        if self.node.lock_round < 0 or self.node.lock_value is None:
            return None
        
        # Simplified lock proof
        # In real implementation, this would be a quorum of PREPARE messages
        return f"lock_proof_{self.node.lock_round}_{hash(str(self.node.lock_value))}"
    
    def cleanup_old_view_changes(self, current_view: int):
        """Clean up old view change messages"""
        keep_last_n = 5
        to_remove = []
        
        for view in list(self.round_change_msgs.keys()):
            if view < current_view - keep_last_n:
                to_remove.append(view)
        
        for view in to_remove:
            self.round_change_msgs.pop(view, None)
            self.new_round_msgs.pop(view, None)
            self.pending_view_changes.pop(view, None)