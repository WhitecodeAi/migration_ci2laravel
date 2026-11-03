#!/usr/bin/env python3
"""
Migration Script: Testimonials Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_testimonial)
Target: u207346834_sathayelara.testimonials (MySQL on 193.203.184.233:3306)
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

def migrate_testimonials():
    print("=" * 60)
    print("MIGRATING TESTIMONIALS MODULE: CodeIgniter -> Laravel")
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
        cur.execute("SELECT COUNT(*) AS c FROM testimonials")
        initial_count = cur.fetchone()["c"]
        print(f"Initial records in testimonials: {initial_count}")

        # Fetch lookup ID for student testimonial type
        cur.execute("SELECT id FROM lookups WHERE `key` = 'testimonial_type' AND value = 'Student'")
        student_type_row = cur.fetchone()
        student_type_id = student_type_row["id"] if student_type_row else 201

        matches = re.findall(r"INSERT INTO `tbl_testimonial`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_testimonial!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_rows = []
        for _, vals_str in matches:
            for row in parse_sql_values(vals_str):
                raw_rows.append(dict(zip(cols, row)))

        print(f"Parsed {len(raw_rows)} records from tbl_testimonial.")

        insert_query = """
        INSERT INTO testimonials (
            id, department_id, salutation_id, name,
            designation, photo, message, batch,
            testimonial_type, delete_bit, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            department_id = VALUES(department_id),
            salutation_id = VALUES(salutation_id),
            name = VALUES(name),
            designation = VALUES(designation),
            photo = VALUES(photo),
            message = VALUES(message),
            batch = VALUES(batch),
            testimonial_type = VALUES(testimonial_type),
            delete_bit = VALUES(delete_bit),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at);
        """

        rows_to_insert = []
        for r in raw_rows:
            testim_id = int(r["testim_id"])
            name = (r.get("testim_author_name") or "").strip()
            desig = (r.get("testim_designation") or "").strip() or None
            raw_photo = (r.get("testim_file") or "").strip()
            clean_photo = raw_photo.replace("^%^path", "").strip() if raw_photo else None
            message = (r.get("testim_s_description") or "").strip()
            
            # Infer testimonial_type
            testim_type = (r.get("testim_type") or "").strip().lower()
            if "student" in name.lower() or testim_type == "student":
                t_type_id = student_type_id
            else:
                t_type_id = student_type_id

            delete_bit = 0  # Active
            created_ts = clean_timestamp(r.get("testim_created_date") or r.get("testim_testimonial_date"))

            rows_to_insert.append((
                testim_id, None, None, name,
                desig, clean_photo, message, None,
                t_type_id, delete_bit, created_ts, created_ts
            ))

        print(f"Inserting {len(rows_to_insert)} records into testimonials...")
        cur.executemany(insert_query, rows_to_insert)
        conn.commit()

        # Verification
        print("\n[Verification]")
        cur.execute("SELECT COUNT(*) AS c FROM testimonials")
        print(f"  Total records in testimonials: {cur.fetchone()['c']}")

        cur.execute("SELECT id, name, designation, photo, message, testimonial_type FROM testimonials")
        for t in cur.fetchall():
            print(f"  ID {t['id']} | Name: '{t['name']}' | Desig: '{t['designation']}' | Photo: '{t['photo']}' | Msg: '{t['message']}'")

        print("\n=== TESTIMONIALS MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_testimonials()

