"""
Universal Data Source Integration Engine
Fetches data from any remote source: APIs, websites, webhooks, databases
Lightweight, async-first, high-performance
"""

import aiohttp
import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class DataSource:
    """Universal data source configuration"""
    source_id: str
    source_type: str  # 'api', 'rss', 'website', 'webhook', 'database'
    url: str
    auth: Optional[Dict[str, str]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 3600  # seconds
    parser: Optional[str] = None  # Custom parser name
    last_updated: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataRecord:
    """Unified data record from any source"""
    source_id: str
    record_id: str
    data: Dict[str, Any]
    timestamp: datetime
    raw_data: str = ""
    parsed_at: datetime = field(default_factory=datetime.now)


class DataSourceConnector(ABC):
    """Base connector for any data source"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, DataRecord] = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def connect(self) -> bool:
        """Initialize connection"""
        self.session = aiohttp.ClientSession()
        return True
    
    async def disconnect(self):
        """Close connection"""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch(self) -> List[DataRecord]:
        """Fetch data from source"""
        pass
    
    @abstractmethod
    async def parse(self, raw_data: str) -> List[DataRecord]:
        """Parse raw data into records"""
        pass
    
    async def get_with_cache(self) -> List[DataRecord]:
        """Fetch with caching"""
        cache_key = f"{self.source.source_id}:data"
        if cache_key in self.cache:
            record = self.cache[cache_key]
            if (datetime.now() - record.parsed_at).seconds < self.cache_ttl:
                return [record]
        
        records = await self.fetch()
        if records:
            self.cache[cache_key] = records[0]
        return records


class APIConnector(DataSourceConnector):
    """Connect to REST APIs"""
    
    async def fetch(self) -> List[DataRecord]:
        try:
            async with self.session.request(
                method=self.source.metadata.get('method', 'GET'),
                url=self.source.url,
                headers=self.source.headers,
                params=self.source.params,
                auth=self._build_auth()
            ) as resp:
                raw_data = await resp.text()
                records = await self.parse(raw_data)
                logger.info(f"API {self.source.source_id}: Fetched {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"API fetch failed for {self.source.source_id}: {e}")
            return []
    
    async def parse(self, raw_data: str) -> List[DataRecord]:
        """Parse JSON API response"""
        records = []
        try:
            data = json.loads(raw_data)
            
            # Handle different API response structures
            items = data
            if isinstance(data, dict):
                # Look for common array fields
                for key in ['data', 'items', 'results', 'records']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
            
            if isinstance(items, list):
                for idx, item in enumerate(items):
                    records.append(DataRecord(
                        source_id=self.source.source_id,
                        record_id=f"{self.source.source_id}:{idx}",
                        data=item if isinstance(item, dict) else {'value': item},
                        timestamp=datetime.now(),
                        raw_data=json.dumps(item)
                    ))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from {self.source.source_id}")
        
        return records
    
    def _build_auth(self):
        """Build authentication"""
        if not self.source.auth:
            return None
        
        auth_type = self.source.auth.get('type', 'bearer')
        if auth_type == 'bearer':
            self.source.headers['Authorization'] = f"Bearer {self.source.auth.get('token')}"
        elif auth_type == 'basic':
            return aiohttp.BasicAuth(
                self.source.auth.get('username'),
                self.source.auth.get('password')
            )
        return None


class WebScraperConnector(DataSourceConnector):
    """Scrape data from websites"""
    
    async def fetch(self) -> List[DataRecord]:
        try:
            async with self.session.get(self.source.url, headers=self.source.headers) as resp:
                raw_data = await resp.text()
                records = await self.parse(raw_data)
                logger.info(f"Web scraper {self.source.source_id}: Scraped {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"Web scrape failed for {self.source.source_id}: {e}")
            return []
    
    async def parse(self, raw_data: str) -> List[DataRecord]:
        """Parse HTML using BeautifulSoup"""
        records = []
        try:
            soup = BeautifulSoup(raw_data, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Extract tables if present
            tables = soup.find_all('table')
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                for row_idx, row in enumerate(rows):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                    records.append(DataRecord(
                        source_id=self.source.source_id,
                        record_id=f"{self.source.source_id}:table_{table_idx}:row_{row_idx}",
                        data={'content': cells, 'type': 'table_row'},
                        timestamp=datetime.now()
                    ))
            
            # Extract links
            links = soup.find_all('a')
            for link_idx, link in enumerate(links):
                records.append(DataRecord(
                    source_id=self.source.source_id,
                    record_id=f"{self.source.source_id}:link_{link_idx}",
                    data={'url': link.get('href'), 'text': link.get_text(strip=True)},
                    timestamp=datetime.now()
                ))
            
            # If no tables/links found, create text record
            if not records:
                records.append(DataRecord(
                    source_id=self.source.source_id,
                    record_id=f"{self.source.source_id}:text",
                    data={'content': text_content[:1000]},  # First 1000 chars
                    timestamp=datetime.now()
                ))
        except Exception as e:
            logger.error(f"HTML parse failed: {e}")
        
        return records


class RSSConnector(DataSourceConnector):
    """Connect to RSS/Atom feeds"""
    
    async def fetch(self) -> List[DataRecord]:
        try:
            async with self.session.get(self.source.url, headers=self.source.headers) as resp:
                raw_data = await resp.text()
                records = await self.parse(raw_data)
                logger.info(f"RSS {self.source.source_id}: Fetched {len(records)} feed items")
                return records
        except Exception as e:
            logger.error(f"RSS fetch failed for {self.source.source_id}: {e}")
            return []
    
    async def parse(self, raw_data: str) -> List[DataRecord]:
        """Parse RSS feed"""
        records = []
        try:
            feed = feedparser.parse(raw_data)
            
            for entry_idx, entry in enumerate(feed.entries):
                records.append(DataRecord(
                    source_id=self.source.source_id,
                    record_id=f"{self.source.source_id}:{entry_idx}",
                    data={
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', ''),
                        'published': entry.get('published', ''),
                        'author': entry.get('author', '')
                    },
                    timestamp=datetime.now()
                ))
        except Exception as e:
            logger.error(f"RSS parse failed: {e}")
        
        return records


class DataSourceManager:
    """Manages all data sources and connectors"""
    
    def __init__(self):
        self.sources: Dict[str, DataSource] = {}
        self.connectors: Dict[str, DataSourceConnector] = {}
        self.last_refresh: Dict[str, datetime] = {}
    
    def register_source(self, source: DataSource) -> bool:
        """Register a new data source"""
        try:
            connector = self._create_connector(source)
            self.sources[source.source_id] = source
            self.connectors[source.source_id] = connector
            logger.info(f"Registered data source: {source.source_id} ({source.source_type})")
            return True
        except Exception as e:
            logger.error(f"Failed to register source: {e}")
            return False
    
    def _create_connector(self, source: DataSource) -> DataSourceConnector:
        """Create appropriate connector for source type"""
        connectors = {
            'api': APIConnector,
            'website': WebScraperConnector,
            'rss': RSSConnector,
        }
        
        connector_class = connectors.get(source.source_type, APIConnector)
        return connector_class(source)
    
    async def fetch_from_source(self, source_id: str) -> List[DataRecord]:
        """Fetch data from a specific source"""
        if source_id not in self.connectors:
            logger.warning(f"Unknown source: {source_id}")
            return []
        
        source = self.sources[source_id]
        connector = self.connectors[source_id]
        
        # Check if refresh needed
        if source_id in self.last_refresh:
            elapsed = (datetime.now() - self.last_refresh[source_id]).total_seconds()
            if elapsed < source.refresh_interval:
                logger.debug(f"Source {source_id} still fresh, using cache")
                return []
        
        if not connector.session:
            await connector.connect()
        
        records = await connector.fetch()
        self.last_refresh[source_id] = datetime.now()
        
        return records
    
    async def fetch_all(self) -> Dict[str, List[DataRecord]]:
        """Fetch from all sources concurrently"""
        tasks = [
            self.fetch_from_source(source_id)
            for source_id in self.sources.keys()
        ]
        results = await asyncio.gather(*tasks)
        
        return {
            source_id: records
            for source_id, records in zip(self.sources.keys(), results)
        }
    
    async def cleanup(self):
        """Close all connections"""
        for connector in self.connectors.values():
            await connector.disconnect()


# Global manager instance
data_source_manager = DataSourceManager()
