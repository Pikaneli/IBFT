from dataclasses import dataclass
from typing import Any, Optional, Set
from enum import Enum

class MessageType(Enum):
    PREPREPARE = "PREPREPARE"
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    ROUND_CHANGE = "ROUND_CHANGE"
    NEW_ROUND = "NEW_ROUND"
    
@dataclass
class IBFTMessage:
    msg_type: MessageType
    view: int  #Trenutni broj pogleda/runde
    sequence: int  #Consensus instanca ili lambda
    sender: int  #Proces pi
    value: Optional[Any] = None  #Vrednost 
    justification: Optional[Set['IBFTMessage']] = None  #Skup poruka koje opravdavaju ovu poruku
    signature: Optional[str] = None  #Digitalni potpis poruke