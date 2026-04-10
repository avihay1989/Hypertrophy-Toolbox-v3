"""In-memory caching for filter options."""

from datetime import datetime, timedelta
from threading import Lock
from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()

class FilterCache:
    """Thread-safe in-memory cache for filter options."""
    
    def __init__(self, ttl_seconds=3600):
        self._cache = {}
        self._lock = Lock()
        self._ttl_seconds = ttl_seconds
        self._enabled = True
        logger.info(f"FilterCache initialized with TTL: {ttl_seconds} seconds")
    
    def _is_expired(self, cache_entry):
        if 'timestamp' not in cache_entry:
            return True
        age = datetime.now() - cache_entry['timestamp']
        return age > timedelta(seconds=self._ttl_seconds)
    
    def get(self, table, column):
        if not self._enabled:
            return None
        cache_key = f"{table}.{column}"
        with self._lock:
            if cache_key not in self._cache:
                return None
            entry = self._cache[cache_key]
            if self._is_expired(entry):
                logger.debug(f"Cache expired for {cache_key}")
                del self._cache[cache_key]
                return None
            logger.debug(f"Cache hit for {cache_key}")
            return entry['values']
    
    def set(self, table, column, values):
        if not self._enabled:
            return
        cache_key = f"{table}.{column}"
        with self._lock:
            self._cache[cache_key] = {'values': values, 'timestamp': datetime.now()}
            logger.debug(f"Cached {len(values)} values for {cache_key}")
    
    def invalidate(self, table=None, column=None):
        with self._lock:
            if table is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Invalidated entire cache ({count} entries)")
            elif column is None:
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{table}.")]
                for key in keys_to_delete:
                    del self._cache[key]
                logger.info(f"Invalidated {len(keys_to_delete)} entries for table {table}")
            else:
                cache_key = f"{table}.{column}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.info(f"Invalidated cache for {cache_key}")
    
    def get_stats(self):
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if self._is_expired(entry))
            return {
                'enabled': self._enabled,
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'ttl_seconds': self._ttl_seconds,
                'keys': list(self._cache.keys())
            }

_filter_cache = FilterCache()

def get_cached_unique_values(table, column):
    cached = _filter_cache.get(table, column)
    if cached is not None:
        return cached
    query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column} ASC"
    with DatabaseHandler() as db:
        results = db.fetch_all(query)
        values = [row[column] for row in results if row.get(column)]
        _filter_cache.set(table, column, values)
        return values

def invalidate_cache(table=None, column=None):
    _filter_cache.invalidate(table, column)

def get_cache_stats():
    return _filter_cache.get_stats()

def clear_cache():
    _filter_cache.invalidate()

def warm_cache():
    logger.info("Warming up filter cache...")
    common_filters = [
        ('exercises', 'primary_muscle_group'),
        ('exercises', 'equipment'),
        ('exercises', 'mechanic'),
        ('exercises', 'force'),
        ('exercises', 'difficulty'),
        ('exercises', 'utility'),
    ]
    for table, column in common_filters:
        try:
            get_cached_unique_values(table, column)
        except Exception as e:
            logger.warning(f"Failed to warm cache for {table}.{column}: {e}")
    logger.info("Cache warming complete")
