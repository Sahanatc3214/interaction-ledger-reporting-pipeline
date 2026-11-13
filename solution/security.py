import os
import hmac
import hashlib

from cryptography.fernet import Fernet
from dotenv import load_dotenv


# Load secrets from the project's .env file.
load_dotenv()


ENCRYPTION_KEY = os.getenv("PII_ENCRYPTION_KEY")
HMAC_SECRET = os.getenv("PHONE_HMAC_SECRET")

if not ENCRYPTION_KEY or not HMAC_SECRET:
    raise RuntimeError("Security keys are missing from the .env file")

fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_pii(value):
    """Encrypt personal information before database storage."""
    if value is None:
        return None

    encrypted = fernet.encrypt(str(value).encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_pii(encrypted_value):
    """Decrypt personal information when authorized."""
    if encrypted_value is None:
        return None

    decrypted = fernet.decrypt(encrypted_value.encode("utf-8"))
    return decrypted.decode("utf-8")


def phone_lookup_hash(phone):
    """Create a deterministic HMAC for phone matching."""
    if phone is None:
        return None

    return hmac.new(
        HMAC_SECRET.encode("utf-8"),
        phone.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def mask_phone(phone):
    """Mask a canonical Indian phone number for reports."""
    if phone is None:
        return ""

    digits = "".join(char for char in phone if char.isdigit())

    if len(digits) != 12 or not digits.startswith("91"):
        raise ValueError("Expected a canonical Indian phone number")

    return "+91******" + digits[-4:]