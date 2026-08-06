from typing import List
from pydantic import BaseModel
import os
import json

class Settings(BaseModel):
    # App settings
    APP_NAME: str = "Secure IT Helpdesk AI"
    DEBUG: bool = False
    SECRET_KEY: str = "1234"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./helpdesk.db"
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Ollama (local, free, no API key needed)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Vector DB
    CHROMA_PERSIST_DIR: str = "./vector_db/chroma"
    COLLECTION_NAME: str = "helpdesk_documents"
    
    # File upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".csv", ".xlsx"]
    UPLOAD_DIR: str = "./data/uploads"
    
    # Security
    ENCRYPTION_KEY: str = ""
    AUDIT_LOG_ENABLED: bool = True
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

def load_env_file(filepath=".env"):
    """Load environment variables from .env file manually."""
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    return env_vars

def parse_env_value(key: str, value: str):
    """Parse environment variable value based on field type."""
    # For list fields
    if key in ["ALLOWED_ORIGINS", "ALLOWED_EXTENSIONS"]:
        try:
            # Try JSON parse
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        
        # Split by comma
        return [item.strip() for item in value.split(',') if item.strip()]
    
    # For boolean fields
    if key in ["DEBUG", "AUDIT_LOG_ENABLED"]:
        return value.lower() in ["true", "1", "yes", "on"]
    
    # For integer fields
    if key in ["MAX_UPLOAD_SIZE", "RATE_LIMIT_REQUESTS", "RATE_LIMIT_PERIOD", 
               "ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS"]:
        try:
            return int(value)
        except:
            return None
    
    return value

# Load from .env file
env_vars = load_env_file(".env")

# Create settings dictionary
settings_data = {}
for field_name in Settings.model_fields.keys():
    if field_name in env_vars:
        parsed_value = parse_env_value(field_name, env_vars[field_name])
        if parsed_value is not None:
            settings_data[field_name] = parsed_value

# Create settings instance
settings = Settings(**settings_data)