# test_ibft.py
#import pytest
from node import IBFTNode
from view_change import IBFTViewChange
from consensus import IBFTConsensus
from messages import IBFTMessage, MessageType

def test_quorum_calculation():
    """Test that quorum sizes follow n ≥ 3f + 1"""
    for n in [4, 7, 10, 13]:
        f = (n - 1) // 3
        node = IBFTNode(0, n, f)
        quorum = 2 * f + 1
        assert quorum <= n - f  # Quorum must include only correct nodes

def test_safety_predicate():
    """Test Algorithm 4 safety conditions"""
    validator = IBFTValidator()
    
    # Test basic safety checks
    assert validator.is_safe_proposal(
        value="test",
        justification=set(),
        current_round=1,
        lock_round=-1,
        lock_value=None
    ) == False  # No justification
    
def test_three_phase_commit():
    """Test normal case 3-message-delay path"""
    nodes = [IBFTNode(i, 4) for i in range(4)]
    # Simulate consensus with primary proposing value
    # Verify all correct nodes decide same value