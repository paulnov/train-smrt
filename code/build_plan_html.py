#!/usr/bin/env python3
"""Render quarterly and weekly Markdown plans as root-level HTML pages."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
PLAN_RE = re.compile(r"^(quarter-plan|week-plan)-(\d{4}-\d{2}(?:-\d{2})?)\.md$")
APP_INDEX_RE = re.compile(r"<!--\s*app-index\s*(.*?)-->", re.DOTALL | re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ORDERED_RE = re.compile(r"^(\d+)[.)]\s+(.+)$")
DAY_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?"
    r"(?:\s+(\d{1,2}[/-]\d{1,2}))?"
    r"\s*(?:[-\u2013\u2014]\s*)?(.+)?$",
    re.IGNORECASE,
)

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


@dataclass(frozen=True)
class SourcePlan:
    kind: str
    date_key: str
    source: Path
    output: Path
    title: str
    meta: dict[str, str]


@dataclass(frozen=True)
class DayLink:
    anchor: str
    date_label: str
    title: str


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_inline(value: str) -> str:
    rendered = esc(value)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", rendered)
    return rendered


def display_date(date: dt.date) -> str:
    return f"{MONTH_NAMES[date.month]} {date.day}, {date.year}"


def display_range(start: dt.date, end: dt.date) -> str:
    if start == end:
        return display_date(start)
    if start.year == end.year and start.month == end.month:
        return f"{MONTH_NAMES[start.month]} {start.day}-{end.day}, {start.year}"
    if start.year == end.year:
        return f"{MONTH_NAMES[start.month]} {start.day}-{MONTH_NAMES[end.month]} {end.day}, {start.year}"
    return f"{display_date(start)}-{display_date(end)}"


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def read_app_meta(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = APP_INDEX_RE.search(text)
    if not match:
        return {}

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower().replace("-", "_")
        value = value.strip()
        if key and value:
            meta[key] = value
    return meta


def strip_app_meta(text: str) -> list[str]:
    return APP_INDEX_RE.sub("", text).splitlines()


def first_heading(lines: list[str], fallback: str) -> str:
    for line in lines:
        match = HEADING_RE.match(line.strip())
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return fallback


def output_path(source: Path) -> Path:
    return REPO_ROOT / f"{source.stem}.html"


def read_source_plan(source: Path) -> SourcePlan:
    match = PLAN_RE.match(source.name)
    if not match:
        raise ValueError(f"Not a quarterly or weekly plan: {source}")
    kind, date_key = match.groups()
    meta = read_app_meta(source)
    lines = strip_app_meta(source.read_text(encoding="utf-8"))
    title = meta.get("theme") or first_heading(lines, source.stem)
    return SourcePlan(kind=kind, date_key=date_key, source=source, output=output_path(source), title=title, meta=meta)


def parse_iso(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def plan_range(plan: SourcePlan) -> str:
    if "start" in plan.meta and "end" in plan.meta:
        return display_range(parse_iso(plan.meta["start"]), parse_iso(plan.meta["end"]))

    if plan.kind == "week-plan":
        start = parse_iso(plan.date_key)
        return display_range(start, start + dt.timedelta(days=6))

    start = dt.date.fromisoformat(f"{plan.date_key}-01")
    return display_range(start, start + dt.timedelta(days=120))


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:-1]


def is_table_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def table_html(rows: list[str]) -> str:
    parsed = [split_table_row(row) for row in rows]
    has_header = len(parsed) >= 2 and is_table_separator(parsed[1])
    parts = ["        <table>"]
    if has_header:
        parts.append("          <thead>")
        parts.append("            <tr>")
        for cell in parsed[0]:
            parts.append(f"              <th>{render_inline(cell)}</th>")
        parts.append("            </tr>")
        parts.append("          </thead>")
        body_rows = parsed[2:]
    else:
        body_rows = parsed

    parts.append("          <tbody>")
    for row in body_rows:
        parts.append("            <tr>")
        for cell in row:
            parts.append(f"              <td>{render_inline(cell)}</td>")
        parts.append("            </tr>")
    parts.append("          </tbody>")
    parts.append("        </table>")
    return "\n".join(parts)


def day_parts(title: str) -> tuple[str, str] | None:
    match = DAY_RE.match(title)
    if not match:
        return None
    day, date_label, remaining = match.groups()
    label = f"{day.title()} {date_label}" if date_label else day.title()
    return label, (remaining or title).strip()


def collect_day_links(lines: list[str]) -> list[DayLink]:
    links: list[DayLink] = []
    for line in lines:
        match = HEADING_RE.match(line.strip())
        if not match or len(match.group(1)) != 2:
            continue
        parsed = day_parts(match.group(2).strip())
        if not parsed:
            continue
        date_label, title = parsed
        anchor = slugify(match.group(2), f"day-{len(links) + 1}")
        links.append(DayLink(anchor=anchor, date_label=date_label, title=title))
    return links


def render_markdown(lines: list[str], plan: SourcePlan, day_links: list[DayLink]) -> str:
    parts: list[str] = []
    paragraph: list[str] = []
    table_rows: list[str] = []
    list_type: str | None = None
    section_open = False
    day_open = False
    skipped_first_title = False
    skip_first_h1 = plan.title if "theme" not in plan.meta else None
    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph).strip()
            if text:
                parts.append(f"        <p>{render_inline(text)}</p>")
        paragraph = []

    def close_table() -> None:
        nonlocal table_rows
        if table_rows:
            parts.append(table_html(table_rows))
        table_rows = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            parts.append(f"        </{list_type}>")
        list_type = None

    def close_flow() -> None:
        flush_paragraph()
        close_table()
        close_list()

    def close_section() -> None:
        nonlocal section_open, day_open
        if not section_open:
            return
        if day_open:
            parts.append("        </div>")
        parts.append("      </section>")
        section_open = False
        day_open = False

    def open_list(new_type: str, start: str | None = None) -> None:
        nonlocal list_type
        if list_type == new_type:
            return
        close_list()
        start_attr = f' start="{esc(start)}"' if new_type == "ol" and start else ""
        parts.append(f"        <{new_type}{start_attr}>")
        list_type = new_type

    for raw_line in lines:
        stripped = raw_line.strip()

        if is_table_line(stripped):
            flush_paragraph()
            close_list()
            table_rows.append(stripped)
            continue

        close_table()

        if not stripped:
            close_flow()
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            close_flow()
            marks, heading_text = heading.groups()
            level = len(marks)
            heading_text = heading_text.strip()

            if level == 1 and skip_first_h1 == heading_text and not skipped_first_title:
                skipped_first_title = True
                continue

            if plan.kind == "week-plan" and level == 2 and day_parts(heading_text):
                close_section()
                anchor = slugify(heading_text, "day")
                date_label, title = day_parts(heading_text) or (heading_text, "")
                parts.append(f'      <section class="day" id="{esc(anchor)}">')
                parts.append("        <div class=\"day-heading\">")
                parts.append(f"          <span class=\"day-date\">{esc(date_label)}</span>")
                parts.append(f"          <span class=\"day-title\">{render_inline(title)}</span>")
                parts.append("        </div>")
                parts.append("        <div class=\"day-body\">")
                section_open = True
                day_open = True
                continue

            close_section()
            html_level = min(max(level, 2), 4)
            if level == 1:
                html_level = 2
            parts.append("      <section>")
            parts.append(f"        <h{html_level}>{render_inline(heading_text)}</h{html_level}>")
            section_open = True
            continue

        unordered = stripped.startswith("- ")
        ordered_match = ORDERED_RE.match(stripped)
        if unordered or ordered_match:
            flush_paragraph()
            close_table()
            open_list("ul" if unordered else "ol", None if unordered else ordered_match.group(1))
            item = stripped[2:].strip() if unordered else ordered_match.group(2).strip()
            task_class = ""
            box = ""
            if item.startswith("[ ] "):
                item = item[4:].strip()
                task_class = ' class="task"'
                box = '<span class="task-box" aria-hidden="true"></span>'
            elif item.lower().startswith("[x] "):
                item = item[4:].strip()
                task_class = ' class="task done"'
                box = '<span class="task-box" aria-hidden="true"></span>'
            parts.append(f"          <li{task_class}>{box}{render_inline(item)}</li>")
            continue

        close_list()
        paragraph.append(stripped)

    close_flow()
    close_section()
    return "\n".join(parts)


def nav_href_for(kind: str) -> str:
    sources = sorted(MARKDOWN_DIR.glob(f"{kind}-*.md"))
    if not sources:
        return "index.html"
    source = sources[-1]
    return rel(output_path(source))


def nav_links(plan: SourcePlan) -> str:
    links = [
        ("Training plan", "index.html"),
    ]
    if plan.kind == "week-plan":
        links.append(("Quarterly plan", nav_href_for("quarter-plan")))
    else:
        links.append(("Current week", nav_href_for("week-plan")))
    if (MARKDOWN_DIR / "training-log.md").exists():
        links.append(("Training log", "training-log.html"))
    links.append(("Markdown source", rel(plan.source)))
    return "\n".join(f'        <a href="{esc(href)}">{esc(label)}</a>' for label, href in links)


def sidebar(day_links: list[DayLink]) -> str:
    if not day_links:
        return ""
    links = "\n".join(
        f"""          <a class="day-link" href="#{esc(link.anchor)}">
            <span class="day-link-date">{esc(link.date_label)}</span>
            <span class="day-link-title">{render_inline(link.title)}</span>
          </a>"""
        for link in day_links
    )
    return f"""      <aside class="day-sidebar" aria-label="Training days">
        <div class="day-sidebar-title">Days</div>
        <nav class="day-links">
{links}
        </nav>
      </aside>"""


def css() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f7f6f1;
      --paper: #fffdf7;
      --ink: #20231f;
      --muted: #686d63;
      --line: #d8d5ca;
      --accent: #2f6f5f;
      --accent-2: #8a5a24;
      --soft: #ebe7da;
      --table: #faf8f1;
      --focus: #356f95;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    a:hover { text-decoration: underline; }

    a:focus-visible {
      outline: 3px solid var(--focus);
      outline-offset: 3px;
    }

    code {
      padding: 0.06rem 0.22rem;
      border-radius: 4px;
      background: var(--soft);
      font-size: 0.92em;
    }

    .page {
      width: min(1120px, calc(100% - 40px));
      margin: 0 auto;
      padding: 44px 0 64px;
    }

    header {
      padding: 20px 0 30px;
      border-bottom: 2px solid var(--ink);
    }

    .eyebrow {
      margin: 0 0 10px;
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    h1 {
      max-width: 920px;
      margin: 0;
      font-size: clamp(1.55rem, 2.3vw, 2.3rem);
      line-height: 1.12;
      font-weight: 800;
    }

    .subtitle {
      max-width: 760px;
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 1.04rem;
    }

    header nav {
      display: flex;
      flex-wrap: wrap;
      gap: 14px 24px;
      padding: 18px 0 0;
      font-size: 0.93rem;
      font-weight: 700;
    }

    .weekly-layout {
      display: grid;
      grid-template-columns: 230px minmax(0, 1fr);
      gap: 40px;
      align-items: start;
    }

    .day-sidebar {
      position: sticky;
      top: 18px;
      padding-top: 30px;
    }

    .day-sidebar-title {
      margin-bottom: 10px;
      color: var(--accent-2);
      font-size: 0.74rem;
      font-weight: 850;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .day-links {
      display: grid;
      gap: 4px;
    }

    .day-link {
      display: block;
      padding: 9px 0 9px 12px;
      border-left: 3px solid var(--line);
      color: var(--ink);
      text-decoration: none;
    }

    .day-link:hover {
      color: var(--accent);
      text-decoration: none;
    }

    .day-link-date {
      display: block;
      font-size: 0.75rem;
      font-weight: 850;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .day-link-title {
      display: block;
      margin-top: 2px;
      font-size: 0.9rem;
      font-weight: 720;
      line-height: 1.18;
    }

    .weekly-content { min-width: 0; }

    section {
      padding: 30px 0;
      border-bottom: 1px solid var(--line);
    }

    section:last-of-type { border-bottom: 0; }

    h2 {
      margin: 0 0 16px;
      font-size: clamp(1.12rem, 1.55vw, 1.4rem);
      line-height: 1.18;
    }

    h3 {
      margin: 18px 0 10px;
      font-size: 1.02rem;
    }

    p {
      max-width: 800px;
      margin: 0 0 14px;
    }

    ul,
    ol {
      max-width: 860px;
      margin: 10px 0 0;
      padding-left: 1.25rem;
    }

    li + li { margin-top: 7px; }

    .task {
      list-style: none;
      display: flex;
      gap: 9px;
      align-items: baseline;
      margin-left: -1.25rem;
    }

    .task-box {
      width: 0.82rem;
      height: 0.82rem;
      flex: 0 0 auto;
      border: 1.5px solid var(--accent-2);
      transform: translateY(1px);
    }

    .task.done .task-box {
      background: var(--accent-2);
      box-shadow: inset 0 0 0 2px var(--bg);
    }

    .day {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 28px;
      padding: 26px 0;
    }

    .day-heading {
      color: var(--accent-2);
      font-size: 0.76rem;
      font-weight: 850;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .day-title {
      display: block;
      margin-top: 5px;
      color: var(--ink);
      font-size: 1.05rem;
      font-weight: 780;
      line-height: 1.2;
      letter-spacing: 0;
      text-transform: none;
    }

    .day-body h3 {
      margin-top: 0;
      color: var(--accent);
      font-size: 0.9rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 18px;
      background: var(--table);
      font-size: 0.94rem;
    }

    th {
      background: var(--soft);
      color: var(--ink);
      text-align: left;
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    th,
    td {
      padding: 13px 14px;
      border: 1px solid var(--line);
      vertical-align: top;
    }

    footer {
      padding-top: 24px;
      color: var(--muted);
      font-size: 0.88rem;
    }

    @media (max-width: 820px) {
      .page {
        width: min(100% - 28px, 1120px);
        padding-top: 24px;
      }

      .weekly-layout {
        grid-template-columns: 1fr;
        gap: 0;
      }

      .day-sidebar {
        position: static;
        padding: 20px 0 0;
      }

      .day {
        grid-template-columns: 1fr;
        gap: 12px;
      }

      table,
      thead,
      tbody,
      tr,
      th,
      td {
        display: block;
      }

      thead { display: none; }

      tr {
        border-top: 1px solid var(--line);
        padding: 14px 0;
      }

      td {
        border: 0;
        padding: 4px 0;
      }
    }

    @media print {
      body { background: #fff; }

      .page {
        width: 100%;
        padding: 0;
      }

      header nav,
      .day-sidebar {
        display: none;
      }

      section,
      .day {
        break-inside: avoid;
      }
    }
"""


def render_html(plan: SourcePlan) -> str:
    lines = strip_app_meta(plan.source.read_text(encoding="utf-8"))
    day_links = collect_day_links(lines) if plan.kind == "week-plan" else []
    body = render_markdown(lines, plan, day_links)
    eyebrow = "Weekly plan" if plan.kind == "week-plan" else "Quarterly plan"
    content = body
    if plan.kind == "week-plan" and day_links:
        content = f"""    <div class="weekly-layout">
{sidebar(day_links)}
      <div class="weekly-content">
{body}
      </div>
    </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(plan.title)}</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <style>{css()}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="eyebrow">{esc(eyebrow)}</p>
      <h1>{render_inline(plan.title)}</h1>
      <p class="subtitle">{esc(plan_range(plan))}.</p>
      <nav aria-label="Related files">
{nav_links(plan)}
      </nav>
    </header>

{content}

    <footer>
      Source retained in <a href="{esc(rel(plan.source))}">{esc(plan.source.name)}</a>.
    </footer>
  </main>
</body>
</html>
"""


def build_one(source: Path) -> Path:
    plan = read_source_plan(source)
    plan.output.write_text(render_html(plan), encoding="utf-8")
    return plan.output


def visible_sources() -> list[Path]:
    return sorted(MARKDOWN_DIR.glob("quarter-plan-*.md")) + sorted(MARKDOWN_DIR.glob("week-plan-*.md"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path, help="Plan markdown files. Defaults to all visible plans.")
    parser.add_argument("--all", action="store_true", help="Render all visible quarterly and weekly plans.")
    args = parser.parse_args()

    sources = visible_sources() if args.all or not args.sources else args.sources
    if not sources:
        raise SystemExit("No plan markdown files found.")

    for source in sources:
        output = build_one(source)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
