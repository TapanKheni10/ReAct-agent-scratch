from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class Interaction:
    """Record of a single interaction with the agent"""
    timestamp: datetime
    query: str
    plan: Dict[str, Any]
    reflection_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.reflection_history is None:
            self.reflection_history = []