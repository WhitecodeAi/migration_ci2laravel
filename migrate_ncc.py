#!/usr/bin/env python3
"""
Migration Script: NCC Enrollment Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_ncc_enrollment)
Target: u207346834_mnwc (ncc_enrollments)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date


def migrate_ncc():
    print("=" * 60)
    print("MIGRATING NCC ENROLLMENT: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_ncc_enrollment[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} NCC enrollment records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO ncc_enrollments (
                id, status, academic_year, academic_year_id, full_name, father_name,
                mother_name, dob, nationality, blood_group, institution_details,
                aadhar_no, previous_ncc_training, student_mobile, student_email,
                created_at, updated_at, remarks
            ) VALUES (
                %(id)s, %(status)s, %(academic_year)s, %(academic_year_id)s, %(full_name)s, %(father_name)s,
                %(mother_name)s, %(dob)s, %(nationality)s, %(blood_group)s, %(institution_details)s,
                %(aadhar_no)s, %(previous_ncc_training)s, %(student_mobile)s, %(student_email)s,
                %(created_at)s, %(updated_at)s, %(remarks)s
            ) ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                full_name = VALUES(full_name),
                father_name = VALUES(father_name),
                mother_name = VALUES(mother_name),
                dob = VALUES(dob),
                nationality = VALUES(nationality),
                blood_group = VALUES(blood_group),
                institution_details = VALUES(institution_details),
                aadhar_no = VALUES(aadhar_no),
                previous_ncc_training = VALUES(previous_ncc_training),
                student_mobile = VALUES(student_mobile),
                student_email = VALUES(student_email),
                updated_at = VALUES(updated_at),
                remarks = VALUES(remarks)
            """

            for r in raw_rows:
                dob = clean_date(r.get("dob"))
                if dob:
                    dob = dob[:10]
                c_date = clean_date(r.get("created_at")) or now_ts
                course_roll = f"Course: {r.get('course', '')}, Roll: {r.get('roll_no', '')}".strip()

                cur.execute(insert_query, {
                    "id": int(r["id"]),
                    "status": "Pending",
                    "academic_year": "2024-25",
                    "academic_year_id": 10,
                    "full_name": str(r.get("full_name") or "").strip(),
                    "father_name": str(r.get("father_name") or "").strip(),
                    "mother_name": str(r.get("mother_name") or "").strip(),
                    "dob": dob,
                    "nationality": str(r.get("nationality") or "").strip() or "Indian",
                    "blood_group": str(r.get("blood_group") or "").strip(),
                    "institution_details": str(r.get("institute") or "").strip(),
                    "aadhar_no": str(r.get("aadhar") or "").strip(),
                    "previous_ncc_training": str(r.get("prev_ncc") or "").strip(),
                    "student_mobile": str(r.get("mobile") or "").strip(),
                    "student_email": str(r.get("email") or "").strip(),
                    "created_at": c_date,
                    "updated_at": now_ts,
                    "remarks": course_roll
                })

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} NCC enrollment(s).")

            cur.execute("SELECT COUNT(*) AS c FROM ncc_enrollments")
            print(f"Total active ncc_enrollments count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== NCC ENROLLMENT MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_ncc()
