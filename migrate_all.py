#!/usr/bin/env python3
"""
Master Migration Orchestrator: Complete CodeIgniter -> Laravel CMS ETL Pipeline
Runs all 18 module migrations in topological dependency order and verifies target database.
"""

import sys
import time
import subprocess
import pymysql

MIGRATION_SCRIPTS = [
    ("News & Articles", "migrate_news.py"),
    ("Home Page Sliders", "migrate_homeslider.py"),
    ("Quick Links", "migrate_quicklinks.py"),
    ("Testimonials", "migrate_testimonials.py"),
    ("Photo Gallery & Media", "migrate_photogallery.py"),
    ("Events & Categories", "migrate_events.py"),
    ("Activities & Committees", "migrate_activities.py"),
    ("Faculty & Departments", "migrate_faculty.py"),
    ("Dynamic Popups & Blogs", "migrate_popups_blogs.py"),
    ("Grievances & Anti-Ragging", "migrate_grievances.py"),
    ("Alumni Registrations", "migrate_alumni.py"),
    ("Chatbot FAQs", "migrate_faq.py"),
    ("Academic Calendar", "migrate_academic_calendar.py"),
    ("Academics, Degrees & NIRF", "migrate_academics.py"),
    ("Master Pages (Puck CMS)", "migrate_pages.py"),
    ("NAAC & AQAR Downloads", "migrate_naac_downloads.py"),
    ("Faculty Research Publications", "migrate_faculty_research.py"),
    ("Program Specializations & Subjects", "migrate_specializations.py"),
]

DB_CONFIG = {
    "host": "193.203.184.233",
    "port": 3306,
    "user": "u207346834_sathayelara",
    "password": "Fp>6ClxZZ6",
    "database": "u207346834_sathayelara",
    "charset": "utf8mb4"
}


def main():
    print("=" * 75)
    print("      SATHAYE COLLEGE CMS: MASTER DATA MIGRATION RUNNER")
    print("=" * 75)
    start_all = time.time()

    success_count = 0
    fail_count = 0

    for idx, (label, script) in enumerate(MIGRATION_SCRIPTS, 1):
        print(f"\n[{idx}/{len(MIGRATION_SCRIPTS)}] Running: {label} ({script})...")
        t0 = time.time()
        ret = subprocess.run([sys.executable, script])
        dur = time.time() - t0
        if ret.returncode == 0:
            print(f"--> [SUCCESS] {label} completed in {dur:.2f}s")
            success_count += 1
        else:
            print(f"--> [FAILED] {label} returned code {ret.returncode} in {dur:.2f}s")
            fail_count += 1

    total_time = time.time() - start_all
    print("\n" + "=" * 75)
    print(f"  MIGRATION EXECUTION FINISHED: {success_count} Passed, {fail_count} Failed in {total_time:.2f}s")
    print("=" * 75)

    # Master Reconciliation
    print("\n[Audit] Performing final database reconciliation...")
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            tables = [
                ("news_masters", "News Articles"),
                ("home_page_sliders", "Home Sliders"),
                ("quick_links", "Quick Links"),
                ("testimonials", "Testimonials"),
                ("galleries", "Photo Galleries"),
                ("photos", "Photos"),
                ("events_tables", "Events"),
                ("activity_tables", "Activities"),
                ("committees", "Committees"),
                ("streams", "Faculty Streams"),
                ("departments", "Faculty Departments"),
                ("faculties", "Faculty Members"),
                ("dynamic_popup", "Dynamic Popups"),
                ("blogs", "Blogs"),
                ("student_grievances", "Student Grievances & Anti-Ragging"),
                ("caste_based_discrimination_complaints_registrations", "Caste Complaints"),
                ("alumni_forms", "Alumni Registrations"),
                ("chatbot_faq_category", "FAQ Categories"),
                ("chatbot_faq", "Chatbot FAQs"),
                ("academic_date_category", "Academic Date Categories"),
                ("academic_event_dates", "Academic Calendar Dates"),
                ("programs", "Degree Programs"),
                ("courses", "Courses"),
                ("subjects", "Academic Subjects"),
                ("research_papers", "Faculty Research Publications"),
                ("student_admission_enquiry", "Student Admission Leads"),
                ("nirf", "NIRF Publications"),
                ("pages", "Puck Master Pages"),
                ("downloads", "NAAC & AQAR Downloads"),
                ("iqacs", "IQAC Cell"),
                ("categorys", "Castes & Categories")
            ]
            grand_total = 0
            for tbl, name in tables:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                cnt = cur.fetchone()[0]
                grand_total += cnt
                print(f"  - {name:35s} ({tbl:48s}): {cnt:5d} records")
            print("-" * 75)
            print(f"  GRAND TOTAL DATABASE RECORDS: {grand_total}")
            print("=" * 75)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
