#!/usr/bin/env python3
"""
Migration Script: Student Admission Enquiry Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_student_admission_enquiry)
Target: u207346834_mnwc (student_admission_enquiry)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date


def migrate_admissions():
    print("=" * 60)
    print("MIGRATING STUDENT ADMISSION ENQUIRIES: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_student_admission_enquiry[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} admission enquiry records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO student_admission_enquiry (
                id, name, contact, email, course, comment, year,
                is_replied, created_at, updated_at, delete_bit
            ) VALUES (
                %(id)s, %(name)s, %(contact)s, %(email)s, %(course)s, %(comment)s, %(year)s,
                %(is_replied)s, %(created_at)s, %(updated_at)s, %(delete_bit)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                contact = VALUES(contact),
                email = VALUES(email),
                course = VALUES(course),
                comment = VALUES(comment),
                year = VALUES(year),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            for r in raw_rows:
                c_date = clean_date(r.get("tbl_sae_current_time")) or now_ts

                cur.execute(insert_query, {
                    "id": int(r["tbl_sae_id"]),
                    "name": str(r.get("tbl_sae_name") or "").strip(),
                    "contact": str(r.get("tbl_sae_contact") or "").strip(),
                    "email": str(r.get("tbl_sae_email") or "").strip(),
                    "course": str(r.get("tbl_sae_course") or "").strip(),
                    "comment": str(r.get("tbl_sae_comment") or "").strip(),
                    "year": str(r.get("tbl_sae_year") or "").strip(),
                    "is_replied": 0,
                    "created_at": c_date,
                    "updated_at": now_ts,
                    "delete_bit": 0
                })

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} admission enquiry record(s).")

            cur.execute("SELECT COUNT(*) AS c FROM student_admission_enquiry")
            print(f"Total active student_admission_enquiry count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== STUDENT ADMISSION ENQUIRY MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_admissions()

