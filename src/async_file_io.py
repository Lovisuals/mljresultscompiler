# -*- coding: utf-8 -*-
"""
Async File I/O - Non-blocking file operations
Provides async wrappers for Excel reading/writing and file operations.
Prevents event loop blocking from I/O operations.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="io_async_")


class AsyncFileIO:
    """
    Non-blocking file I/O wrapper.
    
    Provides async methods for Excel, CSV, and binary file operations.
    Runs I/O in thread pool to prevent event loop blocking.
    """
    
    def __init__(self):
        self.io_timeout = 30.0  # I/O operation timeout
        logger.info("✓ AsyncFileIO initialized")
    
    async def read_excel_async(
        self,
        file_path: str,
        sheet_name: Optional[int | str] = None,
        timeout: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Read Excel file asynchronously.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet to read (default: first sheet)
            timeout: I/O timeout in seconds
            
        Returns:
            DataFrame with file contents
            
        Raises:
            FileNotFoundError: If file doesn't exist
            asyncio.TimeoutError: If operation exceeds timeout
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            df = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._read_excel_sync,
                    file_path,
                    sheet_name
                ),
                timeout=timeout
            )
            logger.debug(f"Read Excel: {file_path} ({len(df)} rows)")
            return df
        except asyncio.TimeoutError:
            logger.error(f"Excel read timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Excel read failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _read_excel_sync(file_path: str, sheet_name: Optional[int | str] = None) -> pd.DataFrame:
        """Synchronous Excel read"""
        return pd.read_excel(file_path, sheet_name=sheet_name)
    
    async def write_excel_async(
        self,
        df: pd.DataFrame,
        file_path: str,
        sheet_name: str = "Sheet1",
        timeout: Optional[float] = None
    ) -> str:
        """
        Write DataFrame to Excel file asynchronously.
        
        Args:
            df: DataFrame to write
            file_path: Output file path
            sheet_name: Sheet name
            timeout: I/O timeout in seconds
            
        Returns:
            Path to written file
            
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._write_excel_sync,
                    df,
                    file_path,
                    sheet_name
                ),
                timeout=timeout
            )
            logger.debug(f"Wrote Excel: {file_path} ({len(df)} rows)")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Excel write timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Excel write failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _write_excel_sync(df: pd.DataFrame, file_path: str, sheet_name: str) -> str:
        """Synchronous Excel write"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(file_path, sheet_name=sheet_name, index=False)
        return file_path
    
    async def read_csv_async(
        self,
        file_path: str,
        timeout: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Read CSV file asynchronously.
        
        Args:
            file_path: Path to CSV file
            timeout: I/O timeout in seconds
            
        Returns:
            DataFrame with file contents
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            df = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    pd.read_csv,
                    file_path
                ),
                timeout=timeout
            )
            logger.debug(f"Read CSV: {file_path} ({len(df)} rows)")
            return df
        except asyncio.TimeoutError:
            logger.error(f"CSV read timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"CSV read failed: {file_path}: {e}")
            raise
    
    async def write_csv_async(
        self,
        df: pd.DataFrame,
        file_path: str,
        timeout: Optional[float] = None
    ) -> str:
        """
        Write DataFrame to CSV file asynchronously.
        
        Args:
            df: DataFrame to write
            file_path: Output file path
            timeout: I/O timeout in seconds
            
        Returns:
            Path to written file
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._write_csv_sync,
                    df,
                    file_path
                ),
                timeout=timeout
            )
            logger.debug(f"Wrote CSV: {file_path} ({len(df)} rows)")
            return result
        except asyncio.TimeoutError:
            logger.error(f"CSV write timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"CSV write failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _write_csv_sync(df: pd.DataFrame, file_path: str) -> str:
        """Synchronous CSV write"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(file_path, index=False)
        return file_path
    
    async def read_file_async(
        self,
        file_path: str,
        encoding: str = "utf-8",
        timeout: Optional[float] = None
    ) -> str:
        """
        Read text file asynchronously.
        
        Args:
            file_path: Path to file
            encoding: File encoding
            timeout: I/O timeout in seconds
            
        Returns:
            File contents as string
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._read_file_sync,
                    file_path,
                    encoding
                ),
                timeout=timeout
            )
            logger.debug(f"Read file: {file_path}")
            return content
        except asyncio.TimeoutError:
            logger.error(f"File read timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"File read failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _read_file_sync(file_path: str, encoding: str) -> str:
        """Synchronous file read"""
        return Path(file_path).read_text(encoding=encoding)
    
    async def write_file_async(
        self,
        content: str,
        file_path: str,
        encoding: str = "utf-8",
        timeout: Optional[float] = None
    ) -> str:
        """
        Write text file asynchronously.
        
        Args:
            content: File content
            file_path: Output file path
            encoding: File encoding
            timeout: I/O timeout in seconds
            
        Returns:
            Path to written file
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._write_file_sync,
                    content,
                    file_path,
                    encoding
                ),
                timeout=timeout
            )
            logger.debug(f"Wrote file: {file_path}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"File write timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"File write failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _write_file_sync(content: str, file_path: str, encoding: str) -> str:
        """Synchronous file write"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return file_path
    
    async def delete_file_async(
        self,
        file_path: str,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Delete file asynchronously.
        
        Args:
            file_path: Path to file
            timeout: I/O timeout in seconds
            
        Returns:
            True if deleted, False if not found
        """
        timeout = timeout or self.io_timeout
        
        try:
            loop = asyncio.get_event_loop()
            success = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._delete_file_sync,
                    file_path
                ),
                timeout=timeout
            )
            if success:
                logger.debug(f"Deleted file: {file_path}")
            return success
        except asyncio.TimeoutError:
            logger.error(f"File delete timeout: {file_path}")
            raise
        except Exception as e:
            logger.error(f"File delete failed: {file_path}: {e}")
            raise
    
    @staticmethod
    def _delete_file_sync(file_path: str) -> bool:
        """Synchronous file delete"""
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False


# Global async file I/O instance
_async_file_io: Optional[AsyncFileIO] = None


def get_async_file_io() -> AsyncFileIO:
    """Get or create global async file I/O"""
    global _async_file_io
    if _async_file_io is None:
        _async_file_io = AsyncFileIO()
    return _async_file_io


async def initialize_async_file_io():
    """Initialize async file I/O"""
    global _async_file_io
    _async_file_io = get_async_file_io()
    logger.info("✓ Async file I/O ready")


async def shutdown_async_file_io():
    """Shutdown async file I/O and cleanup executor"""
    global _async_file_io
    _executor.shutdown(wait=True)
    _async_file_io = None
    logger.info("✓ Async file I/O shutdown")
