#!/usr/bin/env python3
"""
Central Database Configuration for Migration (St. Mira College)
"""
import os
import pymysql

# Auto-load .env if present without hardcoding secrets in code
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key not in os.environ:
                    os.environ[key] = val

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USERNAME", ""),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_DATABASE", ""),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

SQL_FILE = os.environ.get("SQL_FILE", "u486681144_st_miraclg_liv.sql")

def get_connection():
    return pymysql.connect(**DB_CONFIG)
