# crypto.py
import hashlib
import json
from typing import Tuple
import base64

# Simplified cryptography for demonstration
# In production, use proper cryptographic libraries like cryptography

class SimpleCrypto:
    """Simple cryptographic functions for demonstration"""
    
    @staticmethod
    def generate_keypair():
        """Generate a simple keypair"""
        import os
        private_key = os.urandom(32).hex()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        return private_key, public_key
    
    @staticmethod
    def sign(private_key: str, message: str) -> str:
        """Sign a message"""
        # Simple hash-based signature for demonstration
        combined = private_key + message
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def verify_signature(public_key: str, message: str, signature: str) -> bool:
        """Verify a signature"""
        # In real implementation, this would use proper crypto
        # For demo, we'll simulate by checking if signature matches expected pattern
        expected = hashlib.sha256(("dummy" + message).encode()).hexdigest()
        return signature.startswith(expected[:16])  # Simplified check

# Use these functions
sign = SimpleCrypto.sign
verify_signature = SimpleCrypto.verify_signature
generate_keypair = SimpleCrypto.generate_keypair