#!/usr/bin/env python3
"""
Migration Script: Photo Gallery Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_gallery, tbl_category_galley_linking)
Target: u207346834_sathayelara (galleries, photos, photo_gallery_mappings)
"""

import sys
import os
import re
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

def clean_timestamp(d_str):
    if not d_str or d_str in ("NULL", "None", "") or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = str(d_str).strip()
    if len(d_str) == 10:
        return f"{d_str} 00:00:00"
    return d_str

def migrate_photogallery():
    print("=" * 60)
    print("MIGRATING PHOTO GALLERY MODULE: CodeIgniter -> Laravel")
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
        # Check initial counts
        cur.execute("SELECT COUNT(*) AS c FROM galleries")
        print(f"Initial records in galleries: {cur.fetchone()['c']}")
        cur.execute("SELECT COUNT(*) AS c FROM photos")
        print(f"Initial records in photos: {cur.fetchone()['c']}")
        cur.execute("SELECT COUNT(*) AS c FROM photo_gallery_mappings")
        print(f"Initial records in photo_gallery_mappings: {cur.fetchone()['c']}")

        # ---------------------------------------------------------
        # Step 1: Parse Category Master (tbl_category_galley_linking)
        # ---------------------------------------------------------
        category_map = {}
        cgl_match = re.search(r"INSERT INTO `tbl_category_galley_linking`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if cgl_match:
            c_cols = [c.strip(" `\r\n") for c in cgl_match.group(1).split(",")]
            for r in parse_sql_values(cgl_match.group(2)):
                d = dict(zip(c_cols, r))
                c_id = str(d.get("cgl_id"))
                c_name = (d.get("cgl_name") or "").strip()
                if c_id and c_name:
                    category_map[c_id] = c_name
        print(f"Parsed {len(category_map)} gallery categories from CI dump.")

        # ---------------------------------------------------------
        # Step 2: Parse tbl_gallery
        # ---------------------------------------------------------
        matches = re.findall(r"INSERT INTO `tbl_gallery`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_gallery!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_galleries = []
        for _, vals_str in matches:
            for r in parse_sql_values(vals_str):
                raw_galleries.append(dict(zip(cols, r)))

        print(f"Parsed {len(raw_galleries)} galleries from tbl_gallery.")

        # Prepare gallery and photo records
        galleries_to_insert = []
        photos_by_gallery = {}  # gallery_id -> list of (photo_path, caption, photo_tag, created_ts)

        for g in raw_galleries:
            g_id = int(g["tg_id"])
            title = (g.get("tg_name") or "Gallery").strip()[:250]
            description = (g.get("tg_description") or "").strip() or None
            academic_year = (g.get("tg_year") or "2024-25").strip()

            cat_id = str(g.get("tg_category") or "").strip()
            cat_name = category_map.get(cat_id, "General")
            gallery_tag = cat_name

            raw_imgs = (g.get("tg_images_path") or "").strip()
            items = [i for i in raw_imgs.split("~^~") if i.strip()]

            # Determine thumbnail
            first_path = ""
            photo_list = []
            for item in items:
                parts = item.split("~%~")
                img_path = parts[0].replace("^%^path", "").strip()[:250]
                caption = (parts[1].strip() if len(parts) > 1 else title)[:250]
                if not caption:
                    caption = title
                if img_path:
                    if not first_path:
                        first_path = img_path
                    photo_list.append((img_path, caption, cat_name))

            thumbnail = first_path if first_path else "uploads/gallery/default-thumbnail.jpg"
            view_style = "slider"
            delete_bit = 0  # Active

            created_ts = clean_timestamp(g.get("tg_created_date"))

            galleries_to_insert.append((
                g_id, title, description, description,
                thumbnail, academic_year, cat_name, gallery_tag,
                view_style, None, None, None, None, None,
                delete_bit, created_ts, created_ts
            ))

            photos_by_gallery[g_id] = (photo_list, created_ts)

        # ---------------------------------------------------------
        # Step 3: Insert into galleries
        # ---------------------------------------------------------
        print(f"\nInserting {len(galleries_to_insert)} records into galleries...")
        insert_gallery_query = """
        INSERT INTO galleries (
            id, title, discription, description,
            thumbnail_path, academic_year, category, gallery_tag,
            view_style, activities, event_id, news_id, department, committee_id,
            delete_bit, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            discription = VALUES(discription),
            description = VALUES(description),
            thumbnail_path = VALUES(thumbnail_path),
            academic_year = VALUES(academic_year),
            category = VALUES(category),
            gallery_tag = VALUES(gallery_tag),
            view_style = VALUES(view_style),
            delete_bit = VALUES(delete_bit),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at);
        """

        batch_size = 100
        for i in range(0, len(galleries_to_insert), batch_size):
            batch = galleries_to_insert[i:i+batch_size]
            cur.executemany(insert_gallery_query, batch)
            conn.commit()

        print("Finished inserting galleries.")

        # ---------------------------------------------------------
        # Step 4: Insert Photos and Mappings
        # ---------------------------------------------------------
        print("\nInserting Photos and PhotoGalleryMappings...")
        total_photos_inserted = 0
        total_mappings_inserted = 0

        # Clear existing mappings for these galleries to avoid duplicates on re-run
        gallery_ids_str = ",".join(str(g[0]) for g in galleries_to_insert)
        cur.execute(f"DELETE FROM photo_gallery_mappings WHERE gallery_id IN ({gallery_ids_str})")
        conn.commit()

        insert_photo_query = """
        INSERT INTO photos (
            photo_path, caption, is_video, video_link,
            photo_tag, delete_bit, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        );
        """

        insert_mapping_query = """
        INSERT INTO photo_gallery_mappings (
            photo_id, gallery_id, sequence, delete_bit, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        );
        """

        mappings_batch = []
        for g_id, (photo_list, created_ts) in photos_by_gallery.items():
            for seq, (p_path, p_caption, p_tag) in enumerate(photo_list, start=1):
                cur.execute(insert_photo_query, (
                    p_path, p_caption, 0, None,
                    p_tag, 0, created_ts, created_ts
                ))
                photo_id = cur.lastrowid
                total_photos_inserted += 1
                mappings_batch.append((photo_id, g_id, seq, 0, created_ts, created_ts))

        conn.commit()

        # Batch insert mappings
        for i in range(0, len(mappings_batch), batch_size):
            batch = mappings_batch[i:i+batch_size]
            cur.executemany(insert_mapping_query, batch)
            conn.commit()
            total_mappings_inserted += len(batch)

        print(f"Finished inserting {total_photos_inserted} photos and {total_mappings_inserted} mappings.")

        # ---------------------------------------------------------
        # Step 5: Verification
        # ---------------------------------------------------------
        print("\n[Step 5] Verification:")
        cur.execute("SELECT COUNT(*) AS c FROM galleries WHERE delete_bit = 0")
        print(f"  Total active galleries in galleries table: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM photos WHERE delete_bit = 0")
        print(f"  Total active photos in photos table: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM photo_gallery_mappings WHERE delete_bit = 0")
        print(f"  Total mappings in photo_gallery_mappings table: {cur.fetchone()['c']}")

        print("\nSample Migrated Galleries with Photo Counts:")
        cur.execute("""
            SELECT g.id, g.title, g.academic_year, g.category, g.thumbnail_path,
                   COUNT(pgm.photo_id) AS photo_count
            FROM galleries g
            LEFT JOIN photo_gallery_mappings pgm ON g.id = pgm.gallery_id
            GROUP BY g.id
            ORDER BY g.id DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"  ID {row['id']:3d} | Year: {row['academic_year']} | Cat: {row['category'][:15]:15s} | Photos: {row['photo_count']:2d} | Title: {row['title'][:30]}")

        print("\n=== PHOTO GALLERY MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_photogallery()
