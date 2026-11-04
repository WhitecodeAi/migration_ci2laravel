#!/usr/bin/env python3
"""
Migration Script: Department Sections Module (CodeIgniter -> Laravel)
Source: u486681144_st_miraclg_liv.sql (tbl_section_master, tbl_section_info)
Target: u207346834_stmiracollege (dept_sections, department_section_mappings)
"""

import os
import sys
import re
import json
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values


def clean_html(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace(r'\"', '"').replace(r"\'", "'")
    text = text.replace(r'\r\n', '\n').replace(r'\n', '\n').replace(r'\t', '\t')
    return text.strip()


def migrate_sections():
    print("=" * 60)
    print("MIGRATING DEPARTMENT SECTIONS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -------------------------------------------------------------
    # 1. Parse tbl_section_master
    # -------------------------------------------------------------
    m_master = re.findall(
        r"INSERT INTO [`\x27]?tbl_section_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)",
        sql,
        re.DOTALL
    )
    raw_master = []
    if m_master:
        cols_m = [c.strip(" `\r\n") for c in m_master[0][0].split(",")]
        for _, vals in m_master:
            for r in parse_sql_values(vals):
                raw_master.append(dict(zip(cols_m, r)))

    print(f"Found {len(raw_master)} section master records in source dump.")

    # -------------------------------------------------------------
    # 2. Parse tbl_section_info
    # -------------------------------------------------------------
    m_info = re.findall(
        r"INSERT INTO [`\x27]?tbl_section_info[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)",
        sql,
        re.DOTALL
    )
    raw_info = []
    if m_info:
        cols_i = [c.strip(" `\r\n") for c in m_info[0][0].split(",")]
        for _, vals in m_info:
            for r in parse_sql_values(vals):
                raw_info.append(dict(zip(cols_i, r)))

    print(f"Found {len(raw_info)} section info records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Load existing departments in Laravel
            cur.execute("SELECT id FROM departments")
            valid_dept_ids = {r["id"] for r in cur.fetchall()}

            # Load existing dept_sections
            cur.execute("SELECT id, section_name FROM dept_sections")
            existing_sections = {r["section_name"].strip().lower(): r["id"] for r in cur.fetchall()}

            # Map CI dsm_id -> Laravel dept_sections_id
            ci_to_lara_sec = {}
            for s in raw_master:
                ci_dsm_id = int(s["dsm_id"])
                sec_name = str(s.get("dsm_section_name") or f"Section {ci_dsm_id}").strip()
                sec_order = int(s.get("dsm_order") or 0)
                sec_del = int(s.get("delete_bit") or 0)

                key = sec_name.lower()
                if key in existing_sections:
                    ci_to_lara_sec[ci_dsm_id] = existing_sections[key]
                else:
                    cur.execute("""
                        INSERT INTO dept_sections (section_name, display_name, is_default, ordering, delete_bit, created_at, updated_at)
                        VALUES (%s, %s, 0, %s, %s, %s, %s)
                    """, (sec_name, sec_name, sec_order, sec_del, now_ts, now_ts))
                    new_id = cur.lastrowid
                    existing_sections[key] = new_id
                    ci_to_lara_sec[ci_dsm_id] = new_id

            conn.commit()
            print(f"Synchronized {len(ci_to_lara_sec)} section masters into dept_sections.")

            # ---------------------------------------------------------
            # 3. Migrate tbl_section_info -> department_section_mappings
            # ---------------------------------------------------------
            insert_mapping_query = """
                INSERT INTO department_section_mappings (
                    id, department_id, dept_sections_id, is_visible,
                    data, ordering, delete_bit, created_at, updated_at
                ) VALUES (
                    %(id)s, %(department_id)s, %(dept_sections_id)s, %(is_visible)s,
                    %(data)s, %(ordering)s, %(delete_bit)s, %(created_at)s, %(updated_at)s
                ) ON DUPLICATE KEY UPDATE
                    department_id = VALUES(department_id),
                    dept_sections_id = VALUES(dept_sections_id),
                    is_visible = VALUES(is_visible),
                    data = VALUES(data),
                    ordering = VALUES(ordering),
                    delete_bit = VALUES(delete_bit),
                    updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            skipped_fks = 0

            for info in raw_info:
                dsi_id = int(info["dsi_id"])
                ci_dsm_id = int(info["dsi_dsm_id"])
                ci_dsl_id = info.get("dsi_dsl_id")

                # Dept foreign key check
                if not ci_dsl_id or str(ci_dsl_id).strip() in ("0", "None", "NULL"):
                    skipped_fks += 1
                    continue
                dept_id = int(ci_dsl_id)
                if dept_id not in valid_dept_ids:
                    skipped_fks += 1
                    continue

                dept_sec_id = ci_to_lara_sec.get(ci_dsm_id)
                if not dept_sec_id:
                    skipped_fks += 1
                    continue

                raw_content = clean_html(info.get("dsi_new_content") or info.get("dsi_content") or "")
                data_json = json.dumps({"content": raw_content})

                is_vis = 1 if str(info.get("dsi_is_display_on_website", "1")).strip() in ("1", "True") else 0
                order = int(info.get("dsm_order") or 0)
                del_bit = int(info.get("delete_bit") or 0)

                cur.execute(insert_mapping_query, {
                    "id": dsi_id,
                    "department_id": dept_id,
                    "dept_sections_id": dept_sec_id,
                    "is_visible": is_vis,
                    "data": data_json,
                    "ordering": order,
                    "delete_bit": del_bit,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()

            cur.execute("SELECT COUNT(*) as cnt FROM department_section_mappings WHERE delete_bit = 0")
            active_mappings = cur.fetchone()["cnt"]

            print(f"Successfully migrated {migrated_count} department section mappings.")
            if skipped_fks:
                print(f"Skipped {skipped_fks} rows with non-department or invalid FKs.")
            print(f"Total active department_section_mappings count: {active_mappings}")
            print("\n=== DEPARTMENT SECTIONS MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_sections()

