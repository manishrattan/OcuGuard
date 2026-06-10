from abc import ABC, abstractmethod
from typing import Dict, Any

class OcuGuardSubAgentPlugin(ABC):
    """
    Official Open-Source Plugin Interface for OcuGuard Sub-Agents.
    Inherit from this base class to add custom ophthalmic condition evaluations.
    """
    
    @property
    @abstractmethod
    def condition_id(self) -> str:
        """Returns the unique tracking string for the eye condition (e.g., 'NYSTAGMUS_STABILIZER')"""
        pass

    @abstractmethod
    def validate_safety_envelope(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes localized mathematical parameter checks.
        Returns a standardized dictionary containing:
        - 'status': 'SAFE' or 'VIOLATION'
        - 'pan_localization': float (-1.0 to 1.0)
        - 'tts_prompt': str (Actionable audio direction)
        """
        pass
