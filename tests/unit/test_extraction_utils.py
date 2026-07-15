"""
Unit Tests for Extraction Utilities Module (src/extraction_utils.py)
Test Case IDs: EU-001 to EU-005

Metodologi: Speech-Driven Development (SDD)
Format: Given-When-Then (GWT)
"""

import pytest
from datetime import datetime

from src.extraction_utils import (
    safe_text,
    safe_int,
    make_naive_datetime,
    clean_caption,
    parse_timestamp,
    parse_engagement_from_text,
    extract_shortcode,
    normalize_instagram_url,
    extract_from_html_string,
    classify_status,
    FieldStatus,
)


# ============================================================
# Test Case: EU-001 & EU-002 - Multi-Selector Fallback
# ============================================================

class TestMultiSelectorFallback:
    """EU-001 & EU-002: Multi-selector fallback behavior"""

    def test_extract_from_html_string_basic(self):
        """
        EU-003: System extracts data from raw HTML using BeautifulSoup

        Given HTML string dengan:
          - <meta property="og:description" content="Caption test">
          - <time datetime="2026-06-15T10:00:00Z">

        When saya memanggil extract_from_html_string(html)

        Then hasil["caption"] = "Caption test"
        And hasil["timestamp"] = "2026-06-15T10:00:00Z"
        """
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="og:description" content="Caption dari kegiatan monitoring">
            <meta property="og:url" content="https://www.instagram.com/p/ABC123/">
        </head>
        <body>
            <time datetime="2026-06-15T10:00:00Z"></time>
            <article>
                <img src="https://example.com/image.jpg" alt="Foto kegiatan">
            </article>
        </body>
        </html>
        '''

        result = extract_from_html_string(html)

        assert "caption" in result
        assert "Caption dari kegiatan monitoring" in result["caption"]
        assert "timestamp" in result
        assert "2026-06-15" in result["timestamp"]

    def test_extract_from_html_canonical_url(self):
        """
        Scenario: System extracts canonical URL from HTML

        Given HTML dengan <link rel="canonical" href="https://instagram.com/p/DEF456/">

        When saya memanggil extract_from_html_string

        Then hasil["permalink"] = canonical URL
        """
        html = '''
        <html>
        <head>
            <link rel="canonical" href="https://www.instagram.com/p/DEF456/">
        </head>
        </html>
        '''

        result = extract_from_html_string(html)

        assert "permalink" in result
        assert "DEF456" in result["permalink"]

    def test_extract_from_html_media_info(self):
        """
        Scenario: System extracts media URL and alt text

        Given HTML dengan div._aagv img

        When saya memanggil extract_from_html_string

        Then hasil["media_url"] dan hasil["alt_text"] terisi
        """
        html = '''
        <html>
        <body>
            <div class="_aagv">
                <img src="https://example.com/foto.jpg" alt="Foto kegiatan monitoring DJPb">
            </div>
        </body>
        </html>
        '''

        result = extract_from_html_string(html)

        assert "media_url" in result
        assert "alt_text" in result

    def test_extract_from_html_like_count(self):
        """
        Scenario: System extracts like count from HTML structure

        Given HTML dengan span.x1ypdohk containing "1,234"

        When saya memanggil extract_from_html_string

        Then hasil["like_count"] = 1234
        """
        html = '''
        <html>
        <body>
            <span class="x1ypdohk">1,234</span>
        </body>
        </html>
        '''

        result = extract_from_html_string(html)

        assert "like_count" in result
        assert result["like_count"] == 1234


# ============================================================
# Test Case: EU-004 - Clean Caption from Noise
# ============================================================

class TestCleanCaption:
    """EU-004: System removes Instagram engagement prefix from caption"""

    def test_clean_caption_removes_engagement_prefix(self):
        """
        Scenario: System removes Instagram engagement prefix from caption

        Given caption: "1,234 likes, 56 comments - djpbjakarta on June 15, 2026: Detail kegiatan..."

        When saya memanggil clean_caption(text)

        Then prefix "1,234 likes..." dihapus
        And hasil tidak dimulai dengan angka
        """
        caption = "1,234 likes, 56 comments - djpbjakarta on June 15, 2026: Detail kegiatan monitoring di Jakarta"
        result = clean_caption(caption)

        # Should not start with numbers
        assert not result[0].isdigit() if result else True
        # Should contain the actual caption
        assert "Detail kegiatan" in result

    def test_clean_caption_removes_quotes(self):
        """
        Scenario: System removes leading quotes

        Given caption: '"Detail kegiatan"'

        When saya memanggil clean_caption

        Then quotes dihapus
        """
        result = clean_caption('"Detail kegiatan"')
        assert result == "Detail kegiatan"

    def test_clean_caption_max_length(self):
        """
        Scenario: System truncates long captions

        Given caption: 1500 karakter

        When saya memanggil clean_caption(caption, max_len=800)

        Then hasil max 803 karakter (800 + "...")
        """
        long_text = "A" * 1500
        result = clean_caption(long_text, max_len=800)

        assert len(result) <= 803

    def test_clean_caption_emoji_removal(self):
        """
        Scenario: System removes emoji characters

        Given caption dengan emoji

        When saya memanggil clean_caption

        Then emoji dihapus
        """
        caption = "Detail kegiatan📢 monitoring 🏛️ DJPb"
        result = clean_caption(caption)

        # Should not contain emoji
        assert "📢" not in result
        assert "🏛️" not in result


# ============================================================
# Test Case: EU-005 - Classify Status
# ============================================================

class TestClassifyStatus:
    """EU-005: System classifies scraping status based on field availability"""

    def test_full_success_classification(self):
        """
        Scenario: All primary fields present = FULL_SUCCESS

        Given fields:
          - caption: OK
          - timestamp: OK
          - permalink: OK
          - media_type: OK (Image/Reels/etc)
          - like_count: OK
          - comment_count: OK

        When saya memanggil classify_status(fields)

        Then hasil[0] = "FULL_SUCCESS"
        """
        fields = {
            "caption": FieldStatus("caption", value="Caption text", status="OK"),
            "timestamp": FieldStatus("timestamp", value="2026-06-15", status="OK"),
            "permalink": FieldStatus("permalink", value="https://...", status="OK"),
            "media_type": FieldStatus("media_type", value="Image", status="OK"),
            "like_count": FieldStatus("like_count", value=100, status="OK"),
            "comment_count": FieldStatus("comment_count", value=10, status="OK"),
        }

        status, message, reasons = classify_status(fields)

        assert status == "FULL_SUCCESS"

    def test_partial_success_classification(self):
        """
        Scenario: Primary fields OK but engagement NULL = PARTIAL_SUCCESS

        Given fields:
          - caption: OK
          - timestamp: OK
          - permalink: OK
          - media_type: OK
          - like_count: NULL
          - comment_count: NULL

        When saya memanggil classify_status(fields)

        Then hasil[0] = "PARTIAL_SUCCESS"
        """
        fields = {
            "caption": FieldStatus("caption", value="Caption text", status="OK"),
            "timestamp": FieldStatus("timestamp", value="2026-06-15", status="OK"),
            "permalink": FieldStatus("permalink", value="https://...", status="OK"),
            "media_type": FieldStatus("media_type", value="Image", status="OK"),
            "like_count": FieldStatus("like_count", value=None, status="NULL"),
            "comment_count": FieldStatus("comment_count", value=None, status="NULL"),
        }

        status, message, reasons = classify_status(fields)

        assert status == "PARTIAL_SUCCESS"

    def test_caption_null_classification(self):
        """
        Scenario: Caption NULL = CAPTION_NULL

        Given fields dengan caption = None

        When saya memanggil classify_status

        Then hasil[0] = "CAPTION_NULL"
        """
        fields = {
            "caption": FieldStatus("caption", value=None, status="NULL", null_reason="NOT_FOUND"),
            "timestamp": FieldStatus("timestamp", value="2026-06-15", status="OK"),
            "permalink": FieldStatus("permalink", value="https://...", status="OK"),
        }

        status, message, reasons = classify_status(fields)

        assert status == "CAPTION_NULL"

    def test_timestamp_null_classification(self):
        """
        Scenario: Timestamp NULL = TIMESTAMP_NULL

        Given fields dengan timestamp = None

        When saya memanggil classify_status

        Then hasil[0] = "TIMESTAMP_NULL"
        """
        fields = {
            "caption": FieldStatus("caption", value="Caption text", status="OK"),
            "timestamp": FieldStatus("timestamp", value=None, status="NULL", null_reason="NOT_FOUND"),
            "permalink": FieldStatus("permalink", value="https://...", status="OK"),
        }

        status, message, reasons = classify_status(fields)

        assert status == "TIMESTAMP_NULL"

    def test_reasons_includes_null_fields(self):
        """
        Scenario: Classification includes reasons for null fields

        Given fields dengan caption dan like_count NULL

        When saya memanggil classify_status

        Then reasons list berisi alasan untuk field yang NULL
        """
        fields = {
            "caption": FieldStatus("caption", value=None, status="NULL", null_reason="ELEMENT_NOT_FOUND"),
            "timestamp": FieldStatus("timestamp", value="2026-06-15", status="OK"),
            "permalink": FieldStatus("permalink", value="https://...", status="OK"),
            "like_count": FieldStatus("like_count", value=None, status="NULL"),
            "comment_count": FieldStatus("comment_count", value=None, status="NULL"),
        }

        status, message, reasons = classify_status(fields)

        assert len(reasons) > 0
        assert any("Caption" in r for r in reasons)


# ============================================================
# Utility Function Tests
# ============================================================

class TestSafeText:
    """Tests for safe_text utility"""

    def test_safe_text_none(self):
        """Given: None -> returns empty string"""
        assert safe_text(None) == ""

    def test_safe_text_strips_whitespace(self):
        """Given: "  text  " -> returns "text" """
        assert safe_text("  text  ") == "text"

    def test_safe_text_converts_int(self):
        """Given: 123 -> returns "123" """
        assert safe_text(123) == "123"

    def test_safe_text_handles_null_strings(self):
        """Given: "null", "None" -> returns empty string"""
        assert safe_text("null") == ""
        assert safe_text("None") == ""
        assert safe_text("undefined") == ""


class TestSafeInt:
    """Tests for safe_int utility"""

    def test_safe_int_direct(self):
        """Given: 123 (int) -> returns 123"""
        assert safe_int(123) == 123

    def test_safe_int_string(self):
        """Given: "1234" -> returns 1234"""
        assert safe_int("1234") == 1234

    def test_safe_int_with_comma(self):
        """Given: "1,234" -> returns 1234"""
        assert safe_int("1,234") == 1234

    def test_safe_int_with_k_suffix(self):
        """Given: "1.5K" -> returns 1500"""
        assert safe_int("1.5K") == 1500

    def test_safe_int_with_m_suffix(self):
        """Given: "2.3M" -> returns 2300000"""
        assert safe_int("2.3M") == 2300000

    def test_safe_int_none(self):
        """Given: None -> returns None"""
        assert safe_int(None) is None

    def test_safe_int_invalid(self):
        """Given: "abc" -> returns None"""
        assert safe_int("abc") is None


class TestMakeNaiveDatetime:
    """Tests for make_naive_datetime utility"""

    def test_make_naive_strips_timezone(self):
        """
        Scenario: System strips timezone from datetime

        Given: datetime dengan tzinfo

        When: saya memanggil make_naive_datetime

        Then: hasil.tzinfo is None
        """
        from zoneinfo import ZoneInfo

        aware_dt = datetime(2026, 6, 15, 10, 30, tzinfo=ZoneInfo("Asia/Jakarta"))
        result = make_naive_datetime(aware_dt)

        assert result.tzinfo is None
        assert result == datetime(2026, 6, 15, 10, 30)

    def test_make_naive_preserves_naive(self):
        """
        Scenario: Naive datetime unchanged

        Given: datetime tanpa tzinfo

        When: saya memanggil make_naive_datetime

        Then: hasil sama dengan input
        """
        naive_dt = datetime(2026, 6, 15, 10, 30)
        result = make_naive_datetime(naive_dt)

        assert result == naive_dt
        assert result.tzinfo is None


class TestParseTimestamp:
    """Tests for parse_timestamp function"""

    def test_parse_iso_format(self):
        """Parse ISO format with Z suffix"""
        result = parse_timestamp("2026-06-15T10:30:00Z")
        assert result is not None
        assert result.year == 2026

    def test_parse_iso_with_timezone(self):
        """Parse ISO format with timezone offset"""
        result = parse_timestamp("2026-06-15T10:30:00+07:00")
        assert result is not None

    def test_parse_date_only(self):
        """Parse date-only format"""
        result = parse_timestamp("2026-06-15")
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 15

    def test_parse_readable_format(self):
        """Parse readable date format"""
        result = parse_timestamp("June 15, 2026")
        assert result is not None

    def test_parse_invalid_returns_none(self):
        """Invalid date string returns None"""
        result = parse_timestamp("not-a-date")
        assert result is None


class TestExtractShortcode:
    """Tests for extract_shortcode function"""

    @pytest.mark.parametrize("url,expected", [
        ("https://instagram.com/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/reel/DEF456/", "DEF456"),
        ("https://instagram.com/tv/GHI789/", "GHI789"),
        ("not-a-url", ""),
        ("", ""),
    ])
    def test_extract_shortcode(self, url, expected):
        result = extract_shortcode(url)
        assert result == expected


class TestNormalizeInstagramUrl:
    """Tests for normalize_instagram_url function"""

    def test_normalize_adds_p_format(self):
        """Given shortcode -> returns full URL with /p/ format"""
        result = normalize_instagram_url("https://instagram.com/p/ABC123/")
        assert result == "https://www.instagram.com/p/ABC123/"

    def test_normalize_preserves_existing(self):
        """Given full URL -> returns unchanged"""
        url = "https://www.instagram.com/p/ABC123DEF/"
        result = normalize_instagram_url(url)
        assert result == url


class TestParseEngagement:
    """Tests for parse_engagement_from_text function"""

    def test_parse_likes_and_comments(self):
        """Parse both likes and comments from text"""
        text = "Post dengan 5,432 likes dan 123 komentar"
        likes, comments = parse_engagement_from_text(text)

        assert likes == 5432
        assert comments == 123

    def test_parse_likes_only(self):
        """Parse likes only"""
        text = "5,432 likes"
        likes, comments = parse_engagement_from_text(text)

        assert likes == 5432
        assert comments is None

    def test_parse_with_suffix(self):
        """Parse numbers with K/M suffix"""
        text = "This has 1.5K likes"
        likes, comments = parse_engagement_from_text(text)

        assert likes == 1500


class TestFieldStatus:
    """Tests for FieldStatus dataclass"""

    def test_field_status_creation(self):
        """Create FieldStatus with all fields"""
        field = FieldStatus(
            field_name="caption",
            value="Test caption",
            status="OK",
            source="og_description",
            selector_used="meta[property='og:description']"
        )

        assert field.field_name == "caption"
        assert field.value == "Test caption"
        assert field.status == "OK"

    def test_field_status_defaults(self):
        """FieldStatus with default values"""
        field = FieldStatus(field_name="test")

        assert field.value is None
        assert field.status == "NULL"
        assert field.null_reason == ""
