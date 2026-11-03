#!/usr/bin/env python3
"""
Migration Script: Academic Calendar Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_academic_calendar)
Target: u207346834_sathayelara (academic_date_category, academic_event_dates)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values, clean_date

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

TYPE_COLORS = {
    "holidays": "#ef4444",   # Red
    "exams": "#f59e0b",      # Amber
    "events": "#10b981",     # Green
    "other": "#3b82f6"       # Blue
}


def get_academic_year_id(date_str, year_to_id_map):
    if date_str and len(date_str) >= 10:
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if dt.month >= 6:
                y_str = f"{dt.year}-{str(dt.year+1)[2:]}"
            else:
                y_str = f"{dt.year-1}-{str(dt.year)[2:]}"
            if y_str in year_to_id_map:
                return year_to_id_map[y_str]
        except Exception:
            pass
    return year_to_id_map.get("2024-25", 10)


def migrate_academic_calendar():
    print("=" * 60)
    print("MIGRATING ACADEMIC CALENDAR: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Load Academic Years
            cur.execute("SELECT id, name FROM academic_years")
            year_to_id_map = {row["name"]: row["id"] for row in cur.fetchall()}
            print(f"Loaded {len(year_to_id_map)} academic years.")

            # Extract tbl_academic_calendar
            m_cal = re.findall(
                r"INSERT INTO [`\x27]?tbl_academic_calendar[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_cals = []
            if m_cal:
                cols = [c.strip(" `\r\n") for c in m_cal[0][0].split(",")]
                for _, vals in m_cal:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_cals.append(dict(zip(cols, r)))

            print(f"Found {len(raw_cals)} calendar entries in source dump.")

            # Load existing categories in academic_date_category
            cur.execute("SELECT id, category FROM academic_date_category WHERE delete_bit = 0")
            cat_map = {row["category"].strip().lower(): row["id"] for row in cur.fetchall()}

            cat_insert_sql = """
            INSERT INTO academic_date_category (category, color, delete_bit, created_at, updated_at)
            VALUES (%(category)s, %(color)s, 0, %(created_at)s, %(updated_at)s)
            """

            event_date_sql = """
            INSERT INTO academic_event_dates (
                id, category_id, academic_year_id, program_id, start_date, end_date,
                calendar_type, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(category_id)s, %(academic_year_id)s, NULL, %(start_date)s, %(end_date)s,
                %(calendar_type)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                category_id = VALUES(category_id),
                academic_year_id = VALUES(academic_year_id),
                start_date = VALUES(start_date),
                end_date = VALUES(end_date),
                calendar_type = VALUES(calendar_type),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for c in raw_cals:
                c_id = int(c["ac_id"])
                c_type = str(c.get("ac_type") or "other").strip().lower()
                c_title = str(c.get("ac_title") or "").strip()
                color = TYPE_COLORS.get(c_type, "#3b82f6")

                # Ensure category exists in academic_date_category
                cat_key = c_title.lower()
                if cat_key not in cat_map:
                    cur.execute(cat_insert_sql, {
                        "category": c_title,
                        "color": color,
                        "created_at": now_ts,
                        "updated_at": now_ts
                    })
                    cat_id = cur.lastrowid
                    cat_map[cat_key] = cat_id
                else:
                    cat_id = cat_map[cat_key]

                start_date_str = clean_date(c.get("ac_start_date"))
                start_date = start_date_str[:10] if start_date_str else now_ts[:10]
                end_date_str = clean_date(c.get("ac_end_date"))
                end_date = end_date_str[:10] if end_date_str else start_date

                ay_id = get_academic_year_id(start_date, year_to_id_map)

                # Determine calendar type
                cal_type = "College"
                if "department" in c_title.lower():
                    cal_type = "Department"

                cur.execute(event_date_sql, {
                    "id": c_id,
                    "category_id": cat_id,
                    "academic_year_id": ay_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "calendar_type": cal_type,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} academic calendar events into academic_event_dates.")

            # Verification
            cur.execute("""
            SELECT e.id, c.category, e.calendar_type, e.start_date, e.end_date, ay.name as academic_year
            FROM academic_event_dates e
            LEFT JOIN academic_date_category c ON e.category_id = c.id
            LEFT JOIN academic_years ay ON e.academic_year_id = ay.id
            WHERE e.delete_bit = 0
            ORDER BY e.start_date ASC
            LIMIT 10
            """)
            print("\nVerification - Sample Academic Calendar Events:")
            for r in cur.fetchall():
                print(f"  ID: {r['id']:2d} | {r['academic_year']:7s} | {r['calendar_type']:10s} | {r['start_date']} to {r['end_date']} | {r['category'][:45]}")

            cur.execute("SELECT COUNT(*) AS c FROM academic_event_dates WHERE delete_bit = 0")
            print(f"\nTotal active academic event dates: {cur.fetchone()['c']}")
            cur.execute("SELECT COUNT(*) AS c FROM academic_date_category WHERE delete_bit = 0")
            print(f"Total active academic date categories: {cur.fetchone()['c']}")

    finally:
        conn.close()

    print("\nAcademic Calendar Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_academic_calendar()
