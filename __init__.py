# ibft/__init__.py
"""
Istanbul BFT Consensus Algorithm Implementation
Based on: The Istanbul BFT Consensus Algorithm (arXiv:2002.03613)

This package implements the IBFT consensus algorithm with:
- Three-phase commit (PREPREPARE, PREPARE, COMMIT)
- View change protocol for leader rotation
- Byzantine fault tolerance (n ≥ 3f + 1)
- External validity predicates
- Quadratic message complexity O(n²)
"""

__version__ = "1.0.0"
__author__ = "IBFT Implementation Team"

from .node import IBFTNode
from .messages import IBFTMessage, MessageType
from .consensus import IBFTConsensus
from .view_change import IBFTViewChange
from .validator import IBFTValidator
from .network import NetworkSimulator
from .crypto import generate_keypair, sign, verify_signature

__all__ = [
    'IBFTNode',
    'IBFTMessage',
    'MessageType',
    'IBFTConsensus',
    'IBFTViewChange',
    'IBFTValidator',
    'NetworkSimulator',
    'generate_keypair',
    'sign',
    'verify_signature',
]