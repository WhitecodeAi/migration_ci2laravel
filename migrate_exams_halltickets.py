#!/usr/bin/env python3
"""
Migration Script: Student Examination & Hall Tickets Module
Source: u486681144_st_miraclg_liv.sql
  - tbl_exam_sessions (2 rows)
  - tbl_hall_tickets (1,305 rows)
  - tbl_exam_results (482 rows)
  - tbl_exam_audit_logs (96 rows)
  - tbl_results (1 row)
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


def migrate_exams_halltickets():
    print("=" * 60)
    print("MIGRATING EXAMINATIONS, HALL TICKETS & RESULTS: CI -> Laravel")
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
            # -------------------------------------------------------------
            # 1. tbl_exam_sessions
            # -------------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_exam_sessions (
                    session_id int NOT NULL,
                    session_name varchar(255) NOT NULL,
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            m_sess = re.findall(r"INSERT INTO [`\x27]?tbl_exam_sessions[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            sess_migrated = 0
            if m_sess:
                cols_s = [c.strip(" `\r\n") for c in m_sess[0][0].split(",")]
                for _, vals in m_sess:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_s, r))
                        sid = int(d["session_id"])
                        sname = clean_val(d.get("session_name") or f"Session {sid}")
                        cts = clean_date(d.get("created_at")) or now_ts
                        cur.execute("""
                            INSERT INTO tbl_exam_sessions (session_id, session_name, created_at)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE session_name = VALUES(session_name)
                        """, (sid, sname, cts))
                        sess_migrated += 1
                conn.commit()
            print(f"Migrated {sess_migrated} exam session(s).")

            # -------------------------------------------------------------
            # 2. tbl_hall_tickets
            # -------------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_hall_tickets (
                    id int NOT NULL,
                    student_name varchar(255) NOT NULL,
                    prn varchar(100) DEFAULT NULL,
                    seat_number varchar(100) NOT NULL,
                    exam_session_id int NOT NULL,
                    course varchar(255) DEFAULT NULL,
                    semester varchar(100) DEFAULT NULL,
                    college_code varchar(100) DEFAULT NULL,
                    mother_name varchar(255) DEFAULT NULL,
                    password varchar(100) DEFAULT NULL,
                    pdf_path varchar(255) DEFAULT NULL,
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_seat_prn (seat_number, prn),
                    KEY idx_session (exam_session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            m_hall = re.findall(r"INSERT INTO [`\x27]?tbl_hall_tickets[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            hall_migrated = 0
            if m_hall:
                cols_h = [c.strip(" `\r\n") for c in m_hall[0][0].split(",")]
                batch = []
                for _, vals in m_hall:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_h, r))
                        batch.append((
                            int(d["id"]),
                            clean_val(d.get("student_name") or ""),
                            clean_val(d.get("prn")),
                            clean_val(d.get("seat_number") or ""),
                            int(d.get("exam_session_id") or 0),
                            clean_val(d.get("course")),
                            clean_val(d.get("semester")),
                            clean_val(d.get("college_code")),
                            clean_val(d.get("mother_name")),
                            clean_val(d.get("password")),
                            clean_path(d.get("pdf_path")),
                            clean_date(d.get("created_at")) or now_ts,
                            clean_date(d.get("updated_at")) or now_ts
                        ))

                insert_hall_query = """
                    INSERT INTO tbl_hall_tickets (
                        id, student_name, prn, seat_number, exam_session_id,
                        course, semester, college_code, mother_name, password,
                        pdf_path, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        student_name = VALUES(student_name),
                        prn = VALUES(prn),
                        seat_number = VALUES(seat_number),
                        exam_session_id = VALUES(exam_session_id),
                        course = VALUES(course),
                        semester = VALUES(semester),
                        college_code = VALUES(college_code),
                        mother_name = VALUES(mother_name),
                        pdf_path = VALUES(pdf_path),
                        updated_at = VALUES(updated_at)
                """

                # Execute in chunks of 500
                chunk_size = 500
                for i in range(0, len(batch), chunk_size):
                    cur.executemany(insert_hall_query, batch[i:i + chunk_size])
                    conn.commit()
                hall_migrated = len(batch)

            print(f"Migrated {hall_migrated} student hall tickets.")

            # -------------------------------------------------------------
            # 3. tbl_exam_results
            # -------------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_exam_results (
                    id int NOT NULL,
                    student_name varchar(255) NOT NULL,
                    prn varchar(100) DEFAULT NULL,
                    seat_number varchar(100) NOT NULL,
                    exam_session_id int NOT NULL,
                    course_year varchar(150) DEFAULT NULL,
                    course varchar(255) DEFAULT NULL,
                    semester varchar(100) DEFAULT NULL,
                    college_code varchar(100) DEFAULT NULL,
                    mother_name varchar(255) DEFAULT NULL,
                    password varchar(100) DEFAULT NULL,
                    subject_details text,
                    total_marks varchar(50) DEFAULT NULL,
                    percentage varchar(50) DEFAULT NULL,
                    grade varchar(50) DEFAULT NULL,
                    result_status varchar(50) DEFAULT NULL,
                    pdf_path varchar(255) DEFAULT NULL,
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_seat_prn (seat_number, prn),
                    KEY idx_session (exam_session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            m_res = re.findall(r"INSERT INTO [`\x27]?tbl_exam_results[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            res_migrated = 0
            if m_res:
                cols_r = [c.strip(" `\r\n") for c in m_res[0][0].split(",")]
                res_batch = []
                for _, vals in m_res:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_r, r))
                        res_batch.append((
                            int(d["id"]),
                            clean_val(d.get("student_name") or ""),
                            clean_val(d.get("prn")),
                            clean_val(d.get("seat_number") or ""),
                            int(d.get("exam_session_id") or 0),
                            clean_val(d.get("course_year")),
                            clean_val(d.get("course")),
                            clean_val(d.get("semester")),
                            clean_val(d.get("college_code")),
                            clean_val(d.get("mother_name")),
                            clean_val(d.get("password")),
                            clean_val(d.get("subject_details")),
                            clean_val(d.get("total_marks")),
                            clean_val(d.get("percentage")),
                            clean_val(d.get("grade")),
                            clean_val(d.get("result_status")),
                            clean_path(d.get("pdf_path")),
                            clean_date(d.get("created_at")) or now_ts,
                            clean_date(d.get("updated_at")) or now_ts
                        ))

                insert_res_query = """
                    INSERT INTO tbl_exam_results (
                        id, student_name, prn, seat_number, exam_session_id,
                        course_year, course, semester, college_code, mother_name,
                        password, subject_details, total_marks, percentage,
                        grade, result_status, pdf_path, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        student_name = VALUES(student_name),
                        prn = VALUES(prn),
                        seat_number = VALUES(seat_number),
                        exam_session_id = VALUES(exam_session_id),
                        course_year = VALUES(course_year),
                        course = VALUES(course),
                        semester = VALUES(semester),
                        college_code = VALUES(college_code),
                        mother_name = VALUES(mother_name),
                        subject_details = VALUES(subject_details),
                        total_marks = VALUES(total_marks),
                        percentage = VALUES(percentage),
                        grade = VALUES(grade),
                        result_status = VALUES(result_status),
                        pdf_path = VALUES(pdf_path),
                        updated_at = VALUES(updated_at)
                """

                for i in range(0, len(res_batch), chunk_size):
                    cur.executemany(insert_res_query, res_batch[i:i + chunk_size])
                    conn.commit()
                res_migrated = len(res_batch)

            print(f"Migrated {res_migrated} student exam result records.")

            # -------------------------------------------------------------
            # 4. tbl_exam_audit_logs
            # -------------------------------------------------------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tbl_exam_audit_logs (
                    id int NOT NULL,
                    user_id int DEFAULT NULL,
                    username varchar(255) DEFAULT NULL,
                    action_type varchar(100) DEFAULT NULL,
                    module varchar(100) DEFAULT NULL,
                    details text DEFAULT NULL,
                    created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            m_log = re.findall(r"INSERT INTO [`\x27]?tbl_exam_audit_logs[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            log_migrated = 0
            if m_log:
                cols_l = [c.strip(" `\r\n") for c in m_log[0][0].split(",")]
                log_batch = []
                for _, vals in m_log:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_l, r))
                        log_batch.append((
                            int(d["id"]),
                            int(d.get("user_id") or 0) if d.get("user_id") else None,
                            clean_val(d.get("username")),
                            clean_val(d.get("action_type")),
                            clean_val(d.get("module")),
                            clean_val(d.get("details")),
                            clean_date(d.get("created_at")) or now_ts
                        ))

                insert_log_query = """
                    INSERT INTO tbl_exam_audit_logs (id, user_id, username, action_type, module, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE details = VALUES(details)
                """
                cur.executemany(insert_log_query, log_batch)
                conn.commit()
                log_migrated = len(log_batch)

            print(f"Migrated {log_migrated} exam audit logs.")

            # -------------------------------------------------------------
            # 5. Public Results (tbl_results -> results)
            # -------------------------------------------------------------
            m_pub_res = re.findall(r"INSERT INTO [`\x27]?tbl_results[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
            if m_pub_res:
                cols_pr = [c.strip(" `\r\n") for c in m_pub_res[0][0].split(",")]
                for _, vals in m_pub_res:
                    for r in parse_sql_values(vals):
                        d = dict(zip(cols_pr, r))
                        r_id = int(d.get("id") or d.get("r_id") or 1)
                        r_title = clean_val(d.get("title") or d.get("r_title") or "Semester Results")
                        r_src = clean_path(d.get("source") or d.get("r_pdf") or "")
                        cur.execute("""
                            INSERT INTO results (id, title, source, academic_year, show_on_website, delete_bit, created_at, updated_at)
                            VALUES (%s, %s, %s, '2026-27', 1, 0, %s, %s)
                            ON DUPLICATE KEY UPDATE title = VALUES(title), source = VALUES(source)
                        """, (r_id, r_title, r_src, now_ts, now_ts))
                conn.commit()

            print("\n=== EXAMINATIONS & HALL TICKETS MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_exams_halltickets()

