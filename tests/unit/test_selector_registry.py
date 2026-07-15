"""
Unit Tests for Selector Registry Module (src/selector_registry.py)
Test Case IDs: SR-001 to SR-004

Metodologi: Speech-Driven Development (SDD)
Format: Given-When-Then (GWT)
"""

import pytest

from src.selector_registry import (
    SELECTORS,
    get_selectors_for_field,
    get_all_field_names,
    get_primary_fields,
    get_secondary_fields,
    is_valid_post_url,
    is_valid_caption,
    is_valid_timestamp,
    is_not_empty,
    is_like_count,
    is_empty_layout,
    is_valid_data_element,
)


# ============================================================
# Test Case: SR-001 - Get Selectors by Priority
# ============================================================

class TestGetSelectorsForField:
    """SR-001: Selectors are returned sorted by priority"""

    def test_timestamp_selectors_sorted_by_priority(self):
        """
        Scenario: Selectors are returned sorted by priority

        Given field "timestamp"

        When saya memanggil get_selectors_for_field("timestamp")

        Then selectors terurut:
          1. time_datetime (priority=1)
          2. article_time (priority=2)
          3. ...dst
        """
        selectors = get_selectors_for_field("timestamp")

        # Verify sorted by priority
        priorities = [s.get("priority", 99) for s in selectors]
        assert priorities == sorted(priorities)

        # Verify first selector is the highest priority
        assert selectors[0]["name"] == "time_datetime"
        assert selectors[0]["priority"] == 1

    def test_caption_selectors_sorted_by_priority(self):
        """
        Scenario: Caption selectors sorted by priority

        Given field "caption"

        When saya memanggil get_selectors_for_field("caption")

        Then og_description adalah selector pertama (priority=1)
        """
        selectors = get_selectors_for_field("caption")

        assert selectors[0]["name"] == "og_description"
        assert selectors[0]["priority"] == 1

    def test_media_type_selectors_sorted_by_priority(self):
        """
        Scenario: Media type selectors start with URL-based detection

        Given field "media_type"

        When saya memanggil get_selectors_for_field("media_type")

        Then selector pertama adalah url_reel_check (priority=1)
        """
        selectors = get_selectors_for_field("media_type")

        assert selectors[0]["name"] == "url_reel_check"
        assert selectors[0]["priority"] == 1

    def test_unknown_field_returns_empty(self):
        """
        Scenario: Unknown field returns empty list

        Given field "unknown_field"

        When saya memanggil get_selectors_for_field

        Then returns empty list
        """
        selectors = get_selectors_for_field("unknown_field")
        assert selectors == []


class TestGetFieldNames:
    """Tests for getting field names from registry"""

    def test_get_all_field_names(self):
        """
        Scenario: System returns all registered field names

        When saya memanggil get_all_field_names

        Then list termasuk: permalink, timestamp, caption, media_type, etc.
        """
        field_names = get_all_field_names()

        assert "permalink" in field_names
        assert "timestamp" in field_names
        assert "caption" in field_names
        assert "media_type" in field_names
        assert "like_count" in field_names
        assert "comment_count" in field_names

    def test_get_primary_fields(self):
        """
        Scenario: System returns primary fields

        When saya memanggil get_primary_fields

        Then returns: permalink, timestamp, caption, media_type
        """
        primary_fields = get_primary_fields()

        assert "permalink" in primary_fields
        assert "timestamp" in primary_fields
        assert "caption" in primary_fields
        assert "media_type" in primary_fields
        assert len(primary_fields) == 4

    def test_get_secondary_fields(self):
        """
        Scenario: System returns secondary fields

        When saya memanggil get_secondary_fields

        Then returns: media_url, alt_text, like_count, comment_count
        """
        secondary_fields = get_secondary_fields()

        assert "media_url" in secondary_fields
        assert "alt_text" in secondary_fields
        assert "like_count" in secondary_fields
        assert "comment_count" in secondary_fields


# ============================================================
# Test Case: SR-002 - Validate Post URL
# ============================================================

class TestIsValidPostUrl:
    """SR-002: System validates Instagram post URLs correctly"""

    @pytest.mark.parametrize("url,expected", [
        ("https://instagram.com/p/ABC123/", True),
        ("https://www.instagram.com/p/ABC123DEF/", True),
        ("https://instagram.com/reel/GHI789/", True),
        ("https://www.instagram.com/reel/XYZ456/", True),
        ("https://instagram.com/tv/JKL012/", True),
        ("https://www.instagram.com/tv/ABC123/", True),
        # Invalid URLs
        ("https://example.com/user", False),
        ("https://instagram.com/djpbjakarta/", False),  # Profile, not post
        ("", False),
        ("not-a-url", False),
        (None, False),
    ])
    def test_is_valid_post_url(self, url, expected):
        """
        Given URLs berikut:
          | URL                                              | Valid? |
          | https://instagram.com/p/ABC123/                  | true    |
          | https://www.instagram.com/reel/DEF456/          | true    |
          | https://example.com/user                         | false   |
          | ""                                               | false   |

        When saya memanggil is_valid_post_url(url)

        Then hasil sesuai ekspektasi
        """
        result = is_valid_post_url(url)
        assert result == expected


# ============================================================
# Test Case: SR-003 - Validate Caption
# ============================================================

class TestIsValidCaption:
    """SR-003: System validates caption text"""

    @pytest.mark.parametrize("text,expected", [
        # Valid captions
        ("Detail kegiatan monitoring hari ini di Jakarta", True),
        ("Publikasi kegiatan Kanwil DJPb Bandung", True),
        ("A" * 100, True),  # Long text is valid
        # Invalid captions
        ("hi", False),  # Too short
        ("", False),  # Empty
        ("   ", False),  # Whitespace only
        ("Instagram", False),  # Noise pattern
        ("login", False),  # Noise pattern
        ("follow", False),  # Noise pattern
    ])
    def test_is_valid_caption(self, text, expected):
        """
        Given texts berikut:
          | Text                                  | Valid? | Reason                |
          | "Detail kegiatan hari ini..."         | true   | Panjang cukup         |
          | "hi"                                  | false  | Terlalu pendek        |
          | "Instagram"                           | false  | Pattern noise         |
          | ""                                    | false  | Kosong                |

        When saya memanggil is_valid_caption(text)

        Then hasil sesuai ekspektasi
        """
        result = is_valid_caption(text)
        assert result == expected

    def test_is_valid_caption_minimum_length(self):
        """
        Scenario: Caption must be at least 5 characters

        Given: "abcd" (4 chars)

        When: saya memanggil is_valid_caption

        Then: False (minimum is 5)
        """
        assert is_valid_caption("abcd") is False
        assert is_valid_caption("abcde") is True


# ============================================================
# Test Case: SR-004 - Skip Empty Layout Elements
# ============================================================

class TestIsEmptyLayout:
    """SR-004: System identifies empty layout elements correctly"""

    def test_known_empty_class_patterns(self):
        """
        Scenario: Known empty layout patterns are skipped

        Given element dengan class "x1ey2m1c" (empty spacer)

        When saya memanggil is_empty_layout

        Then: True (should be skipped)
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "class":
                    return "x1ey2m1c some-other-class"
                return ""

            def locator(self, selector):
                class MockLocator:
                    def count(self):
                        return 0
                return MockLocator()

        element = MockElement()
        result = is_empty_layout(element)
        assert result is True

    def test_layout_classes(self):
        """
        Scenario: Layout classes are identified as empty

        Given element dengan class "_a9z6"

        When saya memanggil is_empty_layout

        Then: True
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "class":
                    return "_a9z6 _a9zs"
                return ""

            def locator(self, selector):
                class MockLocator:
                    def count(self):
                        return 0
                return MockLocator()

        element = MockElement()
        result = is_empty_layout(element)
        assert result is True

    def test_element_with_data_is_not_empty(self):
        """
        Scenario: Element with actual data is not empty

        Given element dengan:
          - class: "content-card"
          - inner_text: "Detail kegiatan..."

        When saya memanggil is_empty_layout

        Then: False (has data)
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "class":
                    return "content-card"
                return ""

            def inner_text(self):
                return "Detail kegiatan monitoring"

        element = MockElement()
        result = is_empty_layout(element)
        assert result is False

    def test_none_element_returns_true(self):
        """
        Scenario: None element returns True (should be skipped)

        When saya memanggil is_empty_layout(None)

        Then: True
        """
        assert is_empty_layout(None) is True


# ============================================================
# Additional Validation Tests
# ============================================================

class TestIsValidTimestamp:
    """Tests for is_valid_timestamp function"""

    @pytest.mark.parametrize("value,expected", [
        ("2026-06-15T10:30:00Z", True),
        ("2026-06-15", True),
        ("2026-06-15T10:30:00+07:00", True),
        ("June 15, 2026", False),  # No YYYY-MM-DD pattern
        ("", False),
        (None, False),
    ])
    def test_is_valid_timestamp(self, value, expected):
        result = is_valid_timestamp(value)
        assert result == expected


class TestIsNotEmpty:
    """Tests for is_not_empty function"""

    @pytest.mark.parametrize("value,expected", [
        ("some text", True),
        ("123", True),
        ("", False),
        ("   ", False),  # Whitespace only
        (None, False),
    ])
    def test_is_not_empty(self, value, expected):
        result = is_not_empty(value)
        assert result == expected


class TestIsLikeCount:
    """Tests for is_like_count function"""

    @pytest.mark.parametrize("value,expected", [
        ("1234", True),
        ("1,234", True),
        ("1.5K", True),
        ("2.3M", True),
        ("abc", False),
        ("", False),
        ("likes", False),
    ])
    def test_is_like_count(self, value, expected):
        result = is_like_count(value)
        assert result == expected


class TestIsValidDataElement:
    """Tests for is_valid_data_element function"""

    def test_element_with_image_src_is_valid(self):
        """
        Scenario: Element with image src containing external URL is valid

        Given element dengan src="https://example.com/image.jpg"

        When saya memanggil is_valid_data_element

        Then: True
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "src":
                    return "https://example.com/image.jpg"
                return ""

        element = MockElement()
        result = is_valid_data_element(element)
        assert result is True

    def test_element_with_alt_text_is_valid(self):
        """
        Scenario: Element with alt text is valid

        Given element dengan alt="Description of image"

        When saya memanggil is_valid_data_element

        Then: True
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "alt":
                    return "Description of image"
                return ""

        element = MockElement()
        result = is_valid_data_element(element)
        assert result is True

    def test_instagram_src_is_invalid(self):
        """
        Scenario: Element with instagram.com in src is not valid for scraping

        Given element dengan src="https://instagram.com/image.jpg"

        When saya memanggil is_valid_data_element

        Then: False
        """
        class MockElement:
            def get_attribute(self, attr):
                if attr == "src":
                    return "https://instagram.com/image.jpg"
                return ""

        element = MockElement()
        result = is_valid_data_element(element)
        assert result is False

    def test_none_element_returns_false(self):
        """None element returns False"""
        result = is_valid_data_element(None)
        assert result is False


# ============================================================
# Registry Structure Tests
# ============================================================

class TestSelectorRegistryStructure:
    """Tests for selector registry structure"""

    def test_all_fields_have_selectors(self):
        """
        Scenario: All registered fields have at least one selector

        When saya memeriksa SELECTORS

        Then setiap field memiliki list dengan minimal 1 selector
        """
        for field_name, selectors in SELECTORS.items():
            assert len(selectors) > 0, f"Field {field_name} has no selectors"

    def test_all_selectors_have_priority(self):
        """
        Scenario: All selectors have priority defined

        When saya memeriksa semua selectors

        Then setiap selector memiliki field "priority"
        """
        for field_name, selectors in SELECTORS.items():
            for selector in selectors:
                assert "priority" in selector, f"Selector in {field_name} missing priority"

    def test_timestamp_has_meta_fallback(self):
        """
        Scenario: Timestamp field has meta-based fallback selectors

        When saya memeriksa timestamp selectors

        Then ada selector dengan type "meta"
        """
        selectors = get_selectors_for_field("timestamp")
        meta_selectors = [s for s in selectors if s.get("type") == "meta"]
        assert len(meta_selectors) > 0

    def test_caption_has_og_fallback(self):
        """
        Scenario: Caption field has og:description as primary source

        When saya memeriksa caption selectors

        Then og_description adalah selector pertama
        """
        selectors = get_selectors_for_field("caption")
        assert selectors[0]["name"] == "og_description"
        assert selectors[0]["type"] == "meta"