#!/usr/bin/env python3
"""
Migration Script: Legal, Forms, Programs & Lookups Module
Source: u486681144_st_miraclg_liv.sql
  - tbl_tender (4 rows)
  - tbl_hostel_registration (3 rows)
  - tbl_news_paper (2 rows)
  - tbl_rti (1 row)
  - tbl_nss_enrollment (1 row)
  - tbl_program_master (2 rows)
  - tbl_program_year_semester (2 rows)
  - tbl_category_master (10 rows)
  - tbl_religion_master (7 rows)
Target: u207346834_stmiracollege
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def clean_val(v):
    if v is None or str(v).strip() in ("None", "NULL", ""):
        return None
    return str(v).strip()


def migrate_legal_forms():
    print("=" * 60)
    print("MIGRATING LEGAL, FORMS, PROGRAMS & LOOKUPS: CI -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            # ---------------------------------------------------------
            # 1. Tenders (tbl_tender -> tenders)
            # ---------------------------------------------------------
            m_ten = re.findall(r"INSERT INTO [`\x27]?tbl_tender[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            ten_count = 0
            if m_ten:
                cols = [c.strip(" `\r\n") for c in m_ten[0][0].split(",")]
                for _, vals in m_ten:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        tid = int(d["tender_id"])
                        cur.execute("""
                            INSERT INTO tenders (id, quotation, enquiry_no, enquiry_date, last_date, link, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE quotation = VALUES(quotation), link = VALUES(link), last_date = VALUES(last_date)
                        """, (
                            tid,
                            clean_val(d.get("tender_title")),
                            clean_val(d.get("tender_enquiry")),
                            clean_date(d.get("tender_date")) or now_ts,
                            clean_date(d.get("tender_lastdate")) or now_ts,
                            clean_path(d.get("tender_link")),
                            int(d.get("delete_bit") or 0),
                            now_ts, now_ts
                        ))
                        ten_count += 1
                conn.commit()
            print(f"Migrated {ten_count} tender record(s).")

            # ---------------------------------------------------------
            # 2. Hostel Registrations (tbl_hostel_registration -> hostel_registrations)
            # ---------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS hostel_registrations (
                    id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                    status varchar(255) DEFAULT 'Approved',
                    name_of_student varchar(255) DEFAULT NULL,
                    class_name varchar(255) DEFAULT NULL,
                    dob date DEFAULT NULL,
                    date_of_admission date DEFAULT NULL,
                    parent_address text DEFAULT NULL,
                    current_address text DEFAULT NULL,
                    mobile_no varchar(50) DEFAULT NULL,
                    email_id varchar(100) DEFAULT NULL,
                    father_name varchar(255) DEFAULT NULL,
                    father_occupation varchar(255) DEFAULT NULL,
                    father_contact varchar(50) DEFAULT NULL,
                    mother_name varchar(255) DEFAULT NULL,
                    mother_occupation varchar(255) DEFAULT NULL,
                    mother_contact varchar(50) DEFAULT NULL,
                    lg1_name varchar(255) DEFAULT NULL,
                    lg1_mobile varchar(50) DEFAULT NULL,
                    lg1_address text DEFAULT NULL,
                    lg2_name varchar(255) DEFAULT NULL,
                    lg2_mobile varchar(50) DEFAULT NULL,
                    lg2_address text DEFAULT NULL,
                    delete_bit tinyint(4) DEFAULT 0,
                    created_at timestamp NULL DEFAULT NULL,
                    updated_at timestamp NULL DEFAULT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            m_hos = re.findall(r"INSERT INTO [`\x27]?tbl_hostel_registration[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            hos_count = 0
            if m_hos:
                cols = [c.strip(" `\r\n") for c in m_hos[0][0].split(",")]
                for _, vals in m_hos:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        hid = int(d["id"])
                        cur.execute("""
                            INSERT INTO hostel_registrations (
                                id, status, name_of_student, class_name, dob, date_of_admission,
                                parent_address, current_address, mobile_no, email_id,
                                father_name, father_occupation, father_contact,
                                mother_name, mother_occupation, mother_contact,
                                lg1_name, lg1_mobile, lg1_address,
                                lg2_name, lg2_mobile, lg2_address,
                                created_at, updated_at
                            ) VALUES (%s, 'Approved', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name_of_student = VALUES(name_of_student), mobile_no = VALUES(mobile_no)
                        """, (
                            hid,
                            clean_val(d.get("student_name")),
                            clean_val(d.get("class")),
                            clean_date(d.get("dob")),
                            clean_date(d.get("doa")),
                            clean_val(d.get("parent_address")),
                            clean_val(d.get("current_address")),
                            clean_val(d.get("mobile")),
                            clean_val(d.get("email")),
                            clean_val(d.get("father_name")),
                            clean_val(d.get("father_occupation")),
                            clean_val(d.get("father_contact")),
                            clean_val(d.get("mother_name")),
                            clean_val(d.get("mother_occupation")),
                            clean_val(d.get("mother_contact")),
                            clean_val(d.get("guardian1_name")),
                            clean_val(d.get("guardian1_mobile")),
                            clean_val(d.get("guardian1_address")),
                            clean_val(d.get("guardian2_name")),
                            clean_val(d.get("guardian2_mobile")),
                            clean_val(d.get("guardian2_address")),
                            now_ts, now_ts
                        ))
                        hos_count += 1
                conn.commit()
            print(f"Migrated {hos_count} hostel registration(s).")

            # ---------------------------------------------------------
            # 3. College News Paper (tbl_news_paper -> college_news_papers)
            # ---------------------------------------------------------
            m_np = re.findall(r"INSERT INTO [`\x27]?tbl_news_paper[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            np_count = 0
            if m_np:
                cols = [c.strip(" `\r\n") for c in m_np[0][0].split(",")]
                for _, vals in m_np:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        npid = int(d["tnp_id"])
                        cur.execute("""
                            INSERT INTO college_news_papers (id, title, year, image, show_on_website, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE title = VALUES(title), image = VALUES(image)
                        """, (
                            npid,
                            clean_val(d.get("tnp_name")),
                            clean_val(d.get("tnp_year")),
                            clean_path(d.get("tnp_images_path")),
                            int(d.get("tnp_display_on_news_paper_page") or 1),
                            int(d.get("delete_bit") or 0),
                            clean_date(d.get("tnp_created_date")) or now_ts,
                            now_ts
                        ))
                        np_count += 1
                conn.commit()
            print(f"Migrated {np_count} college news paper clipping(s).")

            # ---------------------------------------------------------
            # 4. RTI (tbl_rti -> rti)
            # ---------------------------------------------------------
            m_rti = re.findall(r"INSERT INTO [`\x27]?tbl_rti[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            rti_count = 0
            if m_rti:
                cols = [c.strip(" `\r\n") for c in m_rti[0][0].split(",")]
                for _, vals in m_rti:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        rid = int(d["rti_id"])
                        cur.execute("""
                            INSERT INTO rti (id, title, source, show_on_website, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, 1, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE title = VALUES(title), source = VALUES(source)
                        """, (
                            rid,
                            clean_val(d.get("rti_title") or "RTI Document"),
                            clean_path(d.get("rti_file")),
                            int(d.get("delete_bit") or 0),
                            clean_date(d.get("rti_date")) or now_ts,
                            now_ts
                        ))
                        rti_count += 1
                conn.commit()
            print(f"Migrated {rti_count} RTI record(s).")

            # ---------------------------------------------------------
            # 5. NSS Enrollment (tbl_nss_enrollment -> nss_enrollments)
            # ---------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nss_enrollments (
                    id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                    status varchar(255) DEFAULT 'Approved',
                    full_name varchar(255) DEFAULT NULL,
                    branch varchar(255) DEFAULT NULL,
                    roll_no varchar(255) DEFAULT NULL,
                    batch varchar(255) DEFAULT NULL,
                    dob date DEFAULT NULL,
                    category varchar(255) DEFAULT NULL,
                    blood_group varchar(50) DEFAULT NULL,
                    height_weight varchar(255) DEFAULT NULL,
                    residential_address text DEFAULT NULL,
                    father_guardian_name varchar(255) DEFAULT NULL,
                    occupation varchar(255) DEFAULT NULL,
                    nss_group_no varchar(255) DEFAULT NULL,
                    student_mobile varchar(50) DEFAULT NULL,
                    student_email varchar(100) DEFAULT NULL,
                    created_at timestamp NULL DEFAULT NULL,
                    updated_at timestamp NULL DEFAULT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            m_nss = re.findall(r"INSERT INTO [`\x27]?tbl_nss_enrollment[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            nss_count = 0
            if m_nss:
                cols = [c.strip(" `\r\n") for c in m_nss[0][0].split(",")]
                for _, vals in m_nss:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        nid = int(d["id"])
                        cur.execute("""
                            INSERT INTO nss_enrollments (
                                id, status, full_name, branch, roll_no, batch, dob, category,
                                blood_group, height_weight, residential_address, father_guardian_name,
                                occupation, nss_group_no, student_mobile, student_email, created_at, updated_at
                            ) VALUES (%s, 'Approved', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), student_mobile = VALUES(student_mobile)
                        """, (
                            nid,
                            clean_val(d.get("full_name")),
                            clean_val(d.get("branch")),
                            clean_val(d.get("college_roll_no")),
                            clean_val(d.get("batch")),
                            clean_date(d.get("dob")),
                            clean_val(d.get("category")),
                            clean_val(d.get("blood_group")),
                            clean_val(d.get("height_weight")),
                            clean_val(d.get("residential_address")),
                            clean_val(d.get("father_guardian_name")),
                            clean_val(d.get("occupation")),
                            clean_val(d.get("nss_group_no")),
                            clean_val(d.get("student_mobile")),
                            clean_val(d.get("student_email")),
                            clean_date(d.get("created_at")) or now_ts,
                            clean_date(d.get("updated_at")) or now_ts
                        ))
                        nss_count += 1
                conn.commit()
            print(f"Migrated {nss_count} NSS enrollment record(s).")

            # ---------------------------------------------------------
            # 6. Programs & Semesters (tbl_program_master -> programs, program_years)
            # ---------------------------------------------------------
            m_pm = re.findall(r"INSERT INTO [`\x27]?tbl_program_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            pm_count = 0
            if m_pm:
                cols = [c.strip(" `\r\n") for c in m_pm[0][0].split(",")]
                for _, vals in m_pm:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        pid = int(d["pm_id"])
                        pname = clean_val(d.get("pm_name") or f"Program {pid}")
                        cur.execute("""
                            INSERT INTO programs (id, programme_code, name, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name = VALUES(name)
                        """, (pid, pname, pname, int(d.get("delete_bit") or 0), now_ts, now_ts))
                        pm_count += 1
                conn.commit()
            print(f"Migrated {pm_count} academic programs.")

            # Program Years
            m_pys = re.findall(r"INSERT INTO [`\x27]?tbl_program_year_semester[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            pys_count = 0
            if m_pys:
                cols = [c.strip(" `\r\n") for c in m_pys[0][0].split(",")]
                for _, vals in m_pys:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        pys_id = int(d["pys_id"])
                        pys_name = clean_val(d.get("pys_name") or f"Year {pys_id}")
                        cur.execute("""
                            INSERT INTO program_years (id, program_year, created_at, updated_at)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE program_year = VALUES(program_year)
                        """, (pys_id, pys_name, now_ts, now_ts))
                        pys_count += 1
                conn.commit()
            print(f"Migrated {pys_count} program years/semesters.")

            # ---------------------------------------------------------
            # 7. Category & Religion Masters (categorys, religions)
            # ---------------------------------------------------------
            m_cat = re.findall(r"INSERT INTO [`\x27]?tbl_category_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            cat_count = 0
            if m_cat:
                cols = [c.strip(" `\r\n") for c in m_cat[0][0].split(",")]
                for _, vals in m_cat:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        cid = int(d["tcm_id"])
                        cname = clean_val(d.get("tcm_name") or f"Category {cid}")
                        cur.execute("""
                            INSERT INTO categorys (id, name, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name = VALUES(name)
                        """, (cid, cname, int(d.get("tcm_delete_bit") or 0), now_ts, now_ts))
                        cat_count += 1
                conn.commit()
            print(f"Migrated {cat_count} categories.")

            m_rel = re.findall(r"INSERT INTO [`\x27]?tbl_religion_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            rel_count = 0
            if m_rel:
                cols = [c.strip(" `\r\n") for c in m_rel[0][0].split(",")]
                for _, vals in m_rel:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols, r))
                        rid = int(d["trm_id"])
                        rname = clean_val(d.get("trm_name") or f"Religion {rid}")
                        cur.execute("""
                            INSERT INTO religions (id, name, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name = VALUES(name)
                        """, (rid, rname, int(d.get("trm_delete_bit") or 0), now_ts, now_ts))
                        rel_count += 1
                conn.commit()
            print(f"Migrated {rel_count} religions.")

            print("\n=== LEGAL, FORMS & LOOKUPS MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_legal_forms()

