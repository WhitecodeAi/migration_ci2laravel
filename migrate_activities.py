#!/usr/bin/env python3
"""
Migration Script: Activities Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_activities_stream_linking)
Target: u207346834_sathayelara (activity_tables, committees)
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
    if not path_str or str(path_str).strip() in ("None", "NULL"):
        return None
    path_str = str(path_str).strip()
    if "^%^" in path_str:
        path_str = path_str.split("^%^")[0].strip()
    path_str = path_str.lstrip("/")
    return path_str


def get_activity_type_id(name):
    lower = str(name).lower()
    if any(k in lower for k in ["drama", "music", "dance", "film", "theatre", "fine arts", "marathi wangmay", "saptarang"]):
        return 3  # Cultural Activities
    elif any(k in lower for k in ["ncc", "nss", "wdc", "rotaract", "alumni", "social science"]):
        return 5  # Social and Outreach Activities
    elif any(k in lower for k in ["entrepreneur", "commerce"]):
        return 7  # Entrepreneurial Activities
    elif any(k in lower for k in ["gravity", "plantae", "microfista", "nature club", "energy green", "green club"]):
        return 8  # Technical / Environmental Activities
    else:
        return 2  # Co-Curricular Activities


def migrate_activities():
    print("=" * 60)
    print("MIGRATING ACTIVITIES MODULE: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    # Step 1: Parse tbl_activities_stream_linking
    print("\n[Step 1] Parsing tbl_activities_stream_linking from SQL dump...")
    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_activities_stream_linking[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )

    if not matches:
        print("No INSERT statements found for tbl_activities_stream_linking!")
        return

    cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
    raw_activities = []
    for _, vals_str in matches:
        for r in parse_sql_values(vals_str):
            raw_activities.append(dict(zip(cols, r)))

    print(f"Parsed {len(raw_activities)} activities from tbl_activities_stream_linking.")

    # Connect to Remote Database
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Step 2: Insert into committees table
            print("\n[Step 2] Inserting/Updating committees table...")
            committee_insert_query = """
            INSERT INTO committees (
                id, college_id, name, type, grievance_type_id, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(college_id)s, %(name)s, %(type)s, %(grievance_type_id)s, %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                type = VALUES(type),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            # Step 3: Insert into activity_tables
            print("[Step 3] Inserting/Updating activity_tables...")
            activity_insert_query = """
            INSERT INTO activity_tables (
                id, show_on_website, sequence, activity_name, activity_description,
                activity_thumbnail, activity_start_date, activity_end_date,
                department_id, committee_id, activity_type_id, event_id,
                delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(show_on_website)s, %(sequence)s, %(activity_name)s, %(activity_description)s,
                %(activity_thumbnail)s, %(activity_start_date)s, %(activity_end_date)s,
                %(department_id)s, %(committee_id)s, %(activity_type_id)s, %(event_id)s,
                %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                show_on_website = VALUES(show_on_website),
                sequence = VALUES(sequence),
                activity_name = VALUES(activity_name),
                activity_thumbnail = VALUES(activity_thumbnail),
                activity_start_date = VALUES(activity_start_date),
                activity_end_date = VALUES(activity_end_date),
                committee_id = VALUES(committee_id),
                activity_type_id = VALUES(activity_type_id),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            seq = 1
            for act in raw_activities:
                asl_id = int(act["asl_id"])
                name = str(act["asl_name"]).strip()
                thumb = clean_path(act["asl_bred_images_path"])
                c_date = clean_date(act["asl_created_date"]) or now_ts
                show_web = 1 if str(act.get("asl_show_on_website", "1")) == "1" else 0
                act_type_id = get_activity_type_id(name)

                # Committee record
                comm_data = {
                    "id": asl_id,
                    "college_id": 1,
                    "name": name,
                    "type": "Association / Activity Cell",
                    "grievance_type_id": None,
                    "delete_bit": 0,
                    "created_at": c_date,
                    "updated_at": c_date
                }
                cur.execute(committee_insert_query, comm_data)

                # Activity record
                activity_data = {
                    "id": asl_id,
                    "show_on_website": show_web,
                    "sequence": seq,
                    "activity_name": name,
                    "activity_description": f"{name} of Sathaye College",
                    "activity_thumbnail": thumb,
                    "activity_start_date": c_date,
                    "activity_end_date": c_date,
                    "department_id": None,
                    "committee_id": asl_id,
                    "activity_type_id": act_type_id,
                    "event_id": None,
                    "delete_bit": 0,
                    "created_at": c_date,
                    "updated_at": c_date
                }
                cur.execute(activity_insert_query, activity_data)
                seq += 1

            conn.commit()
            print(f"Successfully migrated {len(raw_activities)} activities and committees.")

            # Step 4: Verification
            print("\n[Step 4] Verification:")
            cur.execute("SELECT COUNT(*) as count FROM activity_tables WHERE delete_bit = 0")
            act_count = cur.fetchone()["count"]
            cur.execute("SELECT COUNT(*) as count FROM committees WHERE delete_bit = 0")
            comm_count = cur.fetchone()["count"]

            print(f"  Total active activities in activity_tables: {act_count}")
            print(f"  Total active committees in committees: {comm_count}")

            print("\nSample Migrated Activities:")
            cur.execute("""
                SELECT a.id, a.activity_name, t.type as activity_type, a.activity_start_date, a.show_on_website
                FROM activity_tables a
                LEFT JOIN activity_types t ON a.activity_type_id = t.id
                ORDER BY a.sequence ASC
                LIMIT 8
            """)
            for row in cur.fetchall():
                vis = "Visible" if row["show_on_website"] == 1 else "Hidden"
                dt = str(row["activity_start_date"])[:10] if row["activity_start_date"] else "N/A"
                print(f"  ID {row['id']:2} | {row['activity_name']:32} | Type: {row['activity_type']:28} | Date: {dt} | {vis}")

    finally:
        conn.close()

    print("\n=== ACTIVITIES MODULE MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_activities()
