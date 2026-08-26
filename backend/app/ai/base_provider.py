from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAIProvider(ABC):
    @abstractmethod
    def generate_chat_response(self, prompt: str, system_message: str) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def explain_schedule_decision(self, interview_data: Dict[str, Any]) -> str:
        """Generate human-readable explanation of deterministic scheduling decision."""
        pass
