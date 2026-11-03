#!/usr/bin/env python3
"""
Migration Script: Quick Links Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_quick_links)
Target: u207346834_sathayelara.quick_links (MySQL on 193.203.184.233:3306)
"""

import sys
import os
import re
import pymysql
from datetime import datetime

DB_CONFIG = {
    "host": "193.203.184.233",
    "port": 3306,
    "user": "u207346834_sathayelara",
    "password": "Fp>6ClxZZ6",
    "database": "u207346834_sathayelara",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

SQL_FILE = "u208972730_scnewcms.sql"

def parse_sql_values(values_str):
    records = []
    current_record = []
    current_val = []
    in_quotes = False
    escape = False
    in_record = False
    i = 0
    n = len(values_str)
    while i < n:
        char = values_str[i]
        if not in_record:
            if char == "(":
                in_record = True
                current_record = []
                current_val = []
                in_quotes = False
                escape = False
        else:
            if escape:
                current_val.append(char)
                escape = False
            elif char == "\\":
                escape = True
            elif char == "\x27":
                if in_quotes:
                    if i + 1 < n and values_str[i+1] == "\x27":
                        current_val.append("\x27")
                        i += 1
                    else:
                        in_quotes = False
                else:
                    in_quotes = True
            elif char == "," and not in_quotes:
                val = "".join(current_val).strip()
                current_record.append(None if val == "NULL" else val)
                current_val = []
            elif char == ")" and not in_quotes:
                val = "".join(current_val).strip()
                current_record.append(None if val == "NULL" else val)
                records.append(current_record)
                in_record = False
                current_record = []
                current_val = []
            else:
                current_val.append(char)
        i += 1
    return records

def clean_timestamp(d_str):
    if not d_str or d_str in ("NULL", "None", "") or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = str(d_str).strip()
    if len(d_str) == 10:
        return f"{d_str} 00:00:00"
    return d_str

def migrate_quicklinks():
    print("=" * 60)
    print("MIGRATING QUICK LINKS MODULE: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL dump file '{SQL_FILE}' not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="latin1") as f:
        sql = f.read()

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) AS c FROM quick_links")
        initial_count = cur.fetchone()["c"]
        print(f"Initial records in quick_links: {initial_count}")

        matches = re.findall(r"INSERT INTO `tbl_quick_links`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_quick_links!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_rows = []
        for _, vals_str in matches:
            for row in parse_sql_values(vals_str):
                raw_rows.append(dict(zip(cols, row)))

        print(f"Parsed {len(raw_rows)} records from tbl_quick_links.")

        insert_query = """
        INSERT INTO quick_links (
            id, title, logo, link, show_on_website,
            sequence, delete_bit, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            logo = VALUES(logo),
            link = VALUES(link),
            show_on_website = VALUES(show_on_website),
            sequence = VALUES(sequence),
            delete_bit = VALUES(delete_bit),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at);
        """

        rows_to_insert = []
        for idx, r in enumerate(raw_rows, start=1):
            ql_id = int(r["tql_id"])
            title = (r.get("tql_title") or "").strip()
            raw_logo = (r.get("tql_logo") or "").strip()
            clean_logo = raw_logo.replace("^%^path", "").strip() if raw_logo else None
            link = (r.get("tql_link") or "").strip()
            
            show_on_website = 1
            sequence = idx
            delete_bit = 0  # Active

            created_ts = clean_timestamp(r.get("tql_time"))

            rows_to_insert.append((
                ql_id, title, clean_logo, link, show_on_website,
                sequence, delete_bit, created_ts, created_ts
            ))

        print(f"Inserting {len(rows_to_insert)} records into quick_links...")
        cur.executemany(insert_query, rows_to_insert)
        conn.commit()

        # Verification
        print("\n[Verification]")
        cur.execute("SELECT COUNT(*) AS c FROM quick_links")
        print(f"  Total records in quick_links: {cur.fetchone()['c']}")

        cur.execute("SELECT id, title, logo, link, sequence, show_on_website FROM quick_links")
        for ql in cur.fetchall():
            print(f"  ID {ql['id']} | Seq: {ql['sequence']} | Title: '{ql['title']}' | Link: '{ql['link']}' | Logo: '{ql['logo']}'")

        print("\n=== QUICK LINKS MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_quicklinks()

