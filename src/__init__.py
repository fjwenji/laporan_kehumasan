"""
Mayz - DJPb Social Media Reporting Tool
Package exports
"""

from src.parser import (
    AccountRow,
    ScrapeRow,
    extract_shortcode,
    normalize_url,
    clean_caption,
    parse_dt_to_wib,
    parse_number_token,
    parse_engagement_from_text,
    extract_caption_from_meta,
    status_periode,
)

from src.extraction_utils import (
    ExtractionResult,
    FieldStatus,
    extract_from_html_string,
    detect_media_type,
    parse_timestamp,
    safe_text,
    safe_int,
    clean_caption as extraction_clean_caption,
    get_meta_content,
    get_body_text_filtered,
    parse_engagement_from_text as extraction_parse_engagement,
    get_valid_elements,
    get_element_attr,
    extract_shortcode as extraction_shortcode,
    normalize_instagram_url,
    extract_with_fallback,
    classify_status as extraction_classify_status,
)

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
    get_all_field_names,
    get_primary_fields,
    get_secondary_fields,
)

from src.validation_utils import (
    detect_login_wall,
    detect_page_not_found,
    detect_rate_limit,
    detect_something_wrong,
    classify_status,
    needs_debug_save,
    is_valid_caption as validation_is_valid_caption,
    is_valid_timestamp as validation_is_valid_timestamp,
    is_valid_post_url as validation_is_valid_post_url,
    is_valid_shortcode,
    SCRAPING_STATUS_DISPLAY,
    get_status_display,
)

# Database modules (lazy import to avoid connection errors at import time)
# Use: from src.database import test_connection, init_database
# Use: from src.db_repository import get_active_accounts, upsert_post, etc.


def normalize_instagram_url_safe(url: str) -> str:
    """Normalize Instagram URL to standard format."""
    return normalize_instagram_url(url)

def extract_shortcode_safe(url: str) -> str:
    """Extract shortcode from Instagram URL."""
    return extract_shortcode(url) if 'extract_shortcode' in dir() else extraction_shortcode(url)
