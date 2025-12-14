# tests/test_ibft.py
import unittest
import time
from node import IBFTNode
from messages import IBFTMessage, MessageType
from crypto import generate_keypair

class TestIBFT(unittest.TestCase):
    
    def setUp(self):
        # Create a simple 4-node setup for testing
        self.n_nodes = 4
        keypairs = [generate_keypair() for _ in range(self.n_nodes)]
        self.private_keys = [kp[0] for kp in keypairs]
        self.public_keys = {i: kp[1] for i, kp in enumerate(keypairs)}
        
        # Create test node
        self.node = IBFTNode(
            node_id=0,
            total_nodes=self.n_nodes,
            private_key=self.private_keys[0],
            public_keys=self.public_keys
        )
    
    def test_quorum_calculation(self):
        """Test that quorum sizes are calculated correctly"""
        # For n=4, f=1, quorum should be 2f+1 = 3
        self.assertEqual(2 * self.node.f + 1, 3)
    
    def test_message_signature(self):
        """Test message signing and verification"""
        msg = IBFTMessage(
            msg_type=MessageType.PREPARE,
            view=0,
            sequence=0,
            sender=0,
            value="test"
        )
        
        # Sign message
        msg.sign(self.private_keys[0])
        
        # Verify signature
        self.assertTrue(msg.verify(self.public_keys[0]))
        
        # Should fail with wrong public key
        self.assertFalse(msg.verify(self.public_keys[1]))
    
    def test_preprepare_validation(self):
        """Test PREPREPARE validation"""
        # Primary for view 0 is node 0 (0 % 4 = 0)
        msg = IBFTMessage(
            msg_type=MessageType.PREPREPARE,
            view=0,
            sequence=0,
            sender=0,  # Correct primary
            value="valid block"
        )
        msg.sign(self.private_keys[0])
        
        # This should be accepted
        self.node._process_message(msg)
        
        # Check that prepare was sent (would happen in real execution)
        # We can't easily test this without running full protocol
    
    def test_primary_election(self):
        """Test round-robin primary election"""
        self.assertTrue(self.node._is_primary(0))  # Node 0 is primary for view 0
        self.assertFalse(self.node._is_primary(1))  # Node 1 is primary for view 1
        self.assertTrue(self.node._is_primary(4))  # Node 0 is primary for view 4
    
    def test_safe_value_determination(self):
        """Test Algorithm 4 safe value determination"""
        # Test with no lock
        safe_value = self.node._determine_safe_value(1)
        self.assertIsNone(safe_value)
        
        # Test with lock
        self.node.lock_round = 0
        self.node.lock_value = "locked"
        safe_value = self.node._determine_safe_value(1)
        self.assertEqual(safe_value, "locked")
    
    def test_external_validity(self):
        """Test external validity predicate"""
        # Default implementation accepts non-None values
        self.assertTrue(self.node._is_valid_value("valid"))
        self.assertTrue(self.node._is_valid_value(123))
        self.assertTrue(self.node._is_valid_value({"data": "block"}))
        self.assertFalse(self.node._is_valid_value(None))
    
    def test_message_serialization(self):
        """Test message serialization/deserialization"""
        original = IBFTMessage(
            msg_type=MessageType.PREPARE,
            view=1,
            sequence=2,
            sender=3,
            value={"block": "data", "transactions": ["tx1", "tx2"]},
            justification={"hash1", "hash2"}
        )
        
        # Convert to JSON and back
        json_str = original.to_json()
        restored = IBFTMessage.from_json(json_str)
        
        self.assertEqual(original.msg_type, restored.msg_type)
        self.assertEqual(original.view, restored.view)
        self.assertEqual(original.sequence, restored.sequence)
        self.assertEqual(original.sender, restored.sender)
        self.assertEqual(original.value, restored.value)
        self.assertEqual(original.justification, restored.justification)
    
    def test_consensus_properties(self):
        """Test basic consensus properties"""
        # For n=4, we can tolerate f=1 faulty nodes
        # Need 2f+1 = 3 matching messages for quorum
        self.assertEqual(self.node.f, 1)
        self.assertEqual(2 * self.node.f + 1, 3)
        
        # Total nodes should be at least 3f+1
        self.assertTrue(self.node.n >= 3 * self.node.f + 1)

class TestNetworkSimulator(unittest.TestCase):
    
    def test_network_delivery(self):
        """Test basic network message delivery"""
        # This would test the NetworkSimulator class
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)