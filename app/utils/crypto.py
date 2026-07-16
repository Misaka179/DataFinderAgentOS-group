import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from app.config import config


class CryptoManager:
    _instance = None
    _fernet = None
    _available = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_fernet()
        return cls._instance

    def _init_fernet(self):
        secret_key = config.ENCRYPTION_KEY
        if not secret_key:
            self._available = False
            return

        try:
            password = secret_key.encode()
            salt = b'datafinder_agent_os_salt'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self._fernet = Fernet(key)
            self._available = True
        except Exception:
            self._available = False

    def encrypt(self, plaintext):
        if not plaintext or not self._available:
            return plaintext
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext):
        if not ciphertext or not self._available:
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            return ciphertext


crypto_manager = CryptoManager()


def encrypt_api_key(api_key):
    return crypto_manager.encrypt(api_key)


def decrypt_api_key(api_key):
    return crypto_manager.decrypt(api_key)
