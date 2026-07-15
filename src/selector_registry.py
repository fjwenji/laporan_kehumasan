"""
Selector Registry - Single source of truth untuk semua selector Instagram.
Anti-null approach dengan multi-selector dan semantic priority.

PRIORITAS SELECTOR:
1. Semantic tags (time, img, meta, link)
2. Class-based selectors sebagai fallback
3. JSON embedded data
4. Regex/body text sebagai last resort
"""

from typing import Dict, List, Any
import re


# ============================================================
# SELECTOR REGISTRY
# ============================================================

SELECTORS: Dict[str, List[Dict[str, Any]]] = {
    # PERMALINK - Extract post URL
    "permalink": [
        {
            "name": "canonical_url",
            "type": "attr",
            "selector": "link[rel='canonical']",
            "attr": "href",
            "priority": 1,
            "validate": "is_valid_post_url",
            "description": "Canonical URL - sumber paling reliable",
        },
        {
            "name": "og_url",
            "type": "meta",
            "selector": "meta[property='og:url']",
            "attr": "content",
            "priority": 2,
            "validate": "is_valid_post_url",
            "description": "Open Graph URL dari meta",
        },
        {
            "name": "current_url",
            "type": "url",
            "selector": None,
            "priority": 3,
            "description": "URL browser saat ini",
        },
    ],

    # TIMESTAMP - Extract posting date
    "timestamp": [
        {
            "name": "time_datetime",
            "type": "attr",
            "selector": "time[datetime]",
            "attr": "datetime",
            "priority": 1,
            "validate": "is_valid_timestamp",
            "description": "Semantic time tag - PRIORITAS UTAMA",
        },
        {
            "name": "article_time",
            "type": "attr",
            "selector": "article time[datetime]",
            "attr": "datetime",
            "priority": 2,
            "validate": "is_valid_timestamp",
            "description": "Time dalam article element",
        },
        {
            "name": "time_inner_text",
            "type": "text",
            "selector": "time",
            "priority": 3,
            "validate": "is_valid_timestamp",
            "description": "Time inner text fallback",
        },
        {
            "name": "meta_published_time",
            "type": "meta",
            "selector": "meta[property='article:published_time']",
            "attr": "content",
            "priority": 4,
            "validate": "is_valid_timestamp",
            "description": "Open Graph article published time",
        },
        {
            "name": "script_json_ld",
            "type": "json_script",
            "pattern": r'"datePublished"\s*:\s*"([^"]+)"',
            "priority": 5,
            "validate": "is_valid_timestamp",
            "description": "JSON-LD structured data",
        },
        {
            "name": "meta_og_description_date",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"(January|February|March|April|May|June|Juli|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            "priority": 99,
            "description": "Date dari og:description (LAST RESORT)",
        },
    ],

    # CAPTION - Extract post caption/text
    "caption": [
        {
            "name": "og_description",
            "type": "meta",
            "selector": "meta[property='og:description']",
            "attr": "content",
            "priority": 1,
            "validate": "is_valid_caption",
            "description": "Open Graph description - sumber utama",
        },
        {
            "name": "twitter_description",
            "type": "meta",
            "selector": "meta[name='twitter:description']",
            "attr": "content",
            "priority": 2,
            "validate": "is_valid_caption",
            "description": "Twitter card description",
        },
        {
            "name": "meta_description",
            "type": "meta",
            "selector": "meta[name='description']",
            "attr": "content",
            "priority": 3,
            "validate": "is_valid_caption",
            "description": "Generic meta description",
        },
        {
            "name": "article_h1",
            "type": "text",
            "selector": "article h1",
            "priority": 4,
            "validate": "is_valid_caption",
            "description": "H1 dalam article",
        },
        {
            "name": "article_div_caption",
            "type": "text",
            "selector": "article div[role='presentation']",
            "priority": 5,
            "validate": "is_valid_caption",
            "description": "Div dengan role presentation",
        },
        {
            "name": "script_shared_data_caption",
            "type": "json_script",
            "pattern": r'"text"\s*:\s*"([^"]{10,})"',
            "priority": 6,
            "validate": "is_valid_caption",
            "description": "Caption dari embedded JSON",
        },
        {
            "name": "body_text_fallback",
            "type": "body_filtered",
            "selector": None,
            "priority": 99,
            "validate": "is_valid_caption",
            "description": "Body text setelah filter noise (LAST RESORT)",
        },
    ],

    # MEDIA TYPE - Detect IMAGE/CAROUSEL/REELS/VIDEO
    "media_type": [
        {
            "name": "url_reel_check",
            "type": "url_contains",
            "pattern": "/reel/",
            "value": "REELS",
            "priority": 1,
            "description": "URL mengandung /reel/",
        },
        {
            "name": "url_tv_check",
            "type": "url_contains",
            "pattern": "/tv/",
            "value": "VIDEO",
            "priority": 2,
            "description": "URL mengandung /tv/",
        },
        {
            "name": "video_element",
            "type": "element_exists",
            "selector": "article video",
            "value": "VIDEO",
            "priority": 3,
            "description": "Video element ditemukan",
        },
        {
            "name": "carousel_check",
            "type": "element_count",
            "selector": "article img[alt]",
            "min_count": 2,
            "value": "CAROUSEL",
            "priority": 4,
            "description": "Multiple images = carousel",
        },
        {
            "name": "single_image",
            "type": "element_exists",
            "selector": "article img[alt]",
            "value": "IMAGE",
            "priority": 5,
            "description": "Single image found",
        },
        {
            "name": "aagv_image",
            "type": "element_exists",
            "selector": "div._aagv img[alt]",
            "value": "IMAGE",
            "priority": 6,
            "description": "Image dari div._aagv (FALLBACK)",
        },
        {
            "name": "default_p_url",
            "type": "url_contains",
            "pattern": "/p/",
            "value": "IMAGE",
            "priority": 7,
            "description": "Default untuk /p/ URL",
        },
    ],

    # MEDIA URL - Extract image/video URL
    "media_url": [
        {
            "name": "article_img_src_valid",
            "type": "attr",
            "selector": "article img[alt][src]:not([src=''])",
            "attr": "src",
            "priority": 1,
            "validate": "is_not_empty",
            "description": "Article image dengan alt DAN src valid",
        },
        {
            "name": "article_img_src",
            "type": "attr",
            "selector": "article img[src]",
            "attr": "src",
            "priority": 2,
            "validate": "is_not_empty",
            "description": "Article image dengan src",
        },
        {
            "name": "aagv_img_src",
            "type": "attr",
            "selector": "div._aagv img[alt][src]",
            "attr": "src",
            "priority": 3,
            "validate": "is_not_empty",
            "description": "Image dari div._aagv",
        },
        {
            "name": "og_image",
            "type": "meta",
            "selector": "meta[property='og:image']",
            "attr": "content",
            "priority": 4,
            "validate": "is_not_empty",
            "description": "Open Graph image",
        },
    ],

    # ALT TEXT - Extract image alt text
    "alt_text": [
        {
            "name": "article_img_alt",
            "type": "attr",
            "selector": "article img[alt]:not([alt=''])",
            "attr": "alt",
            "priority": 1,
            "validate": "is_not_empty",
            "description": "Alt text dari article image",
        },
        {
            "name": "aagv_img_alt",
            "type": "attr",
            "selector": "div._aagv img[alt]:not([alt=''])",
            "attr": "alt",
            "priority": 2,
            "validate": "is_not_empty",
            "description": "Alt text dari div._aagv",
        },
        {
            "name": "og_image_alt",
            "type": "meta",
            "selector": "meta[property='og:image:alt']",
            "attr": "content",
            "priority": 3,
            "validate": "is_not_empty",
            "description": "Open Graph image alt",
        },
    ],

    # LIKE COUNT - Extract like count (struktur baru IG)
    "like_count": [
        {
            "name": "span_like_count",
            "type": "text",
            "selector": "span.x1ypdohk",
            "priority": 1,
            "validate": "is_like_count",
            "description": "Span dengan class x1ypdohk (angka like)",
        },
        {
            "name": "aria_label_like_svg",
            "type": "element_text",
            "selector": 'svg[aria-label="Like"]',
            "attr": "aria-label",
            "priority": 2,
            "description": "Like SVG aria-label",
        },
        {
            "name": "og_description_likes",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:like|suka)",
            "priority": 3,
            "parse": "parse_engagement",
            "description": "Parse likes dari og:description",
        },
        {
            "name": "script_like_count",
            "type": "json_script",
            "pattern": r'"like_count"\s*:\s*(\d+)',
            "priority": 4,
            "parse": "extract_number",
            "description": "Like count dari JSON script",
        },
    ],

    # COMMENT COUNT - Extract comment count (struktur baru IG)
    "comment_count": [
        {
            "name": "svg_comment_count",
            "type": "element_exists",
            "selector": 'svg[aria-label="Comment"]',
            "value": "COMMENT_FOUND",
            "priority": 1,
            "description": "Comment SVG exists (untuk cek ada comment atau tidak)",
        },
        {
            "name": "script_comment_count",
            "type": "json_script",
            "pattern": r'"comments_count"\s*:\s*(\d+)',
            "priority": 2,
            "parse": "extract_number",
            "description": "Comment count dari JSON script",
        },
        {
            "name": "og_description_comments",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:comment|komentar)",
            "priority": 3,
            "parse": "parse_engagement",
            "description": "Parse comments dari og:description",
        },
    ],

    # USERNAME - Extract account username
    "username": [
        {
            "name": "og_site_name",
            "type": "meta",
            "selector": "meta[property='og:site_name']",
            "attr": "content",
            "priority": 1,
            "description": "Open Graph site name",
        },
        {
            "name": "url_extract",
            "type": "url_extract",
            "pattern": r"instagram\.com/([^/]+)/",
            "group": 1,
            "priority": 2,
            "description": "Extract dari URL",
        },
    ],

    # VIEW/PLAY COUNT - Extract video views (Reels/Video)
    "view_count": [
        {
            "name": "script_video_views",
            "type": "json_script",
            "pattern": r'"video_view_count"\s*:\s*(\d+)',
            "priority": 1,
            "parse": "extract_number",
            "description": "Video view count dari JSON",
        },
        {
            "name": "script_play_count",
            "type": "json_script",
            "pattern": r'"play_count"\s*:\s*(\d+)',
            "priority": 2,
            "parse": "extract_number",
            "description": "Play count dari JSON (Reels)",
        },
        {
            "name": "script_view_count",
            "type": "json_script",
            "pattern": r'"view_count"\s*:\s*(\d+)',
            "priority": 3,
            "parse": "extract_number",
            "description": "View count dari JSON",
        },
        {
            "name": "og_description_views",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:views?|tayangan|pemutaran)",
            "priority": 4,
            "parse": "parse_engagement",
            "description": "Parse views dari og:description",
        },
    ],

    # SHARE COUNT - Extract share count (insights/private)
    "share_count": [
        {
            "name": "script_share_count",
            "type": "json_script",
            "pattern": r'"share_count"\s*:\s*(\d+)',
            "priority": 1,
            "parse": "extract_number",
            "description": "Share count dari JSON",
        },
        {
            "name": "og_description_shares",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:shares?|dibagikan)",
            "priority": 2,
            "parse": "parse_engagement",
            "description": "Parse shares dari og:description",
        },
    ],

    # SAVE COUNT - Extract save count (insights/private)
    "save_count": [
        {
            "name": "script_save_count",
            "type": "json_script",
            "pattern": r'"save_count"\s*:\s*(\d+)',
            "priority": 1,
            "parse": "extract_number",
            "description": "Save count dari JSON",
        },
        {
            "name": "og_description_saves",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:saves?|disimpan)",
            "priority": 2,
            "parse": "parse_engagement",
            "description": "Parse saves dari og:description",
        },
    ],

    # REACH COUNT - Extract reach count (insights/private)
    "reach_count": [
        {
            "name": "script_reach_count",
            "type": "json_script",
            "pattern": r'"reach_count"\s*:\s*(\d+)',
            "priority": 1,
            "parse": "extract_number",
            "description": "Reach count dari JSON",
        },
        {
            "name": "og_description_reach",
            "type": "regex",
            "selector": "meta[property='og:description']",
            "pattern": r"([\d,.]+[KMRB]?)\s+(?:reach|jangkauan)",
            "priority": 2,
            "parse": "parse_engagement",
            "description": "Parse reach dari og:description",
        },
    ],
}


# ============================================================
# IGNORED ELEMENTS - Layout/overlay yang harus diabaikan
# ============================================================

IGNORED_CLASS_PATTERNS = [
    # Empty spacer classes (dari contoh user)
    "x1ey2m1c", "xtijo5x", "x1o0tod", "x10l6tqk", "x13vifvy",
    # Generic layout
    "_a9z6", "_a9zs", "_aak7", "_a9--",
]

IGNORED_TEXT_PATTERNS = [
    r"^(instagram|posts|reels|tagged|followers|following|follow)$",
    r"^(login|sign up|masuk|daftar)$",
    r"^(notifications|notifikasi)$",
]


# ============================================================
# VALIDATORS
# ============================================================

def is_valid_post_url(url: str) -> bool:
    """Cek apakah URL valid untuk post Instagram."""
    if not url:
        return False
    url_lower = url.lower()
    return any(p in url_lower for p in ["instagram.com/p/", "instagram.com/reel/", "instagram.com/tv/"])


def is_valid_caption(text: str) -> bool:
    """Cek apakah text valid sebagai caption."""
    if not text or not text.strip():
        return False
    if len(text.strip()) < 5:
        return False
    text_lower = text.lower().strip()
    for pattern in IGNORED_TEXT_PATTERNS:
        if re.match(pattern, text_lower):
            return False
    return True


def is_valid_timestamp(value: str) -> bool:
    """Cek apakah value valid sebagai timestamp."""
    if not value:
        return False
    return bool(re.search(r"\d{4}-\d{2}-\d{2}", value))


def is_not_empty(value: str) -> bool:
    """Cek apakah value tidak kosong."""
    return bool(value and value.strip())


def is_like_count(value: str) -> bool:
    """Cek apakah value adalah like count (angka saja)."""
    if not value:
        return False
    value = value.strip()
    return bool(re.match(r'^[\d,.]+[KMRB]?$', value))


def is_empty_layout(element) -> bool:
    """
    Cek apakah element adalah layout/overlay kosong.
    Returns True jika element TIDAK punya data (seharusnya diabaikan).
    """
    if element is None:
        return True

    if hasattr(element, "get_attribute"):
        class_attr = element.get_attribute("class") or ""

        for pattern in IGNORED_CLASS_PATTERNS:
            if pattern in class_attr:
                try:
                    children = element.locator("img[src]:not([src='']), video, time[datetime]")
                    if children.count() > 0:
                        return False
                except Exception:
                    pass
                return True

    if hasattr(element, "inner_text"):
        try:
            text = element.inner_text()
            if not text or not text.strip():
                try:
                    children = element.locator("img[src]:not([src='']), video, time, a[href]")
                    if children.count() == 0:
                        return True
                except Exception:
                    return True
        except Exception:
            return True

    return False


def is_valid_data_element(element) -> bool:
    """
    Cek apakah element mengandung data yang valid untuk scraping.
    Returns True jika element BISA digunakan untuk extract data.
    """
    if element is None:
        return False

    if is_empty_layout(element):
        return False

    if hasattr(element, "get_attribute"):
        src = element.get_attribute("src")
        alt = element.get_attribute("alt")
        href = element.get_attribute("href")
        datetime_attr = element.get_attribute("datetime")
        content = element.get_attribute("content")

        if src and src.strip() and "instagram.com" not in src.lower():
            return True
        if alt and alt.strip():
            return True
        if href and "instagram.com/p/" in href.lower():
            return True
        if datetime_attr:
            return True
        if content and content.strip():
            return True

    if hasattr(element, "inner_text"):
        try:
            text = element.inner_text()
            if text and len(text.strip()) >= 5:
                text_lower = text.lower().strip()
                for pattern in IGNORED_TEXT_PATTERNS:
                    if re.match(pattern, text_lower):
                        return False
                return True
        except Exception:
            pass

    return False


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_selectors_for_field(field_name: str) -> List[Dict]:
    """Get selectors sorted by priority untuk field tertentu."""
    selectors = SELECTORS.get(field_name, [])
    return sorted(selectors, key=lambda x: x.get("priority", 99))


def get_all_field_names() -> List[str]:
    """Get semua field names yang tersedia."""
    return list(SELECTORS.keys())


def get_primary_fields() -> List[str]:
    """Get primary fields (wajib ada)."""
    return ["permalink", "timestamp", "caption", "media_type"]


def get_secondary_fields() -> List[str]:
    """Get secondary fields (optional but valuable)."""
    return ["media_url", "alt_text", "like_count", "comment_count", "view_count"]


def get_extended_fields() -> List[str]:
    """Get extended fields (insights/private metrics - best effort only)."""
    return ["share_count", "save_count", "reach_count", "play_count"]
