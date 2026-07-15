"""
Export Helpers - Helper functions untuk export Excel.

Fungsi-fungsi utility untuk format data export.
"""

from datetime import datetime, date
from typing import Optional, Tuple, List, Dict, Any


def format_null_display(value: Any, return_zero: bool = False) -> str:
    """
    Tampilkan '-' untuk NULL, atau 0 jika return_zero=True.

    Args:
        value: Nilai yang akan diformat
        return_zero: Jika True, tampilkan '0' untuk None; jika False, tampilkan '-'

    Returns:
        String: '-' atau '0' atau str(value)
    """
    if value is None:
        return "0" if return_zero else "-"
    return str(value)


def format_number(value: Any) -> str:
    """Format number dengan thousand separator."""
    if value is None:
        return "-"
    try:
        num = int(value)
        return f"{num:,}"
    except (ValueError, TypeError):
        return str(value) if value else "-"


def compute_engagement(likes: Any, comments: Any) -> int:
    """
    Hitung total engagement.

    Args:
        likes: Jumlah like (bisa None)
        comments: Jumlah comment (bisa None)

    Returns:
        Total engagement (int)
    """
    return (likes or 0) + (comments or 0)


def truncate_caption(caption: str, max_len: int = 100) -> str:
    """
    Potong caption panjang.

    Args:
        caption: Caption asli
        max_len: Maximum panjang karakter

    Returns:
        Caption yang sudah dipotong dengan '...' di akhir jika perlu
    """
    if not caption:
        return ""
    caption = str(caption).strip()
    if len(caption) <= max_len:
        return caption
    return caption[:max_len] + "..."


def clean_text_for_excel(text: Any) -> str:
    """
    Bersihkan text untuk Excel - hapus karakter khusus.

    Args:
        text: Text input

    Returns:
        Text yang sudah dibersihkan
    """
    if text is None:
        return ""
    text = str(text)
    # Remove problematic characters for Excel
    text = text.replace('\x00', '')  # Remove null bytes
    text = text.replace('\r', ' ')
    return text.strip()


def safe_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is naive (no timezone) for Excel compatibility.

    Args:
        dt: Datetime object

    Returns:
        Naive datetime atau None
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def format_date_display(dt: Any) -> str:
    """
    Format datetime untuk display di Excel.

    Args:
        dt: Datetime, date, atau string

    Returns:
        String formatted date atau '-'
    """
    if dt is None:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return str(dt)[:10] if dt else "-"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    if isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    return str(dt)[:10]


def format_date_only(dt: Any) -> str:
    """Format date saja (tanpa waktu)."""
    if dt is None:
        return "-"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    if isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    if isinstance(dt, str):
        return str(dt)[:10]
    return str(dt)[:10]


def get_media_type_display(media_type: str, media_type_normalized: str = None) -> str:
    """
    Get display text untuk media type.

    Args:
        media_type: Media type asli dari scraper
        media_type_normalized: Media type yang sudah dinormalisasi

    Returns:
        Display text: Image, Carousel, Reels, Video, atau Unknown
    """
    if media_type_normalized:
        normalized = media_type_normalized.lower()
        if normalized == 'image':
            return "Image"
        elif normalized == 'carousel':
            return "Carousel"
        elif normalized == 'reels':
            return "Reels"
        elif normalized == 'video':
            return "Video"
        elif normalized == 'unknown':
            return "Unknown"

    # Fallback ke media_type asli
    if media_type:
        m = media_type.lower()
        if 'image' in m or 'picture' in m or 'photo' in m:
            return "Image"
        elif 'carousel' in m or 'album' in m or 'sidecar' in m:
            return "Carousel"
        elif 'reel' in m:
            return "Reels"
        elif 'video' in m or 'tv' in m:
            return "Video"

    return "Unknown"


def determine_coverage_status(
    has_data: bool,
    first_post_date: Any,
    last_post_date: Any,
    period_start: date,
    period_end: date,
    min_expected_posts: int = 5
) -> Tuple[str, str]:
    """
    Tentukan coverage status untuk satu akun.

    Args:
        has_data: Apakah ada data
        first_post_date: Tanggal post pertama
        last_post_date: Tanggal post terakhir
        period_start: Awal periode
        period_end: Akhir periode
        min_expected_posts: Minimum post yang diharapkan

    Returns:
        Tuple[str, str]: (status, note)
        status: COMPLETE, PARTIAL, atau NO_DATA
        note: Penjelasan status
    """
    if not has_data:
        return ("NO_DATA", "Tidak ada postingan dalam periode ini")

    if first_post_date is None or last_post_date is None:
        return ("PARTIAL", "Ada data tapi timestamp tidak valid")

    # Convert ke date jika datetime
    if isinstance(first_post_date, datetime):
        first = first_post_date.date()
    else:
        first = first_post_date

    if isinstance(last_post_date, datetime):
        last = last_post_date.date()
    else:
        last = last_post_date

    # Hitung range
    if first and last:
        date_range = (last - first).days
        period_range = (period_end - period_start).days

        # COMPLETE jika range posts mencakup periode
        if first <= period_start and last >= period_end:
            return ("COMPLETE", f"Data lengkap ({date_range} hari)")

        # PARTIAL jika ada overlap
        if last >= period_start or first <= period_end:
            return ("PARTIAL", f"Data parsial ({first} - {last})")

    return ("PARTIAL", f"Data terbatas")


def is_valid_instagram_url(url: str) -> bool:
    """
    Cek apakah URL valid untuk Instagram.

    Args:
        url: URL string

    Returns:
        True jika valid, False jika tidak
    """
    if not url:
        return False

    url_lower = url.lower()

    # Reject invalid patterns
    invalid_patterns = [
        'chrome-error',
        'chromewebdata',
        'about:blank',
        'data:',
        'file://',
    ]

    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False

    # Valid patterns
    valid_patterns = [
        'instagram.com/p/',
        'instagram.com/reel/',
        'instagram.com/tv/',
    ]

    for pattern in valid_patterns:
        if pattern in url_lower:
            return True

    return False


def calculate_summary_stats(posts: List[Dict]) -> Dict[str, Any]:
    """
    Hitung statistik ringkasan untuk posts.

    Args:
        posts: List of post dictionaries

    Returns:
        Dictionary dengan statistik
    """
    total_posts = len(posts)

    if total_posts == 0:
        return {
            'total_posts': 0,
            'image_count': 0,
            'carousel_count': 0,
            'reels_count': 0,
            'video_count': 0,
            'unknown_count': 0,
            'total_likes': 0,
            'total_comments': 0,
            'total_engagement': 0,
            'total_views': 0,
            'posts_with_views': 0,
            'posts_without_views': 0,
        }

    # Media type counts
    media_counts = {
        'image': 0,
        'carousel': 0,
        'reels': 0,
        'video': 0,
        'unknown': 0,
    }

    for post in posts:
        mt = (post.get('media_type_normalized') or post.get('media_type') or 'unknown').lower()
        if mt == 'image':
            media_counts['image'] += 1
        elif mt == 'carousel':
            media_counts['carousel'] += 1
        elif mt == 'reels':
            media_counts['reels'] += 1
        elif mt == 'video':
            media_counts['video'] += 1
        else:
            media_counts['unknown'] += 1

    # Engagement
    total_likes = sum(post.get('like_count') or 0 for post in posts)
    total_comments = sum(post.get('comments_count') or 0 for post in posts)
    total_engagement = total_likes + total_comments

    # Views
    posts_with_views = sum(1 for post in posts if post.get('view_count') is not None)
    total_views = sum(post.get('view_count') or 0 for post in posts)
    posts_without_views = total_posts - posts_with_views

    return {
        'total_posts': total_posts,
        'image_count': media_counts['image'],
        'carousel_count': media_counts['carousel'],
        'reels_count': media_counts['reels'],
        'video_count': media_counts['video'],
        'unknown_count': media_counts['unknown'],
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_engagement': total_engagement,
        'total_views': total_views,
        'posts_with_views': posts_with_views,
        'posts_without_views': posts_without_views,
    }


def calculate_data_quality(posts: List[Dict]) -> Dict[str, Any]:
    """
    Hitung data quality metrics.

    Args:
        posts: List of post dictionaries

    Returns:
        Dictionary dengan quality metrics
    """
    total_posts = len(posts)

    if total_posts == 0:
        return {
            'missing_timestamp': 0,
            'missing_caption': 0,
            'missing_likes': 0,
            'missing_comments': 0,
            'reels_without_views': 0,
            'unknown_media_type': 0,
            'invalid_urls': 0,
            'duplicate_shortcodes': 0,
            'recommendations': [],
        }

    # Count missing fields
    missing_timestamp = sum(1 for p in posts if not p.get('timestamp'))
    missing_caption = sum(1 for p in posts if not p.get('caption'))
    missing_likes = sum(1 for p in posts if p.get('like_count') is None)
    missing_comments = sum(1 for p in posts if p.get('comments_count') is None)

    # Reels without views
    reels_without_views = sum(
        1 for p in posts
        if p.get('media_type_normalized') in ['reels', 'video']
        and p.get('view_count') is None
    )

    # Unknown media type
    unknown_media_type = sum(
        1 for p in posts
        if p.get('media_type_normalized') == 'unknown'
    )

    # Invalid URLs
    invalid_urls = sum(1 for p in posts if not is_valid_instagram_url(p.get('post_url', '')))

    # Duplicates
    seen_shortcodes = set()
    duplicates = 0
    for p in posts:
        sc = p.get('shortcode', '')
        if sc and sc in seen_shortcodes:
            duplicates += 1
        seen_shortcodes.add(sc)

    # Recommendations
    recommendations = []
    if missing_caption > total_posts * 0.3:
        recommendations.append(f"⚠️ {missing_caption} ({missing_caption/total_posts*100:.0f}%) post tanpa caption - perlu cek scraper")
    if missing_likes > total_posts * 0.5:
        recommendations.append(f"⚠️ {missing_likes} ({missing_likes/total_posts*100:.0f}%) post tanpa like - mungkin perlu refresh")
    if reels_without_views > 0:
        recommendations.append(f"ℹ️ {reels_without_views} reels/video tanpa view count - data nullable")
    if unknown_media_type > total_posts * 0.2:
        recommendations.append(f"⚠️ {unknown_media_type} post dengan media type unknown - perlu refresh media_type")

    return {
        'missing_timestamp': missing_timestamp,
        'missing_caption': missing_caption,
        'missing_likes': missing_likes,
        'missing_comments': missing_comments,
        'reels_without_views': reels_without_views,
        'unknown_media_type': unknown_media_type,
        'invalid_urls': invalid_urls,
        'duplicate_shortcodes': duplicates,
        'recommendations': recommendations,
    }
