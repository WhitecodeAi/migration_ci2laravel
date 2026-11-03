#!/usr/bin/env python3
"""
Central Database Configuration for Migration
"""
import os
import pymysql

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "193.203.184.233"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USERNAME", "u207346834_mnwc"),
    "password": os.environ.get("DB_PASSWORD", "tC/Ew=E#8"),
    "database": os.environ.get("DB_DATABASE", "u207346834_mnwc"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

SQL_FILE = os.environ.get("SQL_FILE", "mnwc_db.sql")

def get_connection():
    return pymysql.connect(**DB_CONFIG)

