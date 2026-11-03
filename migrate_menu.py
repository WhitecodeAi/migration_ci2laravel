#!/usr/bin/env python3
"""
Migration Script: Website Navigation Menu Hierarchy (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_manage_menu, tbl_master_pages)
Target: u207346834_sathayelara (navigations, page_navigation_mappings, pages)
"""

import sys
import os
import re
import json
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
    return text or "menu-item"


def migrate_menus():
    print("=" * 60)
    print("MIGRATING WEBSITE NAVIGATION MENUS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Parse tbl_master_pages for metadata (custom links, targets, etc.)
    m_pages = re.findall(r"INSERT INTO [`\x27]?tbl_master_pages[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
    cols = [c.strip(" `\r\n") for c in m_pages[0][0].split(",")]
    ci_pages_by_id = {}
    for _, vals in m_pages:
        for r in parse_sql_values(vals):
            d = dict(zip(cols, r))
            ci_pages_by_id[int(d["tmp_id"])] = d

    # 2. Parse tbl_manage_menu
    m_menu = re.findall(r"INSERT INTO [`\x27]?tbl_manage_menu[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
    m_cols = [c.strip(" `\r\n") for c in m_menu[0][0].split(",")]
    ci_menus = {}
    for _, vals in m_menu:
        for r in parse_sql_values(vals):
            d = dict(zip(m_cols, r))
            ci_menus[d["mm_menu_type"]] = json.loads(d["mm_parent_id"])

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 3. Load or create Navigations (1: Main Menu, 2: Top Menu)
            nav_map = {}
            for nav_id, nav_name in [(1, "Main Menu"), (2, "Top Menu")]:
                cur.execute("SELECT id FROM navigations WHERE id = %s", (nav_id,))
                row = cur.fetchone()
                if row:
                    nav_map[nav_name] = row["id"]
                else:
                    cur.execute("""
                    INSERT INTO navigations (id, name, delete_bit, created_at, updated_at)
                    VALUES (%s, %s, 0, %s, %s)
                    """, (nav_id, nav_name, now_ts, now_ts))
                    nav_map[nav_name] = nav_id
            conn.commit()

            # 4. Load all pages from DB
            cur.execute("SELECT id, LOWER(TRIM(title)) as title_key, slug FROM pages WHERE delete_bit = '0' OR delete_bit = 0")
            db_pages = cur.fetchall()
            page_by_title = {p["title_key"]: p for p in db_pages}
            page_by_id = {p["id"]: p for p in db_pages}
            existing_slugs = {p["slug"] for p in db_pages if p.get("slug")}

            def get_or_create_page(ci_id, item_title):
                item_title_clean = item_title.strip()
                t_key = item_title_clean.lower()
                if t_key in page_by_title:
                    return page_by_title[t_key]["id"]

                # Check if ci_id exists in ci_pages_by_id
                ci_meta = ci_pages_by_id.get(ci_id, {})
                page_type = ci_meta.get("tmp_page_type", "")
                menu_link = ci_meta.get("tmp_menu_link", "")

                is_ext = '1' if page_type == 'custom_link' or menu_link.startswith('http') or menu_link == '#' else '0'
                ext_link = menu_link if is_ext == '1' else None
                ext_target = 1 if ci_meta.get("tmp_menu_target") == '_blank' else 0

                # Generate unique slug
                base_slug = slugify(item_title_clean)
                cand_slug = base_slug
                suf = 1
                while cand_slug in existing_slugs:
                    cand_slug = f"{base_slug}-{suf}"
                    suf += 1
                existing_slugs.add(cand_slug)

                # Insert placeholder/link page
                cur.execute("""
                INSERT INTO pages (
                    title, seo_title, slug, content, meta_tag, meta_description,
                    breadcrumb_image, show_header, show_footer, show_breadcrumb,
                    is_external, external_link, external_link_target, delete_bit,
                    is_system, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, NULL, NULL, NULL,
                    NULL, 1, 1, 1,
                    %s, %s, %s, '0',
                    0, %s, %s
                )
                """, (item_title_clean, item_title_clean, cand_slug, is_ext, ext_link, ext_target, now_ts, now_ts))
                new_pid = cur.lastrowid
                p_obj = {"id": new_pid, "title_key": t_key, "slug": cand_slug}
                page_by_title[t_key] = p_obj
                page_by_id[new_pid] = p_obj
                return new_pid

            # 5. Clear old navigation mappings for fresh sync
            print("Clearing old page navigation mappings...")
            cur.execute("DELETE FROM page_navigation_mappings WHERE navigation_id IN (1, 2)")
            conn.commit()

            insert_mapping_sql = """
            INSERT INTO page_navigation_mappings (
                page_id, navigation_id, level, parent_id, page_nav_id,
                has_mega_menu, display_mode, mega_menu_rows, created_at, updated_at
            ) VALUES (
                %(page_id)s, %(navigation_id)s, %(level)s, %(parent_id)s, %(page_nav_id)s,
                0, NULL, NULL, %(created_at)s, %(updated_at)s
            )
            """

            total_migrated = 0

            def insert_menu_tree(items, nav_id, parent_page_id=0, parent_map_id=0, level=0):
                nonlocal total_migrated
                for item in items:
                    raw_id = int(item.get("id") or 0)
                    title = str(item.get("type") or "").strip()
                    if not title:
                        continue

                    page_id = get_or_create_page(raw_id, title)

                    cur.execute(insert_mapping_sql, {
                        "page_id": page_id,
                        "navigation_id": nav_id,
                        "level": level,
                        "parent_id": parent_page_id,
                        "page_nav_id": parent_map_id,
                        "created_at": now_ts,
                        "updated_at": now_ts
                    })
                    current_map_id = cur.lastrowid
                    total_migrated += 1

                    if "children" in item and item["children"]:
                        insert_menu_tree(
                            item["children"],
                            nav_id,
                            parent_page_id=page_id,
                            parent_map_id=current_map_id,
                            level=level + 1
                        )

            # Insert Main Menu (navigation_id = 1)
            print("\nMigrating Main Menu hierarchy...")
            main_menu_items = ci_menus.get("main-menu", [])
            insert_menu_tree(main_menu_items, nav_id=1, parent_page_id=0, parent_map_id=0, level=0)
            conn.commit()
            print(f"Main Menu migrated ({len(main_menu_items)} top-level sections).")

            # Insert Top Menu (navigation_id = 2)
            print("\nMigrating Top Menu hierarchy...")
            top_menu_items = ci_menus.get("top-menu", [])
            insert_menu_tree(top_menu_items, nav_id=2, parent_page_id=0, parent_map_id=0, level=0)
            conn.commit()
            print(f"Top Menu migrated ({len(top_menu_items)} top-level items).")

            print(f"\nSuccessfully migrated {total_migrated} total menu mappings!")

            # Verification
            cur.execute("""
            SELECT n.name as nav_name, m.level, COUNT(m.id) as count
            FROM page_navigation_mappings m
            JOIN navigations n ON m.navigation_id = n.id
            GROUP BY n.id, n.name, m.level
            ORDER BY n.id, m.level
            """)
            print("\nMenu Levels Summary:")
            for r in cur.fetchall():
                lvl_str = "Top-level" if r["level"] == 0 else f"Sub-level {r['level']}"
                print(f"  [{r['nav_name']}] {lvl_str}: {r['count']} items")

            cur.execute("""
            SELECT m.id, n.name as nav_name, p.title, m.level
            FROM page_navigation_mappings m
            JOIN navigations n ON m.navigation_id = n.id
            JOIN pages p ON m.page_id = p.id
            WHERE m.level = 0
            ORDER BY n.id, m.id
            """)
            print("\nTop-Level Navigation Items:")
            for r in cur.fetchall():
                print(f"  [{r['nav_name']}] {r['title']}")

    finally:
        conn.close()

    print("\nNavigation Menus Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_menus()
