#!/usr/bin/env python3
"""
Migration Script: Subjects Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_subject_list)
Target: u207346834_mnwc (subjects)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date


def migrate_subjects():
    print("=" * 60)
    print("MIGRATING SUBJECTS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_subject_list[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} subject records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Load valid departments
            cur.execute("SELECT id FROM departments")
            valid_dept_ids = set(row["id"] for row in cur.fetchall())

            insert_query = """
            INSERT INTO subjects (
                id, subject_name, subject_code, department_id,
                delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(subject_name)s, %(subject_code)s, %(department_id)s,
                %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                subject_name = VALUES(subject_name),
                subject_code = VALUES(subject_code),
                department_id = VALUES(department_id),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            batch = []
            for r in raw_rows:
                s_id = int(r["sub_id"])
                name = str(r.get("sub_name") or "").strip()
                if not name:
                    continue
                code = f"SUB-{s_id:04d}"
                c_date = clean_date(r.get("created_at")) or now_ts
                del_bit = 1 if str(r.get("delete_bit")) == "1" else 0

                batch.append({
                    "id": s_id,
                    "subject_name": name[:255],
                    "subject_code": code,
                    "department_id": None,
                    "delete_bit": del_bit,
                    "created_at": c_date,
                    "updated_at": now_ts
                })

            batch_size = 200
            for i in range(0, len(batch), batch_size):
                cur.executemany(insert_query, batch[i:i+batch_size])
                conn.commit()

            print(f"Successfully migrated {len(batch)} subject(s).")

            cur.execute("SELECT COUNT(*) AS c FROM subjects")
            print(f"Total active subjects count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== SUBJECTS MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_subjects()

