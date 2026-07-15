"""Notification Service - Telegram notification integration for Mayz."""

from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Dict, Tuple

import requests
from dotenv import load_dotenv
from src.database import get_setting

load_dotenv()

def get_telegram_enabled() -> bool:
    val = get_setting("TELEGRAM_ENABLED")
    if val is None:
        val = os.getenv("TELEGRAM_ENABLED", "false")
    return str(val).lower() == "true"

def get_telegram_token() -> str:
    val = get_setting("TELEGRAM_BOT_TOKEN")
    return val if val is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")

def get_telegram_chat_id() -> str:
    val = get_setting("TELEGRAM_CHAT_ID")
    return val if val is not None else os.getenv("TELEGRAM_CHAT_ID", "")

def get_telegram_notify_new_post() -> bool:
    val = get_setting("TELEGRAM_NOTIFY_NEW_POST")
    if val is None:
        val = os.getenv("TELEGRAM_NOTIFY_NEW_POST", "true")
    return str(val).lower() == "true"

WHATSAPP_ENABLED = False
WHATSAPP_API_URL = ""


def _safe(value) -> str:
    return html.escape(str(value or "-"))


def send_telegram_message(
    message: str,
    chat_id: str = None,
    bot_token: str = None,
    parse_mode: str = None,
) -> Tuple[bool, str]:
    """Send message via Telegram Bot API."""
    token = bot_token or get_telegram_token()
    chats_str = chat_id or get_telegram_chat_id()

    if not get_telegram_enabled():
        return False, "Telegram tidak diaktifkan."
    if not token or not chats_str:
        return False, "Telegram bot token atau chat ID belum dikonfigurasi."

    chats = [c.strip() for c in chats_str.split(",") if c.strip()]
    if not chats:
        return False, "Tidak ada chat ID yang valid."

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    success_count = 0
    last_error = ""
    for chat in chats:
        try:
            payload = {
                "chat_id": chat,
                "text": message,
                "disable_web_page_preview": False,
            }
            # Only add parse_mode if explicitly provided
            if parse_mode:
                payload["parse_mode"] = parse_mode

            response = requests.post(
                url,
                json=payload,
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200 and data.get("ok"):
                success_count += 1
            else:
                last_error = data.get("description", "Telegram API error.")
                if "chat not found" in last_error.lower():
                    last_error += " (Solusi: Pastikan Anda sudah chat /start ke bot tersebut terlebih dahulu, atau pastikan Chat ID benar)"
        except requests.exceptions.Timeout:
            last_error = "Request timeout saat mengirim Telegram."
        except requests.exceptions.ConnectionError:
            last_error = "Gagal terhubung ke Telegram API."
        except Exception as exc:
            last_error = f"Error Telegram: {exc}"

    if success_count > 0:
        return True, f"Pesan berhasil dikirim ke {success_count} penerima."
    return False, last_error


def build_new_post_message(
    username: str,
    nama_unit: str,
    post_url: str,
    caption: str = "",
    timestamp: datetime = None,
    media_type: str = "",
    like_count: int = None,
    comment_count: int = None,
) -> str:
    """Build professional Telegram message for a new post."""
    if isinstance(timestamp, datetime):
        time_str = timestamp.strftime("%d/%m/%Y %H:%M")
    else:
        time_str = str(timestamp or "-")

    # Format caption - max 200 karakter
    caption_short = (caption or "").strip()
    if len(caption_short) > 200:
        caption_short = caption_short[:200] + "..."

    # Format media type (lowercase untuk tampilan profesional)
    media_display = media_type.lower() if media_type else "unknown"
    if media_display not in ["image", "carousel", "reels", "video"]:
        media_display = "unknown"

    # Build engagement line
    engagement_parts = []
    if like_count is not None:
        engagement_parts.append(f"Like: {like_count:,}")
    if comment_count is not None:
        engagement_parts.append(f"Komentar: {comment_count:,}")
    engagement_str = " | ".join(engagement_parts) if engagement_parts else "-"

    # Build message (tanpa HTML tags untuk kompatibilitas)
    lines = [
        "Mayz Monitoring Alert",
        "",
        f"Username Instagram : @{_safe(username)}",
        f"Unit               : {_safe(nama_unit)}",
        "Status             : Postingan baru terdeteksi",
        f"Tanggal Posting   : {time_str}",
        f"Media Type        : {media_display}",
        f"Engagement         : {engagement_str}",
    ]

    if caption_short:
        lines.extend(["", "Caption Ringkas:"])
        lines.append(caption_short)

    lines.extend(["", f"Link: {post_url}", "", "Segera cek dashboard Mayz untuk validasi data terbaru."])

    return "\n".join(lines)


def should_notify_post(shortcode: str, channel: str = "TELEGRAM") -> bool:
    from src.db_repository import notification_already_sent
    recipient = get_telegram_chat_id() if channel == "TELEGRAM" else ""
    return not notification_already_sent(shortcode, channel, recipient)


def notify_new_post(
    username: str,
    nama_unit: str,
    shortcode: str,
    post_url: str,
    caption: str = "",
    timestamp: datetime = None,
    media_type: str = "",
    like_count: int = None,
    comment_count: int = None,
    post_id: int = None,
) -> Tuple[bool, str]:
    if not get_telegram_enabled():
        return False, "Telegram notification tidak diaktifkan."
    if not get_telegram_notify_new_post():
        return False, "Notifikasi postingan baru dinonaktifkan."
    if not should_notify_post(shortcode, "TELEGRAM"):
        return False, "Notifikasi sudah pernah dikirim untuk postingan ini."

    message = build_new_post_message(
        username=username,
        nama_unit=nama_unit,
        post_url=post_url,
        caption=caption,
        timestamp=timestamp,
        media_type=media_type,
        like_count=like_count,
        comment_count=comment_count,
    )
    success, msg = send_telegram_message(message)

    from src.db_repository import insert_notification_log
    insert_notification_log(
        post_id=post_id,
        username=username,
        shortcode=shortcode,
        channel="TELEGRAM",
        recipient=get_telegram_chat_id(),
        message=message,
        status="SENT" if success else "FAILED",
        error_message=None if success else msg,
    )
    return success, msg


def test_telegram_notification(bot_token: str = None, chat_id: str = None) -> Tuple[bool, str]:
    token = bot_token or get_telegram_token()
    chat = chat_id or get_telegram_chat_id()
    if not token:
        return False, "Bot token belum dikonfigurasi. Tambahkan di menu Pengaturan."
    if not chat:
        return False, "Chat ID belum dikonfigurasi. Tambahkan di menu Pengaturan."

    message = (
        "<b>Mayz Monitoring Test</b>\n\n"
        "Status: Telegram bot berhasil terhubung.\n"
        f"Waktu test: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    return send_telegram_message(message, chat_id=chat, bot_token=token)


def send_job_complete_notification(job_id: str, job_type: str, status: str, total_posts: int = 0, new_posts: int = 0) -> Tuple[bool, str]:
    if not get_telegram_enabled():
        return False, "Telegram tidak diaktifkan."
    message = (
        "<b>Mayz Job Status</b>\n\n"
        f"Job ID: <code>{_safe(job_id)}</code>\n"
        f"Tipe: {_safe(job_type)}\n"
        f"Status: {_safe(status)}\n"
        f"Total postingan: {_safe(total_posts)}\n"
        f"Postingan baru: {_safe(new_posts)}\n\n"
        f"Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    success, msg = send_telegram_message(message)

    from src.db_repository import insert_notification_log
    insert_notification_log(
        post_id=None,
        username="system",
        shortcode=job_id,
        channel="TELEGRAM",
        recipient=get_telegram_chat_id(),
        message=message,
        status="SENT" if success else "FAILED",
        error_message=None if success else msg,
    )
    return success, msg


def notify_new_account_added(username: str, nama_unit: str) -> Tuple[bool, str]:
    if not get_telegram_enabled():
        return False, "Telegram tidak diaktifkan."
    message = (
        "<b>Mayz Account Registry</b>\n\n"
        "Status: Akun monitoring baru ditambahkan.\n"
        f"Username Instagram: @{_safe(username)}\n"
        f"Unit: {_safe(nama_unit)}\n"
        f"Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        "Akun ini akan masuk ke jadwal monitoring otomatis."
    )
    success, msg = send_telegram_message(message)

    from src.db_repository import insert_notification_log
    insert_notification_log(
        post_id=None,
        username=username,
        shortcode=f"account_add_{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        channel="TELEGRAM",
        recipient=get_telegram_chat_id(),
        message=message,
        status="SENT" if success else "FAILED",
        error_message=None if success else msg,
    )
    return success, msg


def notify_new_posts_detected(posts: list, account_name: str = None) -> Tuple[bool, str]:
    if not get_telegram_enabled():
        return False, "Telegram tidak diaktifkan."
    if not posts:
        return False, "Tidak ada postingan baru."

    count = len(posts)
    lines = ["<b>Mayz Monitoring Summary</b>", "", f"{count} postingan baru terdeteksi."]
    if account_name:
        lines.append(f"Akun: {_safe(account_name)}")
    lines.append("")
    for post in posts[:5]:
        timestamp = post.get("timestamp")
        time_str = timestamp.strftime("%d/%m %H:%M") if isinstance(timestamp, datetime) else str(timestamp or "-")[:16]
        caption = (post.get("caption") or "Tanpa caption")[:60]
        lines.append(f"- {time_str} | @{_safe(post.get('username', ''))} | {_safe(caption)}")
    if count > 5:
        lines.append(f"...dan {count - 5} postingan lainnya.")
    message = "\n".join(lines)
    success, msg = send_telegram_message(message)

    from src.db_repository import insert_notification_log
    for post in posts:
        insert_notification_log(
            post_id=post.get("id"),
            username=post.get("username", ""),
            shortcode=post.get("shortcode", ""),
            channel="TELEGRAM",
            recipient=get_telegram_chat_id(),
            message=f"New post notification: {post.get('shortcode', '')}",
            status="SENT" if success else "FAILED",
            error_message=None if success else msg,
        )
    return success, msg


def get_telegram_status() -> Dict:
    token = get_telegram_token()
    chat_id = get_telegram_chat_id()
    enabled = get_telegram_enabled()
    return {
        "enabled": enabled,
        "configured": bool(token and chat_id and enabled),
        "bot_token_set": bool(token),
        "chat_id_set": bool(chat_id),
        "notify_new_post": get_telegram_notify_new_post(),
    }


def send_whatsapp_message(message: str, recipient: str = None) -> Tuple[bool, str]:
    if not WHATSAPP_ENABLED:
        return False, "WhatsApp notification belum tersedia."
    return False, "WhatsApp integration dalam pengembangan."


def whatsapp_available() -> bool:
    return WHATSAPP_ENABLED and bool(WHATSAPP_API_URL)
