"""
Dependencies for API endpoints - Secure implementation
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
import base64
import hmac
from app.config import SECRET_KEY, ALGORITHM
from app.database import get_db_cursor

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Rate limiting storage (in production, use Redis)
_login_attempts = {}
RESET_TOKEN_EXPIRY_HOURS = 1


def simple_hash(password: str) -> str:
    """Simple SHA256 hash with salt - secure hashing."""
    # Add static salt for additional security
    salt = "mayz_djpb_salt_v2"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def hash_password(password: str) -> str:
    """
    Hash password using SHA256 with salt.
    In production, use bcrypt or argon2. For now, SHA256 with salt.
    """
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # iterations
    )
    return f"{salt}${base64.b64encode(hashed).decode('ascii')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash - supports both old and new format."""
    if not hashed_password:
        return False

    # New format: salt$hash
    if '$' in hashed_password:
        try:
            salt, stored_hash = hashed_password.split('$')
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                plain_password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return hmac.compare_digest(
                base64.b64encode(computed_hash).decode('ascii'),
                stored_hash
            )
        except Exception:
            return False

    # Old SHA256 format (for migration)
    if len(hashed_password) == 64:
        return simple_hash(plain_password) == hashed_password

    return False


def get_password_hash(password: str) -> str:
    """Alias for hash_password."""
    return hash_password(password)


def generate_reset_token(user_id: int) -> str:
    """Generate a secure reset token."""
    token_data = f"{user_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
    signature = hashlib.sha256((token_data + SECRET_KEY).encode()).hexdigest()
    token = base64.urlsafe_b64encode(
        f"{token_data}:{signature}".encode()
    ).decode()
    return token


def verify_reset_token(token: str) -> Optional[int]:
    """Verify reset token and return user_id if valid."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(':', 1)
        if len(parts) != 2:
            return None

        token_data, provided_signature = parts
        expected_signature = hashlib.sha256((token_data + SECRET_KEY).encode()).hexdigest()

        if not hmac.compare_digest(expected_signature, provided_signature):
            return None

        # Extract user_id
        user_id = int(token_data.split(':')[0])

        # Check expiry (token valid for 1 hour)
        token_time = datetime.fromisoformat(token_data.split(':')[1])
        if datetime.utcnow() - token_time > timedelta(hours=RESET_TOKEN_EXPIRY_HOURS):
            return None

        return user_id
    except Exception:
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with security enhancements."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=8)

    # Add issued at and other security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16)  # Unique token ID
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user from database by username."""
    # Sanitize username - only allow alphanumeric and underscore
    if not username or not all(c.isalnum() or c == '_' for c in username):
        return None

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )
        return cursor.fetchone()


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    user = get_user_by_username(username)
    if not user:
        return None

    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        return None

    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Get current user from JWT token with security checks."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tidak dapat memvalidasi kredensial",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

        # Check token expiry explicitly
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun dinonaktifkan. Hubungi admin."
        )

    return user


async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure current user is an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Diperlukan hak admin."
        )
    return current_user


def get_username_from_token(token: str) -> Optional[str]:
    """Extract username from token without full validation."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
