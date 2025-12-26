"""
Configuration management with versioning and schema validation.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from ..logging_utils import get_context_logger
from ..errors import ConfigError

logger = get_context_logger(__name__)


@dataclass
class SignalMapping:
    """Mapping for a signal in byte parsing."""
    offset: int
    length: int
    scale: float = 1.0
    unit: Optional[str] = None


@dataclass
class SecondaryParseConfig:
    """Configuration for secondary parsing (aggregations, downsampling)."""
    plot_metrics: list = None  # e.g., ["speed_avg", "temp_max"]
    downsample: Dict[str, Any] = None  # e.g., {"method": "mean", "step": 10}
    
    def __post_init__(self):
        if self.plot_metrics is None:
            self.plot_metrics = []
        if self.downsample is None:
            self.downsample = {}


class ParseConfig:
    """Parsed and validated configuration for a parsing request."""
    
    SUPPORTED_VERSIONS = {"v1", "v2"}
    SUPPORTED_MODULES = {"MVB", "PHM"}
    SUPPORTED_PARSE_MODES = {"standard", "advanced"}
    
    def __init__(
        self,
        version: str,
        module: str,
        parser_version: str,
        byte_order: str,
        parse_mode: str,
        signal_map: Dict[str, Dict[str, Any]],
        second_parse: Optional[Dict[str, Any]] = None,
    ):
        self.version = version
        self.module = module
        self.parser_version = parser_version
        self.byte_order = byte_order
        self.parse_mode = parse_mode
        self.signal_map = signal_map
        self.second_parse = second_parse or {}
        
        # Validate
        self._validate()
    
    def _validate(self) -> None:
        """Validate configuration."""
        if self.version not in self.SUPPORTED_VERSIONS:
            raise ConfigError(
                f"Unsupported config version: {self.version}. Supported: {self.SUPPORTED_VERSIONS}"
            )
        
        if self.module not in self.SUPPORTED_MODULES:
            raise ConfigError(
                f"Unsupported module: {self.module}. Supported: {self.SUPPORTED_MODULES}"
            )
        
        if self.parse_mode not in self.SUPPORTED_PARSE_MODES:
            raise ConfigError(
                f"Unsupported parse mode: {self.parse_mode}. Supported: {self.SUPPORTED_PARSE_MODES}"
            )
        
        if self.byte_order not in {"little", "big"}:
            raise ConfigError(f"Invalid byte order: {self.byte_order}. Use 'little' or 'big'")
        
        if not isinstance(self.signal_map, dict):
            raise ConfigError("signal_map must be a dictionary")
        
        logger.info(f"Config validated: version={self.version}, module={self.module}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ParseConfig":
        """Create from dictionary."""
        try:
            return cls(
                version=config_dict.get("version"),
                module=config_dict.get("module"),
                parser_version=config_dict.get("parser_version"),
                byte_order=config_dict.get("byte_order"),
                parse_mode=config_dict.get("parse_mode", "standard"),
                signal_map=config_dict.get("signal_map", {}),
                second_parse=config_dict.get("second_parse"),
            )
        except Exception as e:
            raise ConfigError(f"Failed to parse config: {str(e)}")
    
    @classmethod
    def from_json_file(cls, filepath: str) -> "ParseConfig":
        """Load configuration from JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            logger.info(f"Loaded config from {filepath}")
            return cls.from_dict(config_dict)
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "version": self.version,
            "module": self.module,
            "parser_version": self.parser_version,
            "byte_order": self.byte_order,
            "parse_mode": self.parse_mode,
            "signal_map": self.signal_map,
            "second_parse": self.second_parse,
        }
    
    def __eq__(self, other) -> bool:
        """Check equality based on version and content."""
        if not isinstance(other, ParseConfig):
            return False
        return self.to_dict() == other.to_dict()
    
    def __hash__(self) -> int:
        """Hash based on version."""
        return hash(self.version)


class ConfigManager:
    """Manages versioned configurations."""
    
    def __init__(self, config_dir: str = "data"):
        self.config_dir = config_dir
        self._loaded_configs: Dict[str, ParseConfig] = {}
        self._load_lock = __import__("threading").Lock()
    
    def load_config(self, version: str, force_reload: bool = False) -> ParseConfig:
        """
        Load a configuration by version.
        
        Args:
            version: Config version (e.g., 'v1', 'v2')
            force_reload: Force reload from disk even if cached
        """
        if not force_reload and version in self._loaded_configs:
            return self._loaded_configs[version]
        
        with self._load_lock:
            # Double-check after lock
            if not force_reload and version in self._loaded_configs:
                return self._loaded_configs[version]
            
            filepath = os.path.join(self.config_dir, f"sample_config_{version}.json")
            config = ParseConfig.from_json_file(filepath)
            self._loaded_configs[version] = config
            logger.info(f"Loaded and cached config version: {version}")
            return config
    
    def get_config(self, version: str) -> ParseConfig:
        """Get a configuration (use cached version if available)."""
        return self.load_config(version, force_reload=False)
    
    def validate_config(self, config_dict: Dict[str, Any]) -> ParseConfig:
        """Validate a raw configuration dictionary."""
        return ParseConfig.from_dict(config_dict)
    
    def list_available_versions(self) -> list:
        """List available config versions in the config directory."""
        if not os.path.exists(self.config_dir):
            return []
        
        versions = []
        for filename in os.listdir(self.config_dir):
            if filename.startswith("sample_config_") and filename.endswith(".json"):
                version = filename.replace("sample_config_", "").replace(".json", "")
                versions.append(version)
        
        return sorted(versions)


# Global config manager instance
_global_config_manager = None


def get_config_manager(config_dir: str = "data") -> ConfigManager:
    """Get or create global config manager."""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_dir)
    return _global_config_manager
