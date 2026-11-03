#!/usr/bin/env python3
"""
Migration Script: Alumni Registrations Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_alumni_registration)
Target: u207346834_sathayelara (alumni_forms)
"""

import sys
import os
import re
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


def format_dob_date(dob_str):
    if not dob_str:
        return None
    dob_str = str(dob_str).strip()
    parts = dob_str.split("/")
    if len(parts) == 3:
        try:
            m, d, y = parts
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            pass
    if len(dob_str) == 10 and dob_str[4] == "-" and dob_str[7] == "-":
        return dob_str
    return None


def format_year(year_val):
    if not year_val:
        return None
    val_str = str(year_val).strip()
    if val_str.isdigit() and len(val_str) == 4:
        return int(val_str)
    return None


def migrate_alumni():
    print("=" * 60)
    print("MIGRATING ALUMNI REGISTRATIONS: CodeIgniter -> Laravel")
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
            print("\n[Step 1] Migrating tbl_alumni_registration -> alumni_forms...")
            m_alumni = re.findall(
                r"INSERT INTO [`\x27]?tbl_alumni_registration[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_alumni = []
            if m_alumni:
                cols = [c.strip(" `\r\n") for c in m_alumni[0][0].split(",")]
                for _, vals in m_alumni:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_alumni.append(dict(zip(cols, r)))

            print(f"Found {len(raw_alumni)} alumni registrations in source dump.")

            alumni_sql = """
            INSERT INTO alumni_forms (
                id, first_name, middle_name, last_name, photo, show_on_website,
                gender, date_of_birth, mobile_number, email, current_country,
                program, passing_year, pass_out_college, current_address,
                current_state, current_district, current_working_place,
                current_working_organization, current_working_designation,
                marital_status, AfterMfirst_name, AfterMmiddle_name, AfterMlast_name,
                employee_identity_card, further_studies, academic_year_id,
                Department, verified, alumni_association_member, what_can_do_college,
                delete_bit, verification_bit, rejected_reason, created_at, updated_at
            ) VALUES (
                %(id)s, %(first_name)s, %(middle_name)s, %(last_name)s, NULL, 0,
                %(gender)s, %(date_of_birth)s, %(mobile_number)s, %(email)s, %(current_country)s,
                %(program)s, %(passing_year)s, %(pass_out_college)s, %(current_address)s,
                %(current_state)s, %(current_district)s, %(current_working_place)s,
                %(current_working_organization)s, %(current_working_designation)s,
                %(marital_status)s, %(AfterMfirst_name)s, %(AfterMmiddle_name)s, %(AfterMlast_name)s,
                NULL, NULL, NULL,
                NULL, 1, 0, %(what_can_do_college)s,
                0, 1, NULL, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                first_name = VALUES(first_name),
                middle_name = VALUES(middle_name),
                last_name = VALUES(last_name),
                gender = VALUES(gender),
                date_of_birth = VALUES(date_of_birth),
                mobile_number = VALUES(mobile_number),
                current_country = VALUES(current_country),
                program = VALUES(program),
                passing_year = VALUES(passing_year),
                current_address = VALUES(current_address),
                current_state = VALUES(current_state),
                current_district = VALUES(current_district),
                current_working_place = VALUES(current_working_place),
                current_working_organization = VALUES(current_working_organization),
                current_working_designation = VALUES(current_working_designation),
                marital_status = VALUES(marital_status),
                AfterMfirst_name = VALUES(AfterMfirst_name),
                AfterMmiddle_name = VALUES(AfterMmiddle_name),
                AfterMlast_name = VALUES(AfterMlast_name),
                what_can_do_college = VALUES(what_can_do_college),
                delete_bit = 0,
                verified = 1,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            seen_emails = set()

            for a in raw_alumni:
                a_id = int(a["id"])
                first_name = str(a.get("name") or "").strip() or "Alumni"
                middle_name = str(a.get("mname") or "").strip() or None
                last_name = str(a.get("lname") or "").strip() or None
                gender = str(a.get("gender") or "").strip() or "Other"
                dob = format_dob_date(a.get("dob"))
                mobile = str(a.get("phno") or "").strip() or None
                email = str(a.get("email") or "").strip().lower()

                # Deduplicate unique emails if needed
                if email in seen_emails:
                    email_parts = email.split("@")
                    if len(email_parts) == 2:
                        email = f"{email_parts[0]}+{a_id}@{email_parts[1]}"
                seen_emails.add(email)

                country = str(a.get("country") or "").strip() or None
                program = str(a.get("EducationQualification") or "").strip() or None
                passing_year = format_year(a.get("year_passed"))
                address = str(a.get("address") or "").strip() or None
                state = str(a.get("state") or "").strip() or None
                district = str(a.get("district") or "").strip() or None
                working_place = str(a.get("workingplace") or "").strip() or None
                working_org = str(a.get("workingorganisation") or "").strip() or None
                working_desig = str(a.get("workingdesignation") or "").strip() or None
                status = str(a.get("status") or "").strip() or None
                after_first = str(a.get("aftermrgname") or "").strip() or None
                after_mid = str(a.get("aftermrgmname") or "").strip() or None
                after_last = str(a.get("aftermrglname") or "").strip() or None
                what_can_do = str(a.get("WhatCanIDo") or "").strip() or None
                created_at = clean_date(a.get("created_date")) or now_ts

                cur.execute(alumni_sql, {
                    "id": a_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "gender": gender,
                    "date_of_birth": dob,
                    "mobile_number": mobile,
                    "email": email,
                    "current_country": country,
                    "program": program,
                    "passing_year": passing_year,
                    "pass_out_college": "Sathaye College",
                    "current_address": address,
                    "current_state": state,
                    "current_district": district,
                    "current_working_place": working_place,
                    "current_working_organization": working_org,
                    "current_working_designation": working_desig,
                    "marital_status": status,
                    "AfterMfirst_name": after_first,
                    "AfterMmiddle_name": after_mid,
                    "AfterMlast_name": after_last,
                    "what_can_do_college": what_can_do,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} alumni registrations into alumni_forms.")

            # Verification
            cur.execute("SELECT COUNT(*) AS c FROM alumni_forms WHERE delete_bit = 0")
            print(f"\nVerification - Active alumni_forms count: {cur.fetchone()['c']}")
            cur.execute("SELECT id, first_name, last_name, email, program, passing_year, current_working_organization FROM alumni_forms ORDER BY id ASC LIMIT 5")
            for r in cur.fetchall():
                print(" ", r)

    finally:
        conn.close()

    print("\nAlumni Registrations Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_alumni()
