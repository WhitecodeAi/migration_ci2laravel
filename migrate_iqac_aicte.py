#!/usr/bin/env python3
"""
Migration Script: IQAC & AICTE Streams Module (CodeIgniter -> Laravel)
Source: mnwc_db.sql (tbl_iqac_stream_linking, tbl_aict_stream_linking)
Target: u207346834_mnwc (iqacs, aictes)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date


def migrate_iqac_aicte():
    print("=" * 60)
    print("MIGRATING IQAC & AICTE STREAMS: CodeIgniter -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. IQAC
    m_iqac = re.findall(
        r"INSERT INTO [`\x27]?tbl_iqac_stream_linking[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_iqac = []
    if m_iqac:
        cols = [c.strip(" `\r\n") for c in m_iqac[0][0].split(",")]
        for _, vals in m_iqac:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_iqac.append(dict(zip(cols, r)))

    # 2. AICTE
    m_aicte = re.findall(
        r"INSERT INTO [`\x27]?tbl_aict_stream_linking[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
        sql,
        re.DOTALL
    )
    raw_aicte = []
    if m_aicte:
        cols = [c.strip(" `\r\n") for c in m_aicte[0][0].split(",")]
        for _, vals in m_aicte:
            for r in parse_sql_values(vals):
                if len(r) == len(cols):
                    raw_aicte.append(dict(zip(cols, r)))

    print(f"Found {len(raw_iqac)} IQAC record(s) and {len(raw_aicte)} AICTE record(s).")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS iqacs (
                    id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                    college_id bigint(20) DEFAULT 1,
                    stream_id bigint(20) DEFAULT NULL,
                    name varchar(255) DEFAULT NULL,
                    delete_bit tinyint(4) DEFAULT 0,
                    created_at timestamp NULL DEFAULT NULL,
                    updated_at timestamp NULL DEFAULT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS aictes (
                    id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                    college_id bigint(20) DEFAULT 1,
                    stream_id bigint(20) DEFAULT NULL,
                    name varchar(255) DEFAULT NULL,
                    delete_bit tinyint(4) DEFAULT 0,
                    created_at timestamp NULL DEFAULT NULL,
                    updated_at timestamp NULL DEFAULT NULL,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # IQAC
            for r in raw_iqac:
                iqac_id = int(r["til_id"])
                name = str(r.get("til_name") or "IQAC").strip()
                c_date = clean_date(r.get("til_created_date")) or now_ts
                del_bit = 1 if str(r.get("delete_bit")) == "1" else 0

                cur.execute("""
                INSERT INTO iqacs (
                    id, college_id, stream_id, name, delete_bit, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    college_id = VALUES(college_id),
                    stream_id = VALUES(stream_id),
                    name = VALUES(name),
                    delete_bit = VALUES(delete_bit),
                    updated_at = VALUES(updated_at)
                """, (
                    iqac_id,
                    1,
                    None,
                    name,
                    del_bit,
                    c_date,
                    now_ts
                ))

            # AICTE
            for r in raw_aicte:
                aicte_id = int(r["tal_id"])
                name = str(r.get("tal_name") or "AICTE").strip()
                c_date = clean_date(r.get("tal_created_date")) or now_ts
                del_bit = 1 if str(r.get("delete_bit")) == "1" else 0

                cur.execute("""
                INSERT INTO aictes (
                    id, college_id, stream_id, name, delete_bit, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    college_id = VALUES(college_id),
                    stream_id = VALUES(stream_id),
                    name = VALUES(name),
                    delete_bit = VALUES(delete_bit),
                    updated_at = VALUES(updated_at)
                """, (
                    aicte_id,
                    1,
                    None,
                    name,
                    del_bit,
                    c_date,
                    now_ts
                ))

            conn.commit()
            print(f"Successfully migrated {len(raw_iqac)} IQAC and {len(raw_aicte)} AICTE records.")

            cur.execute("SELECT COUNT(*) AS c FROM iqacs")
            print(f"Total active iqacs count: {cur.fetchone()['c']}")
            cur.execute("SELECT COUNT(*) AS c FROM aictes")
            print(f"Total active aictes count: {cur.fetchone()['c']}")
    finally:
        conn.close()

    print("\n=== IQAC & AICTE MIGRATION COMPLETE! ===")


if __name__ == "__main__":
    migrate_iqac_aicte()

