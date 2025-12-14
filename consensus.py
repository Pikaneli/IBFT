# ibft/consensus.py
"""
IBFT Consensus Logic - Algorithm 2 from the paper
Handles normal case operation: PREPREPARE → PREPARE → COMMIT
"""

import time
from typing import Dict, Set, List, Optional, Any, Tuple
from collections import defaultdict
from .messages import IBFTMessage, MessageType

class IBFTConsensus:
    """Implements the normal case consensus logic (Algorithm 2)"""
    
    def __init__(self, node):
        self.node = node
        self.message_logs = {
            'preprepare': defaultdict(dict),  # (view, sequence) -> message
            'prepare': defaultdict(lambda: defaultdict(set)),  # (view, sequence, value) -> {senders}
            'commit': defaultdict(lambda: defaultdict(set)),  # (view, sequence, value) -> {senders}
        }
        self.prepared_certificates = {}  # (sequence, value) -> prepare certificate
        self.commit_certificates = {}  # (sequence, value) -> commit certificate
        self.decided_values = {}  # sequence -> value
    
    def handle_preprepare(self, msg: IBFTMessage) -> bool:
        """
        Handle PREPREPARE message (Algorithm 2 lines 1-7)
        Returns: True if message was accepted, False otherwise
        """
        # 1. Verify sender is primary for this view
        if not self._is_primary_for_view(msg.view, msg.sender):
            print(f"Node {self.node.node_id}: PREPREPARE from non-primary {msg.sender} for view {msg.view}")
            return False
        
        # 2. Check if we're in the same view
        if msg.view != self.node.r:
            print(f"Node {self.node.node_id}: PREPREPARE for view {msg.view}, current view {self.node.r}")
            # Could be for future view, store but don't process yet
            if msg.view > self.node.r:
                self._store_future_message(msg)
                return True
            return False
        
        # 3. Check if we already have a preprepare for this (view, sequence)
        key = (msg.view, msg.sequence)
        if key in self.message_logs['preprepare']:
            # Duplicate message
            return True
        
        # 4. Verify external validity (β predicate)
        if not self.node.validator.is_valid_value(msg.value):
            print(f"Node {self.node.node_id}: Invalid value in PREPREPARE: {msg.value}")
            return False
        
        # 5. For view > 0, check justification (Algorithm 4)
        if msg.view > 0 and msg.justification:
            if not self._has_valid_justification(msg.justification, msg.view):
                print(f"Node {self.node.node_id}: Invalid justification in PREPREPARE")
                return False
        
        # 6. Store the preprepare message
        self.message_logs['preprepare'][key] = msg
        
        # 7. Send PREPARE message
        self._send_prepare(msg.value, msg.view, msg.sequence)
        
        # Reset round timer
        self.node.view_change.reset_round_timer()
        
        print(f"Node {self.node.node_id}: Accepted PREPREPARE for view {msg.view}, sequence {msg.sequence}")
        return True
    
    def handle_prepare(self, msg: IBFTMessage) -> bool:
        """
        Handle PREPARE message (Algorithm 2 lines 8-11)
        """
        # Verify we have corresponding PREPREPARE
        key = (msg.view, msg.sequence)
        if key not in self.message_logs['preprepare']:
            # Might arrive before PREPREPARE, store for later
            self._store_pending_message(msg)
            return True
        
        preprepare = self.message_logs['preprepare'][key]
        
        # Verify prepare matches preprepare value
        if msg.value != preprepare.value:
            print(f"Node {self.node.node_id}: PREPARE value mismatch")
            return False
        
        # Store prepare message
        self.message_logs['prepare'][key][msg.value].add(msg.sender)
        
        # Check for prepare quorum (2f + 1)
        prepare_senders = self.message_logs['prepare'][key][msg.value]
        if len(prepare_senders) >= self.node.quorum_size():
            # This is a prepared certificate
            self._on_prepared(msg.view, msg.sequence, msg.value)
        
        return True
    
    def handle_commit(self, msg: IBFTMessage) -> bool:
        """
        Handle COMMIT message
        """
        key = (msg.view, msg.sequence)
        
        # Store commit message
        self.message_logs['commit'][key][msg.value].add(msg.sender)
        
        # Check for commit quorum (2f + 1)
        commit_senders = self.message_logs['commit'][key][msg.value]
        if len(commit_senders) >= self.node.quorum_size():
            # This is a commit certificate
            self._on_committed(msg.sequence, msg.value)
        
        return True
    
    def _send_prepare(self, value, view, sequence):
        """Send PREPARE message (Algorithm 2 lines 8-11)"""
        prepare_msg = IBFTMessage(
            msg_type=MessageType.PREPARE,
            view=view,
            sequence=sequence,
            sender=self.node.node_id,
            value=value
        )
        prepare_msg.sign(self.node.private_key)
        
        # Update local prepared state
        if view > self.node.pr:
            self.node.pr = view
            self.node.pv = value
        
        self.node.broadcast(prepare_msg)
        print(f"Node {self.node.node_id}: Sent PREPARE for view {view}, sequence {sequence}")
    
    def _on_prepared(self, view: int, sequence: int, value: Any):
        """
        Called when value is prepared (quorum of PREPARE messages)
        """
        print(f"Node {self.node.node_id}: Value prepared for view {view}, sequence {sequence}")
        
        # Update lock if this is a higher view
        if view > self.node.lock_round:
            self.node.lock_round = view
            self.node.lock_value = value
            print(f"Node {self.node.node_id}: Locked value at view {view}")
        
        # Send COMMIT message
        self._send_commit(value, view, sequence)
    
    def _send_commit(self, value, view, sequence):
        """Send COMMIT message"""
        commit_msg = IBFTMessage(
            msg_type=MessageType.COMMIT,
            view=view,
            sequence=sequence,
            sender=self.node.node_id,
            value=value
        )
        commit_msg.sign(self.node.private_key)
        self.node.broadcast(commit_msg)
        print(f"Node {self.node.node_id}: Sent COMMIT for view {view}, sequence {sequence}")
    
    def _on_committed(self, sequence: int, value: Any):
        """
        Called when value is committed (quorum of COMMIT messages)
        This means consensus is reached!
        """
        if sequence in self.decided_values:
            # Already decided for this sequence
            return
        
        self.decided_values[sequence] = value
        
        # Update node state
        self.node.decided = True
        self.node.decision = value
        self.node.decisions[sequence] = value
        
        # Move to next consensus instance
        self.node.λ = sequence + 1
        
        # Reset state for next consensus instance
        self._reset_for_new_sequence()
        
        # Notify callback
        if self.node.on_decision_callback:
            self.node.on_decision_callback(self.node.node_id, sequence, value)
        
        print(f"Node {self.node.node_id}: DECISION reached for sequence {sequence}: {value}")
        self.node.stats['decisions'] += 1
    
    def _reset_for_new_sequence(self):
        """Reset state for new consensus instance"""
        # Keep only necessary state from previous sequences
        # In practice, you might want to garbage collect old messages
        pass
    
    def _is_primary_for_view(self, view: int, node_id: int) -> bool:
        """Check if node is primary for given view"""
        return (view % self.node.n) == node_id
    
    def _has_valid_justification(self, justification: Set[str], view: int) -> bool:
        """
        Check if justification is valid for view change (Algorithm 4)
        justification: Set of message hashes that justify the proposal
        """
        if not justification:
            return False
        
        # For simplicity, check if justification contains enough round change messages
        # In full implementation, would verify signatures and quorums
        return len(justification) >= self.node.f + 1
    
    def _store_future_message(self, msg: IBFTMessage):
        """Store message for future view"""
        # Implementation would store in a pending messages buffer
        pass
    
    def _store_pending_message(self, msg: IBFTMessage):
        """Store message pending corresponding PREPREPARE"""
        # Implementation would store in a pending messages buffer
        pass
    
    def get_prepare_quorum(self, view: int, sequence: int, value: Any) -> Set[int]:
        """Get set of nodes that sent PREPARE for given (view, sequence, value)"""
        key = (view, sequence)
        if key in self.message_logs['prepare'] and value in self.message_logs['prepare'][key]:
            return self.message_logs['prepare'][key][value].copy()
        return set()
    
    def get_commit_quorum(self, view: int, sequence: int, value: Any) -> Set[int]:
        """Get set of nodes that sent COMMIT for given (view, sequence, value)"""
        key = (view, sequence)
        if key in self.message_logs['commit'] and value in self.message_logs['commit'][key]:
            return self.message_logs['commit'][key][value].copy()
        return set()
    
    def has_prepared_certificate(self, sequence: int, value: Any) -> bool:
        """Check if we have a prepare certificate for given sequence and value"""
        # Check all views for this sequence
        for (v, s) in self.message_logs['prepare']:
            if s == sequence and value in self.message_logs['prepare'][(v, s)]:
                if len(self.message_logs['prepare'][(v, s)][value]) >= self.node.quorum_size():
                    return True
        return False
    
    def cleanup_old_messages(self, current_sequence: int):
        """Clean up messages for old consensus instances"""
        # Remove messages for sequences < current_sequence - keep_last_n
        keep_last_n = 10
        to_remove = []
        
        for (view, sequence) in list(self.message_logs['preprepare'].keys()):
            if sequence < current_sequence - keep_last_n:
                to_remove.append(('preprepare', (view, sequence)))
        
        for (view, sequence) in list(self.message_logs['prepare'].keys()):
            if sequence < current_sequence - keep_last_n:
                to_remove.append(('prepare', (view, sequence)))
        
        for (view, sequence) in list(self.message_logs['commit'].keys()):
            if sequence < current_sequence - keep_last_n:
                to_remove.append(('commit', (view, sequence)))
        
        for msg_type, key in to_remove:
            if msg_type == 'preprepare':
                self.message_logs['preprepare'].pop(key, None)
            elif msg_type == 'prepare':
                self.message_logs['prepare'].pop(key, None)
            elif msg_type == 'commit':
                self.message_logs['commit'].pop(key, None)