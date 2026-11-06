#!/usr/bin/env python3
"""
Migration Script: Recruitment / Careers Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_recruitment_form)
Target: u207346834_mnwc (careers, job_applications)
"""

import os
import sys
import re
import json
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def migrate_recruitment():
    print("=" * 60)
    print("MIGRATING RECRUITMENT & CAREERS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_recruitment_form[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} recruitment application(s) in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 1. Ensure career positions exist
            # Check available columns in careers and job_applications
            cur.execute("SHOW COLUMNS FROM careers")
            career_cols = {row["Field"] for row in cur.fetchall()}

            cur.execute("SHOW COLUMNS FROM job_applications")
            app_cols = {row["Field"] for row in cur.fetchall()}

            career_map = {}
            cur.execute("SELECT id, title FROM careers")
            for row in cur.fetchall():
                career_map[row["title"].strip().lower()] = row["id"]

            for r in raw_rows:
                post = str(r.get("trf_post_for") or "General Faculty Opening").strip()
                post_key = post.lower()
                if post_key not in career_map:
                    career_data = {
                        "title": post,
                        "experience": str(r.get("trf_teachingExperience") or "Not Specified"),
                        "description": f"Opening for {post}",
                        "show_on_website": 1,
                        "job_type": "Full Time",
                        "created_at": now_ts,
                        "updated_at": now_ts
                    }
                    if "department" in career_cols:
                        career_data["department"] = str(r.get("trf_department") or "Academics")
                    if "skills" in career_cols:
                        s_val = str(r.get("trf_specialization") or "").strip()
                        career_data["skills"] = json.dumps([s_val] if s_val else [])
                    if "qualifications" in career_cols:
                        q_val = str(r.get("trf_qualification") or "").strip()
                        career_data["qualifications"] = json.dumps([q_val] if q_val else [])

                    fields = list(career_data.keys())
                    placeholders = ", ".join(["%s"] * len(fields))
                    cols_str = ", ".join(fields)
                    cur.execute(f"INSERT INTO careers ({cols_str}) VALUES ({placeholders})", [career_data[f] for f in fields])
                    career_id = cur.lastrowid
                    career_map[post_key] = career_id
                else:
                    career_id = career_map[post_key]

                # 2. Insert into job_applications
                fn = str(r.get("trf_first_name") or "").strip()
                mn = str(r.get("trf_middle_name") or "").strip()
                ln = str(r.get("trf_last_name") or "").strip()
                full_name = " ".join(part for part in [fn, mn, ln] if part)

                phone = str(r.get("trf_phone_number") or "").strip()
                email = str(r.get("trf_email_id") or "").strip()
                curr_addr = str(r.get("trf_current_address") or "").strip()
                perm_addr = str(r.get("trf_permenant_address") or "").strip()
                exp = str(r.get("trf_teachingExperience") or "").strip()
                spec = str(r.get("trf_specialization") or "").strip()
                resume = clean_path(r.get("trf_resume"))

                notes = []
                if r.get("trf_researchExperience"):
                    notes.append(f"Research Exp: {r['trf_researchExperience']}")
                if r.get("trf_publications"):
                    notes.append(f"Publications: {r['trf_publications']}")
                if r.get("trf_expectedSalary"):
                    notes.append(f"Expected Salary: {r['trf_expectedSalary']}")
                cover_note = "; ".join(notes) if notes else None

                job_app_data = {
                    "id": int(r["trf_id"]),
                    "career_id": career_id,
                    "full_name": full_name,
                    "phone_number": phone,
                    "email_id": email,
                    "current_address": curr_addr,
                    "permanent_address": perm_addr,
                    "experience_years": exp,
                    "skills": spec,
                    "resume_path": resume,
                    "created_at": now_ts,
                    "updated_at": now_ts
                }
                if "status" in app_cols:
                    job_app_data["status"] = "New"
                if "cover_note" in app_cols:
                    job_app_data["cover_note"] = cover_note
                if "qualification" in app_cols:
                    job_app_data["qualification"] = str(r.get("trf_qualification") or spec or "")

                app_fields = [f for f in job_app_data.keys() if f in app_cols]
                app_cols_str = ", ".join(app_fields)
                app_placeholders = ", ".join(["%s"] * len(app_fields))
                update_assignments = ", ".join([f"{f} = VALUES({f})" for f in app_fields if f != "id"])

                insert_sql = f"""
                    INSERT INTO job_applications ({app_cols_str})
                    VALUES ({app_placeholders})
                    ON DUPLICATE KEY UPDATE {update_assignments}
                """
                cur.execute(insert_sql, [job_app_data[f] for f in app_fields])

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} job application(s).")

            cur.execute("SELECT COUNT(*) AS c FROM job_applications")
            print(f"Total active job_applications count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== RECRUITMENT & CAREERS MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_recruitment()

