#!/usr/bin/env python3
"""
Migration Script: Page Dynamic Components Module (Tabs, Accordions, Cards, Galleries)
Source: u486681144_st_miraclg_liv.sql
  - tbl_page_tabs (483 rows)
  - tbl_page_accordions (573 rows)
  - tbl_page_cards (148 rows)
  - tbl_page_galleries (18 rows)
Target: u207346834_stmiracollege (pages.content)
"""

import os
import sys
import re
import json
import uuid
import pymysql
from datetime import datetime
from db_config import DB_CONFIG, SQL_FILE
from migrate_faculty import parse_sql_values


def clean_html(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace(r'\"', '"').replace(r"\'", "'")
    text = text.replace(r'\r\n', '\n').replace(r'\n', '\n').replace(r'\t', '\t')
    return text.strip()


def slugify_id(text):
    s = re.sub(r'[^a-zA-Z0-9]+', '-', str(text).lower()).strip('-')
    return s or "comp"


def build_accordion_html(acc_list, parent_id):
    if not acc_list:
        return ""
    acc_id = f"acc-{parent_id}-{uuid.uuid4().hex[:6]}"
    html = [f'<div class="accordion mb-4" id="{acc_id}">']
    for idx, a in enumerate(acc_list):
        item_id = f"item-{parent_id}-{idx}-{uuid.uuid4().hex[:4]}"
        heading_id = f"heading-{item_id}"
        collapse_id = f"collapse-{item_id}"
        title = clean_html(a.get("tpa_title") or f"Section {idx+1}")
        content = clean_html(a.get("tpa_content") or "")
        show_class = "show" if idx == 0 else ""
        btn_collapsed = "" if idx == 0 else "collapsed"

        html.append(f"""
        <div class="accordion-item">
            <h2 class="accordion-header" id="{heading_id}">
                <button class="accordion-button {btn_collapsed}" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}" aria-expanded="{ 'true' if idx == 0 else 'false' }" aria-controls="{collapse_id}">
                    {title}
                </button>
            </h2>
            <div id="{collapse_id}" class="accordion-collapse collapse {show_class}" aria-labelledby="{heading_id}" data-bs-parent="#{acc_id}">
                <div class="accordion-body">
                    {content}
                </div>
            </div>
        </div>
        """)
    html.append('</div>')
    return "\n".join(html)


def build_cards_html(cards_list):
    if not cards_list:
        return ""
    html = ['<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4 mb-4">']
    for c in cards_list:
        title = clean_html(c.get("tpc_title") or "")
        desc = clean_html(c.get("tpc_description") or "")
        btn_text = clean_html(c.get("tpc_button_text") or "View Details")
        link = clean_html(c.get("tpc_link") or "#")
        target = clean_html(c.get("tpc_target") or "_blank")

        html.append(f"""
        <div class="col">
            <div class="card h-100 shadow-sm border-0">
                <div class="card-body">
                    <h5 class="card-title fw-bold">{title}</h5>
                    <p class="card-text text-muted">{desc}</p>
                    <a href="{link}" target="{target}" class="btn btn-outline-primary btn-sm">{btn_text}</a>
                </div>
            </div>
        </div>
        """)
    html.append('</div>')
    return "\n".join(html)


def build_galleries_html(gal_list):
    if not gal_list:
        return ""
    html = ['<div class="row g-3 mb-4">']
    for g in gal_list:
        img_url = clean_html(g.get("tpg_image_url") or "")
        title = clean_html(g.get("tpg_title") or g.get("tpg_gallery_title") or "")
        desc = clean_html(g.get("tpg_description") or "")
        cols = int(g.get("tpg_grid_columns") or 3)
        col_class = "col-md-4" if cols == 3 else ("col-md-6" if cols == 2 else "col-md-3")

        html.append(f"""
        <div class="{col_class}">
            <div class="card h-100 border-0 shadow-sm overflow-hidden">
                <img src="{img_url}" class="card-img-top" alt="{title}" style="object-fit: cover; height: 220px;" onerror="this.style.display='none'">
                {f'<div class="card-body p-2"><h6 class="card-title mb-1">{title}</h6><small class="text-muted">{desc}</small></div>' if title or desc else ''}
            </div>
        </div>
        """)
    html.append('</div>')
    return "\n".join(html)


def migrate_page_components():
    print("=" * 60)
    print("MIGRATING PAGE DYNAMIC COMPONENTS: Tabs, Accordions, Cards")
    print("=" * 60)

    if not os.path.exists(SQL_FILE):
        print(f"Error: {SQL_FILE} not found!")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8", errors="replace") as f:
        sql = f.read()

    # 1. Parse Tabs
    m_tabs = re.findall(r"INSERT INTO [`\x27]?tbl_page_tabs[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
    tabs_by_page = {}
    tabs_by_id = {}
    if m_tabs:
        cols_t = [c.strip(" `\r\n") for c in m_tabs[0][0].split(",")]
        for _, vals in m_tabs:
            for r in parse_sql_values(vals):
                d = dict(zip(cols_t, r))
                tid = str(d.get("tpt_id"))
                tabs_by_id[tid] = d
                pid_str = str(d.get("tmp_id") or "").strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    tabs_by_page.setdefault(pid, []).append(d)

    print(f"Loaded {len(tabs_by_id)} tabs across {len(tabs_by_page)} pages.")

    # 2. Parse Accordions
    m_acc = re.findall(r"INSERT INTO [`\x27]?tbl_page_accordions[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
    accs_by_tab = {}
    accs_by_page = {}
    total_acc = 0
    if m_acc:
        cols_a = [c.strip(" `\r\n") for c in m_acc[0][0].split(",")]
        for _, vals in m_acc:
            for r in parse_sql_values(vals):
                d = dict(zip(cols_a, r))
                total_acc += 1
                tab_id = str(d.get("tab_id") or "").strip()
                if tab_id and tab_id not in ("0", "None"):
                    accs_by_tab.setdefault(tab_id, []).append(d)
                else:
                    pid_str = str(d.get("tmp_id") or "").strip()
                    if pid_str.isdigit():
                        accs_by_page.setdefault(int(pid_str), []).append(d)

    print(f"Loaded {total_acc} accordions ({len(accs_by_tab)} tab groups, {len(accs_by_page)} direct page groups).")

    # 3. Parse Cards
    m_card = re.findall(r"INSERT INTO [`\x27]?tbl_page_cards[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
    cards_by_tab = {}
    cards_by_page = {}
    total_cards = 0
    if m_card:
        cols_c = [c.strip(" `\r\n") for c in m_card[0][0].split(",")]
        for _, vals in m_card:
            for r in parse_sql_values(vals):
                d = dict(zip(cols_c, r))
                total_cards += 1
                tab_id = str(d.get("tab_id") or "").strip()
                if tab_id and tab_id not in ("0", "None"):
                    cards_by_tab.setdefault(tab_id, []).append(d)
                else:
                    pid_str = str(d.get("tmp_id") or "").strip()
                    if pid_str.isdigit():
                        cards_by_page.setdefault(int(pid_str), []).append(d)

    print(f"Loaded {total_cards} cards.")

    # 4. Parse Galleries
    m_gal = re.findall(r"INSERT INTO [`\x27]?tbl_page_galleries[`\x27]?[^\(]*\((.*?)\)\s*VALUES\s*(.*?);(?:\r?\n|$)", sql, re.DOTALL)
    gal_by_tab = {}
    gal_by_page = {}
    total_gals = 0
    if m_gal:
        cols_g = [c.strip(" `\r\n") for c in m_gal[0][0].split(",")]
        for _, vals in m_gal:
            for r in parse_sql_values(vals):
                d = dict(zip(cols_g, r))
                total_gals += 1
                tab_id = str(d.get("tab_id") or "").strip()
                if tab_id and tab_id not in ("0", "None"):
                    gal_by_tab.setdefault(tab_id, []).append(d)
                else:
                    pid_str = str(d.get("tmp_id") or "").strip()
                    if pid_str.isdigit():
                        gal_by_page.setdefault(int(pid_str), []).append(d)

    print(f"Loaded {total_gals} page gallery items.")

    # Collect all pages that have any dynamic components
    all_target_page_ids = set(tabs_by_page.keys()) | set(accs_by_page.keys()) | set(cards_by_page.keys()) | set(gal_by_page.keys())
    print(f"\nTotal unique pages with dynamic components: {len(all_target_page_ids)}")

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Load existing page contents
            cur.execute("SELECT id, title, content FROM pages WHERE id IN %s", (tuple(all_target_page_ids),))
            existing_pages = {r["id"]: r for r in cur.fetchall()}

            updated_count = 0
            for pid in all_target_page_ids:
                if pid not in existing_pages:
                    continue

                page_row = existing_pages[pid]
                title = page_row["title"]

                # Extract any existing base HTML
                existing_html = ""
                try:
                    p_data = json.loads(page_row["content"])
                    blocks = p_data if isinstance(p_data, list) else p_data.get("content", [])
                    for b in blocks:
                        props = b.get("props", {}) or b.get("values", {})
                        code = props.get("CodeEditer", "") or props.get("code", "")
                        if code and code.strip():
                            existing_html = code.strip()
                            break
                except Exception:
                    pass

                # Assemble components for this page
                components_html_parts = []

                # A. Page Tabs
                page_tabs = sorted(tabs_by_page.get(pid, []), key=lambda x: int(x.get("tpt_order") or 0))
                if page_tabs:
                    tab_group_id = f"tab-grp-{pid}-{uuid.uuid4().hex[:6]}"
                    is_vertical = any(t.get("tpt_type") == "vertical" for t in page_tabs)

                    nav_items = []
                    pane_items = []

                    for idx, t in enumerate(page_tabs):
                        tid = str(t["tpt_id"])
                        tab_slug = f"tab-{pid}-{tid}"
                        t_title = clean_html(t.get("tpt_title") or f"Tab {idx+1}")
                        t_content = clean_html(t.get("tpt_content") or "")
                        active_class = "active" if idx == 0 else ""
                        selected = "true" if idx == 0 else "false"

                        nav_items.append(f"""
                        <li class="nav-item" role="presentation">
                            <button class="nav-link {active_class}" id="{tab_slug}-btn" data-bs-toggle="pill" data-bs-target="#{tab_slug}" type="button" role="tab" aria-controls="{tab_slug}" aria-selected="{selected}">
                                {t_title}
                            </button>
                        </li>
                        """)

                        # Child components inside this tab
                        tab_inner_parts = []
                        if t_content:
                            tab_inner_parts.append(t_content)

                        # Child accordions
                        c_accs = sorted(accs_by_tab.get(tid, []), key=lambda x: int(x.get("tpa_order") or 0))
                        if c_accs:
                            tab_inner_parts.append(build_accordion_html(c_accs, tid))

                        # Child cards
                        c_cards = cards_by_tab.get(tid, [])
                        if c_cards:
                            tab_inner_parts.append(build_cards_html(c_cards))

                        # Child galleries
                        c_gals = gal_by_tab.get(tid, [])
                        if c_gals:
                            tab_inner_parts.append(build_galleries_html(c_gals))

                        tab_body = "\n".join(tab_inner_parts)
                        pane_items.append(f"""
                        <div class="tab-pane fade { 'show active' if idx == 0 else '' }" id="{tab_slug}" role="tabpanel" aria-labelledby="{tab_slug}-btn">
                            {tab_body}
                        </div>
                        """)

                    if is_vertical:
                        tabs_html = f"""
                        <div class="row my-4">
                            <div class="col-lg-3 col-md-4 mb-3">
                                <ul class="nav nav-pills flex-column shadow-sm p-3 bg-light rounded" id="{tab_group_id}" role="tablist">
                                    {''.join(nav_items)}
                                </ul>
                            </div>
                            <div class="col-lg-9 col-md-8">
                                <div class="tab-content" id="{tab_group_id}-content">
                                    {''.join(pane_items)}
                                </div>
                            </div>
                        </div>
                        """
                    else:
                        tabs_html = f"""
                        <div class="my-4">
                            <ul class="nav nav-tabs mb-3" id="{tab_group_id}" role="tablist">
                                {''.join(nav_items)}
                            </ul>
                            <div class="tab-content" id="{tab_group_id}-content">
                                {''.join(pane_items)}
                            </div>
                        </div>
                        """
                    components_html_parts.append(tabs_html)

                # B. Direct Page Accordions
                p_accs = sorted(accs_by_page.get(pid, []), key=lambda x: int(x.get("tpa_order") or 0))
                if p_accs:
                    components_html_parts.append(build_accordion_html(p_accs, f"p-{pid}"))

                # C. Direct Page Cards
                p_cards = cards_by_page.get(pid, [])
                if p_cards:
                    components_html_parts.append(build_cards_html(p_cards))

                # D. Direct Page Galleries
                p_gals = gal_by_page.get(pid, [])
                if p_gals:
                    components_html_parts.append(build_galleries_html(p_gals))

                # Combine with existing base HTML
                full_page_html = existing_html
                if components_html_parts:
                    comp_block = "\n".join(components_html_parts)
                    if full_page_html:
                        full_page_html = full_page_html + "\n<hr class='my-4'/>\n" + comp_block
                    else:
                        full_page_html = comp_block

                # Construct Code Editer component schema
                block_id = f"Code Editer-{uuid.uuid4()}"
                new_content_json = json.dumps({
                    "content": [
                        {
                            "type": "Code Editer",
                            "props": {
                                "CodeEditer": full_page_html,
                                "id": block_id
                            }
                        }
                    ],
                    "root": {
                        "props": {
                            "title": title,
                            "showHeader": 1,
                            "showFooter": 1,
                            "showBreadcrumb": 1
                        }
                    },
                    "zones": []
                })

                cur.execute("""
                    UPDATE pages 
                    SET content = %s, updated_at = %s 
                    WHERE id = %s
                """, (new_content_json, now_ts, pid))
                updated_count += 1

            conn.commit()
            print(f"Successfully integrated dynamic components into {updated_count} pages.")
            print("\n=== PAGE COMPONENTS MIGRATION COMPLETE! ===")

    finally:
        conn.close()


if __name__ == "__main__":
    migrate_page_components()

