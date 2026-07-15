"""
Database Module - MySQL connection dan initialization.
Single source of truth untuk koneksi database.
"""

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "mayz_monitoring")

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Jakarta")


def get_connection_params() -> dict:
    """Get database connection parameters from environment."""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DATABASE,
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "autocommit": False,
    }


def get_connection():
    """
    Create and return a new MySQL connection.
    Caller is responsible for closing the connection.
    """
    import mysql.connector

    try:
        connection = mysql.connector.connect(
            pool_name="mayz_pool",
            pool_size=DB_POOL_SIZE,
            pool_reset_session=True,
            **get_connection_params()
        )
        return connection
    except mysql.connector.Error:
        return mysql.connector.connect(**get_connection_params())


@contextmanager
def get_db_cursor(commit: bool = True):
    """
    Context manager for database operations.

    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM accounts")
            results = cursor.fetchall()
    """
    import mysql.connector

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        yield cursor
        if commit:
            connection.commit()
    except mysql.connector.Error as e:
        if connection:
            connection.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def test_connection() -> tuple:
    """
    Test database connection.
    Returns: (success: bool, message: str)
    """
    from mysql.connector import Error

    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result and result[0] == 1:
            return True, "Koneksi database berhasil"
        return False, "Koneksi database gagal"
    except Error as e:
        return False, f"Koneksi database gagal: {str(e)}"
    except ImportError:
        return False, "MySQL connector tidak terinstall. Jalankan: pip install mysql-connector-python"


def init_database(drop_existing: bool = False) -> bool:
    """
    Initialize database and create all required tables.

    Args:
        drop_existing: If True, drop existing tables first (DANGEROUS!)

    Returns:
        bool: True if successful
    """
    from mysql.connector import Error

    params = get_connection_params()
    database_name = params.pop("database")

    try:
        connection = mysql.connector.connect(**params)
        cursor = connection.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        connection.close()

        connection = mysql.connector.connect(**get_connection_params())
        cursor = connection.cursor()

        tables = {
            "accounts": """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nama_unit VARCHAR(255) NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    profile_url VARCHAR(500) NOT NULL,
                    kategori_unit VARCHAR(100) DEFAULT '',
                    wilayah VARCHAR(100) DEFAULT '',
                    is_active BOOLEAN DEFAULT TRUE,
                    account_health ENUM('HEALTHY', 'WARNING', 'ERROR') DEFAULT 'HEALTHY',
                    last_checked_at DATETIME NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_username (username)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "posts": """
                CREATE TABLE IF NOT EXISTS posts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    account_id INT NULL,
                    username VARCHAR(100) NOT NULL,
                    nama_unit VARCHAR(255) NOT NULL,
                    shortcode VARCHAR(50) NOT NULL,
                    post_url VARCHAR(500) NOT NULL,
                    caption TEXT,
                    timestamp DATETIME NULL,
                    media_type VARCHAR(50) DEFAULT 'UNKNOWN',
                    media_url VARCHAR(500) DEFAULT '',
                    alt_text TEXT,
                    like_count INT NULL,
                    comments_count INT NULL,
                    total_engagement INT NULL,
                    view_count INT NULL,
                    engagement_rate DECIMAL(5,2) NULL,
                    -- Extended metrics (optional - may require Instagram Insights)
                    play_count INT NULL,
                    share_count INT NULL,
                    save_count INT NULL,
                    reach_count INT NULL,
                    -- Meta
                    status_scraping VARCHAR(50) DEFAULT 'PENDING',
                    status_periode VARCHAR(50) DEFAULT '',
                    source_type ENUM('SCRAPED', 'MANUAL') DEFAULT 'SCRAPED',
                    null_reason TEXT,
                    is_new_post BOOLEAN DEFAULT FALSE,
                    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_account_shortcode (username, shortcode),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_status_scraping (status_scraping),
                    INDEX idx_is_new_post (is_new_post),
                    INDEX idx_username (username),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
                    "scrape_jobs": """
                        CREATE TABLE IF NOT EXISTS scrape_jobs (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            job_id VARCHAR(100) NOT NULL UNIQUE,
                            job_type ENUM('LATEST_SYNC', 'PERIOD_SYNC') NOT NULL,
                            trigger_type ENUM('SCHEDULED', 'MANUAL') NOT NULL,
                            period_start DATE NULL,
                            period_end DATE NULL,
                            status ENUM('QUEUED', 'RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', 'SKIPPED') DEFAULT 'QUEUED',
                            requested_by VARCHAR(100) DEFAULT 'system',
                            started_at DATETIME NULL,
                            finished_at DATETIME NULL,
                            total_accounts INT DEFAULT 0,
                            total_posts_found INT DEFAULT 0,
                            total_posts_inserted INT DEFAULT 0,
                            total_posts_updated INT DEFAULT 0,
                            total_success INT DEFAULT 0,
                            total_partial INT DEFAULT 0,
                            total_failed INT DEFAULT 0,
                            error_message TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_status (status),
                            INDEX idx_job_type (job_type),
                            INDEX idx_created_at (created_at)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """,
                        "job_logs": """
            CREATE TABLE IF NOT EXISTS job_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(100) NOT NULL,
                level VARCHAR(20) DEFAULT 'INFO',
                stage VARCHAR(80) DEFAULT '',
                message TEXT,
                account_username VARCHAR(100) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_job_id (job_id),
                INDEX idx_created_at (created_at),
                INDEX idx_stage (stage)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
            "field_status": """
                CREATE TABLE IF NOT EXISTS field_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    post_id INT NULL,
                    field_name VARCHAR(50) NOT NULL,
                    value_status ENUM('OK', 'NULL', 'FAILED') DEFAULT 'NULL',
                    source VARCHAR(100) DEFAULT '',
                    selector_used VARCHAR(200) DEFAULT '',
                    attempted_selectors TEXT,
                    null_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    INDEX idx_post_id (post_id),
                    INDEX idx_field_name (field_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "debug_logs": """
                CREATE TABLE IF NOT EXISTS debug_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    post_id INT NULL,
                    username VARCHAR(100) DEFAULT '',
                    shortcode VARCHAR(50) DEFAULT '',
                    post_url VARCHAR(500) DEFAULT '',
                    issue_type VARCHAR(100) DEFAULT '',
                    null_reason TEXT,
                    html_file VARCHAR(500) DEFAULT '',
                    screenshot_file VARCHAR(500) DEFAULT '',
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_username (username),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "notification_logs": """
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    post_id INT NULL,
                    username VARCHAR(100) DEFAULT '',
                    shortcode VARCHAR(50) DEFAULT '',
                    channel ENUM('TELEGRAM', 'WHATSAPP') NOT NULL,
                    recipient VARCHAR(200) NOT NULL,
                    message TEXT,
                    status ENUM('SENT', 'FAILED', 'SKIPPED') DEFAULT 'SKIPPED',
                    sent_at DATETIME NULL,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_shortcode_channel_recipient (shortcode, channel, recipient),
                    INDEX idx_status (status),
                    INDEX idx_sent_at (sent_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            "settings": """
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    setting_key VARCHAR(100) NOT NULL UNIQUE,
                    setting_value TEXT,
                    description VARCHAR(500) DEFAULT '',
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        }

        for table_name, create_sql in tables.items():
            cursor.execute(create_sql)
            print(f"  Table '{table_name}' created/verified")
        default_settings = [
            ("running_job_timeout_minutes", "180", "Auto-fail RUNNING jobs older than this value"),
            ("latest_sync_interval_minutes", "60", "Recommended scheduler interval for latest sync"),
            ("nightly_sync_enabled", "true", "Enable/disable nightly sync cron job"),
            ("nightly_sync_window_start", "17:58", "Start time for nightly sync window (HH:MM)"),
            ("nightly_sync_window_end", "19:59", "End time for nightly sync window (HH:MM)"),
            ("telegram_enabled", "false", "Enable/disable Telegram notifications"),
            ("telegram_bot_token", "", "Telegram bot token for notifications"),
            ("telegram_chat_id", "", "Telegram chat ID for notifications"),
            ("telegram_notify_new_post", "true", "Send notification for new posts"),
            ("latest_max_posts_per_account", "12", "Maximum posts checked per account for nightly latest sync"),
            ("latest_scrolls_per_account", "4", "Profile scroll count for latest sync"),
            ("period_max_posts_per_account", "120", "Maximum posts checked per account for manual period sync"),
            ("period_scrolls_per_account", "30", "Profile scroll count for manual period sync"),
            ("delay_between_accounts", "5.0", "Delay between Instagram accounts"),
            ("detail_delay_min", "1.8", "Minimum delay between post detail requests"),
            ("detail_delay_max", "3.8", "Maximum delay between post detail requests"),
            ("detail_batch_size", "12", "Batch size for post detail extraction"),
            ("detail_batch_cooldown", "12.0", "Cooldown between detail extraction batches"),
            ("login_wall_threshold", "3", "Jumlah login wall beruntun sebelum stop batch"),
            ("login_wall_cooldown_minutes", "30", "Cooldown setelah login wall detected"),
            ("max_consecutive_failures", "10", "Maks kegagalan beruntun sebelum stop"),
        ]

        for key, value, description in default_settings:
            cursor.execute("""
                INSERT IGNORE INTO settings (setting_key, setting_value, description)
                VALUES (%s, %s, %s)
            """, (key, value, description))

        connection.commit()
        cursor.close()
        connection.close()

        print("Database initialization complete!")
        return True

    except Error as e:
        print(f"Database initialization failed: {e}")
        return False


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value from the settings table."""
    try:
        with get_db_cursor(commit=False) as cursor:
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key = %s", (key,))
            result = cursor.fetchone()
            return result["setting_value"] if result else default
    except Exception:
        return os.getenv(key.upper(), default)


def set_setting(key: str, value: str) -> bool:
    """Set a setting value in the settings table."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
            """, (key, value, value))
        return True
    except Exception:
        return False


def migrate_extended_metrics_columns() -> bool:
    """
    Add extended metrics columns to posts table if they don't exist.
    Safe migration - only adds columns, never modifies or removes.
    Returns True if successful.
    """
    from mysql.connector import Error

    extended_columns = [
        ("play_count", "INT NULL"),
        ("share_count", "INT NULL"),
        ("save_count", "INT NULL"),
        ("reach_count", "INT NULL"),
    ]

    try:
        with get_db_cursor() as cursor:
            for col_name, col_type in extended_columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE posts
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                    """)
                except Error:
                    # Column might already exist, ignore
                    pass
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def ensure_extended_columns() -> bool:
    """
    Ensure extended metrics columns exist.
    Call this before inserting data with extended metrics.
    """
    return migrate_extended_metrics_columns()


def migrate_rolling_sync_columns() -> bool:
    """
    Add columns for Rolling Latest Sync tracking.
    Safe migration - only adds columns, never modifies or removes.
    Returns True if successful.
    """
    from mysql.connector import Error

    columns = [
        ("last_latest_scrape_at", "DATETIME NULL"),
        ("last_scrape_status", "VARCHAR(50) NULL"),
        ("last_login_wall_at", "DATETIME NULL"),
        ("consecutive_login_wall_count", "INT DEFAULT 0"),
        ("next_eligible_scrape_at", "DATETIME NULL"),
    ]

    try:
        with get_db_cursor() as cursor:
            for col_name, col_type in columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE accounts
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                    """)
                    print(f"  Column '{col_name}' added/verified")
                except Error:
                    # Column might already exist, ignore
                    pass
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def get_global_rate_limit_state() -> dict:
    """Get global rate limit state from settings."""
    with get_db_cursor(commit=False) as cursor:
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key IN ('global_rate_limited_until', 'global_rate_limit_reason')
        """)
        rows = cursor.fetchall()
        result = {"until": None, "reason": ""}
        for row in rows:
            if row["setting_key"] == "global_rate_limited_until":
                result["until"] = row["setting_value"]
            elif row["setting_key"] == "global_rate_limit_reason":
                result["reason"] = row["setting_value"] or ""
        return result


def set_global_rate_limit(until: str, reason: str = "") -> bool:
    """Set global rate limit cooldown."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO settings (setting_key, setting_value, description)
                VALUES ('global_rate_limited_until', %s, 'Global rate limit cooldown until')
                ON DUPLICATE KEY UPDATE setting_value = %s
            """, (until, until))
            cursor.execute("""
                INSERT INTO settings (setting_key, setting_value, description)
                VALUES ('global_rate_limit_reason', %s, 'Reason for global rate limit')
                ON DUPLICATE KEY UPDATE setting_value = %s
            """, (reason, reason))
        return True
    except Exception:
        return False


def clear_global_rate_limit() -> bool:
    """Clear global rate limit (set to NULL)."""
    return set_global_rate_limit(None, "")


if __name__ == "__main__":
    print("Testing database connection...")
    success, message = test_connection()
    print(message)

    if success:
        print("\nInitializing database...")
        init_database()
