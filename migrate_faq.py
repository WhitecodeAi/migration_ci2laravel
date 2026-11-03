#!/usr/bin/env python3
"""
Migration Script: Chatbot FAQ Module (CodeIgniter -> Laravel)
Source: u208972730_scnewcms.sql (tbl_faq)
Target: u207346834_sathayelara (chatbot_faq_category, chatbot_faq)
"""

import sys
import os
import re
import pymysql
from datetime import datetime
from migrate_faculty import parse_sql_values, clean_date

from db_config import DB_CONFIG, SQL_FILE


def format_category_name(cat_str):
    if not cat_str:
        return "General"
    cat = cat_str.strip().title()
    # Normalize synonyms
    if cat.lower() in ("exam", "exams"):
        return "Exams"
    if cat.lower() in ("scholarship", "scholarships"):
        return "Scholarships"
    if cat.lower() in ("admission", "admissions"):
        return "Admission"
    return cat


def migrate_faq():
    print("=" * 60)
    print("MIGRATING CHATBOT FAQ: CodeIgniter -> Laravel")
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
            print("\n[Step 1] Loading existing chatbot_faq_category...")
            cur.execute("SELECT id, LOWER(category) as cat_key, category FROM chatbot_faq_category WHERE delete_bit = 0")
            cat_map = {}
            for r in cur.fetchall():
                cat_map[r["cat_key"]] = r["id"]

            print(f"Existing categories in DB: {len(cat_map)}")

            # Extract tbl_faq
            m_faq = re.findall(
                r"INSERT INTO [`\x27]?tbl_faq[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);\n",
                sql,
                re.DOTALL
            )
            raw_faqs = []
            if m_faq:
                cols = [c.strip(" `\r\n") for c in m_faq[0][0].split(",")]
                for _, vals in m_faq:
                    for r in parse_sql_values(vals):
                        if len(r) == len(cols):
                            raw_faqs.append(dict(zip(cols, r)))

            print(f"Found {len(raw_faqs)} FAQs in source dump.")

            # Ensure all categories exist
            cat_insert_sql = """
            INSERT INTO chatbot_faq_category (category, redirect_url, redirect_target, delete_bit, created_at, updated_at)
            VALUES (%(category)s, NULL, '_blank', 0, %(created_at)s, %(updated_at)s)
            """

            for f in raw_faqs:
                cat_raw = str(f.get("tf_category") or "").strip()
                cat_display = format_category_name(cat_raw)
                cat_key = cat_display.lower()

                if cat_key not in cat_map:
                    cur.execute(cat_insert_sql, {
                        "category": cat_display,
                        "created_at": now_ts,
                        "updated_at": now_ts
                    })
                    cat_id = cur.lastrowid
                    cat_map[cat_key] = cat_id
                    print(f"Created new FAQ category: '{cat_display}' (ID: {cat_id})")

            conn.commit()

            # Insert FAQs
            faq_sql = """
            INSERT INTO chatbot_faq (
                id, category_id, question, answer, delete_bit, created_at, updated_at
            ) VALUES (
                %(id)s, %(category_id)s, %(question)s, %(answer)s, 0, %(created_at)s, %(updated_at)s
            ) ON DUPLICATE KEY UPDATE
                category_id = VALUES(category_id),
                question = VALUES(question),
                answer = VALUES(answer),
                delete_bit = 0,
                updated_at = VALUES(updated_at)
            """

            migrated_count = 0
            for f in raw_faqs:
                f_id = int(f["tf_id"])
                cat_raw = str(f.get("tf_category") or "").strip()
                cat_display = format_category_name(cat_raw)
                cat_id = cat_map[cat_display.lower()]

                question = str(f.get("tf_question") or "").strip()
                answer = str(f.get("tf_answer") or "").strip()
                updated_at = clean_date(f.get("tf_updated_date")) or now_ts

                cur.execute(faq_sql, {
                    "id": f_id,
                    "category_id": cat_id,
                    "question": question,
                    "answer": answer,
                    "created_at": updated_at,
                    "updated_at": updated_at
                })
                migrated_count += 1

            conn.commit()
            print(f"Successfully migrated {migrated_count} FAQs into chatbot_faq.")

            # Verification
            cur.execute("SELECT c.category, COUNT(f.id) as count FROM chatbot_faq_category c LEFT JOIN chatbot_faq f ON c.id = f.category_id WHERE f.delete_bit = 0 GROUP BY c.id, c.category")
            print("\nVerification - FAQs per category:")
            for r in cur.fetchall():
                print(f"  {r['category']}: {r['count']} questions")

            cur.execute("SELECT COUNT(*) AS c FROM chatbot_faq WHERE delete_bit = 0")
            print(f"\nTotal active FAQs in database: {cur.fetchone()['c']}")

    finally:
        conn.close()

    print("\nChatbot FAQ Migration Completed Successfully!")


if __name__ == "__main__":
    migrate_faq()

