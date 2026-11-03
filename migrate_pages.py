#!/usr/bin/env python3
"""
Migration Script: Master Pages & Rich HTML Content (CodeIgniter -> Laravel Puck)
Source: u208972730_scnewcms.sql (tbl_master_pages)
Target: u207346834_sathayelara (pages)
"""

import sys
import os
import re
import json
import uuid
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


def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "page"


def format_puck_content(html_content):
    block_id = f"RichTextBlock-{uuid.uuid4()}"
    puck_obj = {
        "content": [
            {
                "type": "RichTextBlock",
                "props": {
                    "id": block_id,
                    "content": html_content,
                    "richTextConfig": {
                        "content": html_content
                    }
                }
            }
        ],
        "root": {
            "props": {
                "title": None
            }
        },
        "zones": []
    }
    return json.dumps(puck_obj, ensure_ascii=False)


def migrate_pages():
    print("=" * 60)
    print("MIGRATING MASTER PAGES & CONTENT: CodeIgniter -> Laravel Puck")
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
            # 1. Load existing pages in Laravel
            cur.execute("SELECT id, LOWER(TRIM(title)) as title_key, slug, content FROM pages WHERE delete_bit = '0' OR delete_bit = 0")
            existing_pages = cur.fetchall()
            title_to_page = {p["title_key"]: p for p in existing_pages}
            slug_to_page = {p["slug"]: p for p in existing_pages if p.get("slug")}
            print(f"Found {len(existing_pages)} existing pages in target database.")

            # 2. Extract tbl_master_pages
            m_pages = re.findall(
                r"INSERT INTO [`\x27]?tbl_master_pages[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_pages = []
            if m_pages:
                cols = [c.strip(" `\r\n") for c in m_pages[0][0].split(",")]
                for _, vals in m_pages:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_pages.append(dict(zip(cols, r)))

            print(f"Found {len(raw_pages)} pages in source dump.")

            update_sql = """
            UPDATE pages
            SET content = %(content)s,
                seo_title = COALESCE(seo_title, %(seo_title)s),
                meta_tag = COALESCE(meta_tag, %(meta_tag)s),
                meta_description = COALESCE(meta_description, %(meta_description)s),
                updated_at = %(updated_at)s
            WHERE id = %(id)s
            """

            insert_sql = """
            INSERT INTO pages (
                title, seo_title, slug, content, meta_tag, meta_description,
                breadcrumb_image, show_header, show_footer, show_breadcrumb,
                is_external, external_link, external_link_target, delete_bit,
                is_system, created_at, updated_at
            ) VALUES (
                %(title)s, %(seo_title)s, %(slug)s, %(content)s, %(meta_tag)s, %(meta_description)s,
                NULL, 1, 1, 1,
                '0', NULL, 0, '0',
                0, %(created_at)s, %(updated_at)s
            )
            """

            updated_count = 0
            inserted_count = 0

            for p in raw_pages:
                title = str(p.get("tmp_pane_name") or p.get("tmp_page_title") or "").strip()
                if not title:
                    continue

                raw_html = str(p.get("tmp_new_page_content") or p.get("tmp_page_content") or "").strip()
                if not raw_html:
                    continue

                puck_json = format_puck_content(raw_html)
                seo_title = str(p.get("tmp_meta_title") or title).strip() or None
                meta_desc = str(p.get("tmp_meta_description") or "").strip() or None
                meta_keywords = str(p.get("tmp_meta_keywords") or "").strip() or None
                created_at = clean_date(p.get("tmp_added_date")) or now_ts

                title_key = title.lower()
                target_page = title_to_page.get(title_key)
                if not target_page:
                    base_slug = slugify(title)
                    target_page = slug_to_page.get(base_slug)

                if target_page:
                    # Update existing page
                    cur.execute(update_sql, {
                        "id": target_page["id"],
                        "content": puck_json,
                        "seo_title": seo_title,
                        "meta_tag": meta_keywords,
                        "meta_description": meta_desc,
                        "updated_at": now_ts
                    })
                    updated_count += 1
                else:
                    # Insert new page
                    page_slug = slugify(title)
                    slug_cand = page_slug
                    suffix = 1
                    while slug_cand in slug_to_page:
                        slug_cand = f"{page_slug}-{suffix}"
                        suffix += 1
                    page_slug = slug_cand

                    cur.execute(insert_sql, {
                        "title": title,
                        "seo_title": seo_title,
                        "slug": page_slug,
                        "content": puck_json,
                        "meta_tag": meta_keywords,
                        "meta_description": meta_desc,
                        "created_at": created_at,
                        "updated_at": now_ts
                    })
                    new_id = cur.lastrowid
                    slug_to_page[page_slug] = {"id": new_id, "slug": page_slug}
                    title_to_page[title_key] = {"id": new_id, "title_key": title_key}
                    inserted_count += 1

            conn.commit()
            print(f"\nMigration Results:")
            print(f"  Existing Pages Updated with Rich Content: {updated_count}")
            print(f"  New Pages Created: {inserted_count}")

            # Verification
            cur.execute("SELECT COUNT(*) AS total_pages FROM pages WHERE delete_bit = '0' OR delete_bit = 0")
            print(f"  Total Active Pages in DB: {cur.fetchone()['total_pages']}")
            cur.execute("SELECT COUNT(*) AS pages_with_content FROM pages WHERE (delete_bit = '0' OR delete_bit = 0) AND content IS NOT NULL AND LENGTH(content) > 100")
            print(f"  Pages with Rich Content (>100 chars): {cur.fetchone()['pages_with_content']}")

            cur.execute("""
            SELECT id, title, slug, LENGTH(content) as content_len
            FROM pages
            WHERE (delete_bit = '0' OR delete_bit = 0) AND content IS NOT NULL AND LENGTH(content) > 1000
            ORDER BY LENGTH(content) DESC
            LIMIT 10
            """)
            print("\nSample Top Rich Content Pages:")
            for r in cur.fetchall():
                print(f"  ID: {r['id']:3d} | {r['title'][:35]:35s} | Slug: {r['slug'][:25]:25s} | Content: {r['content_len']} bytes")

    finally:
        conn.close()

    print("\nMaster Pages Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_pages()
