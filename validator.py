# ibft/validator.py
"""
External Validity Predicates for IBFT
Implements the β predicate from the paper (Section 4.1)
"""

from typing import Any, List, Dict, Optional
import json
import hashlib

class IBFTValidator:
    """
    External validity validator for IBFT
    The β predicate ensures decided values are acceptable for the application
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.custom_validators = {}
        
        # Default validation rules
        self.min_block_size = self.config.get('min_block_size', 1)
        self.max_block_size = self.config.get('max_block_size', 10000)
        self.allowed_transaction_types = self.config.get('allowed_transaction_types', [])
        self.require_timestamp = self.config.get('require_timestamp', True)
        self.max_future_time = self.config.get('max_future_time', 300)  # 5 minutes
    
    def is_valid_value(self, value: Any) -> bool:
        """
        Main validation function - the β predicate from the paper
        Returns True if value is externally valid
        """
        if value is None:
            return False
        
        # Try different validation methods based on value type
        if isinstance(value, dict):
            return self._validate_block(value)
        elif isinstance(value, str):
            return self._validate_string(value)
        elif isinstance(value, list):
            return self._validate_transaction_list(value)
        elif hasattr(value, 'to_dict'):
            # Object with to_dict method
            return self._validate_block(value.to_dict())
        else:
            # For other types, use custom validator if registered
            value_type = type(value).__name__
            if value_type in self.custom_validators:
                return self.custom_validators[value_type](value)
            
            # Default: accept any non-None value
            return True
    
    def _validate_block(self, block: Dict) -> bool:
        """Validate a block structure"""
        required_fields = ['block_number', 'transactions', 'timestamp']
        
        # Check required fields
        for field in required_fields:
            if field not in block:
                print(f"Block missing required field: {field}")
                return False
        
        # Validate block number
        if not isinstance(block['block_number'], int) or block['block_number'] < 0:
            print(f"Invalid block number: {block['block_number']}")
            return False
        
        # Validate timestamp
        if self.require_timestamp:
            if not isinstance(block['timestamp'], (int, float)):
                print(f"Invalid timestamp: {block['timestamp']}")
                return False
            
            # Check if timestamp is too far in the future
            import time
            current_time = time.time()
            if block['timestamp'] > current_time + self.max_future_time:
                print(f"Timestamp too far in future: {block['timestamp']}")
                return False
        
        # Validate transactions
        if not isinstance(block['transactions'], list):
            print(f"Transactions must be a list, got {type(block['transactions'])}")
            return False
        
        # Check block size limits
        block_size = len(json.dumps(block))
        if block_size < self.min_block_size or block_size > self.max_block_size:
            print(f"Block size {block_size} outside limits [{self.min_block_size}, {self.max_block_size}]")
            return False
        
        # Validate each transaction
        for tx in block['transactions']:
            if not self._validate_transaction(tx):
                print(f"Invalid transaction: {tx}")
                return False
        
        # Check block hash if present
        if 'hash' in block:
            computed_hash = self._compute_block_hash(block)
            if block['hash'] != computed_hash:
                print(f"Block hash mismatch: {block['hash']} != {computed_hash}")
                return False
        
        return True
    
    def _validate_transaction(self, tx: Any) -> bool:
        """Validate a single transaction"""
        if not isinstance(tx, dict):
            return False
        
        required_fields = ['from', 'to', 'value']
        for field in required_fields:
            if field not in tx:
                return False
        
        # Check transaction type if restrictions exist
        if self.allowed_transaction_types:
            tx_type = tx.get('type', 'transfer')
            if tx_type not in self.allowed_transaction_types:
                return False
        
        # Validate addresses (simplified)
        if not self._is_valid_address(tx['from']):
            return False
        if not self._is_valid_address(tx['to']):
            return False
        
        # Validate value
        if not isinstance(tx['value'], (int, float)) or tx['value'] < 0:
            return False
        
        # Check signature if present
        if 'signature' in tx:
            # In real implementation, verify cryptographic signature
            if not self._verify_transaction_signature(tx):
                return False
        
        return True
    
    def _validate_string(self, value: str) -> bool:
        """Validate string value"""
        if not value or not isinstance(value, str):
            return False
        
        # Check length
        if len(value) > self.max_block_size:
            return False
        
        # Try to parse as JSON
        try:
            parsed = json.loads(value)
            return self.is_valid_value(parsed)
        except json.JSONDecodeError:
            # Not JSON, accept any non-empty string
            return len(value.strip()) > 0
    
    def _validate_transaction_list(self, transactions: List) -> bool:
        """Validate list of transactions"""
        if not isinstance(transactions, list):
            return False
        
        if len(transactions) == 0:
            # Empty transaction list is valid
            return True
        
        # Validate each transaction
        for tx in transactions:
            if not self._validate_transaction(tx):
                return False
        
        return True
    
    def _is_valid_address(self, address: str) -> bool:
        """Validate address format (simplified)"""
        if not isinstance(address, str):
            return False
        
        # Ethereum-like address (0x + 40 hex chars)
        if address.startswith('0x'):
            if len(address) != 42:
                return False
            try:
                int(address[2:], 16)
                return True
            except ValueError:
                return False
        
        # Generic address: alphanumeric, 1-64 chars
        return address.isalnum() and 1 <= len(address) <= 64
    
    def _verify_transaction_signature(self, tx: Dict) -> bool:
        """Verify transaction signature (simplified)"""
        # In real implementation, use proper cryptographic verification
        # For demo, just check that signature exists and has correct format
        signature = tx.get('signature', '')
        return isinstance(signature, str) and len(signature) > 0
    
    def _compute_block_hash(self, block: Dict) -> str:
        """Compute block hash (simplified)"""
        block_copy = block.copy()
        block_copy.pop('hash', None)
        block_str = json.dumps(block_copy, sort_keys=True)
        return hashlib.sha256(block_str.encode()).hexdigest()
    
    def register_custom_validator(self, value_type: str, validator_func):
        """
        Register custom validator for specific value type
        Args:
            value_type: Type name (e.g., 'Block', 'Transaction')
            validator_func: Function that takes value and returns bool
        """
        self.custom_validators[value_type] = validator_func
    
    def validate_consensus_properties(self, decided_values: Dict[int, Any]) -> Dict:
        """
        Validate consensus properties across multiple decisions
        Returns dict with validation results
        """
        results = {
            'total_decisions': len(decided_values),
            'valid_decisions': 0,
            'invalid_decisions': 0,
            'sequence_gaps': 0,
            'details': {}
        }
        
        sequences = sorted(decided_values.keys())
        
        # Check for sequence gaps
        for i in range(len(sequences) - 1):
            if sequences[i + 1] != sequences[i] + 1:
                results['sequence_gaps'] += 1
        
        # Validate each decision
        for seq, value in decided_values.items():
            is_valid = self.is_valid_value(value)
            results['details'][seq] = {
                'valid': is_valid,
                'value_type': type(value).__name__,
                'value_repr': str(value)[:100]  # First 100 chars
            }
            
            if is_valid:
                results['valid_decisions'] += 1
            else:
                results['invalid_decisions'] += 1
        
        return results