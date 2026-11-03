#!/usr/bin/env python3
"""
Migration Script: Academics, Enquiries, NIRF & Lookups (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_program_college_list, tbl_manage_courses,
                                  tbl_student_admission_enquiry, tbl_nirfs,
                                  visitors, tbl_category_master)
Target: u207346834_sathayelara (programs, courses, student_admission_enquiry,
                               nirf, lookups, categorys)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values, clean_date, clean_path

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


def clean_program_name(name):
    if not name:
        return ""
    name = str(name).strip()
    name = re.sub(r"^[rRnN\s]+B\.Sc", "B.Sc", name)
    name = re.sub(r"^[rRnN\s]+", "", name)
    name = re.sub(r"-\s*$", "", name).strip()
    return name


def migrate_academics():
    print("=" * 60)
    print("MIGRATING ACADEMICS, ENQUIRIES, NIRF & LOOKUPS")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # ---------------------------------------------------------
            # 1. Programs (tbl_program_college_list -> programs)
            # ---------------------------------------------------------
            print("\n[Step 1] Migrating tbl_program_college_list -> programs...")
            m_prog = re.findall(
                r"INSERT INTO [`\x27]?tbl_program_college_list[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_programs = []
            if m_prog:
                cols = [c.strip(" `\r\n") for c in m_prog[0][0].split(",")]
                for _, vals in m_prog:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_programs.append(dict(zip(cols, r)))

            print(f"Found {len(raw_programs)} programs in source dump.")

            prog_sql = """
            INSERT INTO programs (
                id, name, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(name)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_progs = 0
            for p in raw_programs:
                p_id = int(p["tpcl_id"])
                p_name = clean_program_name(p.get("tpcl_name"))
                if not p_name:
                    continue

                cur.execute(prog_sql, {
                    "id": p_id,
                    "name": p_name,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_progs += 1

            conn.commit()
            print(f"Successfully migrated {migrated_progs} programs into programs.")

            # ---------------------------------------------------------
            # 2. Courses (tbl_manage_courses -> courses)
            # ---------------------------------------------------------
            print("\n[Step 2] Migrating tbl_manage_courses -> courses...")
            m_crs = re.findall(
                r"INSERT INTO [`\x27]?tbl_manage_courses[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_courses = []
            if m_crs:
                cols = [c.strip(" `\r\n") for c in m_crs[0][0].split(",")]
                for _, vals in m_crs:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_courses.append(dict(zip(cols, r)))

            print(f"Found {len(raw_courses)} courses in source dump.")

            course_sql = """
            INSERT INTO courses (
                id, name, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(name)s, %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            migrated_crs = 0
            for c in raw_courses:
                c_id = int(c["courseId"])
                c_name = str(c.get("courseName") or "").strip()
                del_bit = 1 if str(c.get("delete_bit")) == "1" else 0
                created_at = clean_date(c.get("submitedDate")) or now_ts

                cur.execute(course_sql, {
                    "id": c_id,
                    "name": c_name,
                    "delete_bit": del_bit,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_crs += 1

            conn.commit()
            print(f"Successfully migrated {migrated_crs} courses into courses.")

            # ---------------------------------------------------------
            # 3. Admission Enquiries (tbl_student_admission_enquiry -> student_admission_enquiry)
            # ---------------------------------------------------------
            print("\n[Step 3] Migrating tbl_student_admission_enquiry -> student_admission_enquiry...")
            m_enq = re.findall(
                r"INSERT INTO [`\x27]?tbl_student_admission_enquiry[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_enqs = []
            if m_enq:
                cols = [c.strip(" `\r\n") for c in m_enq[0][0].split(",")]
                for _, vals in m_enq:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_enqs.append(dict(zip(cols, r)))

            print(f"Found {len(raw_enqs)} admission enquiries in source dump.")

            enq_sql = """
            INSERT INTO student_admission_enquiry (
                id, name, contact, email, course, comment, year,
                is_replied, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(name)s, %(contact)s, %(email)s, %(course)s, %(comment)s, %(year)s,
                0, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                contact = VALUES(contact),
                email = VALUES(email),
                course = VALUES(course),
                comment = VALUES(comment),
                year = VALUES(year),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_enqs = 0
            for e in raw_enqs:
                e_id = int(e["tbl_sae_id"])
                e_name = str(e.get("tbl_sae_name") or "").strip()
                e_contact = str(e.get("tbl_sae_contact") or "").strip()
                e_email = str(e.get("tbl_sae_email") or "").strip()
                e_course = str(e.get("tbl_sae_course") or "").strip() or None
                e_comment = str(e.get("tbl_sae_comment") or "").strip()
                e_year = str(e.get("tbl_sae_year") or "").strip()
                created_at = clean_date(e.get("tbl_sae_current_time")) or now_ts

                cur.execute(enq_sql, {
                    "id": e_id,
                    "name": e_name,
                    "contact": e_contact,
                    "email": e_email,
                    "course": e_course,
                    "comment": e_comment,
                    "year": e_year,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_enqs += 1

            conn.commit()
            print(f"Successfully migrated {migrated_enqs} enquiries into student_admission_enquiry.")

            # ---------------------------------------------------------
            # 4. NIRF (tbl_nirfs -> nirf)
            # ---------------------------------------------------------
            print("\n[Step 4] Migrating tbl_nirfs -> nirf...")
            m_nirf = re.findall(
                r"INSERT INTO [`\x27]?tbl_nirfs[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_nirfs = []
            if m_nirf:
                cols = [c.strip(" `\r\n") for c in m_nirf[0][0].split(",")]
                for _, vals in m_nirf:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_nirfs.append(dict(zip(cols, r)))

            print(f"Found {len(raw_nirfs)} NIRF records in source dump.")

            nirf_sql = """
            INSERT INTO nirf (
                id, title, source, show_on_website, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(source)s, %(show_on_website)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                source = VALUES(source),
                show_on_website = VALUES(show_on_website),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_nirfs = 0
            for n in raw_nirfs:
                n_id = int(n["nirf_id"])
                title = str(n.get("nirf_title") or "").strip()
                file_path = clean_path(n.get("nirf_link"))
                created_at = clean_date(n.get("nirf_created_date")) or now_ts
                show_site = 1 if str(n.get("approve_bit")) == "1" else 0

                cur.execute(nirf_sql, {
                    "id": n_id,
                    "title": title,
                    "source": file_path,
                    "show_on_website": show_site,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_nirfs += 1

            conn.commit()
            print(f"Successfully migrated {migrated_nirfs} records into nirf.")

            # ---------------------------------------------------------
            # 5. Visitors count -> lookups
            # ---------------------------------------------------------
            print("\n[Step 5] Migrating visitors -> lookups...")
            m_vis = re.findall(
                r"INSERT INTO [`\x27]?visitors[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            if m_vis:
                cols = [c.strip(" `\r\n") for c in m_vis[0][0].split(",")]
                for _, vals in m_vis:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        count_val = str(d.get("total_count") or "0")
                        cur.execute("""
                        INSERT INTO lookups (`key`, `value`, delete_bit, created_at, updated_at)
                        VALUES ('visitor_count', %s, 0, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            `value` = VALUES(`value`),
                            updated_at = VALUES(updated_at)
                        """, (count_val, now_ts, now_ts))
                        print(f"Updated lookup 'visitor_count' = {count_val}")
                conn.commit()

            # ---------------------------------------------------------
            # 6. Additional Categories -> categorys
            # ---------------------------------------------------------
            print("\n[Step 6] Synchronizing categories in categorys...")
            m_cat = re.findall(
                r"INSERT INTO [`\x27]?tbl_category_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            if m_cat:
                cols = [c.strip(" `\r\n") for c in m_cat[0][0].split(",")]
                cur.execute("SELECT LOWER(name) as k FROM categorys WHERE delete_bit = 0")
                existing_cats = {r["k"] for r in cur.fetchall()}

                for _, vals in m_cat:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        cat_name = str(d.get("tcm_name") or "").strip()
                        if cat_name and cat_name.lower() not in existing_cats:
                            cur.execute("""
                            INSERT INTO categorys (name, delete_bit, created_at, updated_at)
                            VALUES (%s, 0, %s, %s)
                            """, (cat_name, now_ts, now_ts))
                            existing_cats.add(cat_name.lower())
                            print(f"Added category: {cat_name}")
                conn.commit()

            # Verification
            print("\nVerification:")
            cur.execute("SELECT COUNT(*) as c FROM programs WHERE delete_bit = 0")
            print(f"  Active Programs: {cur.fetchone()['c']}")
            cur.execute("SELECT COUNT(*) as c FROM courses WHERE delete_bit = 0")
            print(f"  Active Courses: {cur.fetchone()['c']}")
            cur.execute("SELECT COUNT(*) as c FROM student_admission_enquiry WHERE delete_bit = 0")
            print(f"  Active Enquiries: {cur.fetchone()['c']}")
            cur.execute("SELECT COUNT(*) as c FROM nirf WHERE delete_bit = 0")
            print(f"  Active NIRF: {cur.fetchone()['c']}")

    finally:
        conn.close()

    print("\nAcademics, Enquiries, NIRF & Lookups Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_academics()

