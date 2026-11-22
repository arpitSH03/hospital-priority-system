"""
Database Connection and Initialization Utilities.

Uses mysql-connector-python to connect to the MySQL database specified in backend/config.py.
Provides helper functions for acquiring connections and executing the database schema.
"""

from pathlib import Path
from typing import Any, Optional

try:
    import mysql.connector
    from mysql.connector import Error, MySQLConnection
except ImportError:
    mysql = None
    Error = Exception
    MySQLConnection = Any
from backend.config import BASE_DIR, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


def get_db_connection(use_database: bool = True) -> MySQLConnection:
    """
    Creates and returns a connection to the MySQL database server.
    
    Args:
        use_database (bool): If True, connects directly to DB_NAME.
                             If False, connects to the MySQL server without selecting a DB
                             (useful for CREATE DATABASE commands during initialization).
                             
    Returns:
        MySQLConnection: Active MySQL connection.
        
    Raises:
        mysql.connector.Error: If the connection attempt fails.
    """
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "autocommit": True,
    }
    if use_database:
        config["database"] = DB_NAME

    try:
        connection = mysql.connector.connect(**config)
        return connection
    except Error as e:
        print(f"[Database Error] Could not connect to MySQL at {DB_HOST}:{DB_PORT}: {e}")
        raise e


def init_db(schema_file_path: Optional[Path] = None) -> bool:
    """
    Initializes the database by executing sql/schema.sql.
    
    Creates the database (if not exists), sets up tables (doctors, patients, treatment_log),
    creates indexes, and inserts initial seed data.
    
    Args:
        schema_file_path (Optional[Path]): Custom path to schema.sql. Defaults to sql/schema.sql.
        
    Returns:
        bool: True if database initialization succeeded.
    """
    if schema_file_path is None:
        schema_file_path = BASE_DIR / "sql" / "schema.sql"

    if not schema_file_path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_file_path}")

    with open(schema_file_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print(f"[Database] Reading schema from: {schema_file_path}")
    print(f"[Database] Connecting to MySQL server at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")

    # Connect to MySQL server without selecting a database first
    conn = get_db_connection(use_database=False)
    cursor = conn.cursor()

    try:
        # Execute the multi-statement schema SQL script
        for result in cursor.execute(schema_sql, multi=True):
            if result.with_rows:
                result.fetchall()

        conn.commit()
        print(f"[Database] Successfully initialized database '{DB_NAME}' with tables and seed data.")
        return True
    except Error as e:
        print(f"[Database Error] Failed to execute schema script: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_db()
