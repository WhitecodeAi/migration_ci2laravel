#!/usr/bin/env python3
"""
Migration Script: News Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql
Target: u207346834_sathayelara (MySQL on 193.203.184.233:3306)
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

def clean_timestamp(d_str, fallback_date=None):
    if not d_str or d_str in ("NULL", "None", "") or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        d_str = fallback_date
    if not d_str or str(d_str).startswith("1970-01") or str(d_str).startswith("0000-00-00"):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = str(d_str).strip()
    if len(d_str) == 10:
        return f"{d_str} 00:00:00"
    return d_str

def migrate_news():
    print("=" * 60)
    print("MIGRATING NEWS MODULE: CodeIgniter -> Laravel")
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
        # ---------------------------------------------------------
        # Step 1: Manage News Tags (news_tag_masters)
        # ---------------------------------------------------------
        print("\n[Step 1] Synchronizing News Tags (news_tag_masters)...")
        cur.execute("SELECT id, name FROM news_tag_masters")
        existing_tags = {row["name"].strip().lower(): row["id"] for row in cur.fetchall()}
        print(f"Existing tags in Laravel: {existing_tags}")

        # Map CI categories:
        # 1: Under Graduate -> 'UG'
        # 2: Post Graduate -> 'PG'
        # 3: Advertisement -> 'Advertisement'
        # 4: Sports Event -> 'Sports Event'
        # 5: Junior College -> 'Junior College'
        ci_category_names = {
            "1": "UG",
            "2": "PG",
            "3": "Advertisement",
            "4": "Sports Event",
            "5": "Junior College"
        }

        tag_mapping = {} # ci_cat_id -> laravel_tag_id
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ci_id, tag_name in ci_category_names.items():
            key = tag_name.lower()
            if key in existing_tags:
                tag_mapping[ci_id] = existing_tags[key]
                print(f"  Mapped CI Category '{tag_name}' (ID {ci_id}) -> Existing Laravel Tag ID {existing_tags[key]}")
            else:
                cur.execute(
                    "INSERT INTO news_tag_masters (name, created_at, updated_at) VALUES (%s, %s, %s)",
                    (tag_name, now_ts, now_ts)
                )
                conn.commit()
                new_id = cur.lastrowid
                existing_tags[key] = new_id
                tag_mapping[ci_id] = new_id
                print(f"  Inserted new Laravel Tag '{tag_name}' -> ID {new_id}")

        # ---------------------------------------------------------
        # Step 2: Parse and Migrate News (news_masters)
        # ---------------------------------------------------------
        print("\n[Step 2] Parsing tbl_news from SQL dump...")
        matches = re.findall(r"INSERT INTO `tbl_news`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not matches:
            print("No INSERT statements found for tbl_news!")
            return

        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        raw_news = []
        for _, vals_str in matches:
            for row in parse_sql_values(vals_str):
                raw_news.append(dict(zip(cols, row)))

        print(f"Parsed {len(raw_news)} records from tbl_news.")

        # Prepare records for insertion
        insert_query = """
        INSERT INTO news_masters (
            id, show_on_website, title, is_new, description,
            file, attachment_type, attachment_file, attachment_url,
            target_window, start_date, end_date, delete_bit,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        )
        ON DUPLICATE KEY UPDATE
            show_on_website = VALUES(show_on_website),
            title = VALUES(title),
            is_new = VALUES(is_new),
            description = VALUES(description),
            file = VALUES(file),
            attachment_type = VALUES(attachment_type),
            attachment_file = VALUES(attachment_file),
            attachment_url = VALUES(attachment_url),
            target_window = VALUES(target_window),
            start_date = VALUES(start_date),
            end_date = VALUES(end_date),
            delete_bit = VALUES(delete_bit),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at);
        """

        news_rows_to_insert = []
        migrated_news_ids = set()

        for item in raw_news:
            news_id = int(item["nws_id"])
            migrated_news_ids.add(news_id)

            title = (item.get("nws_title") or "").strip()
            # truncate title to 255 if necessary
            if len(title) > 250:
                title = title[:250]

            is_new = 1 if item.get("nws_new_flag") == "1" else 0
            show_on_website = 1
            delete_bit = 0  # Active / approved

            # Dates
            start_date = clean_date(item.get("nws_valid_from"))
            if not start_date:
                start_date = clean_date(item.get("nws_event_date")) or clean_date(item.get("nws_created_date"))

            end_date = clean_date(item.get("nws_valid_till"))

            created_date = item.get("nws_created_date") or item.get("nws_event_date")
            created_at = clean_timestamp(item.get("nws_valid_from"), fallback_date=created_date)
            updated_at = created_at

            # Attachment handling
            raw_link = (item.get("nws_link") or "").strip()
            cleaned_link = raw_link.replace("^%^path", "").strip()

            if cleaned_link.startswith("http://") or cleaned_link.startswith("https://"):
                att_type = "link"
                att_url = cleaned_link
                att_file = None
                file_col = cleaned_link
            elif cleaned_link != "":
                att_type = "file"
                att_url = None
                att_file = cleaned_link
                file_col = cleaned_link
            else:
                att_type = "file"
                att_url = None
                att_file = None
                file_col = None

            target = "_blank" if item.get("nws_target") == "new" else "_self"
            description = None

            news_rows_to_insert.append((
                news_id, show_on_website, title, is_new, description,
                file_col, att_type, att_file, att_url,
                target, start_date, end_date, delete_bit,
                created_at, updated_at
            ))

        print(f"Inserting {len(news_rows_to_insert)} records into news_masters...")
        # Batch execute
        batch_size = 100
        for i in range(0, len(news_rows_to_insert), batch_size):
            batch = news_rows_to_insert[i:i+batch_size]
            cur.executemany(insert_query, batch)
            conn.commit()
            print(f"  Inserted batch {i+1} to {min(i+batch_size, len(news_rows_to_insert))}")

        print("Finished migrating news_masters.")

        # ---------------------------------------------------------
        # Step 3: Parse and Migrate Category Mappings (tag_news_mappings)
        # ---------------------------------------------------------
        print("\n[Step 3] Migrating Category Linking (tag_news_mappings)...")
        cat_matches = re.findall(r"INSERT INTO `tbl_nws_category_linking`[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if cat_matches:
            c_cols = [c.strip(" `\r\n") for c in cat_matches[0][0].split(",")]
            cat_rows = []
            for _, vals_str in cat_matches:
                for row in parse_sql_values(vals_str):
                    cat_rows.append(dict(zip(c_cols, row)))

            print(f"Parsed {len(cat_rows)} rows from tbl_nws_category_linking.")

            tag_mapping_insert = """
            INSERT INTO tag_news_mappings (tag_id, news_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at);
            """

            # Deduplicate (tag_id, news_id)
            seen_pairs = set()
            tag_mappings_to_insert = []
            skipped_missing_news = 0

            for r in cat_rows:
                nws_id_str = r.get("tncl_nws_id")
                ci_cat_id = str(r.get("tncl_nws_category_id"))

                if not nws_id_str or not ci_cat_id:
                    continue

                news_id = int(nws_id_str)
                # Ensure the news exists in news_masters
                if news_id not in migrated_news_ids:
                    skipped_missing_news += 1
                    continue

                laravel_tag_id = tag_mapping.get(ci_cat_id)
                if not laravel_tag_id:
                    continue

                pair = (laravel_tag_id, news_id)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    tag_mappings_to_insert.append((laravel_tag_id, news_id, now_ts, now_ts))

            print(f"Valid unique tag mappings to insert: {len(tag_mappings_to_insert)} (Skipped orphan news: {skipped_missing_news})")

            # Check if tag_news_mappings has a unique constraint or if we should clear existing for these news
            cur.execute("DELETE FROM tag_news_mappings WHERE news_id IN (%s)" % ",".join(map(str, migrated_news_ids)))
            conn.commit()

            insert_simple = """
            INSERT INTO tag_news_mappings (tag_id, news_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            """
            for i in range(0, len(tag_mappings_to_insert), batch_size):
                batch = tag_mappings_to_insert[i:i+batch_size]
                cur.executemany(insert_simple, batch)
                conn.commit()

            print(f"Finished inserting {len(tag_mappings_to_insert)} records into tag_news_mappings.")

        # ---------------------------------------------------------
        # Step 4: Verification
        # ---------------------------------------------------------
        print("\n[Step 4] Verification:")
        cur.execute("SELECT COUNT(*) AS c FROM news_masters WHERE delete_bit = 0")
        print(f"  Total active news in news_masters: {cur.fetchone()['c']}")

        cur.execute("SELECT COUNT(*) AS c FROM tag_news_mappings")
        print(f"  Total tag mappings in tag_news_mappings: {cur.fetchone()['c']}")

        cur.execute("SELECT id, name FROM news_tag_masters")
        for tag in cur.fetchall():
            cur.execute("SELECT COUNT(*) as c FROM tag_news_mappings WHERE tag_id = %s", (tag["id"],))
            print(f"    Tag '{tag['name']}' (ID {tag['id']}): {cur.fetchone()['c']} mapped news")

        print("\n=== NEWS MODULE MIGRATION COMPLETE! ===")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate_news()

