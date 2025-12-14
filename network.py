# network.py
import threading
import queue
import pickle
import time
import random
from typing import Dict, List, Callable, Optional

class NetworkSimulator:
    """Simulated network for testing IBFT"""
    
    def __init__(self, nodes: List, fault_injection: bool = False):
        self.nodes = nodes
        self.fault_injection = fault_injection
        self.message_queues = [queue.Queue() for _ in nodes]
        self.delivery_threads = []
        self.running = False
        self.message_history = []
        self.delays = defaultdict(float)  # (sender, receiver) -> delay
        self.dropped_messages = set()  # For fault injection
        
        # Setup node callbacks
        for i, node in enumerate(nodes):
            node.set_network_callback(lambda msg, target=i: self.send(i, target, msg))
    
    def send(self, sender_id: int, receiver_id: int, message_bytes: bytes):
        """Send message from sender to receiver"""
        if not self.running:
            return
        
        # Simulate network faults
        if self.fault_injection:
            # Randomly drop messages (10% chance)
            if random.random() < 0.1:
                self.dropped_messages.add(hash(message_bytes))
                return
            
            # Random delay (0-100ms)
            delay = random.uniform(0, 0.1)
            key = (sender_id, receiver_id)
            if key in self.delays:
                delay = self.delays[key]
        
        # Queue message for delivery
        delivery_time = time.time() + delay
        self.message_queues[receiver_id].put((delivery_time, sender_id, message_bytes))
        self.message_history.append((time.time(), sender_id, receiver_id, len(message_bytes)))
    
    def _delivery_worker(self, node_id: int):
        """Worker thread for delivering messages to a node"""
        while self.running:
            try:
                delivery_time, sender_id, message_bytes = self.message_queues[node_id].get(timeout=0.1)
                
                # Wait until delivery time
                current_time = time.time()
                if current_time < delivery_time:
                    time.sleep(delivery_time - current_time)
                
                # Deliver message
                try:
                    message = pickle.loads(message_bytes)
                    self.nodes[node_id].receive_message(message)
                except Exception as e:
                    print(f"Delivery error to node {node_id}: {e}")
                
                self.message_queues[node_id].task_done()
                
            except queue.Empty:
                continue
    
    def start(self):
        """Start the network simulator"""
        self.running = True
        
        # Start delivery threads for each node
        for i in range(len(self.nodes)):
            thread = threading.Thread(target=self._delivery_worker, args=(i,), daemon=True)
            thread.start()
            self.delivery_threads.append(thread)
    
    def stop(self):
        """Stop the network simulator"""
        self.running = False
        for thread in self.delivery_threads:
            thread.join(timeout=1)
    
    def set_delay(self, sender: int, receiver: int, delay: float):
        """Set fixed delay for messages between nodes"""
        self.delays[(sender, receiver)] = delay
    
    def get_stats(self):
        """Get network statistics"""
        total_messages = len(self.message_history)
        total_bytes = sum(msg[3] for msg in self.message_history)
        
        return {
            'total_messages': total_messages,
            'total_bytes': total_bytes,
            'dropped_messages': len(self.dropped_messages),
            'active_deliveries': sum(q.qsize() for q in self.message_queues)
        }