from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseParser(ABC):
    @abstractmethod
    def parse_primary(self, data: bytes, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse binary data to domain signals."""
        pass

    @abstractmethod
    def parse_secondary(self, primary_data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Compute secondary metrics or transforms."""
        pass