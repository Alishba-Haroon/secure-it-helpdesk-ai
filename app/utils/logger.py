import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any
import traceback

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
def setup_logger(name: str = "helpdesk") -> logging.Logger:
    """Setup and configure logger"""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Format for logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # JSON formatter for structured logging
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            
            if hasattr(record, 'extra'):
                log_data.update(record.extra)
            
            if record.exc_info:
                log_data["exception"] = traceback.format_exc()
            
            return json.dumps(log_data)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler - general logs
    file_handler = RotatingFileHandler(
        LOG_DIR / "helpdesk.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # File handler - error logs
    error_handler = RotatingFileHandler(
        LOG_DIR / "errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # JSON log handler
    json_handler = RotatingFileHandler(
        LOG_DIR / "helpdesk.json.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3
    )
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    return logger

# Create default logger
logger = setup_logger()

class LoggerContext:
    """Context manager for logging with extra context"""
    
    def __init__(self, logger_instance: logging.Logger, **kwargs):
        self.logger = logger_instance
        self.extra = kwargs
    
    def __enter__(self):
        self.old_extra = getattr(self.logger, 'extra', {})
        self.logger.extra = {**self.old_extra, **self.extra}
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.extra = self.old_extra

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance"""
    if name:
        return logging.getLogger(f"helpdesk.{name}")
    return logger

def log_with_context(logger_instance: logging.Logger, **kwargs):
    """Add context to logger"""
    return LoggerContext(logger_instance, **kwargs)

class LoggerMixin:
    """Mixin for classes that need logging"""
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

# Convenience functions
def debug(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

def exception(msg: str, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)

# Performance logging
def log_performance(func):
    """Decorator to log function performance"""
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        logger.info(
            f"Performance: {func.__name__} took {end_time - start_time:.3f} seconds"
        )
        
        return result
    
    return wrapper

async def log_async_performance(func):
    """Async decorator to log function performance"""
    import time
    
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        logger.info(
            f"Performance: {func.__name__} took {end_time - start_time:.3f} seconds"
        )
        
        return result
    
    return wrapper