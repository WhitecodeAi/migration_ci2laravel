#!/usr/bin/env python3
"""
Migration Script: Program Specializations & Subjects (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_program_specialization)
Target: u207346834_sathayelara (subjects)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values

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


def migrate_specializations():
    print("=" * 60)
    print("MIGRATING PROGRAM SPECIALIZATIONS -> SUBJECTS")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    m_spec = re.findall(
        r"INSERT INTO [`\x27]?tbl_program_specialization[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_specs = []
    if m_spec:
        cols = [c.strip(" `\r\n") for c in m_spec[0][0].split(",")]
        for _, vals in m_spec:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_specs.append(dict(zip(cols, r)))

    print(f"Found {len(raw_specs)} specializations in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Map departments
            cur.execute("SELECT id, LOWER(name) as name_key FROM departments WHERE delete_bit = 0")
            dept_map = {r["name_key"]: r["id"] for r in cur.fetchall()}

            subject_sql = """
            INSERT INTO subjects (
                id, subject_name, subject_code, department_id, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(subject_name)s, %(subject_code)s, %(department_id)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                subject_name = VALUES(subject_name),
                department_id = VALUES(department_id),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for s in raw_specs:
                s_id = int(s["tps_id"])
                name = str(s.get("tps_name") or "").strip()
                dept_id = dept_map.get(name.lower())

                # Generate a short subject code
                code = "".join([w[0] for w in name.split()]).upper()
                if len(code) == 1:
                    code = name[:3].upper()

                cur.execute(subject_sql, {
                    "id": s_id,
                    "subject_name": name,
                    "subject_code": code,
                    "department_id": dept_id,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} subjects into subjects.")

            cur.execute("""
            SELECT s.id, s.subject_name, s.subject_code, d.name as department
            FROM subjects s
            LEFT JOIN departments d ON s.department_id = d.id
            WHERE s.delete_bit = 0
            """)
            print("\nSubjects in Database:")
            for r in cur.fetchall():
                code_str = str(r.get('subject_code') or '')
                name_str = str(r.get('subject_name') or '')
                dept_str = str(r.get('department') or 'General')
                print(f"  ID: {r['id']:2d} | Code: {code_str:4s} | {name_str:20s} | Department: {dept_str}")

    finally:
        conn.close()

    print("\nSpecializations Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_specializations()
