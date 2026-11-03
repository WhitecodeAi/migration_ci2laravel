#!/usr/bin/env python3
"""
Migration Script: Faculty & Departments Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_stream_master, tbl_department_and_stream_linking, tbl_users)
Target: u207346834_sathayelara (streams, departments, users, faculties, faculty_department_models)
"""

import sys
import os
import re
import pymysql
from datetime import datetime

from db_config import DB_CONFIG, SQL_FILE


def parse_sql_values(values_str):
    """Parses SQL tuples from an extended INSERT statement."""
    rows = []
    current_row = []
    current_val = []
    in_quotes = False
    quote_char = None
    escaped = False

    for char in values_str:
        if escaped:
            if char == "n":
                current_val.append("\n")
            elif char == "r":
                current_val.append("\r")
            elif char == "t":
                current_val.append("\t")
            elif char == "0":
                current_val.append("\0")
            elif char == "Z":
                current_val.append("\x1a")
            else:
                current_val.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if not in_quotes:
            if char in ("'", '"'):
                in_quotes = True
                quote_char = char
            elif char == ",":
                val_str = "".join(current_val).strip()
                if val_str.upper() == "NULL":
                    current_row.append(None)
                elif val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
                    current_row.append(int(val_str))
                else:
                    current_row.append(val_str)
                current_val = []
            elif char == "(":
                current_row = []
                current_val = []
            elif char == ")":
                val_str = "".join(current_val).strip()
                if val_str.upper() == "NULL":
                    current_row.append(None)
                elif val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
                    current_row.append(int(val_str))
                else:
                    current_row.append(val_str)
                rows.append(current_row)
                current_row = []
                current_val = []
            else:
                current_val.append(char)
        else:
            if char == quote_char:
                in_quotes = False
                quote_char = None
            else:
                current_val.append(char)

    return rows


def clean_date(d_str):
    if not d_str or str(d_str).strip() in ("0000-00-00", "0000-00-00 00:00:00", "None"):
        return None
    d_str = str(d_str).strip()
    try:
        if len(d_str) == 10:
            return datetime.strptime(d_str, "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
        elif len(d_str) >= 19:
            return datetime.strptime(d_str[:19], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None


def clean_path(path_str):
    if not path_str or str(path_str).strip() in ("None", "NULL", ""):
        return None
    path_str = str(path_str).strip()
    if "^%^" in path_str:
        path_str = path_str.split("^%^")[0].strip()
    path_str = path_str.lstrip("/")
    return path_str


def extract_salutation(name):
    if not name:
        return None, ""
    n = name.strip()
    for sal in ["Dr.", "Dr ", "Prof.", "Prof ", "Mr.", "Mr ", "Mrs.", "Mrs ", "Ms.", "Ms ", "CA "]:
        if n.startswith(sal):
            clean_sal = sal.strip().rstrip(".") + "."
            clean_name = n[len(sal):].strip()
            return clean_sal, clean_name
    return None, n


def migrate_faculty():
    print("=" * 60)
    print("MIGRATING FACULTY & DEPARTMENTS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Connect to Remote Database
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # ---------------------------------------------------------
            # Step 1: Migrate Streams (tbl_stream_master -> streams)
            # ---------------------------------------------------------
            print("\n[Step 1] Migrating streams from tbl_stream_master...")
            m_streams = re.findall(
                r"INSERT INTO [`\x27]?tbl_stream_master[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_streams = []
            if m_streams:
                cols_str = [c.strip(" `\r\n") for c in m_streams[0][0].split(",")]
                for _, vals_str in m_streams:
                    for r in parse_sql_values(vals_str):
                        raw_streams.append(dict(zip(cols_str, r)))

            stream_insert_query = """
            INSERT INTO streams (id, name, delete_bit, created_at, updated_at)
            VALUES (%(id)s, %(name)s, %(delete_bit)s, %(created_at)s, %(updated_at)s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """
            for s in raw_streams:
                s_id = int(s["sm_id"])
                s_name = str(s.get("sm_stream_name") or s.get("sm_name")).strip()
                cur.execute(stream_insert_query, {
                    "id": s_id,
                    "name": s_name,
                    "delete_bit": 0,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
            conn.commit()
            print(f"  Migrated {len(raw_streams)} streams.")

            # ---------------------------------------------------------
            # Step 2: Migrate Departments (tbl_department_and_stream_linking -> departments)
            # ---------------------------------------------------------
            print("\n[Step 2] Migrating departments from tbl_department_and_stream_linking...")
            m_dept = re.findall(
                r"INSERT INTO [`\x27]?tbl_department_and_stream_linking[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_depts = []
            if m_dept:
                cols_dept = [c.strip(" `\r\n") for c in m_dept[0][0].split(",")]
                for _, vals_str in m_dept:
                    for r in parse_sql_values(vals_str):
                        raw_depts.append(dict(zip(cols_dept, r)))

            dept_insert_query = """
            INSERT INTO departments (id, college_id, stream_id, name, delete_bit, created_at, updated_at)
            VALUES (%(id)s, %(college_id)s, %(stream_id)s, %(name)s, %(delete_bit)s, %(created_at)s, %(updated_at)s)
            ON DUPLICATE KEY UPDATE
                stream_id = VALUES(stream_id),
                name = VALUES(name),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """
            valid_dept_ids = set()
            for d in raw_depts:
                d_id = int(d["dsl_id"])
                stream_id = int(d["dsl_sm_id"])
                d_name = str(d["dsl_dept_name"]).strip()
                c_date = clean_date(d.get("dsl_created_date")) or now_ts
                valid_dept_ids.add(d_id)

                cur.execute(dept_insert_query, {
                    "id": d_id,
                    "college_id": 1,
                    "stream_id": stream_id,
                    "name": d_name,
                    "delete_bit": 0,
                    "created_at": c_date,
                    "updated_at": c_date
                })
            conn.commit()
            print(f"  Migrated {len(raw_depts)} departments.")

            # ---------------------------------------------------------
            # Step 3: Parse Users from tbl_users
            # ---------------------------------------------------------
            print("\n[Step 3] Parsing faculty users from tbl_users...")
            m_users = re.findall(
                r"INSERT INTO [`\x27]?tbl_users[`\x27]?\s*\(([^\)]*)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            cols_users = [c.strip(" `\r\n") for c in m_users[0][0].split(",")]
            raw_users = []
            for _, vals_str in m_users:
                for r in parse_sql_values(vals_str):
                    raw_users.append(dict(zip(cols_users, r)))

            # Filter faculty/staff members
            # We skip superadmin users ID 1 and 2 to protect root accounts
            faculty_users = [
                u for u in raw_users
                if int(u["tu_auto_id"]) > 2 and (
                    str(u.get("tu_user_type")) in ("Faculty", "Staff") or
                    u.get("tu_dsl_id") or
                    u.get("tu_designation") or
                    str(u.get("tu_teaching_or_non_teaching")) in ("Teaching", "Non-Teaching")
                )
            ]
            print(f"  Found {len(faculty_users)} faculty/staff candidates in tbl_users.")

            # ---------------------------------------------------------
            # Step 4: Insert into users & faculties
            # ---------------------------------------------------------
            print("\n[Step 4] Inserting into users and faculties...")

            user_insert_query = """
            INSERT INTO users (
                id, name, email, username, avatar, number, department_id,
                role_id, is_global_approver, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(name)s, %(email)s, %(username)s, %(avatar)s, %(number)s, %(department_id)s,
                %(role_id)s, %(is_global_approver)s, %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                email = VALUES(email),
                avatar = VALUES(avatar),
                number = VALUES(number),
                department_id = VALUES(department_id),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            faculty_insert_query = """
            INSERT INTO faculties (
                id, user_id, photo, Salutation, designation, department_id,
                appointment_nature, qualification, Type, is_teaching, gender,
                college_id, delete_bit, ordering, display_order, created_at, updated_at
            ) VALUES (
                %(id)s, %(user_id)s, %(photo)s, %(Salutation)s, %(designation)s, %(department_id)s,
                %(appointment_nature)s, %(qualification)s, %(Type)s, %(is_teaching)s, %(gender)s,
                %(college_id)s, %(delete_bit)s, %(ordering)s, %(display_order)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                photo = VALUES(photo),
                Salutation = VALUES(Salutation),
                designation = VALUES(designation),
                department_id = VALUES(department_id),
                appointment_nature = VALUES(appointment_nature),
                qualification = VALUES(qualification),
                Type = VALUES(Type),
                is_teaching = VALUES(is_teaching),
                gender = VALUES(gender),
                delete_bit = VALUES(delete_bit),
                ordering = VALUES(ordering),
                display_order = VALUES(display_order),
                updated_at = VALUES(updated_at)
            """

            fac_dept_insert_query = """
            INSERT INTO faculty_department_models (
                faculty_id, department_id, display_order, created_at, updated_at
            ) VALUES (
                %(faculty_id)s, %(department_id)s, %(display_order)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                display_order = VALUES(display_order),
                updated_at = VALUES(updated_at)
            """

            seen_usernames = set()
            cur.execute("SELECT username FROM users WHERE username IS NOT NULL")
            for row in cur.fetchall():
                seen_usernames.add(row["username"])

            migrated_users_count = 0
            migrated_faculty_count = 0
            migrated_mappings_count = 0

            for u in faculty_users:
                u_id = int(u["tu_auto_id"])
                raw_name = str(u["tu_name"]).strip()
                salutation, clean_name = extract_salutation(raw_name)
                email = str(u.get("tu_email", "")).strip() or None
                phone = str(u.get("tu_contact", "")).strip() or None
                photo = clean_path(u.get("tu_profile_image_path"))
                desig = str(u.get("tu_designation", "")).strip() or None
                qual = str(u.get("tu_qualification", "")).strip() or None
                gender = str(u.get("tu_gender", "")).strip() or None
                nature = str(u.get("tu_nature_of_oppinment", "")).strip() or None
                teaching_str = str(u.get("tu_teaching_or_non_teaching", "")).strip().lower()
                is_teaching = 1 if (teaching_str == "teaching" or str(u.get("tu_user_type")) == "Faculty") else 0
                type_val = "Teaching" if is_teaching == 1 else "Non-Teaching"
                del_bit = 1 if str(u.get("tu_delete_bit")) == "1" else 0
                order_id = int(u.get("tu_faculty_order_id") or 0)
                c_date = clean_date(u.get("tu_created_at")) or now_ts

                # Department ID resolution
                raw_dsl = u.get("tu_dsl_id")
                dept_id = None
                if raw_dsl and str(raw_dsl).strip().isdigit():
                    cand_id = int(raw_dsl)
                    if cand_id in valid_dept_ids:
                        dept_id = cand_id

                # Generate unique username
                base_username = (email.split("@")[0] if email else f"user_{u_id}").lower()
                candidate_username = f"{base_username}_{u_id}"
                seen_usernames.add(candidate_username)

                # Role: 7 = Teaching Staff, 8 = Non Teaching Staff
                role_id = 7 if is_teaching == 1 else 8

                # 1. Insert user
                user_data = {
                    "id": u_id,
                    "name": raw_name,
                    "email": email,
                    "username": candidate_username,
                    "avatar": photo,
                    "number": phone,
                    "department_id": dept_id,
                    "role_id": role_id,
                    "is_global_approver": 0,
                    "delete_bit": del_bit,
                    "created_at": c_date,
                    "updated_at": c_date
                }
                cur.execute(user_insert_query, user_data)
                migrated_users_count += 1

                # 2. Insert faculty
                faculty_data = {
                    "id": u_id,
                    "user_id": u_id,
                    "photo": photo,
                    "Salutation": salutation,
                    "designation": desig,
                    "department_id": dept_id,
                    "appointment_nature": nature,
                    "qualification": qual,
                    "Type": type_val,
                    "is_teaching": str(is_teaching),
                    "gender": gender,
                    "college_id": 1,
                    "delete_bit": del_bit,
                    "ordering": order_id,
                    "display_order": order_id,
                    "created_at": c_date,
                    "updated_at": c_date
                }
                cur.execute(faculty_insert_query, faculty_data)
                migrated_faculty_count += 1

                # 3. Insert faculty-department mapping
                if dept_id:
                    cur.execute(fac_dept_insert_query, {
                        "faculty_id": u_id,
                        "department_id": dept_id,
                        "display_order": order_id,
                        "created_at": c_date,
                        "updated_at": c_date
                    })
                    migrated_mappings_count += 1

            conn.commit()
            print(f"  Successfully inserted/updated {migrated_users_count} users.")
            print(f"  Successfully inserted/updated {migrated_faculty_count} faculty profiles.")
            print(f"  Successfully mapped {migrated_mappings_count} faculty-department relationships.")

            # ---------------------------------------------------------
            # Step 5: Verification
            # ---------------------------------------------------------
            print("\n[Step 5] Verification:")
            cur.execute("SELECT COUNT(*) as cnt FROM streams WHERE delete_bit = 0")
            print(f"  Active Streams: {cur.fetchone()['cnt']}")

            cur.execute("SELECT COUNT(*) as cnt FROM departments WHERE delete_bit = 0")
            print(f"  Active Departments: {cur.fetchone()['cnt']}")

            cur.execute("SELECT COUNT(*) as cnt FROM faculties WHERE delete_bit = 0")
            print(f"  Active Faculty: {cur.fetchone()['cnt']}")

            cur.execute("SELECT COUNT(*) as cnt FROM faculties WHERE delete_bit = 0 AND photo IS NOT NULL")
            print(f"  Faculty with Photos: {cur.fetchone()['cnt']}")

            cur.execute("SELECT COUNT(*) as cnt FROM faculties WHERE delete_bit = 0 AND department_id IS NOT NULL")
            print(f"  Faculty with Departments: {cur.fetchone()['cnt']}")

            print("\nSample Migrated Faculty:")
            cur.execute("""
                SELECT f.id, u.name, f.designation, d.name as dept_name, f.qualification, f.photo
                FROM faculties f
                JOIN users u ON f.user_id = u.id
                LEFT JOIN departments d ON f.department_id = d.id
                WHERE f.delete_bit = 0 AND f.designation IS NOT NULL
                ORDER BY f.id ASC
                LIMIT 8
            """)
            for row in cur.fetchall():
                has_p = "Photo" if row["photo"] else "No-Photo"
                dept = row["dept_name"] or "General"
                print(f"  ID {row['id']:3} | {row['name']:30} | {row['designation']:22} | {dept:25} | {has_p}")

    finally:
        conn.close()

    print("\n=== FACULTY & DEPARTMENTS MODULE MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_faculty()
