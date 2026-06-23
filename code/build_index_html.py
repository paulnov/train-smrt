#!/usr/bin/env python3
"""Build the static training-plan homepage and file manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
DEFAULT_OUTPUT = REPO_ROOT / "index.html"
DEFAULT_MANIFEST = REPO_ROOT / "site-index.json"

PLAN_RE = re.compile(r"^(quarter-plan|week-plan|advice)-(\d{4}-\d{2}(?:-\d{2})?)([a-z]?)\.md$")
APP_INDEX_RE = re.compile(r"<!--\s*app-index\s*(.*?)-->", re.DOTALL | re.IGNORECASE)
TRAINING_ENTRY_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+--\s+(.+?)\s*$")
WEEK_DAY_RE = re.compile(
    r"^#{2,4}\s+"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?\s+"
    r"(\d{1,2})/(\d{1,2})\b",
    re.IGNORECASE,
)
ISO_DAY_RE = re.compile(r"^#{2,4}.*?(\d{4}-\d{2}-\d{2})\b")
QUARTER_RANGE_RE = re.compile(
    r"Quarterly Plan,\s+([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*"
    r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
    re.IGNORECASE,
)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
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
class PlanFile:
    kind: str
    date_key: str
    suffix: str
    source_path: Path
    html_path: Path
    start: dt.date
    end: dt.date
    dates: tuple[dt.date, ...]
    title: str
    meta: dict[str, str]

    @property
    def html_exists(self) -> bool:
        return self.html_path.exists()

    @property
    def primary_path(self) -> Path:
        return self.html_path if self.html_exists else self.source_path


def parse_iso_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def esc(value: str) -> str:
    return html.escape(value, quote=True)


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


def read_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem


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


def quarter_range(path: Path, fallback: dt.date, meta: dict[str, str]) -> tuple[dt.date, dt.date, tuple[dt.date, ...]]:
    if "start" in meta and "end" in meta:
        return parse_iso_date(meta["start"]), parse_iso_date(meta["end"]), ()

    text = path.read_text(encoding="utf-8")
    match = QUARTER_RANGE_RE.search(text)
    if not match:
        return fallback, fallback + dt.timedelta(days=120), ()

    start_month_name, start_day, end_month_name, end_day, end_year = match.groups()
    start_month = MONTHS[start_month_name.lower()]
    end_month = MONTHS[end_month_name.lower()]
    end_year_int = int(end_year)
    start_year = end_year_int if start_month <= end_month else end_year_int - 1
    start = dt.date(start_year, start_month, int(start_day))
    end = dt.date(end_year_int, end_month, int(end_day))
    return start, end, ()


def week_dates(path: Path, start: dt.date) -> tuple[dt.date, dt.date, tuple[dt.date, ...]]:
    dates: list[dt.date] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        iso_match = ISO_DAY_RE.match(line)
        if iso_match:
            dates.append(parse_iso_date(iso_match.group(1)))
            continue

        day_match = WEEK_DAY_RE.match(line)
        if not day_match:
            continue

        month = int(day_match.group(1))
        day = int(day_match.group(2))
        year = start.year
        parsed = dt.date(year, month, day)
        if parsed < start - dt.timedelta(days=180):
            parsed = dt.date(year + 1, month, day)
        elif parsed > start + dt.timedelta(days=180):
            parsed = dt.date(year - 1, month, day)
        dates.append(parsed)

    if not dates:
        dates = [start + dt.timedelta(days=offset) for offset in range(7)]

    unique_dates = tuple(sorted(set(dates)))
    return unique_dates[0], unique_dates[-1], unique_dates


def html_partner(markdown_path: Path) -> Path:
    return REPO_ROOT / f"{markdown_path.stem}.html"


def collect_plan_files() -> list[PlanFile]:
    plans: list[PlanFile] = []
    for source in sorted(MARKDOWN_DIR.glob("*.md")):
        match = PLAN_RE.match(source.name)
        if not match:
            continue

        kind, date_key, suffix = match.groups()
        html_path = html_partner(source)
        title = read_title(source)
        meta = read_app_meta(source)

        if kind == "quarter-plan":
            start = dt.date.fromisoformat(f"{date_key}-01")
            end = start + dt.timedelta(days=120)
            start, end, dates = quarter_range(source, start, meta)
        elif kind == "week-plan":
            start = parse_iso_date(date_key)
            start, end, dates = week_dates(source, start)
        else:
            start = parse_iso_date(date_key)
            end = start
            dates = (start,)

        plans.append(
            PlanFile(
                kind=kind,
                date_key=date_key,
                suffix=suffix,
                source_path=source,
                html_path=html_path,
                start=start,
                end=end,
                dates=dates,
                title=title,
                meta=meta,
            )
        )

    return plans


def choose_current(plans: list[PlanFile], kind: str, today: dt.date) -> PlanFile | None:
    candidates = [plan for plan in plans if plan.kind == kind]
    if not candidates:
        return None

    covering = [plan for plan in candidates if plan.start <= today <= plan.end]
    if covering:
        return max(covering, key=lambda plan: (plan.start, plan.end, plan.suffix))

    past = [plan for plan in candidates if plan.start <= today]
    if past:
        return max(past, key=lambda plan: (plan.start, plan.end, plan.suffix))

    return min(candidates, key=lambda plan: (plan.start, plan.end, plan.suffix))


def plan_to_manifest(plan: PlanFile) -> dict[str, object]:
    return {
        "kind": plan.kind,
        "date_key": plan.date_key,
        "suffix": plan.suffix,
        "title": plan.title,
        "theme": plan.meta.get("theme", plan.title),
        "source": rel(plan.source_path),
        "html": rel(plan.html_path),
        "href": rel(plan.primary_path),
        "html_exists": plan.html_exists,
        "start": plan.start.isoformat(),
        "end": plan.end.isoformat(),
        "display_date": display_date(plan.start),
        "display_range": display_range(plan.start, plan.end),
        "dates": [date.isoformat() for date in plan.dates],
    }


def training_log_entries(path: Path, limit: int = 3) -> list[dict[str, object]]:
    if not path.exists():
        return []

    entries: list[tuple[dt.date, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = TRAINING_ENTRY_RE.match(line)
        if match:
            entries.append((parse_iso_date(match.group(1)), match.group(2).strip()))

    html_path = REPO_ROOT / "training-log.html"
    href = rel(html_path) if html_path.exists() else rel(path)
    return [
        {
            "date": date.isoformat(),
            "display_date": display_date(date),
            "label": label,
            "href": href,
        }
        for date, label in reversed(entries[-limit:])
    ]


def build_manifest(plans: list[PlanFile], today: dt.date) -> dict[str, object]:
    training_log_path = MARKDOWN_DIR / "training-log.md"
    training_log_html = REPO_ROOT / "training-log.html"
    log_entries = training_log_entries(training_log_path)
    active = {
        kind: (plan_to_manifest(plan) if plan else None)
        for kind, plan in {
            "quarter-plan": choose_current(plans, "quarter-plan", today),
            "week-plan": choose_current(plans, "week-plan", today),
            "advice": choose_current(plans, "advice", today),
        }.items()
    }

    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "build_date": today.isoformat(),
        "files": [plan_to_manifest(plan) for plan in plans],
        "active": active,
        "training_log": {
            "title": "Training Log",
            "href": rel(training_log_html) if training_log_html.exists() else rel(training_log_path),
            "html_exists": training_log_html.exists(),
            "source": "markdown/training-log.md",
            "entries": log_entries,
            "latest": log_entries[0] if log_entries else None,
        },
    }


def validate_manifest(manifest: dict[str, object]) -> None:
    for label in ("quarter-plan", "week-plan", "advice"):
        active_file = manifest["active"].get(label)
        if not active_file or active_file["html_exists"]:
            continue

        source = active_file["source"]
        html_path = active_file["html"]
        if label == "advice":
            command = f"python3 code/build_advice_html.py {source}"
        else:
            command = f"python3 code/build_plan_html.py {source}"
        raise SystemExit(
            f"Active {label} is missing its root HTML page. "
            f"Run `{command}` before rebuilding the index. "
            f"Expected: {html_path}"
        )


def static_home(manifest: dict[str, object]) -> tuple[str, str]:
    active = manifest["active"]
    quarter = active.get("quarter-plan")
    week = active.get("week-plan")
    advice = active.get("advice")
    training_log = manifest["training_log"]
    log_entries = training_log.get("entries", []) if training_log else []

    plan_html = "\n".join(
        [
            plan_row(
                "Current quarterly plan",
                quarter,
                str(quarter["theme"]) if quarter else "No current quarterly plan",
                str(quarter["display_range"]) if quarter else "",
            ),
            plan_row(
                "Current weekly plan",
                week,
                str(week["theme"]) if week else "No current weekly plan",
                str(week["display_range"]) if week else "",
            ),
            plan_row(
                "Last daily plan",
                advice,
                str(advice["display_date"]) if advice else "No daily advice yet",
                "",
            ),
        ]
    )
    logs_html = log_list(log_entries, str(training_log["href"]) if training_log else "#")
    return plan_html, logs_html


def plan_row(label: str, file: dict[str, object] | None, title: str, meta: str) -> str:
    href = str(file["href"]) if file else "#"
    return f"""        <a class="plan-row" href="{esc(href)}">
          <span class="row-label">{esc(label)}</span>
          <span class="row-main">{esc(title)}</span>
          <span class="row-meta">{esc(meta)}</span>
        </a>"""


def log_list(entries: list[dict[str, object]], fallback_href: str) -> str:
    if not entries:
        return f"""        <li>
          <a href="{esc(fallback_href)}">
            <time></time>
            <span>No training logged yet</span>
          </a>
        </li>"""

    items = []
    for entry in entries:
        items.append(
            f"""        <li>
          <a href="{esc(str(entry["href"]))}">
            <time datetime="{esc(str(entry["date"]))}">{esc(str(entry["display_date"]))}</time>
            <span>{esc(str(entry["label"]))}</span>
          </a>
        </li>"""
        )
    return "\n".join(items)


def client_file(file: dict[str, object] | None) -> dict[str, object] | None:
    if file is None:
        return None
    return {
        "kind": file["kind"],
        "suffix": file["suffix"],
        "theme": file["theme"],
        "href": file["href"],
        "start": file["start"],
        "end": file["end"],
        "display_date": file["display_date"],
        "display_range": file["display_range"],
    }


def client_manifest(manifest: dict[str, object]) -> dict[str, object]:
    active = manifest["active"]
    training_log = manifest["training_log"]
    return {
        "files": [client_file(file) for file in manifest["files"]],
        "active": {
            "quarter-plan": client_file(active.get("quarter-plan")),
            "week-plan": client_file(active.get("week-plan")),
            "advice": client_file(active.get("advice")),
        },
        "training_log": {
            "href": training_log["href"],
            "entries": training_log.get("entries", []),
            "latest": training_log.get("latest"),
        },
    }


def render_html(manifest: dict[str, object]) -> str:
    manifest_json = json.dumps(client_manifest(manifest), indent=2, sort_keys=True)
    build_date = display_date(parse_iso_date(str(manifest["build_date"])))
    plan_html, logs_html = static_home(manifest)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Training plan</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f6f1;
      --ink: #171b19;
      --muted: #666f68;
      --line: #d9d6cb;
      --accent: #2f6f5f;
      --accent-2: #8a5a24;
      --focus: #356f95;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    a:focus-visible {{
      outline: 3px solid var(--focus);
      outline-offset: 3px;
    }}

    .page {{
      width: min(880px, calc(100% - 40px));
      margin: 0 auto;
      padding: 34px 0 34px;
    }}

    header {{
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}

    .site-title {{
      margin: 0;
      color: var(--accent);
      font-size: 0.84rem;
      font-weight: 850;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    .plan-stack {{
      padding-top: 18px;
    }}

    .plan-row {{
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr) 185px;
      gap: 18px;
      align-items: baseline;
      padding: 16px 0;
      border-bottom: 1px solid var(--line);
    }}

    .plan-row:hover .row-main,
    .log-list a:hover span {{
      color: var(--accent);
    }}

    .row-label,
    .section-label {{
      color: var(--accent-2);
      font-size: 0.78rem;
      font-weight: 850;
      letter-spacing: 0;
      text-transform: uppercase;
    }}

    .row-main {{
      font-size: 1.08rem;
      font-weight: 760;
      line-height: 1.28;
    }}

    .row-meta {{
      color: var(--muted);
      font-size: 0.92rem;
      text-align: right;
    }}

    .log-section {{
      padding-top: 28px;
    }}

    .log-list {{
      margin: 8px 0 0;
      padding: 0;
      list-style: none;
      border-top: 1px solid var(--line);
    }}

    .log-list a {{
      display: grid;
      grid-template-columns: 160px minmax(0, 1fr);
      gap: 18px;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
    }}

    .log-list time {{
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .log-list span {{
      font-size: 0.98rem;
      font-weight: 650;
    }}

    .build-stamp {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.68rem;
      opacity: 0.45;
      text-align: right;
    }}

    @media (max-width: 720px) {{
      .page {{
        width: min(100% - 28px, 880px);
        padding-top: 24px;
      }}

      .plan-row,
      .log-list a {{
        grid-template-columns: 1fr;
        gap: 4px;
      }}

      .row-meta {{
        text-align: left;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="site-title">Training plan</p>
    </header>

    <section class="plan-stack" aria-label="Current training plan" id="plan-stack">
{plan_html}
    </section>

    <section class="log-section" aria-label="Recent training log">
      <div class="section-label">Recent log</div>
      <ol class="log-list" id="log-list">
{logs_html}
      </ol>
    </section>

    <footer class="build-stamp">Built {esc(build_date)}</footer>
  </main>

  <script type="application/json" id="site-manifest">
{manifest_json}
  </script>
  <script>
    const manifest = JSON.parse(document.getElementById("site-manifest").textContent);
    const files = manifest.files || [];

    function localDateString(date) {{
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${{year}}-${{month}}-${{day}}`;
    }}

    const today = localDateString(new Date());

    function byKind(kind) {{
      return files.filter((file) => file.kind === kind);
    }}

    function choose(kind) {{
      const candidates = byKind(kind);
      if (!candidates.length) return null;

      const covering = candidates.filter((file) => file.start <= today && today <= file.end);
      if (covering.length) {{
        return covering.sort(compareFiles)[covering.length - 1];
      }}

      const past = candidates.filter((file) => file.start <= today);
      if (past.length) {{
        return past.sort(compareFiles)[past.length - 1];
      }}

      return candidates.sort(compareFiles)[0];
    }}

    function compareFiles(left, right) {{
      const leftKey = `${{left.start}}|${{left.end}}|${{left.suffix || ""}}`;
      const rightKey = `${{right.start}}|${{right.end}}|${{right.suffix || ""}}`;
      return leftKey.localeCompare(rightKey);
    }}

    function escapeHtml(value) {{
      return String(value || "").replace(/[&<>"']/g, (character) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\\"": "&quot;",
        "'": "&#39;"
      }}[character]));
    }}

    function planRow(label, file, title, meta) {{
      const href = file?.href || "#";
      return `<a class="plan-row" href="${{escapeHtml(href)}}">
        <span class="row-label">${{escapeHtml(label)}}</span>
        <span class="row-main">${{escapeHtml(title)}}</span>
        <span class="row-meta">${{escapeHtml(meta)}}</span>
      </a>`;
    }}

    function logRows(entries, fallbackHref) {{
      if (!entries?.length) {{
        return `<li><a href="${{escapeHtml(fallbackHref || "#")}}"><time></time><span>No training logged yet</span></a></li>`;
      }}
      return entries.map((entry) => `<li>
        <a href="${{escapeHtml(entry.href || fallbackHref || "#")}}">
          <time datetime="${{escapeHtml(entry.date)}}">${{escapeHtml(entry.display_date)}}</time>
          <span>${{escapeHtml(entry.label)}}</span>
        </a>
      </li>`).join("");
    }}

    const active = {{
      quarter: choose("quarter-plan") || manifest.active?.["quarter-plan"],
      week: choose("week-plan") || manifest.active?.["week-plan"],
      advice: choose("advice") || manifest.active?.advice
    }};

    document.getElementById("plan-stack").innerHTML = [
      planRow("Current quarterly plan", active.quarter, active.quarter?.theme || "No current quarterly plan", active.quarter?.display_range || ""),
      planRow("Current weekly plan", active.week, active.week?.theme || "No current weekly plan", active.week?.display_range || ""),
      planRow("Last daily plan", active.advice, active.advice?.display_date || "No daily advice yet", "")
    ].join("");

    document.getElementById("log-list").innerHTML =
      logRows(manifest.training_log?.entries, manifest.training_log?.href);
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Build fallback date, YYYY-MM-DD.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, type=Path)
    args = parser.parse_args()

    today = parse_iso_date(args.date)
    plans = collect_plan_files()
    manifest = build_manifest(plans, today)
    validate_manifest(manifest)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output.write_text(render_html(manifest), encoding="utf-8")
    print(f"Wrote {args.output} and {args.manifest} with {len(plans)} indexed files.")


if __name__ == "__main__":
    main()
