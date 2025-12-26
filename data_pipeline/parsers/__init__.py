"""
Bytecode parsers for MVB and PHM modules.
Supports streaming/chunked parsing to minimize memory peaks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator, Tuple
import struct
from io import BytesIO

from ..logging_utils import get_context_logger
from ..errors import ParsingError
from ..config import ParseConfig

logger = get_context_logger(__name__)


class BaseParser(ABC):
    """Abstract base for signal parsers."""
    
    def __init__(self, config: ParseConfig):
        self.config = config
        self.signal_map = config.signal_map
        self.byte_order = config.byte_order
        self.parse_mode = config.parse_mode
    
    @abstractmethod
    def parse(self, raw_data: bytes) -> Dict[str, Any]:
        """
        Parse raw bytes into domain signals.
        
        Returns dict: {signal_name: value}
        """
        pass
    
    @abstractmethod
    def parse_streaming(self, data_stream: BytesIO, chunk_size: int = 8192) -> Generator[Dict[str, Any], None, None]:
        """
        Parse streaming data in chunks.
        
        Yields dicts incrementally to minimize memory usage.
        """
        pass
    
    def _get_byte_order_char(self) -> str:
        """Get struct format char for byte order."""
        return "<" if self.byte_order == "little" else ">"
    
    def _unpack_value(self, data: bytes, offset: int, length: int, scale: float = 1.0) -> float:
        """
        Extract and unpack a value from bytes.
        
        Args:
            data: Raw bytes
            offset: Byte offset
            length: Number of bytes
            scale: Scale factor for the value
        """
        if offset + length > len(data):
            raise ParsingError(f"Offset {offset} + length {length} exceeds data size {len(data)}")
        
        byte_order = self._get_byte_order_char()
        
        try:
            if length == 2:
                fmt = f"{byte_order}H"  # unsigned short
                value = struct.unpack(fmt, data[offset:offset+2])[0]
            elif length == 4:
                fmt = f"{byte_order}I"  # unsigned int
                value = struct.unpack(fmt, data[offset:offset+4])[0]
            else:
                raise ParsingError(f"Unsupported length: {length}. Supported: 2, 4 bytes")
            
            return float(value) * scale
        except struct.error as e:
            raise ParsingError(f"Struct unpack failed: {str(e)}", context={"offset": offset, "length": length})


class MVBParser(BaseParser):
    """Parser for MVB (Multifunction Vehicle Bus) signal data."""
    
    def parse(self, raw_data: bytes) -> Dict[str, Any]:
        """Parse MVB bytecode into signal dict."""
        if not raw_data:
            raise ParsingError("Empty data provided to MVB parser")
        
        result = {}
        
        try:
            for signal_name, signal_config in self.signal_map.items():
                offset = signal_config.get("offset", 0)
                length = signal_config.get("length", 2)
                scale = signal_config.get("scale", 1.0)
                
                value = self._unpack_value(raw_data, offset, length, scale)
                result[signal_name] = value
        
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"MVB parsing failed: {str(e)}")
        
        logger.debug(f"Parsed MVB data: {len(result)} signals extracted")
        return result
    
    def parse_streaming(self, data_stream: BytesIO, chunk_size: int = 8192) -> Generator[Dict[str, Any], None, None]:
        """Stream parse MVB data."""
        while True:
            chunk = data_stream.read(chunk_size)
            if not chunk:
                break
            
            try:
                yield self.parse(chunk)
            except ParsingError as e:
                logger.error(f"Streaming parse error: {str(e)}")
                raise


class PHMParser(BaseParser):
    """Parser for PHM (Predictive Health Monitoring) signal data."""
    
    def parse(self, raw_data: bytes) -> Dict[str, Any]:
        """Parse PHM bytecode into signal dict."""
        if not raw_data:
            raise ParsingError("Empty data provided to PHM parser")
        
        result = {}
        
        try:
            for signal_name, signal_config in self.signal_map.items():
                offset = signal_config.get("offset", 0)
                length = signal_config.get("length", 2)
                scale = signal_config.get("scale", 1.0)
                
                value = self._unpack_value(raw_data, offset, length, scale)
                result[signal_name] = value
        
        except ParsingError:
            raise
        except Exception as e:
            raise ParsingError(f"PHM parsing failed: {str(e)}")
        
        logger.debug(f"Parsed PHM data: {len(result)} signals extracted")
        return result
    
    def parse_streaming(self, data_stream: BytesIO, chunk_size: int = 8192) -> Generator[Dict[str, Any], None, None]:
        """Stream parse PHM data."""
        while True:
            chunk = data_stream.read(chunk_size)
            if not chunk:
                break
            
            try:
                yield self.parse(chunk)
            except ParsingError as e:
                logger.error(f"Streaming parse error: {str(e)}")
                raise


class ParserFactory:
    """Factory to create appropriate parser for module."""
    
    _parsers: Dict[str, type] = {
        "MVB": MVBParser,
        "PHM": PHMParser,
    }
    
    @classmethod
    def create_parser(cls, module: str, config: ParseConfig) -> BaseParser:
        """
        Create a parser for the specified module.
        
        Args:
            module: Module name ('MVB' or 'PHM')
            config: ParseConfig instance
        
        Returns:
            Initialized parser instance
        """
        parser_class = cls._parsers.get(module)
        if not parser_class:
            raise ParsingError(f"Unsupported module: {module}. Supported: {list(cls._parsers.keys())}")
        
        logger.info(f"Created {module} parser with mode={config.parse_mode}")
        return parser_class(config)
    
    @classmethod
    def register_parser(cls, module: str, parser_class: type) -> None:
        """Register a custom parser for a module."""
        cls._parsers[module] = parser_class
        logger.info(f"Registered custom parser for {module}")


class SecondaryProcessor:
    """Process parsed signals for aggregations, filtering, downsampling."""
    
    @staticmethod
    def compute_metrics(
        signals: List[Dict[str, Any]],
        metric_names: List[str],
    ) -> Dict[str, Any]:
        """
        Compute secondary metrics from signal list.
        
        Args:
            signals: List of parsed signal dicts
            metric_names: List of metrics to compute (e.g., ['speed_avg', 'temp_max'])
        
        Returns:
            Dict of computed metrics
        """
        if not signals:
            return {}
        
        result = {}
        
        for metric_name in metric_names:
            if metric_name.endswith("_avg"):
                signal_key = metric_name.replace("_avg", "")
                values = [s.get(signal_key) for s in signals if signal_key in s]
                if values:
                    result[metric_name] = sum(values) / len(values)
            
            elif metric_name.endswith("_max"):
                signal_key = metric_name.replace("_max", "")
                values = [s.get(signal_key) for s in signals if signal_key in s]
                if values:
                    result[metric_name] = max(values)
            
            elif metric_name.endswith("_min"):
                signal_key = metric_name.replace("_min", "")
                values = [s.get(signal_key) for s in signals if signal_key in s]
                if values:
                    result[metric_name] = min(values)
        
        return result
    
    @staticmethod
    def downsample(
        signals: List[Dict[str, Any]],
        method: str = "mean",
        step: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Downsample signals using specified method.
        
        Args:
            signals: List of signal dicts
            method: Aggregation method ('mean', 'first', 'last')
            step: Downsample step (keep every Nth sample)
        
        Returns:
            Downsampled signal list
        """
        if step <= 1:
            return signals
        
        result = []
        
        for i in range(0, len(signals), step):
            chunk = signals[i:i+step]
            
            if method == "mean":
                agg = {}
                for key in chunk[0].keys():
                    values = [s.get(key) for s in chunk if key in s]
                    if values and all(isinstance(v, (int, float)) for v in values):
                        agg[key] = sum(values) / len(values)
                    else:
                        agg[key] = chunk[0].get(key)
                result.append(agg)
            
            elif method == "first":
                result.append(chunk[0])
            
            elif method == "last":
                result.append(chunk[-1])
        
        logger.debug(f"Downsampled {len(signals)} signals to {len(result)} using {method}")
        return result
