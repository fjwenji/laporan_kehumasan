"""
Database connection and operations - reusing existing database.py
"""
import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
from typing import Optional
from app.config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER,
    MYSQL_PASSWORD, MYSQL_DATABASE
)

# Connection pool
_connection_pool: Optional[pooling.MySQLConnectionPool] = None


def get_pool() -> pooling.MySQLConnectionPool:
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name="mayz_api_pool",
            pool_size=5,
            pool_reset_session=True,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
    return _connection_pool


def get_connection():
    """Get a connection from pool."""
    return get_pool().get_connection()


@contextmanager
def get_db_cursor(commit: bool = True):
    """Context manager for database operations."""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        yield cursor
        if commit:
            connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def test_connection() -> tuple:
    """Test database connection."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "Koneksi database berhasil"
    except Exception as e:
        return False, str(e)
