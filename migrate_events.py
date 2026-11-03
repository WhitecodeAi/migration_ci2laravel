#!/usr/bin/env python3
"""
Migration Script: Events Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_event)
Target: u207346834_sathayelara (events_tables, event_categories)
"""

import sys
import os
import re
import json
import pymysql
from datetime import datetime

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

def parse_sql_values(values_str):
    records = []
    current_record = []
    current_val = []
    in_quotes = False
    escape = False
    in_record = False
    i = 0
    n = len(values_str)
    while i < n:
        char = values_str[i]
        if not in_record:
            if char == "(":
                in_record = True
                current_record = []
                current_val = []
                in_quotes = False
                escape = False
        else:
            if escape:
                current_val.append(char)
                escape = False
            elif char == "\\":
                escape = True
            elif char == "\x27":
                if in_quotes:
                    if i + 1 < n and values_str[i+1] == "\x27":
                        current_val.append("\x27")
                        i += 1
                    else:
                        in_quotes = False
                else:
                    in_quotes = True
            elif char == "," and not in_quotes:
                val = "".join(current_val).strip()
                current_record.append(None if val == "NULL" else val)
                current_val = []
            elif char == ")" and not in_quotes:
                val = "".join(current_val).strip()
                current_record.append(None if val == "NULL" else val)
                records.append(current_record)
                in_record = False
                current_record = []
                current_val = []
            else:
                current_val.append(char)
        i += 1
    return records

def clean_date(d_str):
    if not d_str or d_str in ("NULL", "None", ""):
        return None
    d_str = str(d_str).strip()
    if d_str.startswith("1970-01") or d_str.startswith("0000-00-00"):
        return None
    parts = d_str.split(" ")[0].split("T")[0]
    if len(parts) == 10 and parts[4] == "-" and parts[7] == "-":
        return parts
    return None

def clean_timestamp(d_str, fallback=None):
    if not d_str or d_str in ("NULL", "None", "") or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        d_str = fallback
    if not d_str or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = str(d_str).strip()
    if len(d_str) == 10:
        return f"{d_str} 00:00:00"
    return d_str

def strip_html(html_str):
    if not html_str:
        return ""
    clean = re.sub(r"<[^>]+>", " ", html_str)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def get_academic_year_id(event_date_str, raw_year_str, year_to_id_map):
    if raw_year_str:
        raw_year_str = raw_year_str.strip()
        if raw_year_str in year_to_id_map:
            return year_to_id_map[raw_year_str]
        if len(raw_year_str) == 4 and raw_year_str.isdigit():
            y = int(raw_year_str)
            y_str = f"{y}-{str(y+1)[2:]}"
            if y_str in year_to_id_map:
                return year_to_id_map[y_str]

    if event_date_str and len(event_date_str) >= 10:
        try:
            dt = datetime.strptime(event_date_str[:10], "%Y-%m-%d")
            if dt.month >= 6:
                y_str = f"{dt.year}-{str(dt.year+1)[2:]}"
            else:
                y_str = f"{dt.year-1}-{str(dt.year)[2:]}"
            if y_str in year_to_id_map:
                return year_to_id_map[y_str]
        except Exception:
            pass
    return year_to_id_map.get("2024-25", 10)

def migrate_events():
    print("=" * 60)
    print("MIGRATING EVENTS MODULE: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL dump file '{SQL_FILE}' not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # ---------------------------------------------------------
        # Step 1: Synchronize Academic Years & Event Categories
        # ---------------------------------------------------------
        print("\n[Step 1] Loading Academic Years & Event Categories...")
        cur.execute("SELECT id, name FROM academic_years")
        year_to_id_map = {row["name"]: row["id"] for row in cur.fetchall()}
        print(f"  Loaded {len(year_to_id_map)} academic years.")

        # Ensure event categories
        categories = ["General", "Upcoming Event", "Past Event"]
        cat_map = {}
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for cat in categories:
            cur.execute("SELECT id FROM event_categories WHERE name = %s", (cat,))
            row = cur.fetchone()
            if row:
                cat_map[cat] = row["id"]
            else:
                cur.execute("INSERT INTO event_categories (name, created_at, updated_at) VALUES (%s, %s, %s)", (cat, now_ts, now_ts))
                conn.commit()
                cat_map[cat] = cur.lastrowid
                print(f"  Created category '{cat}' -> ID {cat_map[cat]}")

        # ---------------------------------------------------------
        # Step 2: Parse tbl_event from SQL Dump
        # ---------------------------------------------------------
        print("\n[Step 2] Parsing tbl_event from SQL dump...")
        matches = re.findall(r"INSERT INTO `tbl_event`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_event!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_events = []
        for _, vals_str in matches:
            for r in parse_sql_values(vals_str):
                raw_events.append(dict(zip(cols, r)))

        print(f"Parsed {len(raw_events)} events from tbl_event.")

        # ---------------------------------------------------------
        # Step 3: Insert into events_tables
        # ---------------------------------------------------------
        insert_query = """
        INSERT INTO events_tables (
            id, event_title, department_id, committee_id,
            show_on_website, event_start_date, event_end_date, acadamicyear_id,
            event_report, description, event_thumbnail, tag_id,
            event_notice_brochure, eventtype, delete_bit, created_at,
            updated_at, rich_description, event_category_id,
            event_category_ids, sequence, department_ids
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            event_title = VALUES(event_title),
            department_id = VALUES(department_id),
            committee_id = VALUES(committee_id),
            show_on_website = VALUES(show_on_website),
            event_start_date = VALUES(event_start_date),
            event_end_date = VALUES(event_end_date),
            acadamicyear_id = VALUES(acadamicyear_id),
            event_report = VALUES(event_report),
            description = VALUES(description),
            event_thumbnail = VALUES(event_thumbnail),
            tag_id = VALUES(tag_id),
            event_notice_brochure = VALUES(event_notice_brochure),
            eventtype = VALUES(eventtype),
            delete_bit = VALUES(delete_bit),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at),
            rich_description = VALUES(rich_description),
            event_category_id = VALUES(event_category_id),
            event_category_ids = VALUES(event_category_ids),
            sequence = VALUES(sequence),
            department_ids = VALUES(department_ids);
        """

        events_to_insert = []
        for seq, e in enumerate(raw_events, start=1):
            e_id = int(e["evt_id"])
            title = (e.get("evt_title") or "Event").strip()[:250]

            start_date = clean_date(e.get("evt_valid_from")) or clean_date(e.get("evt_event_date"))
            end_date = clean_date(e.get("evt_valid_till")) or start_date

            ay_id = get_academic_year_id(start_date, e.get("event_year"), year_to_id_map)

            # Descriptions
            rich_desc = (e.get("evt_descp_content") or e.get("evt_s_description") or "").strip() or None
            plain_desc = strip_html(rich_desc)[:250] if rich_desc else None

            # Thumbnail and Report files
            raw_thumb = (e.get("evt_file") or "").strip()
            thumb = raw_thumb.replace("^%^path", "").strip() if raw_thumb else None

            raw_report = (e.get("evt_report") or "").strip()
            report = raw_report.replace("^%^path", "").strip() if raw_report else None

            # Category
            act_type = (e.get("evtActivityType") or e.get("evt_type") or "").strip()
            if "upcoming" in act_type.lower():
                cat_id = cat_map["Upcoming Event"]
            elif "past" in act_type.lower():
                cat_id = cat_map["Past Event"]
            else:
                cat_id = cat_map["General"]

            cat_ids_json = json.dumps([cat_id])
            show_on_website = 1
            eventtype = 1  # College Event
            delete_bit = 0  # Active

            created_ts = clean_timestamp(e.get("evt_created_date"), fallback=start_date)

            events_to_insert.append((
                e_id, title, None, None,
                show_on_website, start_date, end_date, ay_id,
                report, plain_desc, thumb, None,
                None, eventtype, delete_bit, created_ts,
                created_ts, rich_desc, cat_id,
                cat_ids_json, seq, None
            ))

        print(f"\nInserting {len(events_to_insert)} records into events_tables...")
        batch_size = 100
        for i in range(0, len(events_to_insert), batch_size):
            batch = events_to_insert[i:i+batch_size]
            cur.executemany(insert_query, batch)
            conn.commit()
            print(f"  Inserted batch {i+1} to {min(i+batch_size, len(events_to_insert))}")

        print("Finished inserting events.")

        # ---------------------------------------------------------
        # Step 4: Verification
        # ---------------------------------------------------------
        print("\n[Step 4] Verification:")
        cur.execute("SELECT COUNT(*) AS c FROM events_tables WHERE delete_bit = 0")
        print(f"  Total active events in events_tables: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM events_tables WHERE event_thumbnail IS NOT NULL")
        print(f"  Events with thumbnails: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM events_tables WHERE event_report IS NOT NULL")
        print(f"  Events with reports: {cur.fetchone()['c']}")

        print("\nSample Migrated Events:")
        cur.execute("""
            SELECT e.id, e.event_title, e.event_start_date, e.event_end_date, ay.name AS academic_year, ec.name AS category
            FROM events_tables e
            LEFT JOIN academic_years ay ON e.acadamicyear_id = ay.id
            LEFT JOIN event_categories ec ON e.event_category_id = ec.id
            ORDER BY e.id DESC
            LIMIT 5;
        """)
        for ev in cur.fetchall():
            print(f"  ID {ev['id']:3d} | Year: {ev['academic_year']} | {ev['category']:14s} | Date: {ev['event_start_date']} | Title: {ev['event_title'][:40]}")

        print("\n=== EVENTS MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_events()

