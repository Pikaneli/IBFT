# messages.py
from dataclasses import dataclass, field
from typing import Any, Optional, Set, Dict, List
from enum import Enum
import json
import hashlib
from time import time
from crypto import sign, verify_signature

class MessageType(Enum):
    PREPREPARE = "PREPREPARE"
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    ROUND_CHANGE = "ROUND_CHANGE"
    NEW_ROUND = "NEW_ROUND"

@dataclass
class IBFTMessage:
    """Complete IBFT message implementation with signatures"""
    msg_type: MessageType
    view: int
    sequence: int
    sender: int
    value: Optional[Any] = None
    justification: Optional[Set[str]] = field(default_factory=set)  # Message digests
    signature: Optional[str] = None
    timestamp: float = field(default_factory=time)
    
    def __post_init__(self):
        if self.justification and isinstance(self.justification, set):
            self.justification = {str(digest) for digest in self.justification}
    
    def to_dict(self):
        """Convert message to dictionary for serialization"""
        return {
            'type': self.msg_type.value,
            'view': self.view,
            'sequence': self.sequence,
            'sender': self.sender,
            'value': self.value,
            'justification': list(self.justification) if self.justification else [],
            'timestamp': self.timestamp,
            'signature': self.signature
        }
    
    def to_json(self):
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    def hash(self):
        """Create hash of message (excluding signature)"""
        data = self.to_dict().copy()
        data.pop('signature', None)
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def sign(self, private_key):
        """Sign the message"""
        message_hash = self.hash()
        self.signature = sign(private_key, message_hash)
        return self.signature
    
    def verify(self, public_key):
        """Verify message signature"""
        if not self.signature:
            return False
        message_hash = self.hash()
        return verify_signature(public_key, message_hash, self.signature)
    
    @classmethod
    def from_json(cls, json_str):
        """Deserialize from JSON"""
        data = json.loads(json_str)
        data['type'] = MessageType(data['type'])
        return cls(**data)