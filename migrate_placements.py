#!/usr/bin/env python3
"""
Migration Script: Student Placement Registrations (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_student_placement_form)
Target: u207346834_mnwc (placement_registrations)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def migrate_placements():
    print("=" * 60)
    print("MIGRATING STUDENT PLACEMENTS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_student_placement_form[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
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

    print(f"Found {len(raw_rows)} placement records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS placement_registrations (
                    id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                    full_name varchar(255) DEFAULT NULL,
                    gender varchar(50) DEFAULT NULL,
                    dob date DEFAULT NULL,
                    mobile_no varchar(50) DEFAULT NULL,
                    email_id varchar(100) DEFAULT NULL,
                    roll_no varchar(255) DEFAULT NULL,
                    department varchar(255) DEFAULT NULL,
                    course varchar(255) DEFAULT NULL,
                    year_of_passing varchar(50) DEFAULT NULL,
                    current_semester varchar(50) DEFAULT NULL,
                    cgpa varchar(50) DEFAULT NULL,
                    interested_job_role varchar(255) DEFAULT NULL,
                    preferred_location varchar(255) DEFAULT NULL,
                    skills text DEFAULT NULL,
                    internships text DEFAULT NULL,
                    resume_path varchar(255) DEFAULT NULL,
                    photo_path varchar(255) DEFAULT NULL,
                    created_at timestamp NULL DEFAULT NULL,
                    updated_at timestamp NULL DEFAULT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            insert_query = """
            INSERT INTO placement_registrations (
                id, full_name, gender, dob, mobile_no, email_id, roll_no,
                department, course, year_of_passing, current_semester, cgpa,
                interested_job_role, preferred_location, skills, internships,
                resume_path, photo_path, created_at, updated_at
            ) VALUES (
                %(id)s, %(full_name)s, %(gender)s, %(dob)s, %(mobile_no)s, %(email_id)s, %(roll_no)s,
                %(department)s, %(course)s, %(year_of_passing)s, %(current_semester)s, %(cgpa)s,
                %(interested_job_role)s, %(preferred_location)s, %(skills)s, %(internships)s,
                %(resume_path)s, %(photo_path)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                gender = VALUES(gender),
                dob = VALUES(dob),
                mobile_no = VALUES(mobile_no),
                email_id = VALUES(email_id),
                roll_no = VALUES(roll_no),
                department = VALUES(department),
                course = VALUES(course),
                year_of_passing = VALUES(year_of_passing),
                current_semester = VALUES(current_semester),
                cgpa = VALUES(cgpa),
                interested_job_role = VALUES(interested_job_role),
                preferred_location = VALUES(preferred_location),
                skills = VALUES(skills),
                internships = VALUES(internships),
                resume_path = VALUES(resume_path),
                photo_path = VALUES(photo_path),
                updated_at = VALUES(updated_at)
            """

            for r in raw_rows:
                dob = clean_date(r.get("tspf_dob"))
                if dob:
                    dob = dob[:10]
                c_date = clean_date(r.get("tspf_created_at")) or now_ts
                resume = clean_path(r.get("tspf_resume_file"))
                photo = clean_path(r.get("tspf_photo_file"))

                cur.execute(insert_query, {
                    "id": int(r["tspf_id"]),
                    "full_name": str(r.get("tspf_full_name") or "").strip(),
                    "gender": str(r.get("tspf_gender") or "").strip(),
                    "dob": dob,
                    "mobile_no": str(r.get("tspf_mobile") or "").strip(),
                    "email_id": str(r.get("tspf_email") or "").strip(),
                    "roll_no": str(r.get("tspf_roll_no") or "").strip(),
                    "department": str(r.get("tspf_branch") or "").strip(),
                    "course": str(r.get("tspf_course") or "").strip(),
                    "year_of_passing": str(r.get("tspf_passing_year") or "").strip(),
                    "current_semester": str(r.get("tspf_semester") or "").strip(),
                    "cgpa": str(r.get("tspf_cgpa") or "").strip(),
                    "interested_job_role": str(r.get("tspf_job_role") or "").strip(),
                    "preferred_location": str(r.get("tspf_location") or "").strip(),
                    "skills": str(r.get("tspf_skills") or "").strip(),
                    "internships": str(r.get("tspf_experience") or "").strip(),
                    "resume_path": resume,
                    "photo_path": photo,
                    "created_at": c_date,
                    "updated_at": now_ts
                })

            conn.commit()
            print(f"Successfully migrated {len(raw_rows)} placement registration(s).")

            cur.execute("SELECT COUNT(*) AS c FROM placement_registrations")
            print(f"Total active placement_registrations count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== STUDENT PLACEMENTS MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_placements()

