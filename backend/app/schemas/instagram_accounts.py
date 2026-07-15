"""
Instagram Account Management Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class JenisAkun(str, Enum):
    KANWIL = "kanwil"
    KPPN = "kppn"
    PUSAT = "pusat"
    KANVER_LAINNYA = "kanver_lainnya"


class AccountStatus(str, Enum):
    AKTIF = "aktif"
    NONAKTIF = "nonaktif"


# ============================================================
# ACCOUNT SCHEMAS
# ============================================================

class InstagramAccountBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    nama_unit: str = Field(..., min_length=1, max_length=255)
    jenis_akun: JenisAkun = JenisAkun.KANWIL
    status: AccountStatus = AccountStatus.AKTIF
    notes: Optional[str] = Field(None, max_length=500)


class InstagramAccountCreate(InstagramAccountBase):
    @field_validator('username')
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.lstrip('@').strip().lower()


class InstagramAccountUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=100)
    nama_unit: Optional[str] = Field(None, max_length=255)
    jenis_akun: Optional[JenisAkun] = None
    status: Optional[AccountStatus] = None
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('username')
    @classmethod
    def normalize_username(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lstrip('@').strip().lower()
        return v


class InstagramAccount(InstagramAccountBase):
    id: int
    username: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstagramAccountResponse(BaseModel):
    accounts: List[InstagramAccount]
    total: int
    active_count: int
    inactive_count: int


class InstagramAccountFilters(BaseModel):
    search: Optional[str] = None
    jenis_akun: Optional[JenisAkun] = None
    status: Optional[AccountStatus] = None


# ============================================================
# IMPORT SCHEMAS
# ============================================================

class ImportPreviewRow(BaseModel):
    row_number: int
    username: str
    nama_unit: str
    jenis_akun: str
    status: str
    notes: Optional[str] = None
    is_valid: bool
    error_message: Optional[str] = None
    is_duplicate: bool
    existing_id: Optional[int] = None


class ImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    rows: List[ImportPreviewRow]
    can_proceed: bool


class ImportConfirmRequest(BaseModel):
    skip_duplicates: bool = True  # True = skip, False = update existing
    replace_all: bool = False  # If True, replace all with imported data


class ImportConfirmResponse(BaseModel):
    success: bool
    imported: int
    updated: int
    skipped: int
    failed: int
    errors: List[str] = []


# ============================================================
# BULK IMPORT FROM EXCEL (Internal)
# ============================================================

class ExcelImportData(BaseModel):
    username: str
    nama_unit: str
    jenis_akun: str = "kanwil"
    status: str = "aktif"
    notes: Optional[str] = None


# ============================================================
# USERNAME VALIDATION
# ============================================================

class UsernameValidationRequest(BaseModel):
    username: str


class UsernameValidationResponse(BaseModel):
    valid: bool
    normalized_username: str
    message: str
    is_duplicate: bool
    existing_account: Optional[dict] = None
