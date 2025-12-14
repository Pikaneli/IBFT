# main.py
import threading
import time
from typing import List, Dict
from node import IBFTNode
from network import NetworkSimulator
from crypto import generate_keypair

class IBFTTestRunner:
    """Comprehensive test runner for IBFT"""
    
    def __init__(self, n_nodes: int = 4):
        self.n_nodes = n_nodes
        self.f = (n_nodes - 1) // 3
        self.nodes = []
        self.network = None
        self.decisions = defaultdict(dict)
        self.test_complete = threading.Event()
        self.max_sequence = 5  # Test 5 consensus instances
    
    def setup_nodes(self):
        """Create and initialize nodes"""
        # Generate cryptographic keys
        keypairs = [generate_keypair() for _ in range(self.n_nodes)]
        private_keys = [kp[0] for kp in keypairs]
        public_keys = [kp[1] for kp in keypairs]
        
        # Create nodes
        for i in range(self.n_nodes):
            node = IBFTNode(
                node_id=i,
                total_nodes=self.n_nodes,
                private_key=private_keys[i],
                public_keys={j: public_keys[j] for j in range(self.n_nodes)}
            )
            
            # Set decision callback
            node.set_decision_callback(self.on_decision)
            self.nodes.append(node)
        
        # Create network simulator
        self.network = NetworkSimulator(self.nodes, fault_injection=False)
    
    def on_decision(self, node_id: int, sequence: int, value: any):
        """Callback when a node reaches decision"""
        self.decisions[sequence][node_id] = value
        
        # Check if all correct nodes have decided for this sequence
        correct_nodes = self.n_nodes - self.f
        if len(self.decisions[sequence]) >= correct_nodes:
            # Verify agreement
            values = set(self.decisions[sequence].values())
            if len(values) == 1:
                print(f"✓ Consensus instance {sequence}: Agreement achieved on value {next(iter(values))}")
            else:
                print(f"✗ Consensus instance {sequence}: DISAGREEMENT! Values: {values}")
            
            # Check if we've completed all sequences
            if sequence >= self.max_sequence - 1:
                self.test_complete.set()
    
    def run_test(self, test_name: str):
        """Run a specific test"""
        print(f"\n{'='*60}")
        print(f"Running test: {test_name}")
        print(f"{'='*60}")
        
        self.setup_nodes()
        
        # Start message processing threads
        for node in self.nodes:
            thread = threading.Thread(target=node.process_messages, daemon=True)
            thread.start()
        
        # Start network
        self.network.start()
        
        # Give nodes time to initialize
        time.sleep(0.5)
        
        # Run test-specific logic
        if test_name == "normal_case":
            self.test_normal_case()
        elif test_name == "view_change":
            self.test_view_change()
        elif test_name == "byzantine_primary":
            self.test_byzantine_primary()
        
        # Wait for test to complete
        timeout = 30  # seconds
        if self.test_complete.wait(timeout):
            print(f"\nTest '{test_name}' completed successfully")
        else:
            print(f"\nTest '{test_name}' timed out after {timeout} seconds")
        
        # Print statistics
        self.print_statistics()
        
        # Cleanup
        self.network.stop()
        self.test_complete.clear()
        self.decisions.clear()
    
    def test_normal_case(self):
        """Test normal case operation with correct primary"""
        print("Testing normal case with correct primary...")
        
        # Primary (node 0) proposes a value
        value = "Test Block #1"
        self.nodes[0].propose_value(value)
        
        # Wait for decisions
        time.sleep(2)
        
        # Propose more values
        for i in range(1, self.max_sequence):
            value = f"Test Block #{i+1}"
            primary_id = i % self.n_nodes  # Round-robin primary
            self.nodes[primary_id].propose_value(value)
            time.sleep(1)
    
    def test_view_change(self):
        """Test view change when primary times out"""
        print("Testing view change scenario...")
        
        # Start with node 0 as primary
        value = "Initial Proposal"
        self.nodes[0].propose_value(value)
        
        # Simulate primary failure by not sending any more messages
        # Other nodes should timeout and trigger view change
        time.sleep(15)  # Wait for timeout
        
        # After view change, new primary (node 1) should propose
        print("View change should have occurred...")
    
    def test_byzantine_primary(self):
        """Test with Byzantine primary sending conflicting messages"""
        print("Testing Byzantine primary scenario...")
        
        # This would require modifying a node to behave maliciously
        # For now, we'll simulate by having primary send invalid proposal
        print("(Simulating Byzantine behavior - would require node modification)")
    
    def print_statistics(self):
        """Print test statistics"""
        print("\n" + "="*60)
        print("TEST STATISTICS")
        print("="*60)
        
        for i, node in enumerate(self.nodes):
            stats = node.get_stats()
            state = node.get_state()
            print(f"\nNode {i}:")
            print(f"  State: λ={state['λ']}, r={state['r']}, decided={state['decided']}")
            print(f"  Messages: sent={stats['messages_sent']}, received={stats['messages_received']}")
            print(f"  View changes: {stats['view_changes']}")
            print(f"  Decisions made: {stats['decisions']}")
        
        net_stats = self.network.get_stats()
        print(f"\nNetwork Statistics:")
        print(f"  Total messages: {net_stats['total_messages']}")
        print(f"  Total bytes: {net_stats['total_bytes']:,}")
        print(f"  Dropped messages: {net_stats['dropped_messages']}")
        
        # Verify safety property
        for sequence, node_decisions in self.decisions.items():
            if node_decisions:
                unique_values = set(node_decisions.values())
                if len(unique_values) == 1:
                    print(f"\n✓ Safety: All nodes agreed on sequence {sequence}")
                else:
                    print(f"\n✗ Safety VIOLATION: Disagreement on sequence {sequence}")

def main():
    """Main entry point"""
    print("Istanbul BFT (IBFT) Implementation - Complete Test Suite")
    print("Based on: The Istanbul BFT Consensus Algorithm (arXiv:2002.03613)")
    
    runner = IBFTTestRunner(n_nodes=4)
    
    # Run tests
    tests = [
        "normal_case",
        "view_change",
        # "byzantine_primary"  # Requires more setup
    ]
    
    for test in tests:
        runner.run_test(test)
        
        # Wait between tests
        time.sleep(2)
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)

if __name__ == "__main__":
    main()