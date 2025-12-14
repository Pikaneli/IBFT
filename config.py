# ibft/config.py
"""
Configuration management for IBFT implementation
"""

import yaml
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

class NetworkMode(Enum):
    """Network communication modes"""
    SYNCHRONOUS = "synchronous"
    PARTIALLY_SYNCHRONOUS = "partially_synchronous"
    ASYNCHRONOUS = "asynchronous"

class FaultModel(Enum):
    """Byzantine fault models"""
    CRASH_ONLY = "crash_only"
    BYZANTINE = "byzantine"
    BENIGN = "benign"

@dataclass
class NodeConfig:
    """Configuration for a single node"""
    node_id: int
    host: str = "localhost"
    port: int = 8000
    public_key: str = ""
    is_byzantine: bool = False
    byzantine_behavior: Optional[str] = None  # 'equivocate', 'delay', 'drop'
    network_delay: float = 0.0  # seconds
    message_loss_rate: float = 0.0  # 0.0 to 1.0

@dataclass
class ConsensusConfig:
    """Consensus algorithm configuration"""
    total_nodes: int = 4
    fault_tolerance: int = 1  # f
    timeout_ms: int = 10000  # View change timeout
    max_rounds: int = 100
    batch_size: int = 100  # Transactions per block
    block_time_ms: int = 5000  # Target block time
    
    # Derived property
    @property
    def quorum_size(self) -> int:
        """Calculate quorum size: 2f + 1"""
        return 2 * self.fault_tolerance + 1
    
    @property
    def required_nodes(self) -> int:
        """Minimum nodes required: 3f + 1"""
        return 3 * self.fault_tolerance + 1

@dataclass
class NetworkConfig:
    """Network configuration"""
    mode: NetworkMode = NetworkMode.PARTIALLY_SYNCHRONOUS
    max_message_delay_ms: int = 1000
    min_message_delay_ms: int = 10
    message_size_limit: int = 10 * 1024 * 1024  # 10MB
    enable_compression: bool = True
    enable_encryption: bool = False

@dataclass
class ValidationConfig:
    """Validation configuration"""
    min_block_size: int = 1
    max_block_size: int = 10 * 1024 * 1024  # 10MB
    require_transaction_signatures: bool = True
    max_transactions_per_block: int = 1000
    allowed_transaction_types: List[str] = field(default_factory=lambda: [
        "transfer", "contract_deploy", "contract_call"
    ])
    gas_limit: int = 8000000
    require_timestamp: bool = True
    max_future_time_seconds: int = 300  # 5 minutes

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    file: Optional[str] = "ibft.log"
    console: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_file_size_mb: int = 100
    backup_count: int = 5

@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_tracing: bool = False
    trace_sample_rate: float = 0.1
    health_check_interval: int = 30  # seconds

@dataclass
class IBFTConfig:
    """Complete IBFT configuration"""
    consensus: ConsensusConfig = field(default_factory=ConsensusConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    nodes: List[NodeConfig] = field(default_factory=list)
    
    # Runtime settings
    test_mode: bool = False
    fault_injection: bool = False
    random_seed: Optional[int] = None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check total nodes vs fault tolerance
        if self.consensus.total_nodes < self.consensus.required_nodes:
            errors.append(
                f"Total nodes ({self.consensus.total_nodes}) < required "
                f"({self.consensus.required_nodes}) for f={self.consensus.fault_tolerance}"
            )
        
        # Check node configurations
        if len(self.nodes) != self.consensus.total_nodes:
            errors.append(
                f"Number of node