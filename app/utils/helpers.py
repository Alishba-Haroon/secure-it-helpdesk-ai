from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re
import json
import hashlib
import uuid
from pathlib import Path
import aiofiles
import asyncio
from functools import wraps
import random
import string

# String utilities
def slugify(text: str) -> str:
    """Convert text to slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text

def truncate_text(text: str, max_length: int = 200, suffix: str = '...') -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text"""
    # Remove punctuation and split
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Count frequency
    from collections import Counter
    word_counts = Counter(words)
    
    # Return most common words
    return [word for word, _ in word_counts.most_common(max_keywords)]

def sanitize_filename(filename: str) -> str:
    """Sanitize filename"""
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:195] + '.' + ext if ext else name[:200]
    
    return filename

# Date/time utilities
def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime"""
    return dt.strftime(format_str)

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    
    return None

def get_time_delta(seconds: int) -> str:
    """Get human readable time delta"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} day{'s' if days > 1 else ''} {hours} hour{'s' if hours > 1 else ''}"

def is_within_timeframe(
    dt: datetime,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> bool:
    """Check if datetime is within timeframe"""
    if start and dt < start:
        return False
    if end and dt > end:
        return False
    return True

# File utilities
async def read_file_content(file_path: str) -> str:
    """Read file content asynchronously"""
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        return await f.read()

async def write_file_content(file_path: str, content: str) -> None:
    """Write file content asynchronously"""
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(content)

def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return Path(filename).suffix.lower()

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return Path(file_path).stat().st_size

def is_valid_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """Check if file type is allowed"""
    ext = get_file_extension(filename)
    return ext in allowed_extensions

# JSON utilities
def safe_json_loads(json_str: str) -> Optional[Dict]:
    """Safely load JSON"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely dump JSON"""
    try:
        return json.dumps(obj, indent=indent, default=str)
    except Exception:
        return str(obj)

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries recursively"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

# Security utilities
def generate_random_string(length: int = 32) -> str:
    """Generate random string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_secure_token() -> str:
    """Generate secure token"""
    return uuid.uuid4().hex

def hash_string(text: str) -> str:
    """Hash a string using SHA256"""
    return hashlib.sha256(text.encode()).hexdigest()

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data"""
    if len(data) <= visible_chars * 2:
        return '*' * len(data)
    
    prefix = data[:visible_chars]
    suffix = data[-visible_chars:]
    middle = '*' * (len(data) - visible_chars * 2)
    
    return f"{prefix}{middle}{suffix}"

# Validation utilities
def validate_email(email: str) -> bool:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))

def validate_url(url: str) -> bool:
    """Validate URL"""
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*$'
    return bool(re.match(pattern, url))

# Retry utilities
def retry_on_exception(max_retries: int = 3, delay: int = 1):
    """Decorator to retry on exception"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator

def retry_sync(max_retries: int = 3, delay: int = 1):
    """Decorator to retry on exception (sync version)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator

# Async utilities
async def gather_with_concurrency(*tasks, limit: int = 10):
    """Run tasks with concurrency limit"""
    semaphore = asyncio.Semaphore(limit)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[sem_task(task) for task in tasks])

async def run_in_executor(func, *args, **kwargs):
    """Run a sync function in executor"""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return await asyncio.get_event_loop().run_in_executor(
            executor, func, *args, **kwargs
        )

# Pagination utilities
def paginate_list(items: List[Any], page: int = 1, per_page: int = 20) -> Dict:
    """Paginate a list"""
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_items = items[start:end]
    
    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

# Cache utilities
class SimpleCache:
    """Simple in-memory cache"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > datetime.now():
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def clean_expired(self) -> None:
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if expiry <= now
        ]
        for key in expired_keys:
            del self.cache[key]

# Global cache instance
cache = SimpleCache()