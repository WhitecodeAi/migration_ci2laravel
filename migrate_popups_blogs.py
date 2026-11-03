#!/usr/bin/env python3
"""
Migration Script: Dynamic Popup and Blogs Modules (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_dynamic_popup, tbl_blog)
Target: u207346834_sathayelara (dynamic_popup, blogs)
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


def migrate_popups_and_blogs():
    print("=" * 60)
    print("MIGRATING DYNAMIC POPUP & BLOGS: CodeIgniter -> Laravel")
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
            # Step 1: Migrate Dynamic Popup (tbl_dynamic_popup -> dynamic_popup)
            # ---------------------------------------------------------
            print("\n[Step 1] Migrating tbl_dynamic_popup -> dynamic_popup...")
            m_popup = re.findall(
                r"INSERT INTO [`\x27]?tbl_dynamic_popup[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_popups = []
            if m_popup:
                cols = [c.strip(" `\r\n") for c in m_popup[0][0].split(",")]
                for _, vals in m_popup:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_popups.append(dict(zip(cols, r)))

            print(f"Found {len(raw_popups)} popups in source dump.")

            popup_sql = """
            INSERT INTO dynamic_popup (
                id, title, file, show_on_website, delete_bit, created_at, updated_at,
                image_width, image_height, text_overlay
            ) VALUES (
                %(id)s, %(title)s, %(file)s, %(show_on_website)s, 0, %(created_at)s, %(updated_at)s,
                NULL, NULL, %(text_overlay)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                file = VALUES(file),
                show_on_website = VALUES(show_on_website),
                delete_bit = 0,
                text_overlay = VALUES(text_overlay),
                updated_at = VALUES(updated_at)
            """

            migrated_popups = 0
            for p in raw_popups:
                p_id = int(p["dp_id"])
                title = (p.get("dp_title") or "").strip()
                file_path = clean_path(p.get("dp_popup_images_path"))
                show_on_site = 1 if str(p.get("dp_show_on_website")) == "1" else 0
                created_at = clean_date(p.get("dp_created_date")) or now_ts
                text_overlay = (p.get("dp_text") or "").strip() or None

                cur.execute(popup_sql, {
                    "id": p_id,
                    "title": title,
                    "file": file_path,
                    "show_on_website": show_on_site,
                    "created_at": created_at,
                    "updated_at": now_ts,
                    "text_overlay": text_overlay
                })
                migrated_popups += 1

            conn.commit()
            print(f"Successfully migrated {migrated_popups} popup(s) into dynamic_popup.")

            # ---------------------------------------------------------
            # Step 2: Migrate Blogs (tbl_blog -> blogs)
            # ---------------------------------------------------------
            print("\n[Step 2] Migrating tbl_blog -> blogs...")
            m_blog = re.findall(
                r"INSERT INTO [`\x27]?tbl_blog[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_blogs = []
            if m_blog:
                cols = [c.strip(" `\r\n") for c in m_blog[0][0].split(",")]
                for _, vals in m_blog:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_blogs.append(dict(zip(cols, r)))

            print(f"Found {len(raw_blogs)} blogs in source dump.")

            blog_sql = """
            INSERT INTO blogs (
                id, title, description, start_date, end_date, file, location,
                blog_type, delete_bit, created_by, created_at, updated_at, is_archived
            ) VALUES (
                %(id)s, %(title)s, %(description)s, %(start_date)s, %(end_date)s, %(file)s, %(location)s,
                %(blog_type)s, 0, %(created_by)s, %(created_at)s, %(updated_at)s, 0
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                description = VALUES(description),
                start_date = VALUES(start_date),
                end_date = VALUES(end_date),
                file = VALUES(file),
                location = VALUES(location),
                blog_type = VALUES(blog_type),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_blogs = 0
            for b in raw_blogs:
                b_id = int(b["bg_id"])
                title = (b.get("bg_title") or "").strip()
                description = (b.get("bg_descp_content") or b.get("bg_s_description") or "").strip()
                file_path = clean_path(b.get("bg_file"))
                location = (b.get("bg_location") or "").strip() or None
                b_type = (b.get("bg_type") or b.get("bg_blog_type") or "").strip() or None
                start_date = clean_date(b.get("bg_valid_from"))
                if start_date:
                    start_date = start_date[:10]
                end_date = clean_date(b.get("bg_valid_till"))
                if end_date:
                    end_date = end_date[:10]
                created_at = clean_date(b.get("bg_created_date") or b.get("bg_blog_date")) or now_ts
                created_by = int(b.get("bg_user_id")) if b.get("bg_user_id") and str(b.get("bg_user_id")).isdigit() else None

                cur.execute(blog_sql, {
                    "id": b_id,
                    "title": title,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "file": file_path,
                    "location": location,
                    "blog_type": b_type,
                    "created_by": created_by,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_blogs += 1

            conn.commit()
            print(f"Successfully migrated {migrated_blogs} blog(s) into blogs.")

            # Summary verification
            cur.execute("SELECT COUNT(*) AS c FROM dynamic_popup WHERE delete_bit = 0")
            print(f"\nVerification - Active dynamic_popup count: {cur.fetchone()['c']}")
            cur.execute("SELECT id, title, file, show_on_website FROM dynamic_popup")
            for r in cur.fetchall():
                print(" ", r)

            cur.execute("SELECT COUNT(*) AS c FROM blogs WHERE delete_bit = 0")
            print(f"\nVerification - Active blogs count: {cur.fetchone()['c']}")
            cur.execute("SELECT id, title, start_date, file, blog_type FROM blogs")
            for r in cur.fetchall():
                print(" ", r)

    finally:
        conn.close()

    print("\nDynamic Popup & Blogs Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_popups_and_blogs()

