"""
Account Service - business logic untuk manajemen akun Instagram.
Tidak berisi UI/Streamlit logic agar stabil dipakai dashboard dan worker.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import List, Optional, Tuple

import requests

from src.database import get_db_cursor
from src.db_repository import (
    add_account as db_add_account,
    delete_account as db_delete_account,
    get_account_by_username,
    get_active_accounts,
    get_all_accounts,
    update_account as db_update_account,
    update_account_health as db_update_health,
    update_account_status as db_update_status,
)

INSTAGRAM_BASE_URL = "https://www.instagram.com"
VALIDATE_IG_PROFILE_ON_ADD = os.getenv("VALIDATE_IG_PROFILE_ON_ADD", "true").lower() == "true"


# ============================================================
# USERNAME VALIDATION
# ============================================================

def normalize_username(username: str) -> str:
    """Normalize Instagram username to lowercase without @."""
    return (username or "").lstrip("@").strip().lower()


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate Instagram username format."""
    username = normalize_username(username)

    if not username:
        return False, "Username tidak boleh kosong."

    if len(username) > 30:
        return False, "Username maksimal 30 karakter."

    if not re.match(r"^[a-zA-Z0-9._]+$", username):
        return False, "Username hanya boleh huruf, angka, titik, dan underscore."

    if username.startswith(".") or username.endswith("."):
        return False, "Username tidak boleh diawali atau diakhiri titik."

    if ".." in username:
        return False, "Username tidak boleh mengandung titik berurutan."

    reserved = {"instagram", "about", "explore", "support", "blog", "press", "api"}
    if username in reserved:
        return False, f"Username @{username} tidak tersedia."

    return True, "Username valid."


def build_profile_url(username: str) -> str:
    return f"{INSTAGRAM_BASE_URL}/{normalize_username(username)}/"


def check_instagram_profile(username: str, timeout: int = 12) -> Tuple[Optional[bool], str]:
    """
    Lightweight profile existence check.

    Returns:
        (True, message)  -> profile likely exists
        (False, message) -> profile is not found / wrong username
        (None, message) -> cannot verify due network, rate limit, or login wall
    """
    username = normalize_username(username)
    is_valid, msg = validate_username(username)
    if not is_valid:
        return False, msg

    url = build_profile_url(username)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        ),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response.status_code == 404:
            return False, f"Username @{username} tidak ditemukan. Cek lagi username Instagram-nya."
        if response.status_code in (200, 301, 302):
            text = response.text.lower()
            if "sorry, this page isn't available" in text or "halaman ini tidak tersedia" in text:
                return False, f"Username @{username} tidak ditemukan. Cek lagi username Instagram-nya."
            return True, f"Akun @{username} berhasil divalidasi."
        if response.status_code in (401, 403, 429):
            return None, "Validasi live Instagram tidak bisa dipastikan karena akses dibatasi. Akun tetap dapat disimpan."
        return None, f"Validasi live tidak pasti. Status HTTP: {response.status_code}."
    except requests.RequestException:
        return None, "Validasi live Instagram tidak bisa dilakukan karena koneksi/timeout. Akun tetap dapat disimpan."


# ============================================================
# ACCOUNT MANAGEMENT
# ============================================================

def add_instagram_account(
    username: str,
    nama_unit: str,
    kategori_unit: str = "",
    wilayah: str = "",
    send_notification: bool = False,
    validate_live_profile: bool = None,
) -> Tuple[bool, str]:
    """Add a new Instagram account to monitoring."""
    username = normalize_username(username)
    is_valid, msg = validate_username(username)
    if not is_valid:
        return False, msg

    if not nama_unit or not nama_unit.strip():
        return False, "Nama unit tidak boleh kosong."

    if validate_live_profile is None:
        validate_live_profile = VALIDATE_IG_PROFILE_ON_ADD

    if validate_live_profile:
        exists, profile_msg = check_instagram_profile(username)
        if exists is False:
            return False, profile_msg
        # if None, do not block saving because production servers can hit login wall/rate limit.

    success, result_msg = db_add_account(
        nama_unit=nama_unit.strip(),
        username=username,
        kategori_unit=(kategori_unit or "").strip(),
        wilayah=(wilayah or "").strip(),
    )

    return success, result_msg


def update_instagram_account(
    account_id: int,
    username: str,
    nama_unit: str,
    kategori_unit: str = "",
    wilayah: str = "",
    is_active: bool = True,
    validate_live_profile: bool = False,
) -> Tuple[bool, str]:
    """Update an existing account safely."""
    username = normalize_username(username)
    is_valid, msg = validate_username(username)
    if not is_valid:
        return False, msg

    if validate_live_profile:
        exists, profile_msg = check_instagram_profile(username)
        if exists is False:
            return False, profile_msg

    return db_update_account(
        account_id=account_id,
        nama_unit=nama_unit,
        username=username,
        kategori_unit=kategori_unit,
        wilayah=wilayah,
        is_active=is_active,
    )


def deactivate_account(account_id: int) -> Tuple[bool, str]:
    success = db_update_status(account_id, False)
    return (True, "Akun berhasil dinonaktifkan.") if success else (False, "Gagal menonaktifkan akun.")


def activate_account(account_id: int) -> Tuple[bool, str]:
    success = db_update_status(account_id, True)
    return (True, "Akun berhasil diaktifkan kembali.") if success else (False, "Gagal mengaktifkan akun.")


def delete_account(account_id: int) -> Tuple[bool, str]:
    return db_delete_account(account_id)


def get_accounts_for_monitoring(skip_recent_hours: int = 0) -> List[dict]:
    """
    Get active accounts formatted for scraper compatibility.

    Args:
        skip_recent_hours: Jika > 0, skip akun yang sudah discrape dalam interval ini.
    """
    accounts = get_active_accounts(skip_recent_hours=skip_recent_hours)
    return [
        {
            "id": acc["id"],
            "nama_kanwil": acc["nama_unit"],
            "nama_unit": acc["nama_unit"],
            "url_akun": acc["profile_url"],
            "profile_url": acc["profile_url"],
            "username": acc["username"],
        }
        for acc in accounts
    ]


def update_health_status(account_id: int, health: str, last_checked: datetime = None) -> bool:
    return db_update_health(account_id, health, last_checked)


def get_account_health_summary() -> dict:
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT account_health, COUNT(*) as count
            FROM accounts
            GROUP BY account_health
        """)
        results = cursor.fetchall()

    summary = {"HEALTHY": 0, "WARNING": 0, "ERROR": 0, "total": 0}
    for row in results:
        health = row.get("account_health") or "HEALTHY"
        count = row.get("count") or 0
        if health in summary:
            summary[health] = count
        summary["total"] += count
    return summary


def mark_account_checked(account_id: int, success: bool = True) -> bool:
    health = "HEALTHY" if success else "ERROR"
    return update_health_status(account_id, health, datetime.now())


def bulk_import_accounts(accounts_data: List[dict]) -> Tuple[int, int, List[str]]:
    success_count = 0
    failed_count = 0
    errors = []
    for acc in accounts_data:
        success, msg = add_instagram_account(
            acc.get("username", ""),
            acc.get("nama_unit", ""),
            acc.get("kategori_unit", ""),
            acc.get("wilayah", ""),
            validate_live_profile=False,
        )
        if success:
            success_count += 1
        else:
            failed_count += 1
            errors.append(f"@{acc.get('username', '')}: {msg}")
    return success_count, failed_count, errors


# ============================================================
# ACCOUNT LOOKUP
# ============================================================

def get_account_id_by_username(username: str) -> Optional[int]:
    account = get_account_by_username(normalize_username(username))
    return account["id"] if account else None


def get_account_info(username: str) -> Optional[dict]:
    return get_account_by_username(normalize_username(username))


def search_accounts(query: str) -> List[dict]:
    query = (query or "").lower().strip()
    if not query:
        return []
    all_accounts = get_all_accounts()
    return [
        acc for acc in all_accounts
        if query in (acc.get("username") or "").lower()
        or query in (acc.get("nama_unit") or "").lower()
    ]
