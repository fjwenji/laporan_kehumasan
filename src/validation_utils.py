"""
Validation Utilities - Validasi hasil scraping dan page condition detection.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class ValidationResult:
    """Hasil validasi post."""
    is_valid: bool
    status_code: str
    status_message: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class PageCondition:
    """Kondisi halaman yang terdeteksi."""
    condition_type: str
    detected: bool
    confidence: str  # high, medium, low
    details: Optional[str] = None


def detect_login_wall(page: Any) -> bool:
    """
    Deteksi apakah halaman adalah login wall.
    Menggunakan multi-signal untuk akurasi tinggi, menghindari false positives.
    """
    try:
        url = page.url if hasattr(page, "url") else ""
        body_text = page.locator("body").inner_text(timeout=2000).lower()
    except Exception:
        return False

    # Check URL - ini sinyal paling akurat
    if "/accounts/login" in url or "/accounts/login/" in url:
        return True

    # Check for login form elements (most reliable)
    try:
        has_username_input = page.locator('input[name="username"]').count() > 0
        has_password_input = page.locator('input[name="password"]').count() > 0
        if has_username_input and has_password_input:
            return True
    except Exception:
        pass

    # High confidence signals (kata-kata SPESIFIK login wall)
    # FRASE LENGKAP, bukan kata individual
    high_confidence_signals = [
        "log in to see photos",
        "sign up to see photos",
        "log in to see posts",
        "phone number, username, or email",
        "forgot password",
        "dont have an account",
        "create a new account",
        "log in to continue",
        "sign up to continue",
    ]

    for signal in high_confidence_signals:
        if signal in body_text:
            return True

    # Check for empty article (profile without posts = login wall)
    try:
        article_text = page.locator("article").first.inner_text(timeout=1000)
        # If article is very short and contains login-related words, likely login wall
        if len(article_text) < 200:
            if any(word in article_text.lower() for word in ["log in", "sign up", "masuk", "daftar"]):
                # But check if it's just navigation buttons (not login wall)
                if "followers" not in article_text.lower() and "postingan" not in article_text.lower():
                    return True
    except Exception:
        pass

    return False


def get_page_debug_info(page: Any) -> dict:
    """
    Get debug info dari page untuk troubleshooting.
    """
    try:
        url = page.url if hasattr(page, "url") else ""
        title = page.title() if hasattr(page, "title") else ""
        try:
            body_text = page.locator("body").inner_text(timeout=2000)
        except Exception:
            body_text = ""

        # Check for various elements
        has_username_input = page.locator('input[name="username"]').count() > 0
        has_password_input = page.locator('input[name="password"]').count() > 0
        has_article = page.locator("article").count() > 0
        has_header = page.locator("header").count() > 0

        return {
            "url": url,
            "title": title,
            "body_length": len(body_text),
            "body_preview": body_text[:500] if body_text else "",
            "has_login_form": has_username_input,
            "has_password_input": has_password_input,
            "has_article": has_article,
            "has_header": has_header,
        }
    except Exception as e:
        return {"error": str(e)}


def detect_page_not_found(page: Any) -> bool:
    """Deteksi apakah halaman 404/not found."""
    try:
        body_text = page.locator("body").inner_text(timeout=2000).lower()
    except Exception:
        return False

    signals = [
        "halaman ini tidak tersedia",
        "sorry, this page isn't available",
        "maaf, halaman ini tidak tersedia",
    ]

    return any(s in body_text for s in signals)


def detect_rate_limit(page: Any) -> bool:
    """Deteksi apakah kena rate limit."""
    try:
        body_text = page.locator("body").inner_text(timeout=2000).lower()
    except Exception:
        return False

    signals = [
        "please wait a few minutes",
        "coba lagi nanti",
        "terlalu banyak permintaan",
        "too many requests",
    ]

    return any(s in body_text for s in signals)


def detect_something_wrong(page: Any) -> str:
    """Deteksi error page."""
    try:
        body_text = page.locator("body").inner_text(timeout=2000).lower()
    except Exception:
        return ""

    if "something went wrong" in body_text:
        return "Something went wrong"
    if "terjadi kesalahan" in body_text:
        return "Terjadi kesalahan"

    return ""


def classify_status(fields: Dict[str, Any]) -> Tuple[str, str, List[str]]:
    """
    Classify scraping status berdasarkan field status.
    Accepts either dicts with 'value' key or FieldStatus objects.
    Returns: (status_code, message, reasons)
    """
    reasons = []

    def get_value(field_data: Any) -> Any:
        """Extract value from either dict or FieldStatus object."""
        if isinstance(field_data, dict):
            return field_data.get("value")
        elif hasattr(field_data, "value"):
            return field_data.value
        return None

    def get_null_reason(field_data: Any) -> str:
        """Extract null_reason from either dict or FieldStatus object."""
        if isinstance(field_data, dict):
            return field_data.get("null_reason", "")
        elif hasattr(field_data, "null_reason"):
            return field_data.null_reason
        return ""

    # Get values
    caption_ok = get_value(fields.get("caption")) is not None
    timestamp_ok = get_value(fields.get("timestamp")) is not None
    permalink_ok = get_value(fields.get("permalink")) is not None
    media_value = get_value(fields.get("media_type"))
    media_ok = media_value not in (None, "UNKNOWN", "")

    like_ok = get_value(fields.get("like_count")) is not None
    comment_ok = get_value(fields.get("comment_count")) is not None

    # Collect null reasons
    if not caption_ok:
        reasons.append(f"Caption: {get_null_reason(fields.get('caption')) or 'NULL'}")
    if not timestamp_ok:
        reasons.append(f"Timestamp: {get_null_reason(fields.get('timestamp')) or 'NULL'}")
    if not like_ok:
        reasons.append("Like: NULL")
    if not comment_ok:
        reasons.append("Comment: NULL")

    # Classification logic
    if caption_ok and timestamp_ok and permalink_ok and media_ok:
        if like_ok and comment_ok:
            return "FULL_SUCCESS", "Semua field berhasil", reasons
        else:
            return "PARTIAL_SUCCESS", "Field utama OK, engagement null", reasons

    if caption_ok and timestamp_ok:
        return "FIELD_PARTIAL_NULL", "Caption dan timestamp OK", reasons

    if not caption_ok:
        return "CAPTION_NULL", "Caption tidak ditemukan", reasons

    if not timestamp_ok:
        return "TIMESTAMP_NULL", "Timestamp tidak ditemukan", reasons

    return "MANUAL_REVIEW_REQUIRED", "Field utama null", reasons


def needs_debug_save(status_code: str) -> bool:
    """Check apakah perlu simpan debug data."""
    debug_needed = [
        "CAPTION_NULL",
        "TIMESTAMP_NULL",
        "FIELD_PARTIAL_NULL",
        "HTML_STRUCTURE_CHANGED",
        "SELECTOR_NOT_FOUND",
        "MANUAL_REVIEW_REQUIRED",
        "PAGE_LOAD_FAILED",
    ]
    return status_code in debug_needed


SCRAPING_STATUS_DISPLAY = {
    "FULL_SUCCESS": {"label": "Success", "color": "green"},
    "PARTIAL_SUCCESS": {"label": "Partial", "color": "yellow"},
    "FIELD_PARTIAL_NULL": {"label": "Field Null", "color": "yellow"},
    "CAPTION_NULL": {"label": "Caption Null", "color": "orange"},
    "TIMESTAMP_NULL": {"label": "Timestamp Null", "color": "orange"},
    "LOGIN_WALL": {"label": "Login Wall", "color": "red"},
    "PAGE_NOT_FOUND": {"label": "Not Found", "color": "red"},
    "RATE_LIMITED": {"label": "Rate Limited", "color": "red"},
    "PAGE_LOAD_FAILED": {"label": "Load Failed", "color": "red"},
    "HTML_STRUCTURE_CHANGED": {"label": "Structure Changed", "color": "orange"},
    "SELECTOR_NOT_FOUND": {"label": "Selector Failed", "color": "orange"},
    "MANUAL_REVIEW_REQUIRED": {"label": "Manual Review", "color": "orange"},
}


def get_status_display(status_code: str) -> Dict[str, str]:
    """Get display info untuk status code."""
    return SCRAPING_STATUS_DISPLAY.get(status_code, {
        "label": status_code,
        "color": "gray"
    })


def is_valid_caption(text: str) -> bool:
    """Cek apakah text valid sebagai caption."""
    if not text or not text.strip():
        return False
    if len(text.strip()) < 5:
        return False

    noise_patterns = [
        r"^(instagram|posts|reels|tagged|followers|following|follow)$",
        r"^(login|sign up|masuk|daftar)$",
    ]

    text_lower = text.lower().strip()
    for pattern in noise_patterns:
        if re.match(pattern, text_lower):
            return False

    return True


def is_valid_timestamp(value: str) -> bool:
    """Cek apakah value valid sebagai timestamp."""
    if not value:
        return False
    return bool(re.search(r"\d{4}-\d{2}-\d{2}", value))


def is_valid_post_url(url: str) -> bool:
    """Cek apakah URL valid untuk post Instagram."""
    if not url:
        return False
    return any(p in url.lower() for p in ["instagram.com/p/", "instagram.com/reel/", "instagram.com/tv/"])


def is_valid_shortcode(code: str) -> bool:
    """Cek apakah shortcode valid."""
    if not code:
        return False
    return bool(re.match(r"^[A-Za-z0-9_-]{5,30}$", code))
