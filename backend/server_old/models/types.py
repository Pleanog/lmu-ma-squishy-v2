from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class HardwareMetadata:
    brightness: str = "normal"
    shaken: bool = False
    generated_by: Optional[str] = None

@dataclass
class MessageRecord:
    id: str
    collection_id: str
    conversation: str
    sender: str
    content: str
    audio: List[str] = field(default_factory=list) # PB sends list for multi-file
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_pb_record(cls, record):
        # Handle case where audio is single string or list
        raw_audio = getattr(record, 'audio', [])
        audio_list = [raw_audio] if isinstance(raw_audio, str) and raw_audio else raw_audio
        
        return cls(
            id=record.id,
            collection_id=record.collection_id,
            conversation=record.conversation,
            sender=record.sender,
            content=record.content,
            audio=audio_list,
            metadata=record.metadata or {}
        )