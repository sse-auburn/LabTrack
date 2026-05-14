"""
One-off script: creates the LabTrack database on the configured MySQL server.
Run once before 'python manage.py migrate'.
Safe to re-run — uses CREATE DATABASE IF NOT EXISTS.
"""
import sys
import pymysql
from decouple import config

host = config('DB_HOST', default='')
if not host:
    print("DB_HOST is not set — nothing to do (SQLite mode).")
    sys.exit(0)

db_name = config('DB_NAME', default='labtrack')
conn_args = dict(
    host=host,
    port=int(config('DB_PORT', default='3306')),
    user=config('DB_USER', default='labtrack'),
    password=config('DB_PASSWORD', default=''),
    ssl={'check_hostname': False},
)

try:
    conn = pymysql.connect(**conn_args)
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
    conn.close()
    print(f"Database '{db_name}' is ready.")
except pymysql.err.OperationalError as e:
    print(f"Error: {e}")
    print("\nIf the error is 'Access denied', you don't have CREATE DATABASE")
    print("privileges on this server. Ask the DBA to create the database, or")
    print("run this SQL in MySQL Workbench:")
    print(f"\n  CREATE DATABASE `{db_name}`")
    print("    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    sys.exit(1)
