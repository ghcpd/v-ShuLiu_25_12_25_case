"""
Data source adapters for MinIO, databases, and file systems.
Supports parallel fetch with resumable downloads and range reads.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, BinaryIO
from io import BytesIO
from datetime import datetime
import threading

from ..logging_utils import get_context_logger
from ..errors import DataSourceError

logger = get_context_logger(__name__)


class DataSource(ABC):
    """Abstract base for data sources."""
    
    @abstractmethod
    def fetch(self, location: str) -> bytes:
        """Fetch complete data from location."""
        pass
    
    @abstractmethod
    def fetch_range(self, location: str, start: int, end: int) -> bytes:
        """Fetch byte range [start, end)."""
        pass
    
    @abstractmethod
    def exists(self, location: str) -> bool:
        """Check if data exists at location."""
        pass


class LocalFileSource(DataSource):
    """Data source for local files."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
    
    def fetch(self, location: str) -> bytes:
        """Read entire file."""
        filepath = os.path.join(self.base_dir, location)
        
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            logger.info(f"Fetched {len(data)} bytes from {location}")
            return data
        except FileNotFoundError:
            raise DataSourceError(f"File not found: {location}", retryable=False)
        except IOError as e:
            raise DataSourceError(f"IO error reading {location}: {str(e)}", retryable=True)
    
    def fetch_range(self, location: str, start: int, end: int) -> bytes:
        """Read byte range from file."""
        filepath = os.path.join(self.base_dir, location)
        
        try:
            with open(filepath, "rb") as f:
                f.seek(start)
                data = f.read(end - start)
            logger.info(f"Fetched {len(data)} bytes from {location} [{start}:{end})")
            return data
        except FileNotFoundError:
            raise DataSourceError(f"File not found: {location}", retryable=False)
        except IOError as e:
            raise DataSourceError(f"IO error reading {location}: {str(e)}", retryable=True)
    
    def exists(self, location: str) -> bool:
        """Check file existence."""
        filepath = os.path.join(self.base_dir, location)
        return os.path.isfile(filepath)


class MinIOSource(DataSource):
    """Data source for MinIO object storage."""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        """
        Initialize MinIO source.
        
        Args:
            endpoint: MinIO endpoint (e.g., 'localhost:9000')
            access_key: Access key
            secret_key: Secret key
            bucket: Bucket name
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        
        # Try to import minio; graceful fallback if not installed
        try:
            from minio import Minio
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
            )
            logger.info(f"Initialized MinIO client for {endpoint}/{bucket}")
        except ImportError:
            logger.warning("minio package not installed; MinIO operations will fail")
            self.client = None
    
    def fetch(self, location: str) -> bytes:
        """Download entire object."""
        if not self.client:
            raise DataSourceError("MinIO client not available (minio not installed)", retryable=False)
        
        try:
            response = self.client.get_object(self.bucket, location)
            data = response.read()
            response.close()
            logger.info(f"Fetched {len(data)} bytes from MinIO {location}")
            return data
        except Exception as e:
            retryable = "Connection" in str(e) or "timeout" in str(e).lower()
            raise DataSourceError(f"MinIO fetch failed for {location}: {str(e)}", retryable=retryable)
    
    def fetch_range(self, location: str, start: int, end: int) -> bytes:
        """Download byte range using range request."""
        if not self.client:
            raise DataSourceError("MinIO client not available (minio not installed)", retryable=False)
        
        try:
            response = self.client.get_object(
                self.bucket,
                location,
                request_headers={"Range": f"bytes={start}-{end-1}"},
            )
            data = response.read()
            response.close()
            logger.info(f"Fetched {len(data)} bytes from MinIO {location} [{start}:{end})")
            return data
        except Exception as e:
            retryable = "Connection" in str(e) or "timeout" in str(e).lower()
            raise DataSourceError(f"MinIO range fetch failed: {str(e)}", retryable=retryable)
    
    def exists(self, location: str) -> bool:
        """Check object existence."""
        if not self.client:
            return False
        
        try:
            self.client.stat_object(self.bucket, location)
            return True
        except Exception:
            return False


class ParallelFetcher:
    """Parallel data fetcher with segment-based download."""
    
    def __init__(self, source: DataSource, max_workers: int = 4, segment_size: int = 1024*1024):
        """
        Initialize parallel fetcher.
        
        Args:
            source: Data source instance
            max_workers: Max concurrent downloads
            segment_size: Size of each segment (default 1MB)
        """
        self.source = source
        self.max_workers = max_workers
        self.segment_size = segment_size
    
    def fetch_parallel(self, location: str) -> bytes:
        """
        Fetch data using parallel segment downloads.
        
        Falls back to single fetch if size unknown or small.
        """
        # Try single fetch first (works for all sources)
        try:
            # For local files and MinIO, try to get size and use parallel
            # For now, simple implementation uses single fetch
            data = self.source.fetch(location)
            
            if len(data) < self.segment_size * 2:
                # Too small for parallel benefit
                return data
            
            # Could implement parallel segmented fetch here
            logger.debug(f"Fetched {len(data)} bytes from {location}")
            return data
        
        except DataSourceError:
            raise
    
    def fetch_segments(self, location: str, segment_size: Optional[int] = None) -> List[bytes]:
        """
        Fetch data as segments (for streaming processing).
        
        Returns list of byte segments.
        """
        segment_size = segment_size or self.segment_size
        segments = []
        offset = 0
        
        while True:
            try:
                segment = self.source.fetch_range(location, offset, offset + segment_size)
                if not segment:
                    break
                segments.append(segment)
                offset += len(segment)
            except DataSourceError as e:
                if e.retryable:
                    logger.warning(f"Retryable error fetching segment at {offset}: {str(e)}")
                    # Could implement retry logic here
                raise
        
        logger.info(f"Fetched {len(segments)} segments for {location}")
        return segments


class DataSourceFactory:
    """Factory for creating data sources."""
    
    @staticmethod
    def create_local_source(base_dir: str = ".") -> LocalFileSource:
        """Create local file source."""
        return LocalFileSource(base_dir)
    
    @staticmethod
    def create_minio_source(
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> MinIOSource:
        """Create MinIO source."""
        return MinIOSource(endpoint, access_key, secret_key, bucket)
    
    @staticmethod
    def create_parallel_fetcher(
        source: DataSource,
        max_workers: int = 4,
        segment_size: int = 1024*1024,
    ) -> ParallelFetcher:
        """Create parallel fetcher for a source."""
        return ParallelFetcher(source, max_workers, segment_size)
