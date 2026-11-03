#!/usr/bin/env python3
"""
Migration Script: Recruitment / Careers Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_recruitment_form)
Target: u207346834_mnwc (careers, job_applications)
"""

import os
import sys
import re
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
            career_map = {}
            cur.execute("SELECT id, title FROM careers")
            for row in cur.fetchall():
                career_map[row["title"].strip().lower()] = row["id"]

            for r in raw_rows:
                post = str(r.get("trf_post_for") or "General Faculty Opening").strip()
                post_key = post.lower()
                if post_key not in career_map:
                    cur.execute("""
                    INSERT INTO careers (
                        title, experience, description, show_on_website, job_type,
                        department, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """, (
                        post,
                        str(r.get("trf_teachingExperience") or "Not Specified"),
                        f"Opening for {post}",
                        1,
                        "Full Time",
                        str(r.get("trf_department") or "Academics"),
                        now_ts,
                        now_ts
                    ))
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

                cur.execute("""
                INSERT INTO job_applications (
                    id, career_id, full_name, phone_number, email_id,
                    current_address, permanent_address, experience_years,
                    skills, resume_path, created_at, updated_at, status, cover_note
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    career_id = VALUES(career_id),
                    full_name = VALUES(full_name),
                    phone_number = VALUES(phone_number),
                    email_id = VALUES(email_id),
                    current_address = VALUES(current_address),
                    permanent_address = VALUES(permanent_address),
                    experience_years = VALUES(experience_years),
                    skills = VALUES(skills),
                    resume_path = VALUES(resume_path),
                    updated_at = VALUES(updated_at),
                    cover_note = VALUES(cover_note)
                """, (
                    int(r["trf_id"]),
                    career_id,
                    full_name,
                    phone,
                    email,
                    curr_addr,
                    perm_addr,
                    exp,
                    spec,
                    resume,
                    now_ts,
                    now_ts,
                    "New",
                    cover_note
                ))

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} job application(s).")

            cur.execute("SELECT COUNT(*) AS c FROM job_applications")
            print(f"Total active job_applications count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== RECRUITMENT & CAREERS MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_recruitment()

