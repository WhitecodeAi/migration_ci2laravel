#!/usr/bin/env python3
"""
Migration Script: Grievances & Discrimination Complaints Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (student_grievance, student_anti_ragging, tbl_discrimination_complaint)
Target: u207346834_sathayelara (student_grievances, caste_based_discrimination_complaints_registrations)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values, clean_date

from db_config import DB_CONFIG, SQL_FILE


def format_dob(dob_str):
    if not dob_str:
        return ""
    dob_str = str(dob_str).strip()
    # If format is M/D/YYYY or MM/DD/YYYY
    parts = dob_str.split("/")
    if len(parts) == 3:
        try:
            m, d, y = parts
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            pass
    return dob_str


def migrate_grievances():
    print("=" * 60)
    print("MIGRATING GRIEVANCES & COMPLAINTS: CodeIgniter -> Laravel")
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
            # Step 1: Migrate student_grievance -> student_grievances
            # ---------------------------------------------------------
            print("\n[Step 1] Migrating student_grievance -> student_grievances...")
            m_grievance = re.findall(
                r"INSERT INTO [`\x27]?student_grievance[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_grievances = []
            if m_grievance:
                cols = [c.strip(" `\r\n") for c in m_grievance[0][0].split(",")]
                for _, vals in m_grievance:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_grievances.append(dict(zip(cols, r)))

            print(f"Found {len(raw_grievances)} student grievances in source dump.")

            grievance_sql = """
            INSERT INTO student_grievances (
                id, first_name, middle_name, last_name, class_name, gender,
                Address, date_of_birth, marital_status, mobile_number, email,
                Grievance_Category, complaint, Grievance, SupportingDocuments,
                EmailVarificationCode, verified, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(first_name)s, %(middle_name)s, %(last_name)s, %(class_name)s, %(gender)s,
                %(Address)s, %(date_of_birth)s, %(marital_status)s, %(mobile_number)s, %(email)s,
                %(Grievance_Category)s, %(complaint)s, %(Grievance)s, NULL,
                NULL, 1, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                first_name = VALUES(first_name),
                middle_name = VALUES(middle_name),
                last_name = VALUES(last_name),
                class_name = VALUES(class_name),
                gender = VALUES(gender),
                Address = VALUES(Address),
                date_of_birth = VALUES(date_of_birth),
                marital_status = VALUES(marital_status),
                mobile_number = VALUES(mobile_number),
                email = VALUES(email),
                Grievance_Category = VALUES(Grievance_Category),
                complaint = VALUES(complaint),
                Grievance = VALUES(Grievance),
                verified = 1,
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_grievances = 0
            for g in raw_grievances:
                g_id = int(g["id"])
                first_name = str(g.get("name") or "").strip()
                middle_name = str(g.get("mname") or "").strip()
                last_name = str(g.get("lname") or "").strip()
                class_name = str(g.get("class_name") or "").strip()
                gender = str(g.get("gender") or "").strip()
                address = str(g.get("address") or "").strip()
                dob = format_dob(g.get("dob"))
                marital = str(g.get("status") or "").strip()
                mobile = str(g.get("phno") or "").strip()
                email = str(g.get("email") or "").strip()
                complaint = str(g.get("complaint") or "").strip()
                grievance_text = str(g.get("grievance") or "").strip()
                created_at = clean_date(g.get("created_date")) or now_ts

                cur.execute(grievance_sql, {
                    "id": g_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "class_name": class_name,
                    "gender": gender,
                    "Address": address,
                    "date_of_birth": dob,
                    "marital_status": marital,
                    "mobile_number": mobile,
                    "email": email,
                    "Grievance_Category": "Student Grievance",
                    "complaint": complaint,
                    "Grievance": grievance_text,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_grievances += 1

            conn.commit()
            print(f"Successfully migrated {migrated_grievances} student grievance(s).")

            # ---------------------------------------------------------
            # Step 2: Migrate student_anti_ragging -> student_grievances
            # ---------------------------------------------------------
            print("\n[Step 2] Migrating student_anti_ragging -> student_grievances...")
            m_ragging = re.findall(
                r"INSERT INTO [`\x27]?student_anti_ragging[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_ragging = []
            if m_ragging:
                cols = [c.strip(" `\r\n") for c in m_ragging[0][0].split(",")]
                for _, vals in m_ragging:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_ragging.append(dict(zip(cols, r)))

            print(f"Found {len(raw_ragging)} anti-ragging grievances in source dump.")

            migrated_ragging = 0
            for r in raw_ragging:
                r_id = int(r["id"])
                first_name = str(r.get("name") or "").strip()
                middle_name = str(r.get("mname") or "").strip()
                last_name = str(r.get("lname") or "").strip()
                class_name = str(r.get("class_name") or "").strip()
                gender = str(r.get("gender") or "").strip()
                address = str(r.get("address") or "").strip()
                dob = format_dob(r.get("dob"))
                marital = str(r.get("status") or "").strip()
                mobile = str(r.get("phno") or "").strip()
                email = str(r.get("email") or "").strip()
                complaint = str(r.get("complaint") or "").strip()
                grievance_text = str(r.get("anti_rggaing_message") or "").strip()
                created_at = clean_date(r.get("created_date")) or now_ts

                cur.execute(grievance_sql, {
                    "id": r_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "class_name": class_name,
                    "gender": gender,
                    "Address": address,
                    "date_of_birth": dob,
                    "marital_status": marital,
                    "mobile_number": mobile,
                    "email": email,
                    "Grievance_Category": "Anti Ragging",
                    "complaint": complaint,
                    "Grievance": grievance_text,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_ragging += 1

            conn.commit()
            print(f"Successfully migrated {migrated_ragging} anti-ragging grievance(s).")

            # ---------------------------------------------------------
            # Step 3: Migrate tbl_discrimination_complaint -> caste_based_discrimination_complaints_registrations
            # ---------------------------------------------------------
            print("\n[Step 3] Migrating tbl_discrimination_complaint -> caste_based_discrimination_complaints_registrations...")
            m_disc = re.findall(
                r"INSERT INTO [`\x27]?tbl_discrimination_complaint[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_disc = []
            if m_disc:
                cols = [c.strip(" `\r\n") for c in m_disc[0][0].split(",")]
                for _, vals in m_disc:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_disc.append(dict(zip(cols, r)))

            print(f"Found {len(raw_disc)} discrimination complaints in source dump.")

            caste_sql = """
            INSERT INTO caste_based_discrimination_complaints_registrations (
                id, first_name, middle_name, last_name, email, mobile_number,
                designation, department_stream, class_for_students, roll_number_for_students,
                caste_category, address, complaint_details, created_at, updated_at
            ) VALUES (
                %(id)s, %(first_name)s, %(middle_name)s, %(last_name)s, %(email)s, %(mobile_number)s,
                %(designation)s, %(department_stream)s, %(class_for_students)s, %(roll_number_for_students)s,
                %(caste_category)s, %(address)s, %(complaint_details)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                first_name = VALUES(first_name),
                middle_name = VALUES(middle_name),
                last_name = VALUES(last_name),
                email = VALUES(email),
                mobile_number = VALUES(mobile_number),
                designation = VALUES(designation),
                department_stream = VALUES(department_stream),
                class_for_students = VALUES(class_for_students),
                roll_number_for_students = VALUES(roll_number_for_students),
                caste_category = VALUES(caste_category),
                address = VALUES(address),
                complaint_details = VALUES(complaint_details),
                updated_at = VALUES(updated_at)
            """

            migrated_caste = 0
            for d in raw_disc:
                d_id = int(d["tdc_id"])
                first_name = str(d.get("tdc_name") or "").strip()
                middle_name = str(d.get("tdc_mname") or "").strip()
                last_name = str(d.get("tdc_lname") or "").strip()
                email = str(d.get("tdc_email") or "").strip()
                mobile = str(d.get("tdc_phoneno") or "").strip()
                designation = str(d.get("tdc_designation") or d.get("tdc_designation_other") or "").strip()
                dept = str(d.get("tdc_department") or "").strip()
                s_class = str(d.get("tdc_class") or "").strip()
                roll_no = str(d.get("tdc_roll_no") or "").strip()
                caste = str(d.get("tdc_caste") or d.get("tdc_caste_other") or "").strip()
                address = str(d.get("tdc_address") or "").strip()
                complaint = str(d.get("tdc_complaint") or "").strip()
                created_at = clean_date(d.get("tdc_inserted_at")) or now_ts

                cur.execute(caste_sql, {
                    "id": d_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "mobile_number": mobile,
                    "designation": designation,
                    "department_stream": dept,
                    "class_for_students": s_class,
                    "roll_number_for_students": roll_no,
                    "caste_category": caste,
                    "address": address,
                    "complaint_details": complaint,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_caste += 1

            conn.commit()
            print(f"Successfully migrated {migrated_caste} caste discrimination complaint(s).")

            # Verification
            cur.execute("SELECT Grievance_Category, COUNT(*) as c FROM student_grievances GROUP BY Grievance_Category")
            print("\nVerification - Student Grievances breakdown:")
            for r in cur.fetchall():
                print(f"  Category: {r['Grievance_Category']} => {r['c']} rows")

            cur.execute("SELECT id, first_name, last_name, Grievance_Category, email, created_at FROM student_grievances ORDER BY id ASC")
            for r in cur.fetchall():
                print(" ", r)

            cur.execute("SELECT COUNT(*) as c FROM caste_based_discrimination_complaints_registrations")
            print(f"\nVerification - Caste Complaints count: {cur.fetchone()['c']}")
            cur.execute("SELECT id, first_name, last_name, email, caste_category, created_at FROM caste_based_discrimination_complaints_registrations ORDER BY id ASC")
            for r in cur.fetchall():
                print(" ", r)

    finally:
        conn.close()

    print("\nGrievances & Discrimination Complaints Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_grievances()
