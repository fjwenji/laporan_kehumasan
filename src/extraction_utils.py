"""
Extraction Utilities - Fungsi-fungsi untuk ekstraksi data dengan anti-null approach.
Multi-selector, fallback, dan validasi element.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from src.selector_registry import (
    SELECTORS,
    get_selectors_for_field,
    is_valid_caption,
    is_valid_timestamp,
    is_not_empty,
    is_valid_post_url,
    is_empty_layout,
    is_valid_data_element,
    is_like_count,
)

@dataclass
class ExtractionResult:
    """Result dengan field-level evidence tracking."""
    value: Any = None
    source: str = ""
    selector_used: str = ""
    extraction_method: str = ""
    status: str = "NULL"
    null_reason: str = ""
    attempted_selectors: List[str] = field(default_factory=list)
    raw_value: Any = None

    def is_success(self) -> bool:
        return self.status == "OK" and self.value is not None

    def is_null(self) -> bool:
        return self.status == "NULL"

    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "source": self.source,
            "selector_used": self.selector_used,
            "status": self.status,
            "null_reason": self.null_reason,
            "attempted_selectors": self.attempted_selectors,
        }


@dataclass
class FieldStatus:
    """Status tracking untuk satu field."""
    field_name: str
    value: Any = None
    source: str = ""
    selector_used: str = ""
    status: str = "NULL"
    null_reason: str = ""
    attempted_selectors: List[str] = field(default_factory=list)


def safe_text(value: Any) -> str:
    """Convert value ke string yang aman."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in ("none", "null", "undefined", ""):
        return ""
    return text


def make_naive_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime dengan timezone ke naive datetime (tanpa timezone)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def safe_int(value: Any) -> Optional[int]:
    """Convert value ke integer dengan safety."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = safe_text(value).replace(",", "").replace(" ", "")
    if not text:
        return None
    try:
        multiplier = 1
        text_lower = text.lower()
        for suffix, mult in [("k", 1000), ("m", 1000000), ("rb", 1000), ("jt", 1000000)]:
            if text_lower.endswith(suffix):
                multiplier = mult
                text = text[:-len(suffix)]
                break
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return None


def clean_caption(text: str, max_len: int = 1000) -> str:
    """Clean caption text dari noise."""
    text = safe_text(text)
    if not text:
        return ""
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[A-Za-z0-9_.-]+\s*[:\-]\s*", "", text)

    text = re.sub(
        r'^[\d,.]+\s*(?:likes?|suka|comments?|komentar)(?:,?\s*[\d,.]+\s*(?:likes?|suka|comments?|komentar))?\s*[-–]\s*[a-zA-Z0-9_.]+\s*(?:pada|on)\s*[A-Za-z]+[\s,]+[\d]+[\s,]*[\d]{4}\s*[:：]',
        "",
        text,
        flags=re.IGNORECASE
    )
    # Fallback: Strip any leading pattern like "N likes, N comments - user on date:"
    text = re.sub(
        r'^[\d,.]+\s*(?:likes?|suka)(?:,?\s*[\d,.]+\s*(?:comments?|komentar))?\s*[-–]\s*[^\s:]+\s*(?:pada|on)?\s*[^:：]+[:：]',
        "",
        text,
        flags=re.IGNORECASE
    )

    # Strip leading and trailing quotes if present
    text = text.strip('"“”')

    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text.strip()


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Parse timestamp dari berbagai format. Selalu returns naive datetime (no timezone)."""
    raw = safe_text(raw)
    if not raw:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            normalized = raw.replace("Z", "+0000")
            return datetime.strptime(normalized[:19], fmt.replace("T", " ").replace(".%f", "").replace("%z", ""))
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        # Strip timezone to make it naive (Excel doesn't support timezone)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        pass

    readable_formats = ["%B %d, %Y", "%d %B %Y", "%B %d %Y", "%d %B, %Y"]
    for fmt in readable_formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return None


def parse_engagement_from_text(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse like dan comment count dari text."""
    text = safe_text(text)
    if not text:
        return None, None

    like_count = None
    comment_count = None

    # Pattern yang lebih robust untuk berbagai format angka
    # Menangani: 1.5K, 1,5K, 5K, 1500, 1.5M, 1.2jt, 100rb, 1jt, 1juta, etc.
    # Suffix: K, M, RB, JT, JUBA/JUTA (Indonesia format)
    # Gunakan IGNORECASE untuk menangkap k, m, rb, jt (lowercase)
    number_pattern = r"([\d]+(?:[.,][\d]+)?(?:jt|juta|k|m|rb)?)"

    # Like patterns - cari "number likes" atau "likes: number"
    like_patterns = [
        rf"{number_pattern}\s*(?:like|suka)",
        rf"(?:like|suka)[^\d]*({number_pattern})",
    ]

    for pattern in like_patterns:
        match = re.search(pattern, text.lower(), re.IGNORECASE)
        if match:
            like_count = safe_int(match.group(1))
            break

    # Comment patterns
    comment_patterns = [
        rf"{number_pattern}\s*(?:comment|komentar)",
        rf"(?:comment|komentar)[^\d]*({number_pattern})",
    ]

    for pattern in comment_patterns:
        match = re.search(pattern, text.lower(), re.IGNORECASE)
        if match:
            comment_count = safe_int(match.group(1))
            break

    return like_count, comment_count


def extract_shortcode(url: str) -> str:
    """Extract shortcode dari berbagai format URL Instagram."""
    url = safe_text(url)
    if not url:
        return ""
    pattern = r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ""


def normalize_instagram_url(url: str) -> str:
    """Normalize URL ke format standar."""
    url = safe_text(url)
    if not url:
        return ""
    shortcode = extract_shortcode(url)
    if shortcode:
        return f"https://www.instagram.com/p/{shortcode}/"
    return url


def get_valid_elements(page: Any, selector: str) -> List:
    """Get elements yang valid (bukan empty/layout)."""
    try:
        elements = page.locator(selector).all()
        return [el for el in elements if is_valid_data_element(el)]
    except Exception:
        return []


def get_first_valid_element(page: Any, selector: str) -> Optional[Any]:
    """Get element pertama yang valid."""
    valid_elements = get_valid_elements(page, selector)
    return valid_elements[0] if valid_elements else None


def get_meta_content(page: Any, selector: str) -> str:
    """Get meta tag content. Uses JavaScript to avoid encoding issues."""
    try:
        # Try JavaScript first (handles encoding better)
        js_selector = selector.replace('"', '\\"')
        content = page.evaluate(f'''
            document.querySelector('{js_selector}')?.getAttribute("content") || ""
        ''')
        if content:
            return safe_text(content)

        # Fallback to Playwright locator
        locator = page.locator(selector).first
        if locator.count() == 0:
            return ""
        return safe_text(locator.get_attribute("content", timeout=2000))
    except Exception:
        return ""


def get_element_text(page: Any, selector: str) -> str:
    """Get inner text dari element yang valid."""
    element = get_first_valid_element(page, selector)
    if element is None:
        return ""
    try:
        return safe_text(element.inner_text(timeout=2000))
    except Exception:
        return ""


def get_element_attr(page: Any, selector: str, attr: str) -> str:
    """Get attribute dari element yang valid."""
    element = get_first_valid_element(page, selector)
    if element is None:
        return ""
    try:
        return safe_text(element.get_attribute(attr, timeout=2000))
    except Exception:
        return ""


def get_body_text_filtered(page: Any) -> str:
    """Get meaningful text dari body, filter noise."""
    try:
        body_text = page.locator("body").inner_text(timeout=3000)
    except Exception:
        return ""

    lines = body_text.split("\n")
    candidates = []
    noise_patterns = ["instagram", "posts", "reels", "tagged", "followers", "following", "follow", "message", "login", "sign up", "masuk", "daftar"]

    for line in lines:
        line = safe_text(line)
        if not line or len(line) < 20:
            continue
        is_noise = any(noise in line.lower() for noise in noise_patterns)
        if not is_noise:
            candidates.append(line)

    return clean_caption(candidates[0]) if candidates else ""


def detect_media_type(post_url: str, page: Any = None) -> str:
    """Detect media type."""
    url = safe_text(post_url)
    if "/reel/" in url:
        return "REELS"
    if "/tv/" in url:
        return "VIDEO"
    if page is None:
        return "IMAGE" if "/p/" in url else "UNKNOWN"

    try:
        videos = get_valid_elements(page, "article video")
        if videos:
            return "VIDEO"
        imgs = get_valid_elements(page, "article img[alt]")
        if len(imgs) >= 2:
            return "CAROUSEL"
        if imgs:
            return "IMAGE"
    except Exception:
        pass

    return "IMAGE" if "/p/" in url else "UNKNOWN"


def parse_html_with_beautifulsoup(html: str) -> Any:
    """Parse HTML string dengan BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")
    except ImportError:
        return None


def extract_from_html_string(html: str) -> Dict[str, Any]:
    """
    Extract data dari HTML string menggunakan BeautifulSoup.
    Ini untuk POST-PROCESSING setelah Playwright mengambil HTML.
    """
    soup = parse_html_with_beautifulsoup(html)
    if soup is None:
        return {}

    results = {}

    # 1. time[datetime]
    time_el = soup.find("time", datetime=True)
    if time_el:
        dt = time_el.get("datetime")
        if dt:
            results["timestamp"] = dt
            results["timestamp_source"] = "time_datetime"

    # 2. og:description (caption)
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        content = og_desc.get("content")
        if is_valid_caption(content):
            results["caption"] = clean_caption(content)
            results["caption_source"] = "og_description"

    # 3. canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        href = canonical.get("href")
        if "/p/" in href or "/reel/" in href or "/tv/" in href:
            results["permalink"] = href
            results["permalink_source"] = "canonical"

    # 4. og:url
    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content") and "permalink" not in results:
        href = og_url.get("content")
        if "/p/" in href or "/reel/" in href or "/tv/" in href:
            results["permalink"] = href
            results["permalink_source"] = "og_url"

    # 5. div._aagv img (media)
    aagv_img = soup.select_one("div._aagv img")
    if aagv_img:
        src = aagv_img.get("src")
        alt = aagv_img.get("alt")
        if src and alt:
            results["media_url"] = src
            results["alt_text"] = alt
            results["media_source"] = "aagv_img"

    # 6. span.x1ypdohk (like count - struktur baru IG)
    like_spans = soup.select("span.x1ypdohk")
    for span in like_spans:
        text = span.get_text(strip=True)
        if text and re.match(r"^[\d,.]+[KMRB]?$", text):
            parsed = safe_int(text)
            if parsed:
                results["like_count"] = parsed
                results["like_source"] = "span_like_count"
                break

    # 7. Parse engagement dari og:description
    if "like_count" not in results and results.get("caption"):
        og_content = og_desc.get("content") if og_desc else ""
        likes, comments = parse_engagement_from_text(og_content)
        if likes is not None:
            results["like_count"] = likes
            results["like_source"] = "og_description_parse"
        if comments is not None:
            results["comment_count"] = comments
            results["comment_source"] = "og_description_parse"

    # 8. article img (media fallback)
    article_imgs = soup.select("article img")
    if article_imgs and "media_url" not in results:
        for img in article_imgs:
            src = img.get("src")
            alt = img.get("alt")
            if src and alt and "instagram.com" not in src.lower():
                results["media_url"] = src
                results["alt_text"] = alt
                results["media_source"] = "article_img"
                break

    return results


# MAIN EXTRACTION FUNCTION
def extract_with_fallback(page: Any, field_name: str) -> ExtractionResult:
    """Extract field dengan multi-selector fallback."""
    selectors = get_selectors_for_field(field_name)

    if not selectors:
        return ExtractionResult(null_reason=f"NO_SELECTORS_FOR_FIELD:{field_name}", extraction_method="registry")

    result = ExtractionResult(extraction_method="multi_selector")

    for selector_config in selectors:
        selector_name = selector_config.get("name", "unknown")
        selector_type = selector_config.get("type", "attr")
        selector = selector_config.get("selector")

        result.attempted_selectors.append(selector_name)

        try:
            value = None

            if selector_type == "url":
                value = page.url if hasattr(page, "url") else ""
                if "shortcode" in field_name:
                    value = extract_shortcode(value)

            elif selector_type == "url_contains":
                url = page.url if hasattr(page, "url") else ""
                pattern = selector_config.get("pattern", "")
                if re.search(pattern, url):
                    value = selector_config.get("value", True)
                else:
                    continue

            elif selector_type == "meta":
                if selector:
                    value = get_meta_content(page, selector)

            elif selector_type == "attr":
                if selector:
                    attr = selector_config.get("attr", "src")
                    value = get_element_attr(page, selector, attr)

            elif selector_type == "text":
                if selector:
                    value = get_element_text(page, selector)

            elif selector_type == "element_exists":
                if selector:
                    valid_el = get_first_valid_element(page, selector)
                    if valid_el is not None:
                        value = selector_config.get("value", True)
                    else:
                        continue

            if value and selector_config.get("parse") == "extract_number":
                value = safe_int(value)

            if value is not None and value != "":
                validate = selector_config.get("validate")
                if validate:
                    if validate == "is_valid_caption" and not is_valid_caption(value):
                        continue
                    elif validate == "is_valid_timestamp" and not is_valid_timestamp(value):
                        continue
                    elif validate == "is_not_empty" and not is_not_empty(value):
                        continue
                    elif validate == "is_valid_post_url" and not is_valid_post_url(value):
                        continue
                    elif validate == "is_like_count" and not is_like_count(value):
                        continue

                result.value = value
                result.status = "OK"
                result.source = selector_name
                result.selector_used = selector or selector_type
                result.extraction_method = f"{selector_type}:{selector_name}"
                return result

        except Exception:
            continue

    result.null_reason = f"{field_name.upper()}_NOT_FOUND"
    result.status = "NULL"
    return result


# CLASSIFICATION
def classify_status(fields: Dict[str, FieldStatus]) -> Tuple[str, str, List[str]]:
    """Classify scraping status berdasarkan field status."""
    reasons = []

    caption_ok = fields.get("caption", FieldStatus("caption")).value is not None
    timestamp_ok = fields.get("timestamp", FieldStatus("timestamp")).value is not None
    permalink_ok = fields.get("permalink", FieldStatus("permalink")).value is not None
    media_ok = fields.get("media_type", FieldStatus("media_type")).value not in (None, "UNKNOWN", "")
    like_ok = fields.get("like_count", FieldStatus("like_count")).value is not None
    comment_ok = fields.get("comment_count", FieldStatus("comment_count")).value is not None

    if not caption_ok:
        reasons.append(f"Caption: {fields.get('caption', FieldStatus('caption')).null_reason or 'NULL'}")
    if not timestamp_ok:
        reasons.append(f"Timestamp: {fields.get('timestamp', FieldStatus('timestamp')).null_reason or 'NULL'}")
    if not like_ok:
        reasons.append("Like: NULL")
    if not comment_ok:
        reasons.append("Comment: NULL")

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