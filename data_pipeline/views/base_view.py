from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseView(ABC):
    @abstractmethod
    def parse(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def plot(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def download(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass