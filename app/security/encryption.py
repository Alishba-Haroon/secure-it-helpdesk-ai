import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional, Dict, Any
import json
from app.config import settings
from app.utils.logger import logger

# Password hashing
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

# Encryption utilities
class EncryptionManager:
    """Manage encryption and decryption"""
    
    def __init__(self):
        self.encryption_key = settings.ENCRYPTION_KEY or self._generate_key()
        self.cipher_suite = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
    
    def _generate_key(self) -> str:
        """Generate a new encryption key"""
        key = Fernet.generate_key()
        return key.decode('utf-8')
    
    def encrypt_data(self, data: Any) -> str:
        """Encrypt data"""
        try:
            # Convert to JSON string if not already string
            if not isinstance(data, str):
                data = json.dumps(data)
            
            encrypted_data = self.cipher_suite.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """Decrypt data"""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            decrypted_str = decrypted_data.decode('utf-8')
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted_str)
            except json.JSONDecodeError:
                return decrypted_str
        
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    def encrypt_text(self, text: str) -> str:
        """Encrypt text"""
        return self.encrypt_data(text)
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt text"""
        result = self.decrypt_data(encrypted_text)
        return str(result) if result else ""

# Key derivation for additional security
def derive_key(password: str, salt: bytes = None) -> bytes:
    """Derive a key from a password"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

# Sensitive data encryption
class SecureStorage:
    """Secure storage for sensitive data"""
    
    def __init__(self):
        self.encryption_manager = EncryptionManager()
    
    def store_credential(self, service: str, credential: str) -> str:
        """Store a credential securely"""
        data = {
            'service': service,
            'credential': credential,
            'timestamp': str(os.times().elapsed)
        }
        return self.encryption_manager.encrypt_data(data)
    
    def retrieve_credential(self, encrypted_credential: str) -> Optional[str]:
        """Retrieve a credential"""
        try:
            data = self.encryption_manager.decrypt_data(encrypted_credential)
            if isinstance(data, dict) and 'credential' in data:
                return data['credential']
            return str(data) if data else None
        except Exception:
            return None
    
    def store_config(self, config: Dict[str, Any]) -> str:
        """Store configuration securely"""
        return self.encryption_manager.encrypt_data(config)
    
    def retrieve_config(self, encrypted_config: str) -> Optional[Dict[str, Any]]:
        """Retrieve configuration"""
        try:
            data = self.encryption_manager.decrypt_data(encrypted_config)
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            return None

# Mask sensitive data for logging
def mask_sensitive_data(data: str) -> str:
    """Mask sensitive data in strings"""
    import re
    
    # Patterns to mask
    patterns = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'password="[MASKED]"'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'token="[MASKED]"'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'secret="[MASKED]"'),
        (r'key["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'key="[MASKED]"'),
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'api_key="[MASKED]"'),
        (r'authorization["\']?\s*[:=]\s*["\']?([^"\',\s]+)["\']?', 'authorization="[MASKED]"'),
    ]
    
    masked_data = data
    for pattern, replacement in patterns:
        masked_data = re.sub(pattern, replacement, masked_data, flags=re.IGNORECASE)
    
    return masked_data

# Validate encryption key
def validate_encryption_key(key: str) -> bool:
    """Validate an encryption key"""
    try:
        # Check if key is valid Fernet key
        if len(key) != 44:  # Base64 encoded 32-byte key
            return False
        
        # Try to create Fernet instance
        Fernet(key.encode())
        return True
    
    except Exception:
        return False

# Initialize encryption
encryption_manager = EncryptionManager()
secure_storage = SecureStorage()