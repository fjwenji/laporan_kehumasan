"""
Database Repository - CRUD operations untuk semua tabel.
Single source of truth untuk akses data.
"""

import base64
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import unquote
from src.database import get_db_cursor, get_connection_params

def decode_instagram_efg_markers(html_content: str) -> Tuple[bool, str]:
    """
    Decode Instagram efg markers from img src URLs.

    Instagram encodes metadata in the 'efg' query parameter of image URLs.
    When decoded, carousel items contain "CAROUSEL_ITEM" in the payload.

    Example HTML may contain &amp; encoding:
    ...&amp;efg=eyJ2ZW5jb2RlX3RhZyI6IkNBUk9VU0VMX0lURU0ueHBpZHMuMTA4MC5zZHIucmVndWxhcl9waG90by5DMyJ9

    Returns:
        Tuple of (is_carousel, reason)
        - is_carousel: True if CAROUSEL_ITEM marker found
        - reason: Explanation of detection
    """
    import html as html_lib
    import base64 as b64_module
    import urllib.parse as url_lib

    if not html_content:
        return (False, "")

    html_text = html_lib.unescape(html_content)
    efg_pattern = r'efg=([^&\s"\'<>]+)'
    matches = re.findall(efg_pattern, html_text)

    for efg_value in matches:
        try:
            # Step 1: URL decode
            decoded = url_lib.unquote(efg_value)

            # Step 2: Add padding if needed (base64 requires padding)
            padding_needed = 4 - (len(decoded) % 4)
            if padding_needed < 4:
                decoded += '=' * padding_needed

            # Step 3: URL-safe base64 decode
            # Replace - with + and _ with / for standard base64
            decoded_standard = decoded.replace('-', '+').replace('_', '/')

            # Step 4: Decode base64 to bytes (manual decode to handle errors)
            try:
                decoded_bytes = b64_module.b64decode(decoded_standard)
            except Exception:
                try:
                    decoded_bytes = b64_module.b64decode(decoded_standard + '==')
                except Exception:
                    decoded_bytes = b64_module.b64decode(decoded_standard + '=')

            # Step 5: Convert to string
            decoded_str = decoded_bytes.decode('utf-8', errors='ignore')

            # Step 6: Check for CAROUSEL_ITEM marker
            if 'CAROUSEL_ITEM' in decoded_str:
                return (True, "efg decoded contains CAROUSEL_ITEM")

        except Exception:
            # Silently continue on decode errors
            continue

    return (False, "")


def is_valid_instagram_post_url(url: str) -> Tuple[bool, str]:
    """
    Validate if URL is a valid Instagram post URL.

    This prevents invalid URLs like chrome-error://chromewebdata/ from being inserted.

    Valid patterns:
    - https://www.instagram.com/p/{shortcode}/
    - https://instagram.com/p/{shortcode}/
    - https://www.instagram.com/reel/{shortcode}/
    - https://www.instagram.com/tv/{shortcode}/

    Returns:
        Tuple of (is_valid, reason)
    """
    if not url:
        return (False, "URL kosong")

    url_lower = url.lower()

    # Reject common invalid patterns
    invalid_patterns = [
        'chrome-error',
        'chromewebdata',
        'about:blank',
        'data:',
        'file://',
    ]
    for pattern in invalid_patterns:
        if pattern in url_lower:
            return (False, f"URL mengandung pola tidak valid: {pattern}")

    # Must start with https://www.instagram.com or https://instagram.com
    if not (url_lower.startswith('https://www.instagram.com/') or
            url_lower.startswith('https://instagram.com/')):
        return (False, "URL bukan dari instagram.com")

    # Must contain /p/, /reel/, or /tv/
    path_valid = '/p/' in url_lower or '/reel/' in url_lower or '/tv/' in url_lower
    if not path_valid:
        return (False, "URL tidak mengandung /p/, /reel/, atau /tv/")

    return (True, "URL valid")


def parse_indonesian_number(text: str) -> Optional[int]:
    """
    Parse Indonesian number format to integer.

    Most common cases from Instagram:
    - "1.534" -> 1534 (thousand separator - most common)
    - "12.345" -> 12345 (thousand separator)
    - "2 jt" -> 2000000 (suffix juta)
    - "1,5 rb" -> 1500 (decimal comma + suffix ribu)
    - "328" -> 328 (plain number)
    - "153" -> 153 (plain number)

    Note: "1.2jt" (1.2 juta) is rare in real Instagram pages.
    """
    if not text:
        return None

    original = str(text).strip().lower()

    # Remove extra whitespace
    original = re.sub(r'\s+', ' ', original)

    # Check for suffix first
    multiplier = 1
    has_suffix_juta = 'jt' in original or 'juta' in original
    has_suffix_ribu = 'rb' in original or 'ribu' in original

    if has_suffix_juta:
        multiplier = 1000000
        original = re.sub(r'\bjt\b|\bjuta\b', '', original).strip()
    elif has_suffix_ribu:
        multiplier = 1000
        original = re.sub(r'\brb\b|\bribu\b', '', original).strip()

    # Handle decimal comma format like "1,5 rb" or "1,2 jt"
    # Pattern: number with comma followed by digits, like "1,5" or "2,3"
    decimal_comma_match = re.match(r'^(\d+),(\d+)(.*)$', original)
    if decimal_comma_match:
        whole_part = decimal_comma_match.group(1)
        decimal_part = decimal_comma_match.group(2)
        remainder = decimal_comma_match.group(3).strip()

        # Check if there's a multiplier suffix in remainder
        if 'jt' in remainder or 'juta' in remainder:
            multiplier = 1000000
        elif 'rb' in remainder or 'ribu' in remainder:
            multiplier = 1000

        # Parse: "1,5" -> 1.5 -> 1.5 * multiplier
        try:
            value = float(f"{whole_part}.{decimal_part}")
            return int(value * multiplier)
        except (ValueError, TypeError):
            pass

    # Standard case: remove all dots (thousand separators) and parse
    # But keep dots if they're thousand separators (like 1.234)
    cleaned = original

    # Remove dots that are thousand separators (between digits)
    # But keep dots that might be decimal points followed by 3 digits (unlikely in Indonesian)
    # Actually, Indonesian uses dots for thousand separators and commas for decimals
    # So "1.534" = 1534, not 1.534

    # Remove all dots first (thousand separator)
    cleaned = cleaned.replace('.', '')

    # Handle comma as decimal point
    if ',' in cleaned:
        # "1,5" should be 1.5 for multiplier calculations
        parts = cleaned.split(',')
        if len(parts) == 2:
            # Check if it's a decimal (single digit after comma) or thousand separator
            if len(parts[1]) <= 2:
                # Likely decimal: "1,5" or "2,3"
                try:
                    cleaned = parts[0] + '.' + parts[1]
                except Exception:
                    pass

    # Extract digits only
    digits = re.findall(r'\d+', cleaned)
    if not digits:
        return None

    # For thousand separator case like "5.790", after removing dots we get "5790"
    # This works because we removed all dots
    num_str = ''.join(digits)

    try:
        result = int(num_str) * multiplier
        # Reasonable bounds check (views should be > 0 and < 1B)
        if result > 0 and result < 1_000_000_000:
            return result
        return None
    except (ValueError, TypeError):
        return None


def parse_view_count_from_html(html_content: str) -> Tuple[Optional[int], str]:
    """
    Parse view count from Instagram Reels/video page.

    Marker HTML:
    <svg aria-label="Ikon Lihat Jumlah">
    <title>Ikon Lihat Jumlah</title>
    ...
    <span>1.534</span>

    Rules:
    - View count only for Reels/video
    - Don't confuse with like count, comment count, or date
    - Parse Indonesian format: 1.534 -> 1534

    Returns:
        Tuple of (view_count, source)
        - view_count: integer or None
        - source: explanation of where the value came from
    """
    if not html_content:
        return (None, "HTML kosong")

    # Check for "Ikon Lihat Jumlah" marker
    if 'Ikon Lihat Jumlah' not in html_content:
        return (None, "Tidak ada marker 'Ikon Lihat Jumlah'")

    # Pattern 1: Direct span after "Ikon Lihat Jumlah"
    # <title>Ikon Lihat Jumlah</title>...<span>1.534</span>
    pattern1 = r'Ikon Lihat Jumlah[^<]*</title>[^<]*<span[^>]*>([\d.,\s]+)</span>'
    match1 = re.search(pattern1, html_content, re.DOTALL)
    if match1:
        raw_value = match1.group(1).strip()
        view_count = parse_indonesian_number(raw_value)
        if view_count is not None and view_count > 0:
            return (view_count, f"Parsed dari span dekat marker: {raw_value}")

    # Pattern 2: aria-label with "Ikon Lihat Jumlah"
    # <svg aria-label="Ikon Likut Jumlah">...<span>...</span>
    pattern2 = r'aria-label="Ikon Lihat Jumlah"[^>]*>.*?<span[^>]*>([\d.,\s]+)</span>'
    match2 = re.search(pattern2, html_content, re.DOTALL)
    if match2:
        raw_value = match2.group(1).strip()
        view_count = parse_indonesian_number(raw_value)
        if view_count is not None and view_count > 0:
            return (view_count, f"Parsed dari aria-label span: {raw_value}")

    # Pattern 3: Search all spans with number patterns near the marker
    # Look for spans in a section containing the marker
    section_pattern = r'(Ikon Lihat Jumlah.{0,500})'
    sections = re.findall(section_pattern, html_content, re.DOTALL)
    for section in sections:
        # Find all spans in this section
        spans = re.findall(r'<span[^>]*>([\d.,\s]+)</span>', section)
        for span_value in spans:
            view_count = parse_indonesian_number(span_value)
            # View count should be at least 3 digits for Reels (usually > 100)
            if view_count is not None and view_count >= 100:
                return (view_count, f"Parsed dari section marker: {span_value}")

    return (None, "Tidak dapat parse view count dari marker")


def detect_carousel_from_html(html_content: str) -> Tuple[str, str]:
    """
    Detect carousel from raw HTML content.

    CAROUSEL MARKERS (clear evidence - set carousel):
    1. aria-label="Carousel" or aria-label containing "Carousel"
    2. SVG with aria-label "Carousel"
    3. <title>Carousel</title>
    4. alt="Carousel"
    5. GraphSidecar in page data
    6. edge_sidecar_to_children in page data
    7. carousel_media in page data
    8. sidecar in page data
    9. decoded efg contains CAROUSEL_ITEM

    IMAGE MARKERS (set image - only if no carousel marker):
    1. og:image meta tag present
    2. <img> tag present
    3. Has meaningful content (not login wall)

    Returns: Tuple of (result, reason)
    - result: 'carousel', 'image', or 'unknown'
    - reason: explanation for the detection
    """
    if not html_content:
        return ("unknown", "HTML kosong")

    content_lower = html_content.lower()

    # ============================================
    # CAROUSEL MARKERS - CLEAR EVIDENCE
    # ============================================

    # 1. SVG with aria-label="Carousel" - MOST RELIABLE
    if 'svg' in content_lower and 'aria-label="carousel"' in content_lower:
        return ("carousel", "SVG dengan aria-label='Carousel'")

    if 'svg' in content_lower and 'aria-label="foto carousel"' in content_lower:
        return ("carousel", "SVG dengan aria-label='Foto Carousel'")

    # 2. Title tag with Carousel
    import re
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
    if title_match and 'carousel' in title_match.group(1).lower():
        return ("carousel", f"Title tag mengandung 'Carousel': {title_match.group(1)[:50]}")

    # 3. aria-label containing Carousel anywhere
    aria_carousel = re.findall(r'aria-label="([^"]*[Cc]arousel[^"]*)"', html_content)
    for aria in aria_carousel:
        if 'carousel' in aria.lower():
            return ("carousel", f"aria-label mengandung 'Carousel': '{aria}'")

    # 4. alt="Carousel"
    alt_carousel = re.findall(r'alt="([^"]*[Cc]arousel[^"]*)"', html_content)
    for alt in alt_carousel:
        if 'carousel' in alt.lower():
            return ("carousel", f"alt attribute mengandung 'Carousel': '{alt}'")

    # 5. GraphSidecar / edge_sidecar_to_children - GraphQL indicators
    if 'graphsidecar' in content_lower:
        return ("carousel", "GraphSidecar dalam page data")

    if 'edge_sidecar_to_children' in content_lower:
        return ("carousel", "edge_sidecar_to_children dalam page data")

    if 'carousel_media' in content_lower:
        return ("carousel", "carousel_media dalam page data")

    if 'sidecar' in content_lower:
        return ("carousel", "sidecar dalam page data")

    # 6. Instagram efg marker decoding
    efg_is_carousel, efg_reason = decode_instagram_efg_markers(html_content)
    if efg_is_carousel:
        return ("carousel", efg_reason)

    # 7. Specific carousel button indicators
    if 'role="button"' in content_lower and 'carousel' in content_lower:
        # Check if there's a button specifically for carousel
        carousel_buttons = re.findall(r'aria-label="([^"]*next[^"]*)"', html_content, re.IGNORECASE)
        for btn in carousel_buttons:
            if 'carousel' in btn.lower() or 'foto' in btn.lower():
                return ("carousel", f"Carousel navigation button: '{btn}'")

    # ============================================
    # IMAGE MARKERS - Only if no carousel marker
    # ============================================

    # Image indicators (only if no carousel found)
    image_markers = [
        'og:image',
        'property="og:image"',
        'twitter:image',
    ]

    has_image_meta = any(marker in content_lower for marker in image_markers)
    has_img_tag = '<img' in content_lower

    # Check if page has meaningful content (not login wall)
    login_wall_indicators = [
        'log in to continue',
        'sign up to continue',
        '/accounts/login',
        '/accounts/signup',
        'forgot password',
    ]

    is_login_wall = any(indicator in content_lower for indicator in login_wall_indicators)

    if not is_login_wall and (has_image_meta or has_img_tag):
        # Check if it's NOT a video (reels/tv already handled by URL)
        video_indicators = ['video', 'playbutton', 'reels']
        has_video = any(marker in content_lower for marker in video_indicators)

        if not has_video:
            marker_found = "og:image meta" if has_image_meta else "img tag"
            return ("image", f"Halaman detail terbuka normal, {marker_found} terdeteksi, tidak ada video marker")

    # Check for post content indicators (caption, timestamp)
    has_post_content = (
        ('og:description' in content_lower or 'og:title' in content_lower) and
        len(html_content) > 10000  # Minimum content length
    )

    if not is_login_wall and has_post_content:
        return ("image", "Halaman detail terbuka, ada meta tags, tidak ada carousel marker")

    # If we can't determine, stay unknown
    if is_login_wall:
        return ("unknown", "Login wall terdeteksi")

    return ("unknown", "Tidak ada marker carousel/image yang jelas")


def detect_image_from_html(html_content: str) -> Tuple[str, str]:
    """
    Detect single image from raw HTML content.

    If we can read the page and there's no carousel marker,
    and we see image/video indicators, it's likely an image.

    Returns: Tuple of (result, reason)
    - result: 'image' or 'unknown'
    - reason: explanation
    """
    if not html_content:
        return ("unknown", "HTML kosong")

    content_lower = html_content.lower()

    # Image indicators
    image_markers = [
        'og:image',
        'property="og:image"',
        'twitter:image',
        '<img',
        '.jpg',
        '.jpeg',
        '.png',
    ]

    # Check if page has image content (not just login wall/error)
    has_image = any(marker in content_lower for marker in image_markers)

    if has_image:
        # Check if it's NOT a video (reels/tv already handled by URL)
        video_indicators = ['video', 'playbutton', 'reels']
        has_video = any(marker in content_lower for marker in video_indicators)

        if not has_video:
            marker = "og:image" if 'og:image' in content_lower else "img tag"
            return ("image", f"Image marker ({marker}) terdeteksi, tidak ada video marker")

    # Check for post content indicators
    has_post_content = (
        ('og:description' in content_lower or 'og:title' in content_lower) and
        len(html_content) > 10000
    )

    if not has_image and has_post_content:
        return ("image", "Halaman detail terbuka, ada meta content")

    return ("unknown", "Tidak ada bukti image yang jelas")


def normalize_media_type(
    post_url: str,
    page_data: dict = None,
    existing_media_type: str = None,
    html_content: str = None,
) -> Tuple[str, str]:
    """
    Normalize media type to standard values: image, carousel, reels, video, unknown.

    Priority rules:
    1. /reel/ in URL = reels
    2. /tv/ in URL = video
    3. HTML content with clear carousel markers = carousel
    4. HTML content showing image (no carousel) = image
    5. Otherwise = unknown

    Args:
        post_url: Instagram post URL
        page_data: Optional dict from page scraping
        existing_media_type: Original media_type value if available
        html_content: Raw HTML content for carousel/image detection

    Returns:
        Tuple of (normalized_type, reason)
        - normalized_type: image, carousel, reels, video, or unknown
        - reason: explanation for the detection
    """
    if not post_url:
        return ("unknown", "URL kosong")

    url_lower = post_url.lower()

    # 1. Check URL path first (most reliable)
    if "/reel/" in url_lower:
        return ("reels", "URL mengandung /reel/")
    if "/tv/" in url_lower:
        return ("video", "URL mengandung /tv/")

    # 2. /p/ path - check HTML content for carousel markers
    if "/p/" in url_lower:
        # Check HTML content for clear carousel markers
        if html_content:
            carousel_result, carousel_reason = detect_carousel_from_html(html_content)
            if carousel_result == "carousel":
                return ("carousel", carousel_reason)

        # Check page_data for GraphSidecar indicators
        if page_data:
            try:
                data_str = str(page_data).lower()

                # Clear carousel indicators
                if "graphsidecar" in data_str:
                    return ("carousel", "GraphSidecar dalam page_data")
                if "edge_sidecar_to_children" in data_str:
                    return ("carousel", "edge_sidecar_to_children dalam page_data")
                if "carousel_media" in data_str:
                    return ("carousel", "carousel_media dalam page_data")
            except (TypeError, AttributeError):
                pass

        # If HTML provided, check for image evidence
        if html_content:
            image_result, image_reason = detect_image_from_html(html_content)
            if image_result == "image":
                return ("image", image_reason)

        # 3. If we have existing_media_type, use it cautiously
        if existing_media_type:
            existing_lower = existing_media_type.lower()
            if existing_lower == "image":
                return ("image", f"existing_media_type='{existing_media_type}'")
            if existing_lower in ["carousel", "sidecar", "album"]:
                return ("carousel", f"existing_media_type='{existing_media_type}'")
            # Don't trust "Post / Picture / Carousel" - too ambiguous
            if "post" in existing_lower or "picture" in existing_lower:
                # Default to unknown unless we have clear evidence
                return ("unknown", f"existing_media_type ambigu: '{existing_media_type}'")

        # 4. Default for /p/ without clear evidence
        return ("unknown", "Tidak ada bukti cukup untuk menentukan tipe media")

    # 5. Default fallback
    return ("unknown", "URL bukan /p/ /reel/ /tv/")


def get_all_usernames() -> set:
    """Get all existing usernames in database as a set for fast lookup."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT username FROM accounts")
        return set(row["username"].lower() for row in cursor.fetchall() if row.get("username"))


def bulk_import_accounts_from_excel(excel_path: str, skip_header_rows: int = 5) -> dict:
    """
    Import accounts from Excel file.

    Excel structure expected:
    - Header at row skip_header_rows (0-indexed)
    - Kolom 0: Nama Kanwil → wilayah
    - Kolom 1: Nama Unit Eselon III → URL Instagram (extract username + profile_url)

    Rules:
    - Kunci dedupe: username (extracted from URL)
    - Jika username sudah ada → UPDATE hanya jika field DB kosong
    - Jika username baru → INSERT
    - Kategori default: "Kanwil"

    Returns dict with: inserted, updated, skipped, errors, total
    """
    import re
    import pandas as pd

    result = {
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "total": 0,
        "details": []
    }

    try:
        # Read Excel
        df = pd.read_excel(excel_path, header=skip_header_rows)

        # Expected columns: No., Nama Kanwil, Nama Unit Eselon III (URL), Unnamed: 3
        if len(df.columns) < 3:
            result["errors"].append("Format Excel tidak sesuai. Pastikan ada kolom: No., Nama Kanwil, URL Instagram")
            return result

        # Filter valid rows (ada No. dan URL)
        df = df[df["No."].notna()].copy()
        result["total"] = len(df)

        # Extract username from URL
        def extract_username(url):
            if pd.isna(url):
                return None
            match = re.search(r'instagram\.com/([^/?#]+)/?', str(url))
            return match.group(1).lower() if match else None

        df["username"] = df.iloc[:, 2].apply(extract_username)  # Kolom ke-3 = URL

        # Filter rows with valid username
        df = df[df["username"].notna()].copy()

        if len(df) == 0:
            result["errors"].append("Tidak ada username valid yang bisa di-import")
            return result

        # Get existing usernames from DB
        existing_usernames = get_all_usernames()

        # Store all data first, then commit once
        updates = []
        inserts = []
        errors_list = []

        for idx, row in df.iterrows():
            try:
                username = row["username"]
                # Kolom 1 = Nama Kanwil (wilayah), Kolom 2 = URL Instagram
                wilayah = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                profile_url = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                nama_unit = wilayah  # Gunakan Nama Kanwil sebagai nama_unit

                if not username:
                    continue

                if username.lower() in existing_usernames:
                    # UPDATE - hanya jika field kosong
                    updates.append({
                        "username": username.lower(),
                        "nama_unit": nama_unit,
                        "profile_url": profile_url,
                        "wilayah": wilayah,
                    })
                else:
                    # INSERT baru
                    inserts.append({
                        "username": username.lower(),
                        "nama_unit": nama_unit,
                        "profile_url": profile_url,
                        "wilayah": wilayah,
                    })
                    existing_usernames.add(username.lower())

            except Exception as e:
                errors_list.append(f"Error baris {idx + 1}: {str(e)}")

        # Execute all updates with single commit
        try:
            with get_db_cursor() as cursor:
                # Do updates - only if field is empty in DB
                for u in updates:
                    cursor.execute("""
                        UPDATE accounts
                        SET nama_unit = COALESCE(NULLIF(%s, ''), nama_unit),
                            profile_url = COALESCE(NULLIF(%s, ''), profile_url),
                            wilayah = COALESCE(NULLIF(%s, ''), wilayah),
                            updated_at = NOW()
                        WHERE LOWER(username) = %s
                          AND (nama_unit IS NULL OR nama_unit = ''
                               OR wilayah IS NULL OR wilayah = ''
                               OR profile_url IS NULL OR profile_url = '')
                    """, (u["nama_unit"], u["profile_url"], u["wilayah"], u["username"]))
                    if cursor.rowcount > 0:
                        result["updated"] += 1
                        result["details"].append(f"UPDATE: @{u['username']}")
                    else:
                        result["skipped"] += 1
                        result["details"].append(f"SKIP: @{u['username']} (data sudah ada)")

                # Do inserts
                for i in inserts:
                    cursor.execute("""
                        INSERT INTO accounts (nama_unit, username, profile_url, kategori_unit, wilayah, is_active)
                        VALUES (%s, %s, %s, 'Kanwil', %s, TRUE)
                    """, (i["nama_unit"], i["username"], i["profile_url"], i["wilayah"]))
                    result["inserted"] += 1
                    result["details"].append(f"INSERT: @{i['username']}")

        except Exception as e:
            result["errors"].append(f"Database error: {str(e)}")

    except Exception as e:
        result["errors"].append(f"Gagal membaca file Excel: {str(e)}")

    return result


def get_active_accounts(skip_recent_hours: int = 0) -> List[Dict]:
    """
    Get all active Instagram accounts from database.

    Args:
        skip_recent_hours: Jika > 0, skip akun yang sudah discrape dalam interval ini.
                          Misalnya skip_recent_hours=24 berarti skip akun yang
                          last_checked_at < 24 jam yang lalu.
    """
    with get_db_cursor(commit=False) as cursor:
        if skip_recent_hours > 0:
            cursor.execute("""
                SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                       is_active, account_health, last_checked_at, created_at
                FROM accounts
                WHERE is_active = TRUE
                  AND (
                      last_checked_at IS NULL
                      OR last_checked_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                  )
                ORDER BY nama_unit ASC
            """, (skip_recent_hours,))
        else:
            cursor.execute("""
                SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                       is_active, account_health, last_checked_at, created_at
                FROM accounts
                WHERE is_active = TRUE
                ORDER BY nama_unit ASC
            """)
        return cursor.fetchall()


def get_all_accounts() -> List[Dict]:
    """Get all accounts including inactive."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                   is_active, account_health, last_checked_at, created_at
            FROM accounts
            ORDER BY is_active DESC, nama_unit ASC
        """)
        return cursor.fetchall()


def get_accounts_with_scrape_status(skip_recent_hours: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """
    Get accounts split into two groups: needs_scraping vs recently_scraped.

    Returns:
        (needs_scraping_list, recently_scraped_list)

    Args:
        skip_recent_hours: Threshold untuk menentukan "recently scraped".
                          Jika 0, semua akun aktif masuk needs_scraping.
    """
    with get_db_cursor(commit=False) as cursor:
        if skip_recent_hours > 0:
            # Akun yang perlu discrape (last_checked_at NULL atau > skip_recent_hours lalu)
            cursor.execute("""
                SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                       is_active, account_health, last_checked_at, created_at
                FROM accounts
                WHERE is_active = TRUE
                  AND (
                      last_checked_at IS NULL
                      OR last_checked_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                  )
                ORDER BY nama_unit ASC
            """, (skip_recent_hours,))
            needs_scraping = cursor.fetchall()

            # Akun yang baru discrape (last_checked_at <= skip_recent_hours lalu)
            cursor.execute("""
                SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                       is_active, account_health, last_checked_at, created_at
                FROM accounts
                WHERE is_active = TRUE
                  AND last_checked_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY last_checked_at DESC
            """, (skip_recent_hours,))
            recently_scraped = cursor.fetchall()

            return needs_scraping, recently_scraped
        else:
            # Tidak ada skip, semua akun aktif perlu discrape
            cursor.execute("""
                SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                       is_active, account_health, last_checked_at, created_at
                FROM accounts
                WHERE is_active = TRUE
                ORDER BY nama_unit ASC
            """)
            needs_scraping = cursor.fetchall()
            return needs_scraping, []


def get_account_by_username(username: str) -> Optional[Dict]:
    """Get account by username."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT * FROM accounts WHERE username = %s", (username,))
        return cursor.fetchone()


def get_eligible_accounts_for_rolling_sync(limit: int = 15, skip_hours: int = 6) -> List[Dict]:
    """
    Get accounts eligible for rolling latest sync.

    Eligible account criteria:
    - is_active = TRUE
    - next_eligible_scrape_at IS NULL OR <= NOW()
    - last_latest_scrape_at IS NULL OR < NOW - skip_hours hours
    - ORDER BY last_latest_scrape_at ASC NULL FIRST (belum pernah discrape duluan)
    - ORDER BY consecutive_login_wall_count ASC (akun dengan login wall count rendah duluan)

    Args:
        limit: Maksimal jumlah akun yang diambil
        skip_hours: Skip akun yang sudah discrape dalam X jam terakhir

    Returns:
        List of account dicts
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT id, nama_unit, username, profile_url, kategori_unit, wilayah,
                   is_active, account_health, last_checked_at,
                   last_latest_scrape_at, last_scrape_status,
                   last_login_wall_at, consecutive_login_wall_count, next_eligible_scrape_at,
                   created_at
            FROM accounts
            WHERE is_active = TRUE
              AND (
                  next_eligible_scrape_at IS NULL
                  OR next_eligible_scrape_at <= NOW()
              )
              AND (
                  last_latest_scrape_at IS NULL
                  OR last_latest_scrape_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
              )
            ORDER BY
                IFNULL(last_latest_scrape_at, '1900-01-01') ASC,
                consecutive_login_wall_count ASC,
                nama_unit ASC
            LIMIT %s
        """, (skip_hours, limit))
        return cursor.fetchall()


def get_total_active_accounts() -> int:
    """Get total count of active accounts from database (dynamic)."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT COUNT(*) as total FROM accounts WHERE is_active = TRUE")
        result = cursor.fetchone()
        return result["total"] if result else 0


def update_account_scrape_status(
    account_id: int,
    status: str,
    is_login_wall: bool = False,
    next_eligible_at: datetime = None
) -> bool:
    """
    Update account scrape status after scraping attempt.

    Args:
        account_id: ID akun
        status: last_scrape_status value
        is_login_wall: True jika scrape gagal karena login wall
        next_eligible_at: DATETIME untuk cooldown, None untuk reset
    """
    try:
        with get_db_cursor() as cursor:
            if is_login_wall:
                # Login wall: increment counter dan set cooldown
                cursor.execute("""
                    UPDATE accounts
                    SET last_scrape_status = %s,
                        last_login_wall_at = NOW(),
                        consecutive_login_wall_count = consecutive_login_wall_count + 1,
                        next_eligible_scrape_at = %s,
                        last_latest_scrape_at = COALESCE(last_latest_scrape_at, NOW())
                    WHERE id = %s
                """, (status, next_eligible_at, account_id))
            else:
                # Sukses atau error lain: reset counter
                cursor.execute("""
                    UPDATE accounts
                    SET last_scrape_status = %s,
                        consecutive_login_wall_count = 0,
                        last_latest_scrape_at = COALESCE(last_latest_scrape_at, NOW()),
                        last_login_wall_at = NULL
                    WHERE id = %s
                """, (status, account_id))
            return True
    except Exception:
        return False


def get_account_scrape_summary() -> dict:
    """Get summary of account scrape status for dashboard."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_accounts,
                SUM(CASE WHEN last_scrape_status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN last_scrape_status = 'LOGIN_WALL' THEN 1 ELSE 0 END) as login_wall_count,
                SUM(CASE WHEN last_scrape_status = 'PARTIAL_SUCCESS' THEN 1 ELSE 0 END) as partial_count,
                SUM(CASE WHEN last_scrape_status IS NULL THEN 1 ELSE 0 END) as never_scraped_count,
                SUM(CASE WHEN consecutive_login_wall_count >= 3 THEN 1 ELSE 0 END) as rate_limited_count,
                SUM(CASE WHEN next_eligible_scrape_at > NOW() THEN 1 ELSE 0 END) as in_cooldown_count
            FROM accounts
            WHERE is_active = TRUE
        """)
        result = cursor.fetchone()
        return {
            "total_accounts": result["total_accounts"] or 0,
            "success_count": result["success_count"] or 0,
            "login_wall_count": result["login_wall_count"] or 0,
            "partial_count": result["partial_count"] or 0,
            "never_scraped_count": result["never_scraped_count"] or 0,
            "rate_limited_count": result["rate_limited_count"] or 0,
            "in_cooldown_count": result["in_cooldown_count"] or 0,
        }


def add_account(nama_unit: str, username: str, kategori_unit: str = "", wilayah: str = "") -> Tuple[bool, str]:
    """
    Add new Instagram account to database.
    Returns: (success: bool, message: str)
    """
    # Normalize username
    username = username.lower().strip()

    # Validate username format
    if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
        return False, "Format username tidak valid. Gunakan hanya huruf, angka, titik, dan underscore."

    # Check duplicate
    existing = get_account_by_username(username)
    if existing:
        existing_unit = existing.get("nama_unit", "Unknown")
        return False, f"Data duplikasi! Akun @{username} sudah terdaftar untuk {existing_unit}."

    # Build profile URL
    profile_url = f"https://www.instagram.com/{username}/"

    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO accounts (nama_unit, username, profile_url, kategori_unit, wilayah)
                VALUES (%s, %s, %s, %s, %s)
            """, (nama_unit, username, profile_url, kategori_unit, wilayah))
        return True, f"Akun @{username} berhasil ditambahkan."
    except Exception as e:
        return False, f"Gagal menambahkan akun: {str(e)}"


def update_account(
    account_id: int,
    nama_unit: str,
    username: str,
    kategori_unit: str = "",
    wilayah: str = "",
    is_active: bool = True,
) -> Tuple[bool, str]:
    """Update account master data safely."""
    username = (username or "").lower().lstrip("@").strip()
    nama_unit = (nama_unit or "").strip()

    if not nama_unit:
        return False, "Nama unit tidak boleh kosong."

    if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
        return False, "Format username tidak valid. Gunakan hanya huruf, angka, titik, dan underscore."

    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT id, nama_unit FROM accounts WHERE username = %s AND id <> %s", (username, account_id))
            duplicate = cursor.fetchone()
            if duplicate:
                return False, f"Akun @{username} sudah dipakai oleh {duplicate.get('nama_unit', 'unit lain')}."

        profile_url = f"https://www.instagram.com/{username}/"
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE accounts
                SET nama_unit = %s,
                    username = %s,
                    profile_url = %s,
                    kategori_unit = %s,
                    wilayah = %s,
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (nama_unit, username, profile_url, kategori_unit or "", wilayah or "", is_active, account_id))
        return True, "Akun berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui akun: {str(e)}"


def update_account_status(account_id: int, is_active: bool) -> bool:
    """Update account active status."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE accounts SET is_active = %s, updated_at = NOW()
                WHERE id = %s
            """, (is_active, account_id))
        return True
    except Exception:
        return False


def update_account_health(account_id: int, health: str, last_checked: datetime = None) -> bool:
    """Update account health status and last checked time."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE accounts
                SET account_health = %s, last_checked_at = %s, updated_at = NOW()
                WHERE id = %s
            """, (health, last_checked or datetime.now(), account_id))
        return True
    except Exception:
        return False


def delete_account(account_id: int) -> Tuple[bool, str]:
    """Delete an account permanently from database."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
        return True, "Akun berhasil dihapus."
    except Exception as e:
        return False, f"Gagal menghapus akun: {str(e)}"


def upsert_post(
    username: str,
    nama_unit: str,
    shortcode: str,
    post_url: str,
    caption: str = "",
    timestamp: datetime = None,
    media_type: str = "UNKNOWN",
    media_type_normalized: str = None,
    media_url: str = "",
    alt_text: str = "",
    like_count: int = None,
    comments_count: int = None,
    total_engagement: int = None,
    status_scraping: str = "PENDING",
    status_periode: str = "",
    source_type: str = "SCRAPED",
    null_reason: str = "",
    account_id: int = None,
    # Extended metrics (optional)
    view_count: int = None,
    play_count: int = None,
    share_count: int = None,
    save_count: int = None,
    reach_count: int = None,
) -> Tuple[bool, bool, int]:
    """
    Insert or update a post.
    Returns: (success: bool, is_new: bool, post_id: int)

    Extended metrics (view_count, play_count, share_count, save_count, reach_count)
    are optional and stored if available. These fields generally require Instagram
    Insights access and may not be available from public scraping.
    """
    # Guard: Validate URL before processing
    is_valid, url_reason = is_valid_instagram_post_url(post_url)
    if not is_valid:
        return (False, False, 0)

    try:
        with get_db_cursor() as cursor:
            # Calculate engagement
            eng = total_engagement
            if eng is None and (like_count is not None or comments_count is not None):
                eng = (like_count or 0) + (comments_count or 0)

            # Build extended metrics SQL
            # IMPORTANT: Only update extended metrics if new value is valid (not None, > 0)
            # Don't overwrite existing valid values with NULL
            extended_cols = []
            extended_values = []
            extended_update = []

            if view_count is not None and view_count > 0:
                extended_cols.append("view_count")
                extended_values.append("%s")
                extended_update.append("view_count = VALUES(view_count)")
            if play_count is not None and play_count > 0:
                extended_cols.append("play_count")
                extended_values.append("%s")
                extended_update.append("play_count = VALUES(play_count)")
            if share_count is not None and share_count > 0:
                extended_cols.append("share_count")
                extended_values.append("%s")
                extended_update.append("share_count = VALUES(share_count)")
            if save_count is not None and save_count > 0:
                extended_cols.append("save_count")
                extended_values.append("%s")
                extended_update.append("save_count = VALUES(save_count)")
            if reach_count is not None and reach_count > 0:
                extended_cols.append("reach_count")
                extended_values.append("%s")
                extended_update.append("reach_count = VALUES(reach_count)")

            # Auto-normalize media_type if not provided
            if media_type_normalized is None:
                media_type_normalized, _ = normalize_media_type(post_url, None, media_type)

            # Build base INSERT columns and values
            base_cols = [
                "account_id", "username", "nama_unit", "shortcode", "post_url",
                "caption", "timestamp", "media_type", "media_type_normalized", "media_url", "alt_text",
                "like_count", "comments_count", "total_engagement",
                "status_scraping", "status_periode", "source_type", "null_reason",
                "is_new_post", "last_scraped_at"
            ]
            base_values = [
                "%s", "%s", "%s", "%s", "%s",
                "%s", "%s", "%s", "%s", "%s", "%s",
                "%s", "%s", "%s",
                "%s", "%s", "%s", "%s",
                "%s", "%s"
            ]

            # Combine columns and values
            all_cols = base_cols + extended_cols
            all_values = base_values + extended_values

            insert_sql = f"""
                INSERT INTO posts ({', '.join(all_cols)})
                VALUES ({', '.join(all_values)})
                ON DUPLICATE KEY UPDATE
                    caption = COALESCE(NULLIF(%s, ''), caption),
                    timestamp = COALESCE(%s, timestamp),
                    media_type = COALESCE(NULLIF(%s, 'UNKNOWN'), media_type),
                    media_type_normalized = COALESCE(%s, media_type_normalized),
                    media_url = COALESCE(NULLIF(%s, ''), media_url),
                    alt_text = COALESCE(NULLIF(%s, ''), alt_text),
                    like_count = COALESCE(%s, like_count),
                    comments_count = COALESCE(%s, comments_count),
                    total_engagement = COALESCE(%s, total_engagement),
                    status_scraping = COALESCE(%s, status_scraping),
                    null_reason = COALESCE(NULLIF(%s, ''), null_reason),
                    last_scraped_at = NOW()
                    {', ' + ', '.join(extended_update) if extended_update else ''}
            """

            # Build params: base values + extended values (for INSERT) + ON DUPLICATE values
            params = [
                account_id, username, nama_unit, shortcode, post_url,
                caption, timestamp, media_type, media_type_normalized, media_url, alt_text,
                like_count, comments_count, eng,
                status_scraping, status_periode, source_type, null_reason,
                True, datetime.now(),
            ]

            # Add extended metrics values (for INSERT)
            if view_count is not None:
                params.append(view_count)
            if play_count is not None:
                params.append(play_count)
            if share_count is not None:
                params.append(share_count)
            if save_count is not None:
                params.append(save_count)
            if reach_count is not None:
                params.append(reach_count)

            # Add ON DUPLICATE KEY UPDATE params (same as INSERT base values for COALESCE)
            params.extend([
                caption, timestamp, media_type, media_type_normalized, media_url, alt_text,
                like_count, comments_count, eng,
                status_scraping, null_reason
            ])

            cursor.execute(insert_sql, params)

            post_id = cursor.lastrowid

            # Check if this was an insert or update
            if cursor.rowcount == 1:
                # New insert
                return True, True, cursor.lastrowid
            else:
                # Update - get existing post_id
                cursor.execute("SELECT id FROM posts WHERE username = %s AND shortcode = %s", (username, shortcode))
                result = cursor.fetchone()
                post_id = result["id"] if result else post_id
                return True, False, post_id

    except Exception as e:
        print(f"Error upserting post: {e}")
        return False, False, 0


def get_posts_by_period(
    period_start: date,
    period_end: date,
    username: str = None,
    status_scraping: str = None,
    is_new_post: bool = None,
    limit: int = 1000
) -> List[Dict]:
    """
    Get posts within a date range based on Instagram post timestamp.
    Filters by DATE(timestamp) which is the Instagram posting date.

    IMPORTANT: This should return ALL posts in the period, not just new posts.

    NOTE: For user-facing output, media_type is replaced with normalized version.
    Original media_type is preserved as media_type_raw if needed for audit.
    """
    query = """
        SELECT p.*,
               a.nama_unit as account_nama_unit,
               a.is_active as account_is_active,
               COALESCE(p.media_type_normalized, 'unknown') AS media_type
        FROM posts p
        LEFT JOIN accounts a ON p.username = a.username
        WHERE DATE(p.timestamp) BETWEEN %s AND %s
    """
    params = [period_start, period_end]

    if username:
        query += " AND p.username = %s"
        params.append(username)

    if status_scraping:
        query += " AND p.status_scraping = %s"
        params.append(status_scraping)

    if is_new_post is not None:
        query += " AND p.is_new_post = %s"
        params.append(is_new_post)

    query += " ORDER BY p.timestamp DESC LIMIT %s"
    params.append(limit)

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def get_posts_count_by_period(
    period_start: date,
    period_end: date,
) -> dict:
    """
    Get detailed counts for posts in period.
    Returns counts for: total, new_posts, failed, need_review, with_engagement.

    This is a more efficient alternative to multiple separate queries.
    """
    with get_db_cursor(commit=False) as cursor:
        # Total posts in period (all statuses)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (period_start, period_end))
        total = cursor.fetchone()["total"]

        # New posts (is_new_post = TRUE)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND is_new_post = TRUE
        """, (period_start, period_end))
        new_posts = cursor.fetchone()["total"]

        # Failed posts
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND status_scraping IN ('LOGIN_WALL', 'PAGE_NOT_FOUND', 'RATE_LIMITED', 'PAGE_LOAD_FAILED', 'FAILED')
        """, (period_start, period_end))
        failed = cursor.fetchone()["total"]

        # Posts needing review (partial success or missing data)
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND status_scraping IN ('PARTIAL_SUCCESS', 'FIELD_PARTIAL_NULL')
        """, (period_start, period_end))
        need_review = cursor.fetchone()["total"]

        # Posts with engagement data
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND like_count IS NOT NULL
        """, (period_start, period_end))
        with_likes = cursor.fetchone()["total"]

        # Total views (for reels/video)
        cursor.execute("""
            SELECT COALESCE(SUM(view_count), 0) as total_views,
                   COUNT(CASE WHEN view_count IS NOT NULL THEN 1 END) as posts_with_views
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND view_count IS NOT NULL
        """, (period_start, period_end))
        views_data = cursor.fetchone()

        return {
            "total": total,
            "new_posts": new_posts,
            "failed": failed,
            "need_review": need_review,
            "with_likes": with_likes,
            "total_views": views_data["total_views"],
            "posts_with_views": views_data["posts_with_views"],
        }


def get_failed_posts(period_start: date = None, period_end: date = None, limit: int = 100) -> List[Dict]:
    """Get posts with failed scraping status."""
    query = """
        SELECT p.*,
               a.nama_unit as account_nama_unit,
               COALESCE(p.media_type_normalized, 'unknown') AS media_type
        FROM posts p
        LEFT JOIN accounts a ON p.username = a.username
        WHERE p.status_scraping IN ('LOGIN_WALL', 'PAGE_NOT_FOUND', 'RATE_LIMITED', 'PAGE_LOAD_FAILED', 'FAILED')
    """
    params = []

    if period_start:
        query += " AND p.timestamp >= %s"
        params.append(period_start)
    if period_end:
        query += " AND DATE(p.timestamp) <= %s"
        params.append(period_end)

    query += " ORDER BY p.last_scraped_at DESC LIMIT %s"
    params.append(limit)

    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def get_posts_needing_review(limit: int = 100) -> List[Dict]:
    """Get posts with partial/null fields that need manual review."""
    query = """
        SELECT p.*,
               a.nama_unit as account_nama_unit,
               COALESCE(p.media_type_normalized, 'unknown') AS media_type
        FROM posts p
        LEFT JOIN accounts a ON p.username = a.username
        WHERE p.status_scraping IN ('PARTIAL_SUCCESS', 'FIELD_PARTIAL_NULL')
           OR p.caption IS NULL OR p.caption = ''
           OR p.timestamp IS NULL
           OR p.like_count IS NULL
        ORDER BY p.last_scraped_at DESC
        LIMIT %s
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, (limit,))
        return cursor.fetchall()


def get_new_posts_since(since: datetime) -> List[Dict]:
    """Get posts marked as new since a certain time."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT p.*,
                   a.nama_unit as account_nama_unit,
                   COALESCE(p.media_type_normalized, 'unknown') AS media_type
            FROM posts p
            LEFT JOIN accounts a ON p.username = a.username
            WHERE p.is_new_post = TRUE
              AND p.first_seen_at >= %s
            ORDER BY p.first_seen_at DESC
        """, (since,))
        return cursor.fetchall()


def mark_posts_as_not_new(post_ids: List[int]) -> bool:
    """Mark posts as not new anymore."""
    if not post_ids:
        return True
    try:
        with get_db_cursor() as cursor:
            placeholders = ",".join(["%s"] * len(post_ids))
            cursor.execute(f"""
                UPDATE posts SET is_new_post = FALSE
                WHERE id IN ({placeholders})
            """, post_ids)
        return True
    except Exception:
        return False


def debug_posts_by_period(period_start: date, period_end: date) -> dict:
    """
    Debug function to check posts data in period.
    Returns detailed counts and sample data for troubleshooting.
    """
    with get_db_cursor(commit=False) as cursor:
        # Total all posts
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
        """)
        db_total = cursor.fetchone()["total"]

        # Posts with NULL timestamp
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE timestamp IS NULL
        """)
        null_timestamp = cursor.fetchone()["total"]

        # Posts in period (DATE comparison)
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (period_start, period_end))
        in_period = cursor.fetchone()["total"]

        # Posts in period with new_post = TRUE
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND is_new_post = TRUE
        """, (period_start, period_end))
        in_period_new = cursor.fetchone()["total"]

        # Posts in period with new_post = FALSE
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND is_new_post = FALSE
        """, (period_start, period_end))
        in_period_updated = cursor.fetchone()["total"]

        # Sample timestamps from posts
        cursor.execute("""
            SELECT timestamp, username, shortcode, is_new_post
            FROM posts
            WHERE timestamp IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        sample_timestamps = cursor.fetchall()

        # Check for posts with timestamps in expected range
        cursor.execute("""
            SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts
            FROM posts
        """)
        range_info = cursor.fetchone()

        return {
            "db_total": db_total,
            "null_timestamp": null_timestamp,
            "in_period_total": in_period,
            "in_period_new": in_period_new,
            "in_period_updated": in_period_updated,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "sample_timestamps": sample_timestamps,
            "db_timestamp_range": {
                "min": str(range_info["min_ts"]) if range_info["min_ts"] else None,
                "max": str(range_info["max_ts"]) if range_info["max_ts"] else None,
            }
        }


def reset_is_new_post_flags(period_start: date = None, period_end: date = None) -> int:
    """
    Reset is_new_post flags for posts that are no longer "new".
    By default resets all posts. Optionally filter by period.

    Returns number of posts updated.
    """
    try:
        with get_db_cursor() as cursor:
            if period_start and period_end:
                cursor.execute("""
                    UPDATE posts
                    SET is_new_post = FALSE
                    WHERE DATE(timestamp) BETWEEN %s AND %s
                      AND is_new_post = TRUE
                """, (period_start, period_end))
            else:
                cursor.execute("""
                    UPDATE posts
                    SET is_new_post = FALSE
                    WHERE is_new_post = TRUE
                """)
            return cursor.rowcount or 0
    except Exception as e:
        print(f"Error resetting is_new_post flags: {e}")
        return 0


def get_dashboard_summary(period_start: date, period_end: date) -> Dict:
    """Get summary statistics for dashboard."""
    with get_db_cursor(commit=False) as cursor:
        # Total active accounts
        cursor.execute("SELECT COUNT(*) as total FROM accounts WHERE is_active = TRUE")
        total_accounts = cursor.fetchone()["total"]

        # Posts in period
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (period_start, period_end))
        total_posts = cursor.fetchone()["total"]

        # New posts
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND is_new_post = TRUE
        """, (period_start, period_end))
        new_posts = cursor.fetchone()["total"]

        # Total engagement
        cursor.execute("""
            SELECT
                COALESCE(SUM(like_count), 0) as total_likes,
                COALESCE(SUM(comments_count), 0) as total_comments,
                COALESCE(SUM(total_engagement), 0) as total_engagement
            FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
        """, (period_start, period_end))
        engagement = cursor.fetchone()

        # Failed posts
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND status_scraping IN ('LOGIN_WALL', 'PAGE_NOT_FOUND', 'RATE_LIMITED', 'PAGE_LOAD_FAILED', 'FAILED')
        """, (period_start, period_end))
        failed = cursor.fetchone()["total"]

        # Posts needing review
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND status_scraping IN ('PARTIAL_SUCCESS', 'FIELD_PARTIAL_NULL')
        """, (period_start, period_end))
        need_review = cursor.fetchone()["total"]

        # Coverage (posts with complete data)
        cursor.execute("""
            SELECT COUNT(*) as total FROM posts
            WHERE DATE(timestamp) BETWEEN %s AND %s
              AND caption IS NOT NULL AND caption != ''
              AND status_scraping = 'FULL_SUCCESS'
        """, (period_start, period_end))
        complete = cursor.fetchone()["total"]

        return {
            "total_accounts": total_accounts,
            "total_posts": total_posts,
            "new_posts": new_posts,
            "total_likes": engagement["total_likes"],
            "total_comments": engagement["total_comments"],
            "total_engagement": engagement["total_engagement"],
            "failed": failed,
            "need_review": need_review,
            "complete_posts": complete,
            "coverage_rate": round((complete / total_posts * 100), 1) if total_posts > 0 else 0,
        }


def get_coverage_by_account(period_start: date, period_end: date) -> List[Dict]:
    """Get coverage status per account."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT
                p.username,
                a.nama_unit,
                COUNT(*) as total_posts,
                SUM(CASE WHEN p.caption IS NOT NULL AND p.caption != '' THEN 1 ELSE 0 END) as posts_with_caption,
                SUM(CASE WHEN p.like_count IS NOT NULL THEN 1 ELSE 0 END) as posts_with_likes,
                SUM(CASE WHEN p.status_scraping = 'FULL_SUCCESS' THEN 1 ELSE 0 END) as full_success,
                SUM(CASE WHEN p.status_scraping IN ('LOGIN_WALL', 'PAGE_NOT_FOUND', 'RATE_LIMITED', 'PAGE_LOAD_FAILED')
                    THEN 1 ELSE 0 END) as failed
            FROM posts p
            LEFT JOIN accounts a ON p.username = a.username
            WHERE DATE(p.timestamp) BETWEEN %s AND %s
            GROUP BY p.username, a.nama_unit
            ORDER BY a.nama_unit
        """, (period_start, period_end))
        return cursor.fetchall()


def create_scrape_job(
    job_id: str,
    job_type: str,
    trigger_type: str,
    period_start: date = None,
    period_end: date = None,
    requested_by: str = "system"
) -> Tuple[bool, int]:
    """
    Create a new scrape job.
    Returns: (success: bool, job_id: int)
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO scrape_jobs (
                    job_id, job_type, trigger_type, period_start, period_end,
                    status, requested_by
                ) VALUES (%s, %s, %s, %s, %s, 'QUEUED', %s)
            """, (job_id, job_type, trigger_type, period_start, period_end, requested_by))
            return True, cursor.lastrowid
    except Exception as e:
        print(f"Error creating job: {e}")
        return False, 0


def update_scrape_job(
    job_id: str,
    status: str = None,
    started_at: datetime = None,
    finished_at: datetime = None,
    total_accounts: int = None,
    total_posts_found: int = None,
    total_posts_inserted: int = None,
    total_posts_updated: int = None,
    total_success: int = None,
    total_partial: int = None,
    total_failed: int = None,
    error_message: str = None
) -> bool:
    """Update job status and statistics."""
    try:
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
        if started_at:
            updates.append("started_at = %s")
            params.append(started_at)
        if finished_at:
            updates.append("finished_at = %s")
            params.append(finished_at)
        if total_accounts is not None:
            updates.append("total_accounts = %s")
            params.append(total_accounts)
        if total_posts_found is not None:
            updates.append("total_posts_found = %s")
            params.append(total_posts_found)
        if total_posts_inserted is not None:
            updates.append("total_posts_inserted = %s")
            params.append(total_posts_inserted)
        if total_posts_updated is not None:
            updates.append("total_posts_updated = %s")
            params.append(total_posts_updated)
        if total_success is not None:
            updates.append("total_success = %s")
            params.append(total_success)
        if total_partial is not None:
            updates.append("total_partial = %s")
            params.append(total_partial)
        if total_failed is not None:
            updates.append("total_failed = %s")
            params.append(total_failed)
        if error_message:
            updates.append("error_message = %s")
            params.append(error_message)

        if not updates:
            return True

        params.append(job_id)
        query = f"UPDATE scrape_jobs SET {', '.join(updates)} WHERE job_id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(query, params)
        return True
    except Exception as e:
        print(f"Error updating job: {e}")
        return False
def touch_job_heartbeat(job_id: str, worker_id: str = None, worker_pid: int = None) -> bool:
    """
    Update heartbeat untuk job RUNNING.

    Tujuan:
    - Kalau worker masih hidup, heartbeat selalu update.
    - Kalau worker mati/crash/terminal ditutup, heartbeat berhenti.
    - Job yang heartbeat-nya mati bisa otomatis diubah ke FAILED.
    """
    if not job_id:
        return False

    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE scrape_jobs
                SET worker_heartbeat_at = NOW(),
                    worker_id = COALESCE(%s, worker_id),
                    worker_pid = COALESCE(%s, worker_pid)
                WHERE job_id = %s
                  AND status = 'RUNNING'
            """, (
                worker_id,
                worker_pid,
                job_id,
            ))

        return True

    except Exception as e:
        print(f"Error touching job heartbeat: {e}")
        return False

def get_latest_job_status() -> Dict:
    """
    Adapter function untuk System Status page.

    Baca dari scrape_jobs dengan schema-aware query.
    Kolom yang ada: started_at, finished_at, created_at, worker_pid, worker_heartbeat_at
    Kolom yang TIDAK ada: job_runs.started_at (tabel job_runs tidak ada)

    Returns dict dengan keys:
    - job_id, status, job_type, trigger_type
    - started_at, finished_at, created_at
    - worker_pid, worker_heartbeat_at
    - total_accounts, total_posts_found, total_posts_inserted, total_failed
    - error_message
    """
    try:
        with get_db_cursor(commit=False) as cursor:
            # Schema-aware: gunakan started_at dari scrape_jobs, bukan job_runs.started_at
            cursor.execute("""
                SELECT
                    job_id, job_type, trigger_type, status,
                    started_at, finished_at, created_at,
                    worker_id, worker_pid, worker_heartbeat_at,
                    total_accounts, total_posts_found,
                    total_posts_inserted, total_posts_updated, total_failed,
                    error_message
                FROM scrape_jobs
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}
    except Exception as e:
        print(f"Error get_latest_job_status: {e}")
        return {}


def get_stale_jobs() -> List[Dict]:
    """
    Get jobs that are RUNNING but their worker process is dead.

    Returns jobs where worker_pid is not found in system processes.
    """
    try:
        # First get RUNNING jobs with worker_pid
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT
                    job_id, status, worker_pid, worker_heartbeat_at, started_at
                FROM scrape_jobs
                WHERE status = 'RUNNING'
                  AND worker_pid IS NOT NULL
            """)
            running_jobs = cursor.fetchall()

        if not running_jobs:
            return []

        # Check which processes exist
        import subprocess
        stale_jobs = []

        try:
            result = subprocess.run([
                'powershell', '-Command',
                'Get-CimInstance Win32_Process -Filter "name=\'python.exe\'" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessId'
            ], capture_output=True, text=True, encoding='utf-8', timeout=10)

            if result.stdout:
                active_pids = set()
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line.isdigit():
                        active_pids.add(int(line))
            else:
                active_pids = set()
        except Exception:
            # If can't check processes, assume all are stale
            return running_jobs

        # Check each job
        for job in running_jobs:
            worker_pid = job.get('worker_pid')
            if worker_pid and worker_pid not in active_pids:
                stale_jobs.append(dict(job))

        return stale_jobs

    except Exception as e:
        print(f"Error get_stale_jobs: {e}")
        return []


def reset_stale_jobs(reason: str = "Manual reset via dashboard") -> int:
    """
    Reset all RUNNING jobs whose workers are dead.
    Returns count of jobs reset.
    """
    stale = get_stale_jobs()
    if not stale:
        return 0

    try:
        with get_db_cursor() as cursor:
            # Reset to FAILED with error message
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'FAILED',
                    finished_at = NOW(),
                    error_message = CONCAT(
                        COALESCE(error_message, ''),
                        CASE
                            WHEN error_message IS NULL OR error_message = ''
                            THEN ''
                            ELSE '\\n'
                        END,
                        'Auto-reset: worker process tidak ditemukan. Kemungkinan worker crash atau hang. ',
                        %s,
                        '. '
                    )
                WHERE status = 'RUNNING'
                  AND worker_pid IS NOT NULL
                  AND worker_pid NOT IN (
                      SELECT ProcessId FROM (
                          SELECT CAST(ProcessId AS SIGNED) as ProcessId
                          FROM WIN32_Process
                          WHERE Name = 'python.exe'
                      ) AS active_pids
                  )
            """, (reason,))

            return cursor.rowcount or 0
    except Exception as e:
        # Fallback: just mark all RUNNING as FAILED if worker_pid is stale
        print(f"Complex reset failed, trying simple reset: {e}")
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE scrape_jobs
                    SET status = 'FAILED',
                        finished_at = NOW(),
                        error_message = %s
                    WHERE status = 'RUNNING'
                """, (f"Auto-reset: {reason}",))
                return cursor.rowcount or 0
        except Exception:
            return 0


def get_running_job() -> Optional[Dict]:
    """Get the currently running job if any, after cleaning stale RUNNING jobs."""
    # Schema-aware: kolom started_at ADA di scrape_jobs (dibuktikan dari DESCRIBE)
    mark_stale_running_jobs()

    with get_db_cursor(commit=False) as cursor:
        # Gunakan started_at DESC, created_at DESC untuk ordering yang konsisten
        # karena started_at mungkin NULL untuk beberapa job lama
        cursor.execute("""
            SELECT *
            FROM scrape_jobs
            WHERE status = 'RUNNING'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        return cursor.fetchone()
def get_queued_job() -> Optional[Dict]:
    """Get the oldest queued job if any."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE status = 'QUEUED'
            ORDER BY created_at ASC
            LIMIT 1
        """)
        return cursor.fetchone()


def get_last_success_latest_sync() -> Optional[Dict]:
    """Get the last successful LATEST_SYNC job."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT * FROM scrape_jobs
            WHERE job_type = 'LATEST_SYNC'
              AND status = 'SUCCESS'
            ORDER BY finished_at DESC
            LIMIT 1
        """)
        return cursor.fetchone()


def get_recent_jobs(limit: int = 10) -> List[Dict]:
    """Get recent jobs for display."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT * FROM scrape_jobs
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()


def get_job_by_id(job_id: str) -> Optional[Dict]:
    """Get job by job_id."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("SELECT * FROM scrape_jobs WHERE job_id = %s", (job_id,))
        return cursor.fetchone()

def mark_stale_running_jobs(max_minutes: int = 15) -> int:
    """
    Auto-fail RUNNING jobs yang heartbeat-nya sudah mati.

    Ini lebih aman daripada menghitung dari started_at saja.
    Job production boleh berjalan lama, tapi heartbeat harus tetap update.
    Kalau heartbeat berhenti, berarti worker mati/crash/terminal tertutup.
    """
    try:
        try:
            from src.database import get_setting
            max_minutes = int(
                get_setting(
                    "running_job_heartbeat_timeout_minutes",
                    str(max_minutes),
                )
            )
        except Exception:
            pass

        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'FAILED',
                    finished_at = NOW(),
                    error_message = CONCAT(
                        COALESCE(error_message, ''),
                        CASE
                            WHEN error_message IS NULL OR error_message = ''
                            THEN ''
                            ELSE '\n'
                        END,
                        'Auto failed: worker heartbeat berhenti lebih dari ',
                        %s,
                        ' menit. Kemungkinan worker mati/crash/terminal ditutup.'
                    )
                WHERE status = 'RUNNING'
                  AND (
                        worker_heartbeat_at IS NULL
                        OR worker_heartbeat_at < DATE_SUB(NOW(), INTERVAL %s MINUTE)
                  )
            """, (
                max_minutes,
                max_minutes,
            ))

            return cursor.rowcount or 0

    except Exception as e:
        print(f"Error marking stale jobs: {e}")
        return 0
def add_job_log(
    job_id: str,
    level: str = "INFO",
    stage: str = "",
    message: str = "",
    account_username: str = None,
) -> bool:
    """
    Insert worker progress log.

    Tambahan penting:
    - Setiap ada log worker, heartbeat juga ikut di-update.
    - Jadi dashboard tahu job masih benar-benar hidup.
    """
    if not job_id:
        return False

    try:
        level = (level or "INFO").upper()[:20]
        stage = (stage or "").upper()[:80]

        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO job_logs (
                    job_id,
                    level,
                    stage,
                    message,
                    account_username
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                job_id,
                level,
                stage,
                str(message or "")[:2000],
                account_username,
            ))

            cursor.execute("""
                UPDATE scrape_jobs
                SET worker_heartbeat_at = NOW()
                WHERE job_id = %s
                  AND status = 'RUNNING'
            """, (
                job_id,
            ))

        return True

    except Exception as e:
        print(f"Error adding job log: {e}")
        return False

def get_job_logs(
    job_id: str = None,
    limit: int = 100,
) -> List[Dict]:
    """Get recent worker logs. If job_id is provided, filter by that job."""
    with get_db_cursor(commit=False) as cursor:
        if job_id:
            cursor.execute("""
                SELECT
                    created_at,
                    job_id,
                    level,
                    stage,
                    message,
                    account_username
                FROM job_logs
                WHERE job_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            """, (
                job_id,
                limit,
            ))
        else:
            cursor.execute("""
                SELECT
                    created_at,
                    job_id,
                    level,
                    stage,
                    message,
                    account_username
                FROM job_logs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            """, (
                limit,
            ))

        return cursor.fetchall()


def reset_stuck_running_jobs(
    reason: str = "Manual reset dari dashboard/SQL",
) -> int:
    """Manual helper: reset all RUNNING jobs to FAILED."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'FAILED',
                    finished_at = NOW(),
                    error_message = %s
                WHERE status = 'RUNNING'
            """, (
                reason,
            ))

            return cursor.rowcount or 0

    except Exception as e:
        print(f"Error resetting running jobs: {e}")
        return 0
def notification_already_sent(shortcode: str, channel: str, recipient: str) -> bool:
    """Check if notification was already sent for this post."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT id FROM notification_logs
            WHERE shortcode = %s AND channel = %s AND recipient = %s
              AND status = 'SENT'
        """, (shortcode, channel, recipient))
        return cursor.fetchone() is not None


def insert_notification_log(
    post_id: int,
    username: str,
    shortcode: str,
    channel: str,
    recipient: str,
    message: str,
    status: str = "SKIPPED",
    error_message: str = None
) -> bool:
    """Insert notification log entry."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO notification_logs (
                    post_id, username, shortcode, channel, recipient,
                    message, status, sent_at, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    sent_at = VALUES(sent_at),
                    message = VALUES(message),
                    error_message = VALUES(error_message)
            """, (
                post_id, username, shortcode, channel, recipient,
                message, status,
                datetime.now() if status == "SENT" else None,
                error_message
            ))
        return True
    except Exception:
        return False


def get_notification_stats() -> Dict:
    """Get notification statistics."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN channel = 'TELEGRAM' THEN 1 ELSE 0 END) as telegram,
                SUM(CASE WHEN channel = 'WHATSAPP' THEN 1 ELSE 0 END) as whatsapp
            FROM notification_logs
        """)
        result = cursor.fetchone()

        cursor.execute("""
            SELECT sent_at FROM notification_logs
            WHERE status = 'SENT'
            ORDER BY sent_at DESC
            LIMIT 1
        """)
        last_sent = cursor.fetchone()

        return {
            "total": result["total"] or 0,
            "sent": result["sent"] or 0,
            "failed": result["failed"] or 0,
            "telegram": result["telegram"] or 0,
            "whatsapp": result["whatsapp"] or 0,
            "last_sent": last_sent["sent_at"] if last_sent else None,
        }


def insert_field_status(
    post_id: int,
    field_name: str,
    value_status: str,
    source: str = "",
    selector_used: str = "",
    attempted_selectors: str = "",
    null_reason: str = ""
) -> bool:
    """Insert field status for debugging."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO field_status (
                    post_id, field_name, value_status, source,
                    selector_used, attempted_selectors, null_reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (post_id, field_name, value_status, source, selector_used, attempted_selectors, null_reason))
        return True
    except Exception:
        return False


def insert_debug_log(
    post_id: int = None,
    username: str = "",
    shortcode: str = "",
    post_url: str = "",
    issue_type: str = "",
    null_reason: str = "",
    html_file: str = "",
    screenshot_file: str = "",
    error_message: str = ""
) -> bool:
    """Insert debug log entry."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO debug_logs (
                    post_id, username, shortcode, post_url,
                    issue_type, null_reason, html_file, screenshot_file, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                post_id, username, shortcode, post_url,
                issue_type, null_reason, html_file, screenshot_file, error_message
            ))
        return True
    except Exception:
        return False
