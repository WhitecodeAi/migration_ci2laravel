#!/usr/bin/env python3
"""
Master Migration Runner: CodeIgniter -> Laravel
Runs all migration scripts in sequence and provides a complete summary report.
"""
import sys
import time
from db_config import DB_CONFIG, SQL_FILE

SCRIPTS = [
    ("Faculty & Departments", "migrate_faculty.py", "migrate_faculty"),
    ("Activities", "migrate_activities.py", "migrate_activities"),
    ("Alumni", "migrate_alumni.py", "migrate_alumni"),
    ("Events", "migrate_events.py", "migrate_events"),
    ("Grievances & Complaints", "migrate_grievances.py", "migrate_grievances"),
    ("Home Slider", "migrate_homeslider.py", "migrate_homeslider"),
    ("News", "migrate_news.py", "migrate_news"),
    ("Photo Gallery", "migrate_photogallery.py", "migrate_photogallery"),
    ("Popups & Blogs", "migrate_popups_blogs.py", "migrate_popups_and_blogs"),
    ("Academic Calendar", "migrate_academic_calendar.py", "migrate_academic_calendar"),
    ("Chatbot FAQ", "migrate_faq.py", "migrate_faq"),
    ("Quick Links", "migrate_quicklinks.py", "migrate_quicklinks"),
    ("Testimonials", "migrate_testimonials.py", "migrate_testimonials"),
    ("NCC Enrollment", "migrate_ncc.py", "migrate_ncc"),
    ("Birthday List", "migrate_birthdays.py", "migrate_birthdays"),
    ("NIRF Reports", "migrate_nirf.py", "migrate_nirf"),
    ("Admission Enquiries", "migrate_admissions.py", "migrate_admissions"),
    ("Placements", "migrate_placements.py", "migrate_placements"),
    ("Recruitment & Careers", "migrate_recruitment.py", "migrate_recruitment"),
    ("Subjects", "migrate_subjects.py", "migrate_subjects"),
    ("IQAC & AICTE Streams", "migrate_iqac_aicte.py", "migrate_iqac_aicte"),
    ("CMS Master Pages", "migrate_pages.py", "migrate_pages"),
    ("Department Sections", "migrate_sections.py", "migrate_sections"),
    ("Page Dynamic Components", "migrate_page_components.py", "migrate_page_components"),
    ("Statutory Committees & Members", "migrate_committees.py", "migrate_committees"),
    ("Examinations & Hall Tickets", "migrate_exams_halltickets.py", "migrate_exams_halltickets"),
    ("Legal Forms & Lookups", "migrate_legal_forms.py", "migrate_legal_forms"),
    ("NAAC & Media Files", "migrate_naac_files.py", "migrate_naac_files"),
]

def main():
    print("=" * 75)
    print("      COMPLETE CODEIGNITER TO LARAVEL DATABASE MIGRATION RUNNER")
    print("=" * 75)
    print(f"Target Database : {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Target User     : {DB_CONFIG['user']}")
    print(f"Source SQL File : {SQL_FILE}")
    print(f"Total Modules   : {len(SCRIPTS)}")
    print("=" * 75)

    results = []
    total_start = time.time()

    for label, script_file, func_name in SCRIPTS:
        print(f"\n>>> Running: {label} ({script_file})")
        start_time = time.time()
        try:
            mod_name = script_file.replace(".py", "")
            mod = __import__(mod_name)
            func = getattr(mod, func_name)
            func()
            elapsed = time.time() - start_time
            results.append((label, script_file, "SUCCESS", f"{elapsed:.2f}s"))
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"ERROR running {script_file}: {e}")
            results.append((label, script_file, f"FAILED", f"{elapsed:.2f}s"))

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 75)
    print("                      FULL MIGRATION SUMMARY REPORT")
    print("=" * 75)
    print(f"{'#':<3} | {'Module':<26} | {'Script':<27} | {'Status':<10} | {'Time':<8}")
    print("-" * 75)
    for idx, (label, script_file, status, elapsed) in enumerate(results, 1):
        status_disp = status if len(status) <= 10 else status[:10]
        print(f"{idx:<3} | {label:<26} | {script_file:<27} | {status_disp:<10} | {elapsed:<8}")
    print("=" * 75)
    print(f"Total Modules Processed : {len(results)}")
    print(f"Total Execution Time    : {total_elapsed:.2f}s")

    failed = [r for r in results if r[2] != "SUCCESS"]
    if failed:
        print(f"\nWARNING: {len(failed)} module(s) encountered issues.")
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} modules migrated successfully into Laravel database!")

if __name__ == "__main__":
    main()
