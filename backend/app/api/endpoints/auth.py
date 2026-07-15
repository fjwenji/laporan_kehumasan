"""
Authentication endpoints - Secure implementation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import timedelta
import secrets
import string
from app.schemas.auth import Token, User, UserCreate, UserUpdate, PasswordChange
from app.api.deps import (
    authenticate_user, create_access_token, get_current_user,
    get_password_hash, get_db_cursor, generate_reset_token,
    verify_reset_token, hash_password, verify_password
)
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginJsonRequest(BaseModel):
    username: str
    password: str


def generate_temp_password(length: int = 12) -> str:
    """Generate secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint - returns JWT token.
    Uses OAuth2PasswordRequestForm for compatibility with standard OAuth2 clients.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun dinonaktifkan. Hubungi admin.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user.get("role", "user")},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
async def login_json(request: LoginJsonRequest):
    """
    Login endpoint with JSON body (alternative to form).
    For clients that prefer JSON over form data.
    """
    username = request.username
    password = request.password

    # Input validation - prevent injection
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username dan password diperlukan"
        )

    # Length validation
    if len(username) > 50 or len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input tidak valid"
        )

    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun dinonaktifkan. Hubungi admin.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user.get("role", "user")},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user.get("role", "user"),
        "is_active": current_user.get("is_active", True),
        "nama_lengkap": current_user.get("nama_lengkap"),
        "created_at": current_user.get("created_at")
    }


# ==================== USER MANAGEMENT (Admin Only) ====================

@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate, current_user: dict = Depends(get_current_user)):
    """
    Register new user (admin only).
    Only admins can create new users.
    """
    # Only admins can create users
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang dapat mendaftarkan user baru"
        )

    # Validate username - alphanumeric and underscore only
    username = user_data.username.strip()
    if not username.isalnum() and '_' not in username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username hanya boleh huruf, angka, dan underscore"
        )

    if len(username) < 3 or len(username) > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username harus 3-30 karakter"
        )

    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password minimal 8 karakter"
        )

    # Check if username exists (protected from SQL injection via parameterized query)
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username sudah digunakan"
            )

    # Create user with hashed password
    password_hash = hash_password(user_data.password)
    with get_db_cursor() as cursor:
        cursor.execute(
            """INSERT INTO users (username, password_hash, role, nama_lengkap, is_active)
               VALUES (%s, %s, %s, %s, TRUE)""",
            (username, password_hash, user_data.role, user_data.nama_lengkap or "")
        )
        user_id = cursor.lastrowid

    return {
        "id": user_id,
        "username": username,
        "role": user_data.role,
        "is_active": True,
        "nama_lengkap": user_data.nama_lengkap,
        "created_at": None
    }


@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """List all users (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang dapat melihat daftar user"
        )

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            """SELECT id, username, role, is_active, nama_lengkap, created_at
               FROM users ORDER BY created_at DESC"""
        )
        users = cursor.fetchall()

    return {"users": users, "total": len(users)}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang dapat mengubah user"
        )

    # Cannot deactivate yourself
    if current_user["id"] == user_id and user_data.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menonaktifkan akun sendiri"
        )

    # Build update query dynamically
    updates = []
    params = []

    if user_data.nama_lengkap is not None:
        updates.append("nama_lengkap = %s")
        params.append(user_data.nama_lengkap)

    if user_data.role is not None:
        updates.append("role = %s")
        params.append(user_data.role)

    if user_data.is_active is not None:
        updates.append("is_active = %s")
        params.append(user_data.is_active)

    if user_data.password is not None:
        if len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password minimal 8 karakter"
            )
        updates.append("password_hash = %s")
        params.append(hash_password(user_data.password))

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data yang diupdate"
        )

    params.append(user_id)

    with get_db_cursor() as cursor:
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = %s",
            params
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )

    return {"success": True, "message": "User berhasil diupdate"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Reset user password to random password (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang dapat reset password"
        )

    # Generate secure random password
    new_password = generate_temp_password()

    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(new_password), user_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )

    return {
        "success": True,
        "message": "Password berhasil direset",
        "new_password": new_password  # Admin will share this with user
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete user (admin only). Cannot delete self."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin yang dapat menghapus user"
        )

    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat menghapus akun sendiri"
        )

    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )

    return {"success": True, "message": "User berhasil dihapus"}


# ==================== PASSWORD MANAGEMENT ====================

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """Change own password."""
    user = authenticate_user(current_user["username"], password_data.old_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama salah"
        )

    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 8 karakter"
        )

    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(password_data.new_password), current_user["id"])
        )

    return {"success": True, "message": "Password berhasil diubah"}


# ==================== FORGOT PASSWORD ====================

@router.post("/forgot-password")
async def forgot_password(username: str):
    """
    Request password reset.
    In production, this would send an email. For now, it generates a reset token.
    """
    if not username or len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username tidak valid"
        )

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(
            "SELECT id, is_active FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()

    if not user:
        # Don't reveal if user exists or not for security
        return {
            "success": True,
            "message": "Jika username valid, instruksi reset akan dikirim"
        }

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun dinonaktifkan. Hubungi admin."
        )

    # Generate reset token
    reset_token = generate_reset_token(user["id"])

    # In production, send email here
    # For now, just return success message
    return {
        "success": True,
        "message": "Jika username valid, instruksi reset akan dikirim ke email",
        # Remove this in production - only for development
        "reset_token": reset_token if __import__("os").get("ENV", "dev") == "dev" else None
    }


@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password using token."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 8 karakter"
        )

    user_id = verify_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token tidak valid atau sudah kadaluarsa"
        )

    with get_db_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(new_password), user_id)
        )

    return {"success": True, "message": "Password berhasil direset"}
