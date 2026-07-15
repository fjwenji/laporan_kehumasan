"""
Mayz Instagram Scraper - Production with Login Wall Safety
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.parser import (
    AccountRow,
    ScrapeRow,
    clean_caption,
    detect_media_type,
    extract_caption_from_meta,
    extract_shortcode,
    parse_dt_to_wib,
    parse_engagement_from_text,
    safe_text,
    status_periode,
)
from src.db_repository import parse_view_count_from_html


# Module-level state
_last_scrape_stats = {}
_reels_views_cache = {}

DEFAULT_MAX_POSTS = 30
MIN_DELAY = 2.0
MAX_DELAY = 4.0
DETAIL_DELAY_MIN = 1.8
DETAIL_DELAY_MAX = 3.8
BATCH_SIZE = 12
BATCH_COOLDOWN = 12.0

PROFILE_READY_TIMEOUT = 70000
DETAIL_READY_TIMEOUT = 70000
MAX_NAVIGATION_RETRIES = 3
EXPONENTIAL_BACKOFF_BASE = 2.0
MAX_BACKOFF_DELAY = 30
DEBUG_SAVE_DIR = "debug_logs"


# Basic helpers
def human_delay(min_sec: float = MIN_DELAY, max_sec: float = MAX_DELAY):
    time.sleep(random.uniform(min_sec, max_sec))


def normalize_instagram_url(url: str) -> str:
    url = safe_text(url)

    if not url:
        return ""

    if not url.startswith("http"):
        url = "https://" + url

    return url.strip()


def normalize_post_url(url: str) -> str:
    """
    Normalize:
    https://www.instagram.com/username/p/SHORTCODE/
    menjadi:
    https://www.instagram.com/p/SHORTCODE/
    """
    url = normalize_instagram_url(url)

    if not url:
        return ""

    try:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]

        media_type = None
        shortcode = None

        for index, part in enumerate(parts):
            if part in ["p", "reel", "tv"]:
                media_type = part
                if index + 1 < len(parts):
                    shortcode = parts[index + 1]
                break

        if media_type and shortcode:
            return urlunparse((
                "https",
                "www.instagram.com",
                f"/{media_type}/{shortcode}/",
                "",
                "",
                "",
            ))

        return url

    except Exception:
        return url


def is_target_closed_error(error: Exception | str) -> bool:
    text = str(error)
    return (
        "Target page, context or browser has been closed" in text
        or "TargetClosedError" in text
        or "Target closed" in text
        or "Protocol error" in text
        or "Browser has been closed" in text
    )


def page_is_alive(page: Page) -> bool:
    try:
        _ = page.url
        return not page.is_closed()
    except Exception:
        return False


def save_debug_snapshot(page: Page, prefix: str = "debug") -> str:
    """Simpan screenshot dan HTML debug ke file."""
    import os
    try:
        os.makedirs(DEBUG_SAVE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prefix = prefix.replace("/", "_").replace(":", "_")

        # Screenshot
        screenshot_path = os.path.join(DEBUG_SAVE_DIR, f"{safe_prefix}_{timestamp}.png")
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            screenshot_path = ""

        # HTML
        html_path = os.path.join(DEBUG_SAVE_DIR, f"{safe_prefix}_{timestamp}.html")
        try:
            html_content = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception:
            html_path = ""

        result = f"Saved: {screenshot_path}, {html_path}"
        print(f"    [DEBUG] {result}")
        return result
    except Exception as e:
        return f"Debug save failed: {e}"

def is_login_wall_url(page: Page) -> Tuple[bool, str]:
    """
    FAST login wall detection berdasarkan URL saja.
    Ini harus dipanggil SEBELUM fungsi lain yang bisa error.

    Returns: (is_login_wall, reason)
    """
    if not page_is_alive(page):
        return True, "page_dead"

    try:
        current_url = page.url or ""
    except Exception:
        return True, "url_read_error"

    # Pattern URL yang menunjukkan login wall
    login_url_patterns = [
        "/accounts/login",
        "/accounts/signup",
        "/accounts/embedded/signup",
        "/checkpoint",
        "/challenge",
        "source=omni_redirect",
        "next=%2F",
        "fbconnect",
    ]

    for pattern in login_url_patterns:
        if pattern in current_url.lower():
            return True, f"url_pattern:{pattern}"

    return False, ""


def fetch_post_detail_for_carousel(post_url: str, show_browser: bool = False) -> dict:
    """
    Fetch post detail page to check for carousel evidence.

    This is a LIGHTWEIGHT function that:
    - Navigates to the post URL
    - Checks for login wall
    - Looks for carousel indicators in the page data
    - Returns a dict with page_data and html_content for analysis

    Returns:
        dict with:
        - is_login_wall: bool
        - page_data: dict (from JSON-LD or similar)
        - media_count: int (estimated)
        - is_carousel: bool (if detected)
        - html_content: str (raw HTML for detection)
        - reason: str (explanation)

    Returns None if login wall or error.
    """
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not show_browser)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Navigate to post
            try:
                response = page.goto(post_url, timeout=30000)
                if response and response.status >= 400:
                    browser.close()
                    return None
            except Exception:
                browser.close()
                return None

            # Check for login wall
            time.sleep(2)
            current_url = page.url.lower()
            if "/accounts/login" in current_url or "/accounts/signup" in current_url:
                browser.close()
                return {
                    "is_login_wall": True,
                    "page_data": None,
                    "html_content": None,
                    "media_count": 0,
                    "is_carousel": False,
                    "reason": "Login wall terdeteksi"
                }

            # Wait for page to load
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # Get HTML content for analysis
            html_content = None
            page_data = None
            media_count = 0
            is_carousel = False
            reason = "Tidak ada marker jelas"

            try:
                # Get raw HTML for carousel detection
                html_content = page.content()

                # Method 1: Try JSON-LD from script tags
                match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>', html_content)
                if match:
                    try:
                        import json
                        data = json.loads(match.group(1))
                        page_data = data
                    except Exception:
                        pass

                # Method 2: Check for carousel indicators via evaluate
                # This looks for GraphSidecar and media_count in the page scripts
                carousel_check = page.evaluate("""
                    () => {
                        // Check for GraphSidecar or carousel indicators
                        const scripts = document.querySelectorAll('script');
                        let hasCarousel = false;
                        let mediaCount = 1;

                        for (const script of scripts) {
                            const text = script.textContent || '';
                            if (text.includes('GraphSidecar') || text.includes('edge_sidecar_to_children')) {
                                hasCarousel = true;
                            }
                            // Extract media count from __data__
                            if (text.includes('__typename') && text.includes('Post')) {
                                const match = text.match(/"media_count"[:\\s]*(\\d+)/);
                                if (match) {
                                    mediaCount = parseInt(match[1]);
                                }
                            }
                        }

                        // Also check accessibility/caption for album/carousel indicators
                        const accessibilityElements = document.querySelectorAll('[aria-label]');
                        for (const el of accessibilityElements) {
                            const label = el.getAttribute('aria-label') || '';
                            if (label.toLowerCase().includes('album') || label.toLowerCase().includes('carousel')) {
                                hasCarousel = true;
                                break;
                            }
                        }

                        return { hasCarousel, mediaCount };
                    }
                """)

                if carousel_check:
                    is_carousel = carousel_check.get("hasCarousel", False)
                    media_count = carousel_check.get("mediaCount", 1)

                # Update reason based on findings
                if is_carousel:
                    reason = "GraphSidecar atau aria-label carousel terdeteksi"
                elif media_count > 1:
                    reason = f"Media count: {media_count}"

            except Exception as e:
                reason = f"Error saat analisis: {str(e)[:50]}"

            browser.close()

            return {
                "is_login_wall": False,
                "page_data": page_data,
                "html_content": html_content,
                "media_count": media_count,
                "is_carousel": is_carousel,
                "reason": reason,
            }

    except Exception as e:
        return None


def safe_eval_on_selector_all(page: Page, selector: str, js_code: str):
    """Wrapper aman untuk page.eval_on_selector_all dengan fallback."""
    # Try eval_on_selector_all
    try:
        return page.eval_on_selector_all(selector, js_code)
    except Exception as e:
        pass

    # Fallback: locator-based
    try:
        locators = page.locator(selector)
        count = locators.count()
        results = []
        for i in range(count):
            try:
                href = locators.nth(i).get_attribute("href")
                if href:
                    results.append(href)
            except Exception:
                pass
        return results
    except Exception:
        pass

    # Try method 3: evaluate dengan document.querySelectorAll
    try:
        return page.evaluate(f"""
            () => {{
                const els = document.querySelectorAll('{selector}');
                return Array.from(els).map(el => el.href || el.getAttribute('href') || '');
            }}
        """)
    except Exception:
        pass

    return []


def close_popups(page: Page, max_attempts: int = 3) -> dict:
    """Tutup popup/modal Instagram."""
    if not page_is_alive(page):
        return {"modal_found": False, "modal_closed": False, "attempts": 0}

    debug_info = {
        "modal_found": False,
        "modal_closed": False,
        "attempts": 0,
        "popup_texts": [],
    }

    for attempt in range(1, max_attempts + 1):
        debug_info["attempts"] = attempt

        # Cek apakah ada modal di DOM
        try:
            modal_info = page.evaluate("""
                () => {
                    const badTexts = [
                        "Lihat foto, video, dan banyak lagi",
                        "Daftar dan jangan lewatkan postingan",
                        "Log in to see photos",
                        "Sign up to see photos",
                        "See photos and videos",
                        "See more from"
                    ];

                    const dialogs = Array.from(document.querySelectorAll(
                        "div[role='dialog'], div[aria-modal='true']"
                    ));

                    let foundModal = null;
                    let foundText = "";

                    for (const dialog of dialogs) {
                        const text = (dialog.innerText || dialog.textContent || "").trim();
                        if (text.length > 0) {
                            for (const bad of badTexts) {
                                if (text.includes(bad)) {
                                    foundModal = dialog;
                                    foundText = text.substring(0, 200);
                                    break;
                                }
                            }
                            if (foundModal) break;
                        }
                    }

                    return { found: !!foundModal, text: foundText };
                }
            """)

            if modal_info and modal_info.get("found"):
                debug_info["modal_found"] = True
                debug_info["popup_texts"].append(modal_info.get("text", "")[:100])

        except Exception:
            pass

        # Tekan Escape
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Klik tombol close umum (aria-label)
        close_selectors = [
            'svg[aria-label="Close"]',
            'svg[aria-label="Tutup"]',
            'button[aria-label="Close"]',
            'button[aria-label="Tutup"]',
            'button[aria-label="Not Now"]',
            'button[aria-label="Not now"]',
            'div[aria-label="Close"]',
            'div[aria-label="Tutup"]',
            '[role="button"][aria-label="Close"]',
            '[role="button"][aria-label="Tutup"]',
        ]

        for selector in close_selectors:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click(timeout=1500, force=True)
                    page.wait_for_timeout(800)
                    debug_info["modal_closed"] = True
                    break
            except Exception:
                pass

        # Klik tombol text-based
        try:
            page.evaluate("""
                () => {
                    const labels = [
                        "Close",
                        "Tutup",
                        "Not Now",
                        "Not now",
                        "Nanti Saja",
                        "Nanti saja",
                        "Lain Kali",
                        "Lain kali",
                        "Batal",
                        "Cancel"
                    ];

                    const nodes = Array.from(document.querySelectorAll(
                        "button, div[role='button'], span[role='button'], a[role='button']"
                    ));

                    for (const node of nodes) {
                        const text = (
                            node.innerText ||
                            node.textContent ||
                            node.getAttribute("aria-label") ||
                            ""
                        ).trim();

                        if (labels.includes(text)) {
                            node.click();
                            return true;
                        }
                    }

                    return false;
                }
            """)
            page.wait_for_timeout(500)
            debug_info["modal_closed"] = True
        except Exception:
            pass

        # Emergency: hapus modal signup dari DOM kalau masih nutup layar
        try:
            removed = page.evaluate("""
                () => {
                    const badTexts = [
                        "Lihat foto, video, dan banyak lagi",
                        "Daftar dan jangan lewatkan postingan",
                        "Log in to see photos",
                        "Sign up to see photos",
                        "See photos and videos",
                        "See more from"
                    ];

                    let removedCount = 0;

                    const dialogs = Array.from(document.querySelectorAll(
                        "div[role='dialog'], div[aria-modal='true']"
                    ));

                    for (const dialog of dialogs) {
                        const text = (dialog.innerText || dialog.textContent || "");
                        if (badTexts.some(function(t) { return text.includes(t); })) {
                            dialog.remove();
                            removedCount++;
                        }
                    }

                    document.body.style.overflow = "auto";
                    document.documentElement.style.overflow = "auto";

                    const fixedNodes = Array.from(document.querySelectorAll("div"));
                    for (const node of fixedNodes) {
                        const style = window.getComputedStyle(node);
                        const text = (node.innerText || node.textContent || "");

                        if (
                            style.position === "fixed" &&
                            badTexts.some(function(t) { return text.includes(t); })
                        ) {
                            node.remove();
                            removedCount++;
                        }
                    }

                    return removedCount;
                }
            """)

            if removed and removed > 0:
                debug_info["modal_closed"] = True
                page.wait_for_timeout(700)
        except Exception:
            pass

        # Cek lagi apakah modal sudah hilang
        try:
            still_has_modal = page.evaluate("""
                () => {
                    const badTexts = [
                        "Lihat foto, video, dan banyak lagi",
                        "Daftar dan jangan lewatkan postingan"
                    ];

                    const dialogs = Array.from(document.querySelectorAll(
                        "div[role='dialog'], div[aria-modal='true']"
                    ));

                    for (const dialog of dialogs) {
                        const text = (dialog.innerText || dialog.textContent || "");
                        if (badTexts.some(function(t) { return text.includes(t); })) {
                            return true;
                        }
                    }
                    return false;
                }
            """)

            if not still_has_modal:
                break

        except Exception:
            break

    return debug_info


def is_fatal_login_wall(page: Page, wait_for_render: bool = True) -> bool:
    """
    Login wall fatal hanya jika benar-benar halaman login/form login.

    Popup Daftar/Masuk di atas profile TIDAK fatal kalau:
    - Link postingan sudah ada di DOM
    - Ada profile indicators (followers, posts, dll)
    - Page meta tags sudah terload

    Args:
        page: Playwright page object
        wait_for_render: Tunggu sebentar untuk render complete
    """
    if not page_is_alive(page):
        return True

    try:
        current_url = page.url or ""
    except Exception:
        current_url = ""

    # Jika di halaman login, itu fatal
    if "/accounts/login" in current_url or "/accounts/signup" in current_url:
        return True

    # Tunggu sebentar untuk render
    if wait_for_render:
        try:
            page.wait_for_timeout(2000)
        except Exception:
            pass

    # Check 1: Apakah ada login form?
    try:
        has_username = page.locator('input[name="username"]').count() > 0
        has_password = page.locator('input[name="password"]').count() > 0

        if has_username and has_password:
            # Double check - apakah ini benar-benar halaman login atau popup?
            try:
                # Cek apakah ada profile header
                profile_header = page.locator('header').count()
                if profile_header > 0:
                    return False  # Ini profile page dengan popup login
            except Exception:
                pass
            return True  # Benar-benar halaman login
    except Exception:
        pass

    # Check 2: Apakah ada meta og:url yang menunjukkan profile loaded?
    try:
        og_url = page.locator('meta[property="og:url"]')
        if og_url.count() > 0:
            og_url_content = og_url.first.get_attribute("content") or ""
            if "instagram.com" in og_url_content and "/accounts/" not in og_url_content:
                return False  # Page properly loaded
    except Exception:
        pass

    # Check 3: Apakah ada link postingan?
    try:
        media_count = page.locator(
            'a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]'
        ).count()

        if media_count > 0:
            return False  # Ada link postingan, profile terbuka
    except Exception:
        pass

    # Check 4: Apakah ada profile indicators?
    try:
        body_text = page.locator("body").inner_text(timeout=2500).lower()

        profile_signals = [
            "followers", "pengikut", "following", "diikuti",
            "posts", "postingan", "viewing", "menyukai", "liked"
        ]

        if any(signal in body_text for signal in profile_signals):
            return False  # Ada profile content
    except Exception:
        pass

    # Check 5: Canonical URL
    try:
        canonical = page.locator('link[rel="canonical"]')
        if canonical.count() > 0:
            canonical_href = canonical.first.get_attribute("href") or ""
            if "instagram.com" in canonical_href and "/accounts/" not in canonical_href:
                return False  # Page properly loaded
    except Exception:
        pass

    # Check 6: Time element (posting time)
    try:
        time_element = page.locator("time[datetime]")
        if time_element.count() > 0:
            return False  # Ada waktu postingan, profile terbuka
    except Exception:
        pass

    # Jika tidak ada bukti profile terbuka, dianggap login wall
    fatal_signals = [
        "phone number, username, or email",
        "forgot password",
        "log in to continue",
        "sign up to continue",
        "masukkan nomor telepon",
        "nama pengguna, atau email",
        "lupa kata sandi",
        "lihat foto, video, dan banyak lagi",
        "daftar dan jangan lewatkan",
    ]

    try:
        body_text = page.locator("body").inner_text(timeout=2500).lower()
        return any(signal in body_text for signal in fatal_signals)
    except Exception:
        return True  # Tidak bisa baca page, assume fatal


def count_media_links(page: Page) -> dict:
    """Count media links by type."""
    result = {"total": 0, "p": 0, "reel": 0, "tv": 0}

    if not page_is_alive(page):
        return result

    try:
        p_count = page.locator('a[href*="/p/"]').count()
        reel_count = page.locator('a[href*="/reel/"]').count()
        tv_count = page.locator('a[href*="/tv/"]').count()

        result["p"] = p_count
        result["reel"] = reel_count
        result["tv"] = tv_count
        result["total"] = p_count + reel_count + tv_count
    except Exception:
        pass

    return result


def check_page_ready(page: Page, profile_mode: bool = False) -> bool:
    """
    Halaman dianggap ready jika:
    - Ada link postingan /p/ /reel/ /tv/
    - Ada main/header/body profile
    - Ada meta post detail
    """
    if not page_is_alive(page):
        return False

    try:
        current_url = page.url or ""

        if current_url == "about:blank":
            return False
    except Exception:
        return False

    try:
        media_counts = count_media_links(page)
        if media_counts["total"] > 0:
            return True
    except Exception:
        pass

    try:
        if page.locator("time[datetime]").count() > 0:
            return True
    except Exception:
        pass

    try:
        if page.locator('meta[property="og:description"]').count() > 0:
            content = page.locator('meta[property="og:description"]').first.get_attribute("content")
            if content and len(content.strip()) > 5:
                return True
    except Exception:
        pass

    try:
        if page.locator('meta[property="og:url"]').count() > 0:
            return True
    except Exception:
        pass

    try:
        if page.locator('link[rel="canonical"]').count() > 0:
            return True
    except Exception:
        pass

    try:
        body_text = page.locator("body").inner_text(timeout=2500)
        body_lower = body_text.lower()

        if len(body_text.strip()) > 80:
            if profile_mode:
                profile_signals = [
                    "followers",
                    "pengikut",
                    "following",
                    "diikuti",
                    "posts",
                    "postingan",
                    "instagram",
                ]

                if any(signal in body_lower for signal in profile_signals):
                    return True
            else:
                return True
    except Exception:
        pass

    try:
        html_len = page.evaluate("document.documentElement.outerHTML.length")
        body_len = page.evaluate("(document.body && document.body.innerText || '').length")

        if html_len > 15000 or body_len > 100:
            return True
    except Exception:
        pass

    return False


def is_network_error(error: Exception | str) -> bool:
    """Check if error is network-related and should trigger retry."""
    text = str(error).lower()
    network_signals = [
        "timeout",
        "timed out",
        "connection",
        "network",
        "reset",
        "refused",
        "host",
        "internet",
        "ssl",
        "certificate",
        "certificate_verify_failed",
        "handshake",
        "eof",
        "broken pipe",
        "address",
        "dns",
        "proxy",
        "tunnel",
        # DNS specific
        "err_name_not_resolved",
        "err_name_resolution_failed",
        "name_not_resolved",
        "name_resolve",
        "getaddrinfo",
        "nodename nor servname provided",
        "server can't be found",
        "server not found",
        # Connection specific
        "connection refused",
        "connection reset",
        "connection timed out",
        "connection aborted",
        "eai_again",
        "temporary failure in name resolution",
        "no address associated",
    ]
    return any(signal in text for signal in network_signals)


def safe_goto(
    page: Page,
    url: str,
    max_retries: int = MAX_NAVIGATION_RETRIES,
    profile_mode: bool = False,
) -> Tuple[bool, str, List[str]]:
    """
    Navigasi yang tidak kaku dengan exponential backoff.

    Fitur:
    - Exponential backoff untuk network error
    - Lebih banyak wait strategies
    - Tidak kaku kalau page sudah kebuka
    """
    url = normalize_instagram_url(url)
    tried: List[str] = []
    final_url = url

    candidate_urls = [url]

    if "instagram.com" in url and "?" not in url:
        candidate_urls.append(url.rstrip("/") + "/?hl=id")

    wait_strategies = [
        ("commit", 70000),
        ("domcontentloaded", 70000),
        ("load", 90000),
    ]

    for candidate_url in candidate_urls:
        for wait_until, timeout in wait_strategies:
            for attempt in range(1, max_retries + 1):
                label = f"{wait_until}:{timeout}ms attempt {attempt}/{max_retries}"
                tried.append(label)

                if not page_is_alive(page):
                    return False, final_url, tried

                try:
                    if attempt > 1:
                        try:
                            page.goto("about:blank", wait_until="commit", timeout=8000)
                        except Exception:
                            pass

                        # Exponential backoff
                        backoff_delay = min(
                            EXPONENTIAL_BACKOFF_BASE ** attempt,
                            MAX_BACKOFF_DELAY
                        )
                        print(f"    [RETRY] Waiting {backoff_delay:.1f}s before retry...")
                        time.sleep(random.uniform(backoff_delay * 0.8, backoff_delay * 1.2))

                    try:
                        page.goto(candidate_url, wait_until=wait_until, timeout=timeout)
                    except Exception as goto_error:
                        # Check if it's network error - use longer backoff
                        if is_network_error(goto_error):
                            backoff_delay = min(
                                EXPONENTIAL_BACKOFF_BASE ** (attempt + 1),
                                MAX_BACKOFF_DELAY
                            )
                            print(f"    [NETWORK ERROR] {str(goto_error)[:80]}... Waiting {backoff_delay:.1f}s...")
                            time.sleep(random.uniform(backoff_delay * 0.8, backoff_delay * 1.2))
                        else:
                            print(f"    [WARN] goto error: {str(goto_error)[:80]}")

                    try:
                        page.wait_for_timeout(7000 if profile_mode else 4000)
                    except Exception:
                        pass

                    close_popups(page)

                    try:
                        page.wait_for_timeout(1500)
                    except Exception:
                        pass

                    if check_page_ready(page, profile_mode=profile_mode):
                        close_popups(page)
                        final_url = page.url
                        return True, final_url, tried

                    # Khusus profile: kalau body sudah ada dan bukan blank, jangan langsung gagal.
                    if profile_mode:
                        try:
                            body_text = page.locator("body").inner_text(timeout=2500)
                            if len(body_text.strip()) > 50:
                                close_popups(page)
                                final_url = page.url
                                return True, final_url, tried
                        except Exception:
                            pass

                except Exception as e:
                    if is_target_closed_error(e):
                        print(f"    [WARN] Browser/page closed saat goto: {str(e)[:120]}")
                        return False, final_url, tried

                    # Exponential backoff for any error
                    backoff_delay = min(
                        EXPONENTIAL_BACKOFF_BASE ** attempt,
                        MAX_BACKOFF_DELAY
                    )
                    print(f"    [WARN] Error attempt {attempt}: {str(e)[:80]}... Waiting {backoff_delay:.1f}s...")
                    time.sleep(random.uniform(backoff_delay * 0.8, backoff_delay * 1.2))

    # Last emergency: tidak pakai wait_until.
    try:
        tried.append("emergency:no-wait")
        page.goto(url, timeout=90000)
    except Exception as e:
        print(f"    [WARN] emergency goto error: {str(e)[:80]}")

    try:
        page.wait_for_timeout(9000 if profile_mode else 5000)
        close_popups(page)

        if check_page_ready(page, profile_mode=profile_mode):
            final_url = page.url
            return True, final_url, tried
    except Exception:
        pass

    return False, final_url, tried


def env_true(key: str) -> bool:
    return os.getenv(key, "false").lower() in {"1", "true", "yes", "on"}


def ig_auth_state_path() -> Path:
    raw = os.getenv("IG_AUTH_STATE_PATH", "data/instagram/auth_state.json")
    path = Path(raw)
    return path if path.is_absolute() else Path(__file__).resolve().parent.parent / path


def login_form_visible(page: Page) -> bool:
    try:
        return page.locator('input[name="username"], input[name="password"]').count() > 0
    except Exception:
        return False


def challenge_visible(page: Page) -> bool:
    markers = ("challenge", "checkpoint", "verifikasi", "verify", "suspicious", "konfirmasi")
    try:
        text = page.locator("body").inner_text(timeout=3000).lower()
    except Exception:
        text = ""
    url = page.url.lower()
    return any(marker in url or marker in text for marker in markers)


def logged_in(page: Page) -> bool:
    try:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        close_popups(page)
        return not login_form_visible(page) and not challenge_visible(page)
    except Exception:
        return False


def ensure_instagram_login(context: BrowserContext):
    if not env_true("IG_LOGIN_ENABLED"):
        return

    page = context.new_page()
    try:
        if logged_in(page):
            return

        username = os.getenv("IG_USERNAME")
        password = os.getenv("IG_PASSWORD")
        if not username or not password:
            raise RuntimeError("IG_LOGIN_CONFIG_MISSING")

        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector('input[name="username"]', timeout=15000)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.wait_for_timeout(2000)
        page.click('button[type="submit"]')
        page.wait_for_timeout(7000)

        if challenge_visible(page):
            raise RuntimeError("IG_LOGIN_CHALLENGE_REQUIRED")
        if login_form_visible(page) or not logged_in(page):
            raise RuntimeError("IG_LOGIN_FAILED")

        path = ig_auth_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(path))
        print("[LOGIN] Instagram session saved.")
    finally:
        try:
            page.close()
        except Exception:
            pass


def create_context(browser: Browser, show_browser: bool = False) -> BrowserContext:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    ]

    viewports = [
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080},
    ]

    options = {
        "viewport": random.choice(viewports),
        "user_agent": random.choice(user_agents),
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "java_script_enabled": True,
        "ignore_https_errors": True,
        "bypass_csp": True,
    }
    auth_path = ig_auth_state_path()
    if env_true("IG_LOGIN_ENABLED") and auth_path.exists():
        options["storage_state"] = str(auth_path)

    try:
        context = browser.new_context(**options)
    except Exception:
        options.pop("storage_state", None)
        context = browser.new_context(**options)

    context.set_default_navigation_timeout(90000)
    context.set_default_timeout(45000)

    # Stealth anti-detection scripts
    context.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // Mock languages properly
        Object.defineProperty(navigator, 'languages', {
            get: () => ['id-ID', 'id', 'en-US', 'en', 'ms'],
            configurable: true
        });

        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                plugins.length = 3;
                return plugins;
            },
            configurable: true
        });

        // Remove automation flags
        window.navigator.chrome = {
            runtime: { id: undefined },
            loadTimes: function() {},
            csi: function() {}
        };

        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // NOTE: Do NOT override window.eval - it breaks Playwright's page.evaluate()
        // The original anti-detection is sufficient via navigator.webdriver undefined

        // Mock chrome app
        if (!window.chrome) {
            window.chrome = { runtime: {} };
        }
    """)

    try:
        def route_handler(route):
            resource_type = route.request.resource_type
            request_url = route.request.url.lower()

            if resource_type in ["font", "media"]:
                return route.abort()

            blocked_keywords = [
                "doubleclick",
                "googletagmanager",
                "google-analytics",
                "facebook.com/tr",
                "connect.facebook.net/tr",
            ]

            if any(keyword in request_url for keyword in blocked_keywords):
                return route.abort()

            return route.continue_()

        context.route("**/*", route_handler)
    except Exception:
        pass

    return context


def extract_media_links_from_html(html: str) -> List[str]:
    results: List[str] = []

    if not html:
        return results

    patterns = [
        r'https?://(?:www\.)?instagram\.com/(?:[^/"\']+/)?(?:p|reel|tv)/[A-Za-z0-9_-]+/?',
        r'href=["\']((?:/[^/"\']+)?/(?:p|reel|tv)/[A-Za-z0-9_-]+/?)["\']',
        r'"url":"(https?:\\/\\/www\.instagram\.com\\/(?:p|reel|tv)\\/[A-Za-z0-9_-]+\\/?)"',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html):
            if isinstance(match, tuple):
                match = match[0]

            link = str(match).replace("\\/", "/")

            if link.startswith("/"):
                link = urljoin("https://www.instagram.com", link)

            if "/p/" in link or "/reel/" in link or "/tv/" in link:
                results.append(normalize_post_url(link))

    return results


def collect_post_links(page: Page, max_posts: int) -> Tuple[List[str], str]:
    """Kumpulkan link postingan dari halaman."""
    links: List[str] = []
    seen: set[str] = set()
    status = "success"

    if not page_is_alive(page):
        return links, "error"

    # Fast login wall check
    is_login, login_reason = is_login_wall_url(page)
    if is_login:
        print(f"    [LOGIN WALL] URL redirect detected: {login_reason}")
        return [], "login_wall"

    debug_info = {
        "url": page.url or "",
        "body_length": 0,
        "method_used": "none",
    }

    try:
        debug_info["body_length"] = len(page.locator("body").inner_text(timeout=3000))
    except Exception:
        pass

    # Try safe_eval_on_selector_all
    try:
        hrefs = safe_eval_on_selector_all(
            page,
            "a[href]",
            """
            elements => elements
                .map(el => el.href || el.getAttribute('href') || '')
                .filter(href =>
                    href.includes('/p/') ||
                    href.includes('/reel/') ||
                    href.includes('/tv/')
                )
            """
        )

        debug_info["method_used"] = "eval_or_locator"

        for href in hrefs:
            href = normalize_post_url(href)
            shortcode = extract_shortcode(href)

            if shortcode and shortcode not in seen:
                seen.add(shortcode)
                links.append(href)

            if len(links) >= max_posts:
                return links[:max_posts], status

    except Exception:
        # Fallback ke method lain, tidak perlu log warning
        pass

    # Try locator-based fallback
    try:
        locators = page.locator('a[href*="/p/"], a[href*="/reel/"], a[href*="/tv/"]')
        count = locators.count()

        if count > 0:
            debug_info["method_used"] = "playwright_locator"
            for i in range(min(count, max_posts * 2)):
                try:
                    href = locators.nth(i).get_attribute("href")
                    if href:
                        href = normalize_post_url(href)
                        shortcode = extract_shortcode(href)
                        if shortcode and shortcode not in seen:
                            seen.add(shortcode)
                            links.append(href)
                            if len(links) >= max_posts:
                                break
                except Exception:
                    pass

            if links:
                return links[:max_posts], status

    except Exception:
        pass

    # HTML fallback (only if not login wall)
    is_login, _ = is_login_wall_url(page)
    if is_login:
        print(f"    [LOGIN WALL] URL became login wall during collection")
        status = "login_wall"
        return links, status

    try:
        html = page.content()
        html_links = extract_media_links_from_html(html)

        if html_links:
            debug_info["method_used"] = "html_fallback"
            for href in html_links:
                shortcode = extract_shortcode(href)
                if shortcode and shortcode not in seen:
                    seen.add(shortcode)
                    links.append(href)
                    if len(links) >= max_posts:
                        break

            if links:
                return links[:max_posts], status

    except Exception:
        pass

    # If 0 links, save debug snapshot (only if not login wall)
    is_login, _ = is_login_wall_url(page)
    if not is_login and len(links) == 0 and page_is_alive(page):
        try:
            url_part = debug_info['url'].split('/')[-1][:20]
            save_debug_snapshot(page, prefix=f"no_links_{url_part}")
        except Exception:
            pass

    return links[:max_posts], status


def _extract_view_from_anchor(a: dict) -> Optional[int]:
    from src.db_repository import parse_indonesian_number
    href = a.get("href", "") or ""
    view_text = a.get("viewText", "")
    if not href or "/reel/" not in href.lower():
        return None
    if not a.get("hasViewMarker") or not view_text:
        return None
    return parse_indonesian_number(view_text)


def extract_reels_views_from_profile_grid(page) -> dict:
    result = {}
    try:
        try:
            page.wait_for_selector('a[href*="/reel/"], a[href*="/tv/"]', timeout=15000)
        except Exception:
            return result

        reel_data = page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"], a[href*="/tv/"]'));
                return anchors.map(a => {
                    const href = a.getAttribute('href') || '';
                    if (!href.includes('/reel/') && !href.includes('/tv/')) return null;
                    const cardHtml = a.innerHTML || '';
                    const hasMarker = cardHtml.includes('Ikon Lihat Jumlah') || cardHtml.includes('Lihat Jumlah');
                    let viewText = '';
                    if (hasMarker) {
                        const match = a.innerHTML.match(/<span[^>]*>([\\d.,]+(?:rb|juta)?)<\\/span>/i);
                        if (match) viewText = match[1];
                    }
                    return { href, hasMarker, viewText };
                }).filter(Boolean);
            }
        """)
        if not reel_data:
            return result
        print(f"  [VIEWS] Collected {len(reel_data)} anchors")
        for item in reel_data:
            href = item["href"]
            if not href.startswith("http"):
                href = "https://www.instagram.com" + href
            if not href.endswith("/"):
                href += "/"
            if href in result:
                continue

            view_count = _extract_view_from_anchor(item)
            if view_count and view_count > 0:
                result[href] = view_count
        return result

    except Exception:
        return result


def scroll_and_collect(
    page: Page,
    max_posts: int,
    scrolls: int,
    progress: Optional[Callable] = None,
) -> Tuple[List[str], str]:
    """Scroll dan collect links dari halaman profile."""
    all_links: List[str] = []
    seen: set[str] = set()
    no_new_count = 0
    last_height = 0
    overall_status = "success"

    print(f"    Starting scroll (max={max_posts}, scrolls={scrolls})")

    # Check login wall before scroll
    is_login, login_reason = is_login_wall_url(page)
    if is_login:
        print(f"    [LOGIN WALL] Cannot scroll - URL is login wall: {login_reason}")
        return [], "login_wall"

    for scroll_index in range(scrolls):
        if not page_is_alive(page):
            break

        # ==========================================
        # Check login wall BEFORE each scroll iteration
        # ==========================================
        is_login, login_reason = is_login_wall_url(page)
        if is_login:
            print(f"    [LOGIN WALL] URL became login wall during scroll at iteration {scroll_index + 1}")
            overall_status = "partial_login_wall"
            break

        # Wait sebentar untuk render
        try:
            page.wait_for_timeout(1500)
        except Exception:
            pass

        # Re-check after wait
        is_login, login_reason = is_login_wall_url(page)
        if is_login:
            print(f"    [LOGIN WALL] URL became login wall after wait")
            overall_status = "partial_login_wall"
            break

        current_links, link_status = collect_post_links(page, max_posts)

        # Handle login wall status from collect_post_links
        if link_status == "login_wall":
            print(f"    [LOGIN WALL] Detected during collect at scroll {scroll_index + 1}")
            overall_status = "partial_login_wall"
            break

        new_count = 0

        for link in current_links:
            shortcode = extract_shortcode(link)

            if shortcode and shortcode not in seen:
                seen.add(shortcode)
                all_links.append(link)
                new_count += 1

            if len(all_links) >= max_posts:
                break

        if progress:
            progress({
                "stage": "SCROLL",
                "message": f"Scroll {scroll_index + 1}/{scrolls} - {len(all_links)} links",
            })

        print(f"    Scroll {scroll_index + 1}/{scrolls}: total links={len(all_links)}, new={new_count}")

        if len(all_links) >= max_posts:
            break

        if new_count == 0 and len(all_links) > 0:
            no_new_count += 1
            if no_new_count >= 3:
                print("    No more new content after 3 scrolls.")
                break

        try:
            # Aktifkan scrolling dengan force
            page.evaluate("""
                () => {
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                    window.scrollBy(0, Math.floor(window.innerHeight * 1.5));
                }
            """)
            page.wait_for_timeout(random.randint(2500, 4000))
        except Exception as e:
            print(f"    [WARN] scroll error: {str(e)[:100]}")
            break

        try:
            new_height = page.evaluate("document.body.scrollHeight")
        except Exception:
            new_height = last_height

        if new_count == 0 and new_height == last_height:
            no_new_count += 1
        else:
            no_new_count = 0

        last_height = new_height

        if no_new_count >= 4:
            print("    No more new content.")
            break

    print(f"    Collection complete: {len(all_links)} links (status: {overall_status})")
    return all_links[:max_posts], overall_status


def get_meta_content(page: Page, selector: str) -> str:
    try:
        locator = page.locator(selector).first

        if locator.count() > 0:
            return safe_text(locator.get_attribute("content"))
    except Exception:
        pass

    return ""


def get_canonical_url(page: Page) -> str:
    try:
        locator = page.locator('link[rel="canonical"]').first

        if locator.count() > 0:
            href = safe_text(locator.get_attribute("href"))

            if href:
                return normalize_post_url(href)
    except Exception:
        pass

    return ""


def extract_timestamp(page: Page) -> Optional[datetime]:
    try:
        time_locator = page.locator("time[datetime]").first

        if time_locator.count() > 0:
            raw = safe_text(time_locator.get_attribute("datetime"))
            parsed = parse_dt_to_wib(raw)

            if parsed:
                return parsed
    except Exception:
        pass

    try:
        raw = get_meta_content(page, 'meta[property="article:published_time"]')
        parsed = parse_dt_to_wib(raw)

        if parsed:
            return parsed
    except Exception:
        pass

    return None


def extract_caption(page: Page) -> str:
    og_desc = get_meta_content(page, 'meta[property="og:description"]')
    twitter_desc = get_meta_content(page, 'meta[name="twitter:description"]')
    meta_desc = get_meta_content(page, 'meta[name="description"]')

    caption = extract_caption_from_meta(og_desc, twitter_desc, meta_desc)

    if caption:
        return clean_caption(caption)

    try:
        article_text = page.locator("article").first.inner_text(timeout=3000)
        article_text = clean_caption(article_text)

        if article_text:
            return article_text
    except Exception:
        pass

    try:
        body_text = page.locator("body").inner_text(timeout=3000)
        body_text = clean_caption(body_text)

        if body_text:
            return body_text
    except Exception:
        pass

    return ""


def extract_engagement(page: Page) -> Tuple[Optional[int], Optional[int]]:
    """Extract engagement (likes & comments) dari halaman Instagram."""
    # Try og:description
    og_desc = get_meta_content(page, 'meta[property="og:description"]')
    likes, comments = parse_engagement_from_text(og_desc)
    if likes is not None or comments is not None:
        return likes, comments

    # Strategy 2: Body text filtered
    try:
        body_text = page.locator("body").inner_text(timeout=3000)
        likes, comments = parse_engagement_from_text(body_text)
        if likes is not None or comments is not None:
            return likes, comments
    except Exception:
        pass

    # Strategy 3: Try specific engagement spans (Instagram new structure)
    # Like count biasanya di span dengan class tertentu
    try:
        # Cari span dengan angka like
        like_spans = page.locator("span").filter(has_text=re.compile(r'^\d'))
        for span in like_spans.all():
            try:
                text = span.inner_text(timeout=1000)
                # Skip kalau terlalu pendek atau mengandung huruf
                if text and len(text) <= 15:
                    # Skip kalau ada spasi atau huruf (bukan angka)
                    clean_text = text.strip().replace(',', '').replace('.', '')
                    if clean_text.isdigit() and int(clean_text) > 0:
                        # Coba parse dengan suffix
                        parsed = _parse_engagement_number(text)
                        if parsed and parsed >= 0:
                            if likes is None:
                                likes = parsed
                            elif comments is None:
                                comments = parsed
            except Exception:
                continue
    except Exception:
        pass

    # Strategy 4: Try article section
    try:
        article_text = page.locator("article").first.inner_text(timeout=3000)
        likes, comments = parse_engagement_from_text(article_text)
        if likes is not None or comments is not None:
            return likes, comments
    except Exception:
        pass

    return likes, comments


def _parse_engagement_number(text: str) -> Optional[int]:
    """Parse number dengan suffix K, M, rb, jt."""
    text = text.strip().replace(',', '').replace(' ', '')
    if not text:
        return None

    # Check for suffix
    multiplier = 1
    suffix_map = {'k': 1000, 'rb': 1000, 'jt': 1000000, 'm': 1000000}

    for suffix, mult in suffix_map.items():
        if suffix in text.lower():
            multiplier = mult
            text = text.lower().replace(suffix, '').replace('.', '')
            try:
                return int(float(text) * multiplier)
            except (ValueError, TypeError):
                return None

    # No suffix, try direct parse
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def extract_media_url(page: Page) -> str:
    og_image = get_meta_content(page, 'meta[property="og:image"]')

    if og_image:
        return og_image

    try:
        img = page.locator("article img").first

        if img.count() > 0:
            src = safe_text(img.get_attribute("src"))

            if src:
                return src
    except Exception:
        pass

    return ""


def extract_post_detail(
    page: Page,
    post_url: str,
    period_start: datetime,
    period_end: datetime,
    account_name: str,
    account_url: str,
    max_retries: int = MAX_NAVIGATION_RETRIES,
) -> ScrapeRow:
    normalized_url = normalize_post_url(post_url)

    # Retry loop untuk detail extraction
    last_error = None
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            # Exponential backoff
            backoff_delay = min(
                EXPONENTIAL_BACKOFF_BASE ** attempt,
                MAX_BACKOFF_DELAY
            )
            print(f"    [RETRY] Retrying detail extraction, waiting {backoff_delay:.1f}s...")
            time.sleep(random.uniform(backoff_delay * 0.8, backoff_delay * 1.2))

        success, final_url, tried = safe_goto(
            page,
            normalized_url,
            max_retries=2,  # internal retries per safe_goto call
            profile_mode=False,
        )

        if not success:
            last_error = f"Failed after {attempt} attempts. Tried: {', '.join(tried[-3:])}"
            continue

        # Success - extract data
        close_popups(page)

        canonical = get_canonical_url(page)
        og_url = get_meta_content(page, 'meta[property="og:url"]')

        final_post_url = normalize_post_url(canonical or og_url or final_url or normalized_url)
        shortcode = extract_shortcode(final_post_url)

        timestamp = extract_timestamp(page)
        caption = extract_caption(page)
        like_count, comment_count = extract_engagement(page)

        total_engagement = None

        if like_count is not None or comment_count is not None:
            total_engagement = (like_count or 0) + (comment_count or 0)

        media_type = detect_media_type(final_post_url)
        _ = extract_media_url(page)

        # ============================================================
        # VIEW COUNT EXTRACTION FOR REELS/VIDEO
        # Only attempt for Reels/video URLs or detected video media type
        # ============================================================
        view_count = None
        play_count = None
        is_video_url = "/reel/" in final_post_url.lower() or "/tv/" in final_post_url.lower()
        is_video_type = media_type and media_type.lower() in ("reels", "video", "tv")

        if is_video_url or is_video_type:
            try:
                html_content = page.content()
                if html_content:
                    view_count, view_source = parse_view_count_from_html(html_content)
                    if view_count is not None and view_count > 0:
                        play_count = view_count  # Same value for Reels
                        print(f"    [VIEWS] Extracted view_count={view_count:,} from detail page ({view_source})")
                    else:
                        print(f"    [VIEWS] No view_count found from detail page ({view_source})")
            except Exception as e:
                # Don't fail the extraction if view_count fails
                print(f"    [VIEWS] View count extraction failed: {str(e)[:50]}")

        periode_status = status_periode(timestamp, period_start, period_end)

        missing = []

        if not timestamp:
            missing.append("timestamp")

        if not caption:
            missing.append("caption")

        if like_count is None:
            missing.append("like_count")

        if comment_count is None:
            missing.append("comment_count")

        # Check if data is incomplete - retry if so
        if not missing:
            status_scraping = "FULL_SUCCESS"
            catatan = "OK"
            break
        elif timestamp or caption or like_count is not None or comment_count is not None:
            # Has some data - check if worth retrying
            if attempt < max_retries:
                print(f"    [RETRY] Partial data, {len(missing)} fields missing: {missing}")
                last_error = f"Partial data: {', '.join(missing)}"
                continue
            status_scraping = "PARTIAL_SUCCESS"
            catatan = "Sebagian field kosong: " + ", ".join(missing)
        else:
            if attempt < max_retries:
                print(f"    [RETRY] All fields null, will retry...")
                last_error = "All fields null"
                continue
            status_scraping = "FIELD_PARTIAL_NULL"
            catatan = "Field utama belum terbaca setelah " + str(max_retries) + " percobaan."

    # If all retries failed
    if 'status_scraping' not in dir() or status_scraping is None:
        return ScrapeRow(
            nama_kanwil=account_name,
            url_akun=account_url,
            post_url=normalized_url,
            shortcode=extract_shortcode(normalized_url),
            tanggal_postingan=None,
            media_type=detect_media_type(normalized_url),
            caption="",
            like_count=None,
            comment_count=None,
            total_engagement=None,
            status_periode="Perlu Cek Manual",
            status_scraping="DETAIL_EXTRACTION_FAILED",
            catatan=last_error or "Detail gagal setelah multiple retries.",
            view_count=None,
            play_count=None,
        )

    return ScrapeRow(
        nama_kanwil=account_name,
        url_akun=account_url,
        post_url=final_post_url,
        shortcode=shortcode,
        tanggal_postingan=timestamp,
        media_type=media_type,
        caption=caption,
        like_count=like_count,
        comment_count=comment_count,
        total_engagement=total_engagement,
        status_periode=periode_status,
        status_scraping=status_scraping,
        catatan=catatan,
        view_count=view_count,
        play_count=play_count,
    )


def run_scraping(
    accounts: List[AccountRow],
    period_start: datetime,
    period_end: datetime,
    max_posts: int = DEFAULT_MAX_POSTS,
    scrolls: int = 8,
    delay: float = 5.0,
    with_detail: bool = True,
    show_browser: bool = False,
    progress: Optional[Callable] = None,
    stop_on_login: bool = False,
    stop_after_failed_streak: int = 0,
    detail_delay_min: float = DETAIL_DELAY_MIN,
    detail_delay_max: float = DETAIL_DELAY_MAX,
    detail_batch_size: int = BATCH_SIZE,
    detail_batch_cooldown: float = BATCH_COOLDOWN,
    profile_delay_min: float = 15.0,
    profile_delay_max: float = 25.0,
) -> List[ScrapeRow]:
    all_rows: List[ScrapeRow] = []
    headless_mode = not show_browser

    # Login wall tracking
    login_wall_count = 0
    login_wall_streak = 0
    accounts_processed = 0
    accounts_skipped = 0

    # Adaptive delay state
    adaptive_delay_min = profile_delay_min
    adaptive_delay_max = profile_delay_max

    # Module-level stats for worker access
    global _last_scrape_stats
    _last_scrape_stats = {}

    # Clean logging - production-friendly
    print(f"\n[SCRAPER] Starting: {len(accounts)} akun, max_posts={max_posts}, scrolls={scrolls}")
    print(f"[SCRAPER] Profile delay: {adaptive_delay_min}-{adaptive_delay_max}s")

    failed_streak = 0

    print("[PLAYWRIGHT] Browser starting...")
    with sync_playwright() as p:
        print("[PLAYWRIGHT] Browser started.")
        browser = p.chromium.launch(
            headless=headless_mode,
            args=[
                # Disable automation detection
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--start-maximized",
                # Additional stealth args
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-client-side-phishing-detection",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-hang-monitor",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-sync",
                "--enable-automation",
                "--ignore-certificate-errors",
                "--no-first-run",
                "--password-store=basic",
                "--use-mock-keychain",
            ],
        )

        context = create_context(browser, show_browser=show_browser)
        ensure_instagram_login(context)

        # Reset reels views cache at start of scraping
        global _reels_views_cache
        _reels_views_cache = {}

        try:
            print("\n" + "=" * 60)
            print("PHASE 1: Collecting Post Links")
            print("=" * 60)

            total_accounts = len(accounts)

            for account_index, account in enumerate(accounts, 1):
                # Check login wall streak BEFORE processing
                if login_wall_streak >= 3:
                    print(f"\n[STOP] Login wall streak limit reached ({login_wall_streak}). Stopping batch.")
                    print(f"[STOP] Remaining accounts: {total_accounts - account_index}")
                    accounts_skipped = total_accounts - account_index
                    break

                account_name = safe_text(account.nama_kanwil) or f"Account {account_index}"
                account_url = normalize_instagram_url(account.url_akun)

                if not account_url:
                    all_rows.append(ScrapeRow(
                        nama_kanwil=account_name,
                        url_akun="",
                        post_url="",
                        shortcode="",
                        tanggal_postingan=None,
                        media_type="Unknown",
                        caption="",
                        like_count=None,
                        comment_count=None,
                        total_engagement=None,
                        status_periode="Perlu Cek Manual",
                        status_scraping="INVALID_ACCOUNT_URL",
                        catatan="URL akun kosong",
                    ))
                    continue

                if progress:
                    progress({
                        "stage": "ACCOUNT",
                        "message": f"Mengambil link {account_index}/{total_accounts} - {account_name}",
                    })

                print(f"\n[ACCOUNT {account_index}/{total_accounts}] {account_name}")
                print(f"  URL: {account_url}")

                import time
                account_start_time = time.time()
                account_posts_found = 0
                account_error = None
                account_login_wall = False
                account_status = "UNKNOWN"

                page: Optional[Page] = None

                try:
                    # Retry loop untuk profile loading
                    profile_loaded = False
                    last_profile_error = None

                    for profile_attempt in range(1, MAX_NAVIGATION_RETRIES + 1):
                        if profile_attempt > 1:
                            # Exponential backoff
                            backoff_delay = min(
                                EXPONENTIAL_BACKOFF_BASE ** profile_attempt,
                                MAX_BACKOFF_DELAY
                            )
                            print(f"  [RETRY] Profile attempt {profile_attempt}/{MAX_NAVIGATION_RETRIES}, waiting {backoff_delay:.1f}s...")
                            time.sleep(random.uniform(backoff_delay * 0.8, backoff_delay * 1.2))

                        try:
                            page = context.new_page()
                        except Exception as page_error:
                            print(f"  [ERROR] Gagal membuat page: {page_error}")
                            last_profile_error = str(page_error)
                            continue

                        success, final_url, tried = safe_goto(
                            page,
                            account_url,
                            max_retries=2,
                            profile_mode=True,
                        )

                        if not success:
                            last_profile_error = f"Attempt {profile_attempt} failed. Tried: {', '.join(tried[-3:])}"
                            try:
                                page.close()
                            except Exception:
                                pass
                            continue

                        # Profile loaded - check status
                        profile_loaded = True
                        break

                    if not profile_loaded:
                        print(f"  [!] Profile gagal dibuka setelah {MAX_NAVIGATION_RETRIES} percobaan. Last error: {last_profile_error}")

                        all_rows.append(ScrapeRow(
                            nama_kanwil=account_name,
                            url_akun=account_url,
                            post_url="",
                            shortcode="",
                            tanggal_postingan=None,
                            media_type="Unknown",
                            caption="",
                            like_count=None,
                            comment_count=None,
                            total_engagement=None,
                            status_periode="Perlu Cek Manual",
                            status_scraping="PAGE_LOAD_FAILED",
                            catatan=f"Profile gagal load setelah {MAX_NAVIGATION_RETRIES} percobaan. {last_profile_error}",
                        ))

                        failed_streak += 1
                        login_wall_streak = 0  # Reset on page load fail
                    else:
                        # Check login wall before DOM operations
                        is_login, login_reason = is_login_wall_url(page)
                        if is_login:
                            print(f"  [LOGIN WALL] URL redirect detected: {login_reason}")

                            login_wall_count += 1
                            login_wall_streak += 1
                            account_login_wall = True

                            # Save debug snapshot
                            if page_is_alive(page):
                                save_debug_snapshot(page, prefix=f"loginwall_{account_name[:20]}")

                            all_rows.append(ScrapeRow(
                                nama_kanwil=account_name,
                                url_akun=account_url,
                                post_url="",
                                shortcode="",
                                tanggal_postingan=None,
                                media_type="Unknown",
                                caption="",
                                like_count=None,
                                comment_count=None,
                                total_engagement=None,
                                status_periode="Perlu Cek Manual",
                                status_scraping="LOGIN_REQUIRED",
                                catatan=f"Instagram redirect ke login. URL: {page.url}",
                            ))

                            # Check if should stop due to login wall streak
                            if login_wall_streak >= 3:
                                print(f"\n[STOP] Login wall streak limit reached ({login_wall_streak}). Stopping batch.")
                                break
                        else:
                            # Profile genuinely open - reset login wall streak
                            login_wall_streak = 0
                            accounts_processed += 1

                            # TUTUP POPUP SEBELUM CEK LINKS
                            close_popups(page, max_attempts=3)

                            # Wait sebentar
                            try:
                                page.wait_for_timeout(2000)
                            except Exception:
                                pass

                            # Double check login wall after popup close
                            is_login, _ = is_login_wall_url(page)
                            if is_login:
                                print(f"  [LOGIN WALL] Detected after popup close")

                                login_wall_count += 1
                                login_wall_streak += 1
                                account_login_wall = True

                                all_rows.append(ScrapeRow(
                                    nama_kanwil=account_name,
                                    url_akun=account_url,
                                    post_url="",
                                    shortcode="",
                                    tanggal_postingan=None,
                                    media_type="Unknown",
                                    caption="",
                                    like_count=None,
                                    comment_count=None,
                                    total_engagement=None,
                                    status_periode="Perlu Cek Manual",
                                    status_scraping="LOGIN_REQUIRED",
                                    catatan=f"Instagram redirect ke login setelah popup close.",
                                ))

                                if login_wall_streak >= 3:
                                    print(f"\n[STOP] Login wall streak limit reached ({login_wall_streak}). Stopping batch.")
                                    break
                            else:
                                # Profile is genuinely open - show READY
                                media_count = count_media_links(page)
                                print(f"  [READY] Profile terbuka. Media links: {media_count['total']} (p={media_count['p']}, reel={media_count['reel']}, tv={media_count['tv']})")

                                # Scroll dan collect links
                                print("  [SCROLL] Mengumpulkan link...")
                                links, scroll_status = scroll_and_collect(
                                    page=page,
                                    max_posts=max_posts,
                                    scrolls=scrolls,
                                    progress=progress,
                                )

                                print("  [VIEWS] Waiting for grid to render...")
                                try:
                                    page.wait_for_timeout(5000)  # Wait 5s for rendering
                                except Exception:
                                    pass

                                reels_views = extract_reels_views_from_profile_grid(page)
                                if reels_views:
                                    print(f"  [VIEWS] Extracted view counts for {len(reels_views)} reels from profile grid")
                                    # Merge into global cache
                                    _reels_views_cache.update(reels_views)
                                else:
                                    print("  [VIEWS] No view counts found in profile grid")

                                # Handle scroll status
                                if scroll_status == "login_wall":
                                    print(f"  [LOGIN WALL] During scroll: {scroll_status}")
                                    login_wall_count += 1
                                    login_wall_streak += 1
                                    account_login_wall = True

                                    all_rows.append(ScrapeRow(
                                        nama_kanwil=account_name,
                                        url_akun=account_url,
                                        post_url="",
                                        shortcode="",
                                        tanggal_postingan=None,
                                        media_type="Unknown",
                                        caption="",
                                        like_count=None,
                                        comment_count=None,
                                        total_engagement=None,
                                        status_periode="Perlu Cek Manual",
                                        status_scraping="LOGIN_REQUIRED",
                                        catatan="Login wall terdeteksi saat scroll.",
                                    ))

                                    if login_wall_streak >= 3:
                                        print(f"\n[STOP] Login wall streak limit reached ({login_wall_streak}). Stopping batch.")
                                        break

                                elif scroll_status == "partial_login_wall":
                                    print(f"  [WARN] Login wall during scroll - some links collected")

                                print(f"  [RESULT] {len(links)} links (scroll_status: {scroll_status})")

                                if links:
                                    failed_streak = 0

                                    for link in links:
                                        normalized_link = normalize_post_url(link)
                                        shortcode = extract_shortcode(normalized_link)

                                        # Get view count from cache if this is a reel
                                        view_count = None
                                        play_count = None
                                        if "/reel/" in normalized_link.lower():
                                            view_count = _reels_views_cache.get(normalized_link)
                                            if view_count is not None:
                                                play_count = view_count  # Same value for reels

                                        all_rows.append(ScrapeRow(
                                            nama_kanwil=account_name,
                                            url_akun=account_url,
                                            post_url=normalized_link,
                                            shortcode=shortcode,
                                            tanggal_postingan=None,
                                            media_type=detect_media_type(normalized_link),
                                            caption="",
                                            like_count=None,
                                            comment_count=None,
                                            total_engagement=None,
                                            status_periode="Perlu Cek Manual",
                                            status_scraping="Link Collected",
                                            catatan="Menunggu detail...",
                                            # Extended metrics from profile grid
                                            view_count=view_count,
                                            play_count=play_count,
                                        ))
                                else:
                                    # No links found - but profile was open
                                    print("  [!] Tidak ada links ditemukan meskipun profile terbuka.")

                                    all_rows.append(ScrapeRow(
                                        nama_kanwil=account_name,
                                        url_akun=account_url,
                                        post_url="",
                                        shortcode="",
                                        tanggal_postingan=None,
                                        media_type="Unknown",
                                        caption="",
                                        like_count=None,
                                        comment_count=None,
                                        total_engagement=None,
                                        status_periode="Perlu Cek Manual",
                                        status_scraping="NO_POST_LINKS",
                                        catatan="Tidak ada links ditemukan.",
                                    ))

                                    failed_streak += 1

                except Exception as e:
                    print(f"  [ERROR] Account error: {str(e)[:200]}")
                    account_error = e

                    all_rows.append(ScrapeRow(
                        nama_kanwil=account_name,
                        url_akun=account_url,
                        post_url="",
                        shortcode="",
                        tanggal_postingan=None,
                        media_type="Unknown",
                        caption="",
                        like_count=None,
                        comment_count=None,
                        total_engagement=None,
                        status_periode="Perlu Cek Manual",
                        status_scraping="ACCOUNT_ERROR",
                        catatan=str(e)[:200],
                    ))

                    failed_streak += 1

                finally:
                    # Per-account log summary
                    account_duration = time.time() - account_start_time
                    # Count posts from this account
                    account_rows_for_this = [
                        r for r in all_rows
                        if r.url_akun == account_url and r.post_url
                    ]
                    account_posts_found = len(account_rows_for_this)
                    account_inserted = len([r for r in account_rows_for_this if r.status_scraping == "FULL_SUCCESS"])
                    account_skipped = len([r for r in account_rows_for_this if r.status_scraping in ["Link Collected"]])

                    # Determine final status
                    if account_login_wall:
                        account_status = "LOGIN_WALL"
                    elif account_error:
                        account_status = f"ERROR: {type(account_error).__name__}"
                    elif account_posts_found == 0:
                        account_status = "ZERO_POST"
                    elif account_inserted > 0:
                        account_status = "SUCCESS"
                    else:
                        account_status = "PARTIAL"

                    print(f"[ACCOUNT] {account_index}/{total_accounts} finish: {account_name} | status={account_status} | posts={account_posts_found} | inserted={account_inserted} | duration={account_duration:.0f}s")

                    try:
                        if page and not page.is_closed():
                            page.close()
                    except Exception:
                        pass

                # Check login wall streak before next account
                if login_wall_streak >= 3:
                    print(f"\n[STOP] Login wall streak limit reached after account {account_index}. Stopping batch.")
                    accounts_skipped = total_accounts - account_index
                    break

                if account_index < total_accounts:
                    # Adaptive delay dengan jitter - production-safe
                    if login_wall_streak > 0:
                        # Adaptive: naikkan delay jika ada login wall
                        adaptive_delay_min = 30.0
                        adaptive_delay_max = 60.0
                        current_delay = random.uniform(adaptive_delay_min, adaptive_delay_max)
                    else:
                        current_delay = random.uniform(adaptive_delay_min, adaptive_delay_max)
                    time.sleep(current_delay)

            link_rows = [
                row for row in all_rows
                if row.post_url and row.status_scraping == "Link Collected"
            ]

            if with_detail and link_rows:
                print("\n" + "=" * 60)
                print("PHASE 2: Extracting Post Details")
                print("=" * 60)
                print(f"Total posts: {len(link_rows)}")

                success_count = 0
                partial_count = 0
                failed_count = 0

                for index, row in enumerate(link_rows, 1):
                    if progress:
                        progress({
                            "stage": "DETAIL",
                            "message": f"Detail {index}/{len(link_rows)} - {row.nama_kanwil}",
                            "index": index,
                            "total": len(link_rows),
                        })

                    print(f"  [DETAIL {index}/{len(link_rows)}] {row.post_url}")

                    page = None

                    try:
                        page = context.new_page()

                        detail = extract_post_detail(
                            page=page,
                            post_url=row.post_url,
                            period_start=period_start,
                            period_end=period_end,
                            account_name=row.nama_kanwil,
                            account_url=row.url_akun,
                        )

                        row.post_url = detail.post_url
                        row.shortcode = detail.shortcode
                        row.tanggal_postingan = detail.tanggal_postingan
                        row.media_type = detail.media_type
                        row.caption = detail.caption
                        row.like_count = detail.like_count
                        row.comment_count = detail.comment_count
                        row.total_engagement = detail.total_engagement
                        row.status_periode = detail.status_periode
                        row.status_scraping = detail.status_scraping
                        row.catatan = detail.catatan
                        row.view_count = detail.view_count
                        row.play_count = detail.play_count

                        # FALLBACK: Use grid view count cache if detail extraction returned None
                        # This is the key fix for Reels - view count is often only available in profile grid
                        if detail.view_count is None or detail.view_count == 0:
                            # Try to get from grid cache (normalized URL)
                            cache_key = normalize_post_url(row.post_url)
                            cached_view = _reels_views_cache.get(cache_key)
                            if cached_view and cached_view > 0:
                                row.view_count = cached_view
                                row.play_count = cached_view
                                print(f"    [VIEWS] Fallback grid cache HIT: shortcode={row.shortcode} view_count={cached_view:,}")
                            else:
                                # Try without trailing slash
                                if cache_key.endswith("/"):
                                    cache_key_no_slash = cache_key.rstrip("/")
                                    cached_view = _reels_views_cache.get(cache_key_no_slash)
                                    if cached_view and cached_view > 0:
                                        row.view_count = cached_view
                                        row.play_count = cached_view
                                        print(f"    [VIEWS] Fallback cache hit: shortcode={row.shortcode} view_count={cached_view:,}")

                        if row.status_scraping == "FULL_SUCCESS":
                            success_count += 1
                        elif row.status_scraping in ["PARTIAL_SUCCESS", "FIELD_PARTIAL_NULL"]:
                            partial_count += 1
                        else:
                            failed_count += 1

                    except Exception as e:
                        row.status_scraping = "DETAIL_ERROR"
                        row.catatan = str(e)[:200]
                        failed_count += 1
                        print(f"    [WARN] Detail error: {str(e)[:120]}")

                    finally:
                        try:
                            if page and not page.is_closed():
                                page.close()
                        except Exception:
                            pass

                    if index < len(link_rows):
                        human_delay(detail_delay_min, detail_delay_max)

                    if detail_batch_cooldown > 0 and index % detail_batch_size == 0:
                        print(f"  [BREAK] Resting {detail_batch_cooldown}s...")
                        time.sleep(detail_batch_cooldown)

                print(f"\n[RESULT] Full: {success_count}, Partial: {partial_count}, Failed: {failed_count}")

            print("\n" + "=" * 60)
            print("SCRAPING COMPLETE")
            print("=" * 60)

            total_with_url = len([row for row in all_rows if row.post_url])
            total_full = len([row for row in all_rows if row.status_scraping == "FULL_SUCCESS"])
            total_partial = len([row for row in all_rows if row.status_scraping in ["PARTIAL_SUCCESS", "FIELD_PARTIAL_NULL"]])
            total_login_wall = len([row for row in all_rows if row.status_scraping == "LOGIN_REQUIRED"])
            total_failed = len([
                row for row in all_rows
                if row.status_scraping not in [
                    "FULL_SUCCESS",
                    "PARTIAL_SUCCESS",
                    "FIELD_PARTIAL_NULL",
                    "Link Collected",
                    "LOGIN_REQUIRED",
                ]
            ])

            # Track stop reason
            stop_reason = None
            if login_wall_streak >= 3:
                stop_reason = "LOGIN_WALL_STREAK_LIMIT"
            elif accounts_skipped > 0:
                stop_reason = "ACCOUNTS_EXHAUSTED"

            print(f"Total rows: {len(all_rows)}")
            print(f"Rows with URL: {total_with_url}")
            print(f"Full Success: {total_full}")
            print(f"Partial: {total_partial}")
            print(f"Login Required: {total_login_wall}")
            print(f"Failed: {total_failed}")
            print(f"Accounts attempted: {account_index}")  # <-- FIXED: show actual attempted
            print(f"Accounts skipped (remaining): {total_accounts - account_index}")  # <-- FIXED
            print(f"Login wall count: {login_wall_count}")
            print(f"Login wall streak: {login_wall_streak}")
            print(f"Stop reason: {stop_reason or 'COMPLETED'}")

            # Determine final scrape status
            if login_wall_streak >= 3:
                scrape_final_status = "LOGIN_WALL_STOPPED"
            elif total_full > 0 or total_partial > 0:
                scrape_final_status = "SUCCESS"
            elif total_login_wall > 0:
                scrape_final_status = "PARTIAL_SUCCESS"
            elif total_failed == 0 and len(all_rows) == 0:
                scrape_final_status = "NO_ACCOUNTS"
            else:
                scrape_final_status = "FAILED"

            # Store stats in module level for worker access
            _last_scrape_stats = {
                "total_rows": len(all_rows),
                "total_with_url": total_with_url,
                "total_full": total_full,
                "total_partial": total_partial,
                "total_login_wall": total_login_wall,
                "total_failed": total_failed,
                "accounts_attempted": account_index,
                "accounts_skipped": total_accounts - account_index,
                "total_accounts": total_accounts,
                "login_wall_count": login_wall_count,
                "login_wall_streak": login_wall_streak,
                "stop_reason": stop_reason,
                "status": scrape_final_status,
                "reels_views_collected": len(_reels_views_cache),
                "reels_views_total_views": sum(v for v in _reels_views_cache.values() if v),
            }

            # Print reels views summary
            if _reels_views_cache:
                print(f"  Reels views collected: {len(_reels_views_cache)} ({_last_scrape_stats['reels_views_total_views']:,} total views)")

        finally:
            print("[PLAYWRIGHT] Browser closing...")
            try:
                context.close()
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass

            print("[PLAYWRIGHT] Browser closed.")

    return all_rows