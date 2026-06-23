#!/usr/bin/env python3
"""Render markdown/advice-*.md files to root-level advice HTML pages."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
ADVICE_RE = re.compile(r"^advice-(\d{4}-\d{2}-\d{2})([a-z]?)\.md$")
WEEK_RE = re.compile(r"^week-plan-(\d{4}-\d{2}-\d{2})\.md$")
ORDERED_RE = re.compile(r"^(\d+)[.)]\s+(.+)$")
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


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_inline(value: str) -> str:
    rendered = esc(value)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    return rendered


def display_date(date_key: str) -> str:
    date = dt.date.fromisoformat(date_key)
    return f"{MONTH_NAMES[date.month]} {date.day}, {date.year}"


def advice_output_path(source: Path) -> Path:
    return REPO_ROOT / f"{source.stem}.html"


def relative_href(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def current_week_href(advice_date: dt.date) -> str:
    candidates: list[tuple[dt.date, Path]] = []
    for source in MARKDOWN_DIR.glob("week-plan-*.md"):
        match = WEEK_RE.match(source.name)
        if not match:
            continue
        start = dt.date.fromisoformat(match.group(1))
        if start <= advice_date:
            candidates.append((start, source))

    if not candidates:
        return "index.html"

    _, source = max(candidates, key=lambda item: item[0])
    html_path = REPO_ROOT / f"{source.stem}.html"
    return relative_href(html_path)


def advice_date_key(source: Path) -> str:
    match = ADVICE_RE.match(source.name)
    if not match:
        raise ValueError(f"Not an advice markdown file: {source}")
    return match.group(1)


def read_title(lines: list[str], source: Path) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return source.stem


def close_list(parts: list[str], list_type: str | None) -> None:
    if list_type:
        parts.append(f"        </{list_type}>")


def close_section(parts: list[str], section_open: bool) -> bool:
    if section_open:
        parts.append("      </section>")
    return False


def markdown_body(lines: list[str]) -> str:
    parts: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    section_open = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph).strip()
        if text:
            parts.append(f"        <p>{render_inline(text)}</p>")
        paragraph = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("# "):
            continue

        if not stripped:
            flush_paragraph()
            close_list(parts, list_type)
            list_type = None
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            close_list(parts, list_type)
            list_type = None
            section_open = close_section(parts, section_open)
            parts.append("      <section>")
            parts.append(f"        <h2>{render_inline(stripped[3:].strip())}</h2>")
            section_open = True
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            close_list(parts, list_type)
            list_type = None
            if not section_open:
                parts.append("      <section>")
                section_open = True
            parts.append(f"        <h3>{render_inline(stripped[4:].strip())}</h3>")
            continue

        ordered_match = ORDERED_RE.match(stripped)
        if stripped.startswith("- ") or ordered_match:
            flush_paragraph()
            if not section_open:
                parts.append("      <section>")
                section_open = True
            new_list_type = "ul" if stripped.startswith("- ") else "ol"
            if list_type != new_list_type:
                close_list(parts, list_type)
                start_attr = f' start="{esc(ordered_match.group(1))}"' if new_list_type == "ol" else ""
                parts.append(f"        <{new_list_type}{start_attr}>")
                list_type = new_list_type
            item = stripped[2:].strip() if new_list_type == "ul" else ordered_match.group(2).strip()
            parts.append(f"          <li>{render_inline(item)}</li>")
            continue

        close_list(parts, list_type)
        list_type = None
        paragraph.append(stripped)

    flush_paragraph()
    close_list(parts, list_type)
    close_section(parts, section_open)
    return "\n".join(parts)


def render_html(source: Path, output: Path) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
    title = read_title(lines, source)
    date_key = advice_date_key(source)
    advice_date = dt.date.fromisoformat(date_key)
    week_href = current_week_href(advice_date)
    body = markdown_body(lines)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Advice | {esc(display_date(date_key))}</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f6f1;
      --ink: #20231f;
      --muted: #686d63;
      --line: #d8d5ca;
      --accent: #2f6f5f;
      --accent-2: #8a5a24;
      --soft: #ebe7da;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}

    a {{
      color: var(--accent);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    code {{
      padding: 0.06rem 0.22rem;
      border-radius: 4px;
      background: var(--soft);
      font-size: 0.92em;
    }}

    .page {{
      width: min(1040px, calc(100% - 40px));
      margin: 0 auto;
      padding: 44px 0 64px;
    }}

    header {{
      padding: 20px 0 30px;
      border-bottom: 2px solid var(--ink);
    }}

    .eyebrow {{
      margin: 0 0 10px;
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1 {{
      max-width: 860px;
      margin: 0;
      font-size: clamp(1.55rem, 2.3vw, 2.25rem);
      line-height: 1.12;
      font-weight: 800;
    }}

    .subtitle {{
      max-width: 760px;
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 1.04rem;
    }}

    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px 24px;
      padding: 18px 0 0;
      font-size: 0.93rem;
      font-weight: 700;
    }}

    section {{
      padding: 28px 0;
      border-bottom: 1px solid var(--line);
    }}

    h2 {{
      margin: 0 0 16px;
      font-size: clamp(1.12rem, 1.55vw, 1.4rem);
      line-height: 1.18;
    }}

    h3 {{
      margin: 18px 0 10px;
      font-size: 1.02rem;
    }}

    p {{
      max-width: 800px;
      margin: 0 0 14px;
    }}

    ul {{
      max-width: 860px;
      margin: 10px 0 0;
      padding-left: 1.25rem;
    }}

    li + li {{
      margin-top: 7px;
    }}

    footer {{
      padding-top: 24px;
      color: var(--muted);
      font-size: 0.88rem;
    }}

    @media (max-width: 760px) {{
      .page {{
        width: min(100% - 28px, 1040px);
        padding-top: 24px;
      }}
    }}

    @media print {{
      body {{
        background: #fff;
      }}

      .page {{
        width: 100%;
        padding: 0;
      }}

      nav {{
        display: none;
      }}

      section {{
        break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="eyebrow">Daily advice</p>
      <h1>{render_inline(title)}</h1>
      <p class="subtitle">Advice dated {esc(display_date(date_key))}.</p>
      <nav aria-label="Related files">
        <a href="index.html">Training plan</a>
        <a href="{esc(week_href)}">Current week</a>
        <a href="training-log.html">Training log</a>
      </nav>
    </header>

{body}
  </main>
</body>
</html>
"""


def build_one(source: Path) -> Path:
    source = source.resolve()
    output = advice_output_path(source)
    output.write_text(render_html(source, output), encoding="utf-8")
    return output


def visible_sources() -> list[Path]:
    return sorted(MARKDOWN_DIR.glob("advice-*.md"))


def latest_source() -> list[Path]:
    sources = visible_sources()
    if not sources:
        return []
    return [max(sources, key=lambda source: source.name)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path, help="Advice markdown files. Defaults to the latest visible advice file.")
    parser.add_argument("--all", action="store_true", help="Render all visible advice markdown files.")
    args = parser.parse_args()

    sources = visible_sources() if args.all else (args.sources or latest_source())
    if not sources:
        raise SystemExit("No advice markdown files found.")

    for source in sources:
        output = build_one(source)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
