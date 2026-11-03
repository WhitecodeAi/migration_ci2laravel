#!/usr/bin/env python3
"""
Migration Script: NIRF Reports Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_nirfs, tbl_nirf_year)
Target: u207346834_mnwc (nirf)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def migrate_nirf():
    print("=" * 60)
    print("MIGRATING NIRF REPORTS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Parse tbl_nirf_year
    year_map = {}
    m_years = re.findall(
        r"INSERT INTO [`\x27]?tbl_nirf_year[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    if m_years:
        cols_y = [c.strip(" `\r\n") for c in m_years[0][0].split(",")]
        for _, vals in m_years:
            for r in parse_sql_values(vals):
                d = dict(zip(cols_y, r))
                y_id = str(d.get("tny_id"))
                y_val = str(d.get("tny_year") or "").strip()
                if y_id and y_val:
                    year_map[y_id] = y_val

    # Parse tbl_nirfs
    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_nirfs[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_rows = []
    if matches:
        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        for _, vals in matches:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_rows.append(dict(zip(cols, r)))

    print(f"Found {len(raw_rows)} NIRF records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO nirf (
                id, title, source, show_on_website, delete_bit,
                created_at, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(source)s, %(show_on_website)s, %(delete_bit)s,
                %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                source = VALUES(source),
                show_on_website = VALUES(show_on_website),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            for r in raw_rows:
                n_id = int(r["nirf_id"])
                title = str(r.get("nirf_title") or "").strip()
                y_id = str(r.get("nirf_year"))
                if y_id in year_map:
                    year_name = year_map[y_id]
                    if year_name not in title:
                        title = f"{title} ({year_name})"
                src = clean_path(r.get("nirf_link"))
                c_date = clean_date(r.get("nirf_created_date")) or now_ts

                cur.execute(insert_query, {
                    "id": n_id,
                    "title": title,
                    "source": src,
                    "show_on_website": 1,
                    "delete_bit": 0,
                    "created_at": c_date,
                    "updated_at": now_ts
                })

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} NIRF report(s).")

            cur.execute("SELECT COUNT(*) AS c FROM nirf")
            print(f"Total active nirf count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== NIRF REPORTS MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_nirf()

