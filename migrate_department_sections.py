#!/usr/bin/env python3
"""
Migration Script: Department Tab Sections & Academic Content (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_section_master, tbl_section_info)
Target: u207346834_sathayelara (dept_sections, department_section_mappings)
"""

import sys
import os
import re
import json
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


def normalize_section_name(name):
    if not name:
        return "About Department"
    name = str(name).strip()
    name_l = name.lower()
    if "about" in name_l:
        return "About Department"
    if "vision" in name_l or "mission" in name_l:
        return "Vision / Mission / Objectives"
    if "outcome" in name_l or "obe" in name_l:
        return "Outcome Based Education"
    if "syllabus" in name_l:
        return "Syllabus"
    if "course" in name_l:
        return "Courses Offered"
    if "infra" in name_l or "facilit" in name_l:
        return "Infrastructure / Facilities"
    if "calendar" in name_l:
        return "Academic Calendar"
    if "time table" in name_l:
        return "Time Table"
    if "career" in name_l or "add-on" in name_l:
        return "Career Oriented Courses"
    if "publication" in name_l or "research" in name_l:
        return "Research Publications"
    if "achievement" in name_l:
        return "Students Achievement"
    if "staff" in name_l or "faculty" in name_l:
        return "Teaching Staff"
    if "alumni" in name_l:
        return "Alumni Corner"
    return name


def migrate_department_sections():
    print("=" * 60)
    print("MIGRATING DEPARTMENT SECTION CONTENTS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Extract tbl_section_master
    m_sm = re.findall(r"INSERT INTO [`\x27]?tbl_section_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
    sm_cols = [c.strip(" `\r\n") for c in m_sm[0][0].split(",")]
    sm_names = {}
    for _, vals in m_sm:
        for r in parse_sql_values(vals):
            d = dict(zip(sm_cols, r))
            sm_names[int(d["dsm_id"])] = d.get("dsm_section_name") or ""

    # Extract tbl_section_info
    m_si = re.findall(r"INSERT INTO [`\x27]?tbl_section_info[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
    si_cols = [c.strip(" `\r\n") for c in m_si[0][0].split(",")]
    raw_info = []
    for _, vals in m_si:
        for r in parse_sql_values(vals):
            d = dict(zip(si_cols, r))
            raw_info.append(d)

    print(f"Parsed {len(raw_info)} section info records from source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Load existing departments
            cur.execute("SELECT id FROM departments WHERE delete_bit = 0")
            valid_dept_ids = {r["id"] for r in cur.fetchall()}

            # Load existing dept_sections
            cur.execute("SELECT id, LOWER(section_name) as name_key FROM dept_sections WHERE delete_bit = 0")
            section_map = {r["name_key"]: r["id"] for r in cur.fetchall()}

            # Helper to get or create dept_section
            def get_or_create_section(sec_name):
                sec_name = sec_name.strip()
                k = sec_name.lower()
                if k in section_map:
                    return section_map[k]
                cur.execute("""
                INSERT INTO dept_sections (section_name, display_name, is_default, ordering, delete_bit, created_at, updated_at)
                VALUES (%s, %s, 0, 0, 0, %s, %s)
                """, (sec_name, sec_name, now_ts, now_ts))
                new_id = cur.lastrowid
                section_map[k] = new_id
                return new_id

            mapping_sql = """
            INSERT INTO department_section_mappings (
                department_id, dept_sections_id, is_visible, data, ordering, delete_bit, created_at, updated_at
            ) VALUES (
                %(department_id)s, %(dept_sections_id)s, 1, %(data)s, %(ordering)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                data = VALUES(data),
                is_visible = 1,
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for row in raw_info:
                content = (row.get("dsi_new_content") or row.get("dsi_content") or "").strip()
                dsl_id = row.get("dsi_dsl_id")
                if not content or not dsl_id or int(dsl_id) <= 0:
                    continue

                dept_id = int(dsl_id)
                if dept_id not in valid_dept_ids:
                    continue

                dsm_id = int(row.get("dsi_dsm_id") or 1)
                raw_sec_name = sm_names.get(dsm_id, "About Department")
                norm_sec_name = normalize_section_name(raw_sec_name)
                dept_sec_id = get_or_create_section(norm_sec_name)

                created_at = clean_date(row.get("dsi_time")) or now_ts
                ordering = int(row.get("dsm_order") or 0)
                json_data = json.dumps([{"type": "richtext", "content": content}], ensure_ascii=False)

                cur.execute(mapping_sql, {
                    "department_id": dept_id,
                    "dept_sections_id": dept_sec_id,
                    "data": json_data,
                    "ordering": ordering,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} department section tabs.")

            cur.execute("""
            SELECT ds.section_name, COUNT(m.id) as count
            FROM department_section_mappings m
            JOIN dept_sections ds ON m.dept_sections_id = ds.id
            WHERE m.delete_bit = 0
            GROUP BY ds.id, ds.section_name
            ORDER BY count DESC
            LIMIT 10
            """)
            print("\nTop Migrated Department Sections:")
            for r in cur.fetchall():
                print(f"  {r['section_name']:35s}: {r['count']:4d} entries")

            cur.execute("SELECT COUNT(*) as c FROM department_section_mappings WHERE delete_bit = 0")
            print(f"\nTotal active department section mappings: {cur.fetchone()['c']}")

    finally:
        conn.close()

    print("\nDepartment Sections Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_department_sections()
