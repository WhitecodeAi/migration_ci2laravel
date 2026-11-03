#!/usr/bin/env python3
"""
Migration Script: Home Page Slider Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_slider_page)
Target: u207346834_sathayelara.home_page_sliders (MySQL on 193.203.184.233:3306)
"""

import sys
import os
import re
import pymysql
from datetime import datetime

from db_config import DB_CONFIG, SQL_FILE

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

def format_title_from_filename(filename, slider_id):
    base = os.path.basename(filename)
    name, _ = os.path.splitext(base)
    name = re.sub(r"^copy-\d+-", "", name)
    if "whatsapp-image" in name.lower():
        return f"Home Slider {slider_id}"
    cleaned = re.sub(r"[-_]+", " ", name).strip()
    return cleaned.title() if cleaned else f"Home Slider {slider_id}"

def clean_timestamp(d_str):
    if not d_str or d_str in ("NULL", "None", "") or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = str(d_str).strip()
    if len(d_str) == 10:
        return f"{d_str} 00:00:00"
    return d_str

def migrate_homeslider():
    print("=" * 60)
    print("MIGRATING HOME SLIDER MODULE: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: SQL dump file '{SQL_FILE}' not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="latin1") as f:
        sql = f.read()

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # Check current count
        cur.execute("SELECT COUNT(*) AS c FROM home_page_sliders")
        initial_count = cur.fetchone()["c"]
        print(f"Initial sliders in home_page_sliders: {initial_count}")

        # Parse tbl_slider_page
        matches = re.findall(r"INSERT INTO `tbl_slider_page`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_slider_page!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_rows = []
        for _, vals_str in matches:
            for row in parse_sql_values(vals_str):
                raw_rows.append(dict(zip(cols, row)))

        print(f"Parsed {len(raw_rows)} records from tbl_slider_page.")

        insert_query = """
        INSERT INTO home_page_sliders (
            id, image, title, sequence, show_on_website,
            delete_bit, description, imagewatermark,
            created_date, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            image = VALUES(image),
            title = VALUES(title),
            sequence = VALUES(sequence),
            show_on_website = VALUES(show_on_website),
            delete_bit = VALUES(delete_bit),
            description = VALUES(description),
            imagewatermark = VALUES(imagewatermark),
            created_date = VALUES(created_date),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at);
        """

        rows_to_insert = []
        for r in raw_rows:
            slider_id = int(r["tsp_id"])
            raw_img = (r.get("tsp_image_path") or "").strip()
            clean_img = raw_img.replace("^%^path", "").strip()

            raw_title = (r.get("tsp_title") or "").strip()
            caption = (r.get("tsp_caption") or "").strip()
            
            if raw_title:
                title = raw_title
            elif caption:
                title = caption
            else:
                title = format_title_from_filename(clean_img, slider_id)

            seq = int(r.get("tsp_slider_order") or 0)
            show = 1 if str(r.get("tsp_visible")) == "1" else 0
            del_bit = 0  # Active

            created_ts = clean_timestamp(r.get("tsp_created_at"))
            description = caption if caption else None
            watermark = None

            rows_to_insert.append((
                slider_id, clean_img, title, seq, show,
                del_bit, description, watermark,
                created_ts, created_ts, created_ts
            ))

        print(f"Inserting {len(rows_to_insert)} records into home_page_sliders...")
        cur.executemany(insert_query, rows_to_insert)
        conn.commit()

        # Verification
        print("\n[Verification]")
        cur.execute("SELECT COUNT(*) AS c FROM home_page_sliders")
        print(f"  Total records in home_page_sliders: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM home_page_sliders WHERE show_on_website = 1")
        print(f"  Visible on website (show_on_website=1): {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM home_page_sliders WHERE show_on_website = 0")
        print(f"  Hidden from website (show_on_website=0): {cur.fetchone()['c']}")

        print("\nSample Migrated Sliders:")
        cur.execute("""
            SELECT id, title, image, sequence, show_on_website, created_date
            FROM home_page_sliders
            ORDER BY sequence ASC, id ASC
            LIMIT 10
        """)
        for s in cur.fetchall():
            vis = "Visible" if s["show_on_website"] else "Hidden"
            print(f"  ID {s['id']:2d} | Seq: {s['sequence']:2d} | {vis:7s} | Title: {s['title'][:25]:25s} | Image: {s['image']}")

        print("\n=== HOME SLIDER MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_homeslider()

