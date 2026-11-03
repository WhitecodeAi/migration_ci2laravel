#!/usr/bin/env python3
"""
Migration Script: Faculty Research Papers & Publications (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_faculty_naac_info)
Target: u207346834_sathayelara (research_papers)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values

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


def to_int(val):
    if not val:
        return None
    val_str = str(val).strip()
    if val_str.isdigit():
        return int(val_str)
    return None


def migrate_research_papers():
    print("=" * 60)
    print("MIGRATING FACULTY RESEARCH PAPERS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    print(f"Reading SQL file: {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    m_papers = re.findall(
        r"INSERT INTO [`\x27]?tbl_faculty_naac_info[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_papers = []
    if m_papers:
        cols = [c.strip(" `\r\n") for c in m_papers[0][0].split(",")]
        for _, vals in m_papers:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_papers.append(dict(zip(cols, r)))

    print(f"Found {len(raw_papers)} research records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Check existing faculty IDs in faculties
            cur.execute("SELECT id FROM faculties")
            valid_faculty_ids = {r["id"] for r in cur.fetchall()}

            paper_sql = """
            INSERT INTO research_papers (
                id, title, journalname, issn_isbn_number, impact_factor,
                number_of_coauthors, is_main_author, published_on, ugc_care,
                is_conferance, faculty_id, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(title)s, %(journalname)s, %(issn_isbn_number)s, %(impact_factor)s,
                %(number_of_coauthors)s, %(is_main_author)s, %(published_on)s, NULL,
                %(is_conferance)s, %(faculty_id)s, %(delete_bit)s, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                journalname = VALUES(journalname),
                issn_isbn_number = VALUES(issn_isbn_number),
                impact_factor = VALUES(impact_factor),
                number_of_coauthors = VALUES(number_of_coauthors),
                is_main_author = VALUES(is_main_author),
                faculty_id = VALUES(faculty_id),
                delete_bit = VALUES(delete_bit),
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for p in raw_papers:
                p_id = int(p["tfni_id"])
                title = str(p.get("tfni_title") or "Research Paper").strip()[:250]
                journal = str(p.get("tfni_journals") or "").strip()[:250] or None
                issn = str(p.get("tfni_issn_no") or "").strip()[:250] or None
                impact = to_int(p.get("tfni_impac_factor"))
                co_authors = to_int(p.get("tfni_co_authors"))
                main_author = str(p.get("tfni_author") or "").strip()[:250] or None
                is_conf = 1 if p.get("tfni_details_conference_publication") else 0
                del_bit = 1 if str(p.get("tfni_delete_bit")) == "1" else 0

                fac_id = to_int(p.get("tfni_faculty_id"))
                if fac_id not in valid_faculty_ids:
                    fac_id = None

                cur.execute(paper_sql, {
                    "id": p_id,
                    "title": title,
                    "journalname": journal,
                    "issn_isbn_number": issn,
                    "impact_factor": impact,
                    "number_of_coauthors": co_authors,
                    "is_main_author": main_author,
                    "published_on": None,
                    "is_conferance": is_conf,
                    "faculty_id": fac_id,
                    "delete_bit": del_bit,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} papers into research_papers.")

            cur.execute("SELECT COUNT(*) as c FROM research_papers WHERE delete_bit = 0")
            print(f"Active research papers in DB: {cur.fetchone()['c']}")

    finally:
        conn.close()

    print("\nFaculty Research Papers Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_research_papers()

