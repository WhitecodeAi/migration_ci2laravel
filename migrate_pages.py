#!/usr/bin/env python3
"""
Migration Script: Master CMS Pages Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_master_pages)
Target: u207346834_mnwc (pages)
"""

import os
import sys
import re
import json
import uuid
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date


def slugify(text):
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text or "page"


def migrate_pages():
    print("=" * 60)
    print("MIGRATING CMS MASTER PAGES: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    matches = re.findall(
        r"INSERT INTO [`\x27]?tbl_master_pages[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_rows = []
    if matches:
        cols = [c.strip(" `\r\n") for c in matches[0][0].split(",")]
        for _, vals in matches:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_rows.append(dict(zip(cols, r)))

    print(f"Found {len(raw_rows)} CMS page record(s) in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Check existing slugs
            cur.execute("SELECT id, slug FROM pages")
            existing_slugs = {row["slug"]: row["id"] for row in cur.fetchall()}

            insert_query = """
            INSERT INTO pages (
                id, title, seo_title, slug, content,
                meta_tag, meta_description, show_header, show_footer,
                show_breadcrumb, is_external, external_link, delete_bit,
                is_system, created_at, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(seo_title)s, %(slug)s, %(content)s,
                %(meta_tag)s, %(meta_description)s, %(show_header)s, %(show_footer)s,
                %(show_breadcrumb)s, %(is_external)s, %(external_link)s, %(delete_bit)s,
                %(is_system)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                seo_title = VALUES(seo_title),
                slug = VALUES(slug),
                content = VALUES(content),
                meta_tag = VALUES(meta_tag),
                meta_description = VALUES(meta_description),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            migrated = 0
            for r in raw_rows:
                p_id = int(r["tmp_id"])
                title = str(r.get("tmp_pane_name") or r.get("tmp_page_title") or f"Page {p_id}").strip()
                seo_title = str(r.get("tmp_page_title") or title).strip()

                base_slug = slugify(title)
                slug = base_slug
                suffix = 1
                while slug in existing_slugs and existing_slugs[slug] != p_id:
                    slug = f"{base_slug}-{suffix}"
                    suffix += 1
                existing_slugs[slug] = p_id

                # Content formatting for JSON check
                raw_content = str(r.get("tmp_new_page_content") or r.get("tmp_page_content") or "").strip()
                raw_content = raw_content.replace(r'\"', '"').replace(r"\'", "'").replace(r'\r\n', '\n').replace(r'\n', '\n').replace(r'\t', '\t')
                is_valid_json = False
                if raw_content.startswith("{") or raw_content.startswith("["):
                    try:
                        json.loads(raw_content)
                        is_valid_json = True
                        content_json = raw_content
                    except Exception:
                        pass
                if not is_valid_json:
                    block_id = f"Code Editer-{uuid.uuid4()}"
                    content_json = json.dumps({
                        "content": [
                            {
                                "type": "Code Editer",
                                "props": {
                                    "CodeEditer": raw_content,
                                    "id": block_id
                                }
                            }
                        ],
                        "root": {
                            "props": {
                                "title": title,
                                "showHeader": 1,
                                "showFooter": 1,
                                "showBreadcrumb": 1
                            }
                        },
                        "zones": []
                    })

                meta_tag = str(r.get("tmp_meta_title") or r.get("tmp_meta_keywords") or "").strip() or None
                meta_desc = str(r.get("tmp_meta_description") or "").strip() or None
                link = str(r.get("tmp_menu_link") or "").strip() or None
                is_ext = "1" if link and (link.startswith("http://") or link.startswith("https://")) else "0"
                c_date = clean_date(r.get("tmp_added_date")) or now_ts

                cur.execute(insert_query, {
                    "id": p_id,
                    "title": title[:255],
                    "seo_title": seo_title[:255],
                    "slug": slug,
                    "content": content_json,
                    "meta_tag": meta_tag,
                    "meta_description": meta_desc,
                    "show_header": 1,
                    "show_footer": 1,
                    "show_breadcrumb": 1,
                    "is_external": is_ext,
                    "external_link": link,
                    "delete_bit": "0",
                    "is_system": 0,
                    "created_at": c_date,
                    "updated_at": now_ts
                })
                migrated += 1

            conn.commit()
            print(f"Successfully migrated {migrated} CMS page(s).")

            cur.execute("SELECT COUNT(*) AS c FROM pages WHERE delete_bit = '0'")
            print(f"Total active pages count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== CMS MASTER PAGES MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_pages()

