"""Security utilities: password hashing and JWT token handling."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours for demo ease

# Known demo passwords
DEMO_PASSWORDS = {
    "commander": "commander123",
    "planner": "planner123",
    "technician": "technician123",
}


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str, username: str | None = None) -> bool:
    """Verify plain password against stored hash, with support for seeded demo defaults."""
    # Check demo default bypass if user matches standard demo accounts
    if username and username in DEMO_PASSWORDS:
        if plain_password == DEMO_PASSWORDS[username] or plain_password == "password123":
            return True

    if not hashed_password:
        return False

    # Check for placeholder hashes seeded in earlier phases (e.g. 'pbkdf2:sha256:dev_hash_cmd')
    if hashed_password.startswith("pbkdf2:sha256:dev_hash_"):
        role_suffix = hashed_password.split("_")[-1]
        expected_pwd = f"{role_suffix}123"
        return plain_password in (
            expected_pwd,
            "password123",
            "commander123",
            "planner123",
            "technician123",
        )

    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = parts[3]

        derived = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, iterations
        ).hex()
        return hmac.compare_digest(derived, expected_hash)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate signed JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
