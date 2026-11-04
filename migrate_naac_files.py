#!/usr/bin/env python3
"""
Migration Script: NAAC, Accreditation & Media File Manager Module
Source: u486681144_st_miraclg_liv.sql
  - tbl_file_manager (3,032 rows)
  - tbl_naac_year (4 rows)
  - tbl_ssr_year (2 rows)
  - tbl_naac_docs_info (5 rows)
  - tbl_faculty_naac_info (6 rows)
  - tbl_faculty_section_docs (5 rows)
Target: u207346834_stmiracollege
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values, clean_date, clean_path


def clean_val(v):
    if v is None or str(v).strip() in ("None", "NULL", ""):
        return None
    return str(v).strip()


def migrate_naac_files():
    print("=" * 60)
    print("MIGRATING NAAC, ACCREDITATION & MEDIA FILES: CI -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = pymysql.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:
            # ---------------------------------------------------------
            # 1. Media Files (tbl_file_manager -> files & tbl_file_manager)
            # ---------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_file_manager (
                    fm_id int NOT NULL,
                    fm_name varchar(255) DEFAULT NULL,
                    fm_path text NOT NULL,
                    fm_size varchar(100) DEFAULT NULL,
                    fm_type varchar(100) DEFAULT NULL,
                    fm_user_id int DEFAULT NULL,
                    fm_created_date timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    approve_bit int DEFAULT '0',
                    rejected_reason text,
                    PRIMARY KEY (fm_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Ensure default folder exists in folders table
            cur.execute("""
                INSERT INTO folders (id, name, parent_id, created_at, updated_at)
                VALUES (1, 'Uploads', NULL, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """, (now_ts, now_ts))
            conn.commit()

            m_fm = re.findall(r"INSERT INTO [`\x27]?tbl_file_manager[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            fm_count = 0
            if m_fm:
                cols_fm = [c.strip(" `\r\n") for c in m_fm[0][0].split(",")]
                raw_fm = []
                files_batch = []
                for _, vals in m_fm:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_fm, r))
                        fid = int(d["fm_id"])
                        fname = clean_val(d.get("fm_name") or f"file_{fid}")
                        fpath = clean_path(d.get("fm_path") or "")
                        fsize = clean_val(d.get("fm_size"))
                        ftype = clean_val(d.get("fm_type"))
                        fuser = int(d["fm_user_id"]) if d.get("fm_user_id") and str(d["fm_user_id"]).isdigit() else None
                        fdate = clean_date(d.get("fm_created_date")) or now_ts

                        raw_fm.append((fid, fname, fpath or "", fsize, ftype, fuser, fdate, int(d.get("approve_bit") or 0), clean_val(d.get("rejected_reason"))))
                        files_batch.append((fid, fname[:250], 1, fpath[:250] if fpath else "", fdate, fdate))

                # Insert into tbl_file_manager in chunks of 500
                insert_fm_query = """
                    INSERT INTO tbl_file_manager (fm_id, fm_name, fm_path, fm_size, fm_type, fm_user_id, fm_created_date, approve_bit, rejected_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE fm_name = VALUES(fm_name), fm_path = VALUES(fm_path)
                """
                insert_files_query = """
                    INSERT INTO files (id, name, folder_id, url, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name = VALUES(name), url = VALUES(url)
                """

                chunk_size = 500
                for i in range(0, len(raw_fm), chunk_size):
                    cur.executemany(insert_fm_query, raw_fm[i:i + chunk_size])
                    cur.executemany(insert_files_query, files_batch[i:i + chunk_size])
                    conn.commit()
                fm_count = len(raw_fm)

            print(f"Migrated {fm_count} media files into files & tbl_file_manager.")

            # ---------------------------------------------------------
            # 2. NAAC Mappings (tbl_naac_year & tbl_ssr_year -> naac_mappings)
            # ---------------------------------------------------------
            # Ensure NAAC lookup exists in lookups
            cur.execute("SELECT id FROM lookups WHERE `key` = 'naac' LIMIT 1")
            lookup_row = cur.fetchone()
            if lookup_row:
                naac_lookup_id = lookup_row["id"]
            else:
                cur.execute("INSERT INTO lookups (`key`, value, delete_bit, created_at, updated_at) VALUES ('naac', 'NAAC Accreditation', 0, %s, %s)", (now_ts, now_ts))
                naac_lookup_id = cur.lastrowid
            conn.commit()

            cur.execute("SELECT id FROM academic_years")
            ay_ids = [r["id"] for r in cur.fetchall()]
            default_ay_id = ay_ids[0] if ay_ids else 1

            m_ny = re.findall(r"INSERT INTO [`\x27]?tbl_naac_year[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            naac_mappings_created = {}
            if m_ny:
                cols_ny = [c.strip(" `\r\n") for c in m_ny[0][0].split(",")]
                for _, vals in m_ny:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_ny, r))
                        ny_id = int(d["ny_id"])
                        ny_year = clean_val(d.get("ny_year") or "2024-25")
                        del_bit = int(d.get("delete_bit") or 0)

                        cur.execute("""
                            INSERT INTO naac_mappings (id, naac_id, academic_year_id_start, academic_year_id_end, cycle, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, 'Cycle 4', %s, %s, %s)
                            ON DUPLICATE KEY UPDATE cycle = VALUES(cycle), delete_bit = VALUES(delete_bit)
                        """, (ny_id, naac_lookup_id, default_ay_id, default_ay_id, del_bit, now_ts, now_ts))
                        naac_mappings_created[ny_id] = ny_id
                conn.commit()

            m_sy = re.findall(r"INSERT INTO [`\x27]?tbl_ssr_year[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            if m_sy:
                cols_sy = [c.strip(" `\r\n") for c in m_sy[0][0].split(",")]
                for _, vals in m_sy:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_sy, r))
                        sy_id = int(d["sy_id"]) + 100  # Offset to avoid conflict with ny_id
                        cycle = clean_val(d.get("sy_cycle") or "Cycle 3")
                        cur.execute("""
                            INSERT INTO naac_mappings (id, naac_id, academic_year_id_start, academic_year_id_end, cycle, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s)
                            ON DUPLICATE KEY UPDATE cycle = VALUES(cycle)
                        """, (sy_id, naac_lookup_id, default_ay_id, default_ay_id, cycle, now_ts, now_ts))
                conn.commit()

            print(f"Migrated NAAC & SSR cycles into naac_mappings.")

            # ---------------------------------------------------------
            # 3. NAAC Documents (tbl_naac_docs_info -> naac_doc_infos)
            # ---------------------------------------------------------
            cur.execute("SELECT id FROM criterias")
            crit_ids = [r["id"] for r in cur.fetchall()]
            default_crit_id = crit_ids[0] if crit_ids else 1

            cur.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1")
            user_row = cur.fetchone()
            default_user_id = user_row["id"] if user_row else 1

            m_ndi = re.findall(r"INSERT INTO [`\x27]?tbl_naac_docs_info[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            ndi_count = 0
            if m_ndi:
                cols_ndi = [c.strip(" `\r\n") for c in m_ndi[0][0].split(",")]
                # Load valid naac_mapping ids
                cur.execute("SELECT id FROM naac_mappings")
                valid_naac_ids = {r["id"] for r in cur.fetchall()}
                first_naac_id = list(valid_naac_ids)[0] if valid_naac_ids else 1

                for _, vals in m_ndi:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_ndi, r))
                        doc_id = int(d["ndi_id"])
                        nydtl_id = int(d.get("ndi_nydtl_id") or 0)
                        target_naac_id = nydtl_id if nydtl_id in valid_naac_ids else first_naac_id
                        pdf_path = clean_path(d.get("ndi_pdf_path"))
                        del_bit = int(d.get("delete_bit") or 0)

                        cur.execute("""
                            INSERT INTO naac_doc_infos (
                                id, naac_mapping_id, metric_id, type, doc_path,
                                user_id, is_approved, is_deleted, created_at, updated_at
                            ) VALUES (%s, %s, %s, 'document', %s, %s, 1, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE doc_path = VALUES(doc_path), is_deleted = VALUES(is_deleted)
                        """, (doc_id, target_naac_id, default_crit_id, pdf_path, default_user_id, del_bit, now_ts, now_ts))
                        ndi_count += 1
                conn.commit()
            print(f"Migrated {ndi_count} NAAC document(s) into naac_doc_infos.")

            # ---------------------------------------------------------
            # 4. Faculty NAAC Research Records
            # ---------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_faculty_naac_info (
                    tfni_id int NOT NULL,
                    tfni_faculty_id int DEFAULT NULL,
                    tfni_title varchar(500) DEFAULT NULL,
                    tfni_issn_no varchar(100) DEFAULT NULL,
                    tfni_co_authors text,
                    tfni_author varchar(255) DEFAULT NULL,
                    tfni_period varchar(100) DEFAULT NULL,
                    tfni_impac_factor varchar(100) DEFAULT NULL,
                    tfni_journals text,
                    tfni_agency varchar(255) DEFAULT NULL,
                    tfni_thesis text,
                    tfni_grant_amt varchar(100) DEFAULT NULL,
                    tfni_delete_bit int DEFAULT '0',
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tfni_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            m_fni = re.findall(r"INSERT INTO [`\x27]?tbl_faculty_naac_info[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            fni_count = 0
            if m_fni:
                cols_fni = [c.strip(" `\r\n") for c in m_fni[0][0].split(",")]
                for _, vals in m_fni:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_fni, r))
                        fid = int(d["tfni_id"])
                        fac_user_id = int(d["tfni_faculty_id"]) if d.get("tfni_faculty_id") and str(d["tfni_faculty_id"]).isdigit() else None
                        cur.execute("""
                            INSERT INTO tbl_faculty_naac_info (
                                tfni_id, tfni_faculty_id, tfni_title, tfni_issn_no, tfni_co_authors,
                                tfni_author, tfni_period, tfni_impac_factor, tfni_journals, tfni_agency,
                                tfni_thesis, tfni_grant_amt, tfni_delete_bit, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE tfni_title = VALUES(tfni_title)
                        """, (
                            fid, fac_user_id, clean_val(d.get("tfni_title")), clean_val(d.get("tfni_issn_no")),
                            clean_val(d.get("tfni_co_authors")), clean_val(d.get("tfni_author")), clean_val(d.get("tfni_period")),
                            clean_val(d.get("tfni_impac_factor")), clean_val(d.get("tfni_journals")), clean_val(d.get("tfni_agency")),
                            clean_val(d.get("tfni_thesis")), clean_val(d.get("tfni_grant_amt")),
                            int(d.get("tfni_delete_bit") or 0), now_ts
                        ))
                        fni_count += 1
                conn.commit()
            print(f"Migrated {fni_count} faculty NAAC research records.")

            print("\n=== NAAC, ACCREDITATION & MEDIA FILES MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_naac_files()
