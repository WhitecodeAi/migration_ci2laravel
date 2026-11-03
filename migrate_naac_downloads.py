#!/usr/bin/env python3
"""
Migration Script: NAAC & AQAR Documentation Downloads (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_naac_docs_info, tbl_naac_year, tbl_naac_year_doc_type_linking, tbl_doc_type_master)
Target: u207346834_sathayelara (downloads)
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


def get_filename_title(path_str, criteria_str):
    if path_str:
        base = os.path.basename(path_str)
        # remove extension
        name, _ = os.path.splitext(base)
        name = name.replace("-", " ").replace("_", " ").strip()
        if len(name) > 3:
            return name.title()
    return f"Criterion {criteria_str} Supporting Document"


def migrate_naac_downloads():
    print("=" * 60)
    print("MIGRATING NAAC & AQAR DOWNLOADS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_table_data(tbl_name):
        m = re.findall(r"INSERT INTO [`\x27]?" + tbl_name + r"[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n", sql, re.DOTALL)
        if not m:
            return []
        cols = [c.strip(" `\r\n") for c in m[0][0].split(",")]
        rows = []
        for _, vals in m:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    rows.append(dict(zip(cols, r)))
        return rows

    naac_years = {r["ny_id"]: r["ny_year"] for r in get_table_data("tbl_naac_year")}
    doc_types = {r["dtm_id"]: r["dtm_type"] for r in get_table_data("tbl_doc_type_master")}
    links = {r["nydtl_id"]: (naac_years.get(r["nydtl_ny_id"]), doc_types.get(r["nydtl_dtm_id"])) for r in get_table_data("tbl_naac_year_doc_type_linking")}

    raw_docs = get_table_data("tbl_naac_docs_info")
    print(f"Found {len(raw_docs)} NAAC document records.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            download_sql = """
            INSERT INTO downloads (
                id, title, source, academic_year, document_added_in, category,
                department_id, department_tab, show_on_website, ordering,
                delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(source)s, %(academic_year)s, %(document_added_in)s, %(category)s,
                NULL, NULL, 1, 0,
                0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                source = VALUES(source),
                academic_year = VALUES(academic_year),
                document_added_in = VALUES(document_added_in),
                category = VALUES(category),
                show_on_website = 1,
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for d in raw_docs:
                d_id = int(d["ndi_id"])
                path = clean_path(d.get("ndi_pdf_path"))
                if not path:
                    continue

                c_crit = d.get("ndi_criteria")
                c_ki = d.get("ndi_key_indicator")
                c_m = d.get("ndi_metric")
                criteria_str = f"{c_crit}.{c_ki}.{c_m}"

                title = str(d.get("ndi_pdf_name") or "").strip()
                if not title:
                    title = get_filename_title(path, criteria_str)

                linked = links.get(d.get("ndi_nydtl_id"), (None, None))
                ay_year = linked[0] or "2023-24"
                doc_type_name = linked[1] or "NAAC"

                doc_added_in = "NAAC"
                if "aqar" in str(doc_type_name).lower():
                    doc_added_in = "AQAR"

                category_name = f"Criterion {c_crit}" if c_crit else "Supporting Documents"
                created_at = clean_date(d.get("ndi_added_date")) or now_ts

                cur.execute(download_sql, {
                    "id": d_id,
                    "title": title[:250],
                    "source": path,
                    "academic_year": str(ay_year),
                    "document_added_in": doc_added_in,
                    "category": category_name,
                    "created_at": created_at,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} documents into downloads.")

            # Verification
            cur.execute("SELECT COUNT(*) AS c FROM downloads WHERE delete_bit = 0")
            print(f"\nTotal active downloads in database: {cur.fetchone()['c']}")

            cur.execute("""
            SELECT id, title, academic_year, document_added_in, category, source
            FROM downloads
            WHERE delete_bit = 0
            ORDER BY id ASC
            LIMIT 5
            """)
            print("Sample Download Records:")
            for r in cur.fetchall():
                print(" ", r)

    finally:
        conn.close()

    print("\nNAAC & AQAR Downloads Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_naac_downloads()
