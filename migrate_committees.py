#!/usr/bin/env python3
"""
Migration Script: Institutional Committees & Members (CodeIgniter -> Laravel)
Source: u486681144_st_miraclg_liv.sql (committees, committee_members)
Target: u207346834_stmiracollege (committees, committee_members)
"""

import os
import sys
import re
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values


def clean_str(val):
    if val is None or str(val).strip() in ("None", "NULL", ""):
        return None
    return str(val).strip()


def migrate_committees():
    print("=" * 60)
    print("MIGRATING INSTITUTIONAL COMMITTEES & MEMBERS: CI -> Laravel")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Parse committees
    m_comm = re.findall(
        r"INSERT INTO [`\x27]?committees[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)",
        sql,
        re.DOTALL
    )
    raw_comm = []
    if m_comm:
        cols_c = [c.strip(" `\r\n") for c in m_comm[0][0].split(",")]
        for _, vals in m_comm:
            for r in parse_sql_values(vals):
                raw_comm.append(dict(zip(cols_c, r)))

    print(f"Found {len(raw_comm)} committee records in source dump.")

    # 2. Parse committee_members
    m_mem = re.findall(
        r"INSERT INTO [`\x27]?committee_members[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)",
        sql,
        re.DOTALL
    )
    raw_mem = []
    if m_mem:
        cols_m = [c.strip(" `\r\n") for c in m_mem[0][0].split(",")]
        for _, vals in m_mem:
            for r in parse_sql_values(vals):
                raw_mem.append(dict(zip(cols_m, r)))

    print(f"Found {len(raw_mem)} committee member records in source dump.")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Check highest existing ID in committees to avoid collisions
            cur.execute("SELECT id, name FROM committees")
            existing_comm = {r["name"].strip().lower(): r["id"] for r in cur.fetchall()}

            # Map CI committee_id -> Laravel committee_id
            ci_to_lara_comm = {}
            for c in raw_comm:
                ci_id = int(c["committee_id"])
                name = clean_str(c.get("committee_name") or f"Committee {ci_id}")
                key = name.lower()

                if key in existing_comm:
                    ci_to_lara_comm[ci_id] = existing_comm[key]
                else:
                    cur.execute("""
                        INSERT INTO committees (name, type, college_id, delete_bit, created_at, updated_at)
                        VALUES (%s, 'Statutory Committee', 1, 0, %s, %s)
                    """, (name, now_ts, now_ts))
                    new_id = cur.lastrowid
                    existing_comm[key] = new_id
                    ci_to_lara_comm[ci_id] = new_id

            conn.commit()
            print(f"Mapped {len(ci_to_lara_comm)} committees in target DB.")

            # Insert committee_members
            mem_insert_query = """
                INSERT INTO committee_members (
                    id, committee_id, name, role, designation, ordering, created_at, updated_at
                ) VALUES (
                    %(id)s, %(committee_id)s, %(name)s, %(role)s, %(designation)s, %(ordering)s, %(created_at)s, %(updated_at)s
                ) ON DUPLICATE KEY UPDATE
                    committee_id = VALUES(committee_id),
                    name = VALUES(name),
                    role = VALUES(role),
                    designation = VALUES(designation),
                    ordering = VALUES(ordering),
                    updated_at = VALUES(updated_at)
            """

            migrated_mems = 0
            for m in raw_mem:
                m_id = int(m["member_id"])
                ci_c_id = int(m["committee_id"])
                target_c_id = ci_to_lara_comm.get(ci_c_id)
                if not target_c_id:
                    continue

                m_name = clean_str(m.get("member_name") or f"Member {m_id}")
                desig = clean_str(m.get("designation") or "Member")
                role = "Chairman" if "chair" in desig.lower() else ("Secretary" if "sec" in desig.lower() else "Member")
                order = int(m.get("display_order") or 0)

                cur.execute(mem_insert_query, {
                    "id": m_id,
                    "committee_id": target_c_id,
                    "name": m_name,
                    "role": role,
                    "designation": desig,
                    "ordering": order,
                    "created_at": now_ts,
                    "updated_at": now_ts
                })
                migrated_mems += 1

            conn.commit()

            cur.execute("SELECT COUNT(*) as cnt FROM committees WHERE delete_bit = 0")
            c_cnt = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM committee_members")
            m_cnt = cur.fetchone()["cnt"]

            print(f"Successfully migrated {migrated_mems} committee member(s).")
            print(f"Total committees: {c_cnt}, Total committee members: {m_cnt}")
            print("\n=== COMMITTEES & MEMBERS MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_committees()

