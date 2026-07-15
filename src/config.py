import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"
STYLE_FILE = BASE_DIR / "static" / "style.css"
LOGO_FILE = BASE_DIR / "assets" / "logo" / "mayz.png"
DJPB_LOGO_FILE = BASE_DIR / "assets" / "logo" / "djpb_logo.png"
TEMPLATE_FILE = DATA_DIR / "template_mayz_djpb.xlsx"
SHEET_SOURCE = "DJPb"
SHEET_OUTPUT = "DJPb"
SHEET_RAW = "Raw_Scraping"
DEFAULT_PERIOD_START = "2026-06-08"
DEFAULT_PERIOD_END = "2026-06-13"

# ============================================================
# PRODUCTION-SAFE SCRAPING SETTINGS (Phase 1)
# ============================================================

# Profile/akun delay - baseline minimum antar akun
# Jangan pakai nilai < 15 detik untuk production
PROFILE_DELAY_MIN = 15  # detik
PROFILE_DELAY_MAX = 25  # detik (+ random jitter)

# Batch processing untuk stability
ACCOUNT_BATCH_SIZE = 10  # akun per batch
ACCOUNT_BATCH_COOLDOWN_SECONDS = 300  # 5 menit cooldown antar batch

# Recent sync - default production (BUKAN full sync 9999!)
RECENT_SYNC_DAYS = 30
RECENT_SYNC_MAX_POSTS_PER_ACCOUNT = 24
RECENT_SYNC_SCROLLS_PER_ACCOUNT = 6

# Full sync - HANYA untuk manual debugging, bukan production default
FULL_SYNC_MAX_POSTS = 9999
FULL_SYNC_SCROLLS = 9999

# Login wall adaptive delay
LOGIN_WALL_ADAPTIVE_DELAY_MIN = 30  # detik
LOGIN_WALL_ADAPTIVE_DELAY_MAX = 60  # detik

# ============================================================
# ROLLING LATEST SYNC (Production Mode)
# ============================================================

# Batch settings untuk rolling latest sync
LATEST_BATCH_SIZE = 15           # akun per batch
LATEST_MAX_POSTS = 12            # post terbaru per akun
LATEST_SCROLLS = 4              # scroll per akun
LATEST_PROFILE_DELAY_MIN = 15     # detik
LATEST_PROFILE_DELAY_MAX = 25     # detik
LATEST_BATCH_COOLDOWN = 600      # detik (10 menit)

# Rate limit settings
SKIP_SUCCESS_HOURS = 6              # skip jika sukses < 6 jam lalu
LOGIN_WALL_COOLDOWN_MINUTES = 120    # cooldown 2 jam setelah login wall
LOGIN_WALL_STREAK_LIMIT = 3          # stop jika 3 beruntun
GLOBAL_COOLDOWN_AFTER_RATE_LIMIT = 180  # 3 jam global cooldown

# MySQL Configuration (loaded from .env)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mayz_monitoring")

# Telegram Configuration (loaded from .env)
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Nightly Sync Configuration
NIGHTLY_SYNC_ENABLED = os.getenv("NIGHTLY_SYNC_ENABLED", "true").lower() == "true"
NIGHTLY_SYNC_WINDOW_START = os.getenv("NIGHTLY_SYNC_WINDOW_START", "22:00")
NIGHTLY_SYNC_WINDOW_END = os.getenv("NIGHTLY_SYNC_WINDOW_END", "23:59")

BASE_HEADERS = [
    "No.",
    "Nama Kanwil",
    "Nama Unit Eselon III",
    "Tanggal Postingan",
    "Jenis Kegiatan",
    "Judul Postingan",
    "Link",
    "Jenis Media Sosial",
    "Jumlah Reach / Audiens",
    "No. Agenda Setting",
    "Topik Agenda Setting",
]
EXTRA_FIELD_MAP = {
    "Like Count": "like_count",
    "Comment Count": "comment_count",
    "Total Engagement": "total_engagement",
    "Source Unique ID": "shortcode",
    "Media Type": "media_type",
    "Status Scraping": "status_scraping",
    "Status Periode": "status_periode",
    "Catatan": "catatan",
}

def prepare_folders():
    DATA_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)