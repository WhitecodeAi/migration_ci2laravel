#!/usr/bin/env python3
"""
Migration Script: Birthday List Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_birthday_list)
Target: u207346834_mnwc (birthdays)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def migrate_birthdays():
    print("=" * 60)
    print("MIGRATING BIRTHDAY LIST: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_birthday_list[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} birthday records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO birthdays (
                id, student_name, class, salutation, gender,
                dob, student_photo, show_on_website, delete_bit,
                created_at, updated_at
            ) VALUES (
                %(id)s, %(student_name)s, %(class)s, %(salutation)s, %(gender)s,
                %(dob)s, %(student_photo)s, %(show_on_website)s, %(delete_bit)s,
                %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                student_name = VALUES(student_name),
                class = VALUES(class),
                gender = VALUES(gender),
                dob = VALUES(dob),
                student_photo = VALUES(student_photo),
                show_on_website = VALUES(show_on_website),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            for r in raw_rows:
                dob = clean_date(r.get("bl_dob"))
                if dob:
                    dob = dob[:10]
                photo = clean_path(r.get("bl_image"))
                g_str = str(r.get("bl_gender") or "").strip().lower()
                gender_id = 1 if "female" in g_str else 2

                cur.execute(insert_query, {
                    "id": int(r["bl_id"]),
                    "student_name": str(r.get("bl_name") or "").strip(),
                    "class": str(r.get("bl_class") or "").strip(),
                    "salutation": 1,
                    "gender": gender_id,
                    "dob": dob,
                    "student_photo": photo,
                    "show_on_website": 1,
                    "delete_bit": 0,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} birthday record(s).")

            cur.execute("SELECT COUNT(*) AS c FROM birthdays")
            print(f"Total active birthdays count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== BIRTHDAY LIST MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_birthdays()

