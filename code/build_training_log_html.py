#!/usr/bin/env python3
"""Convert markdown/training-log.md to a clean, expandable HTML view."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path


EXPECTED_FIELDS = [
    "Plan target",
    "Raw report",
    "Session type",
    "Load signal",
    "Plan match",
    "Training implication",
]

ENTRY_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+--\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^-\s+\*\*(.+?):\*\*\s*(.*)$")
REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
DEFAULT_INPUT = REPO_ROOT / "markdown" / "training-log.md"
DEFAULT_OUTPUT = REPO_ROOT / "training-log.html"


@dataclass
class Entry:
    date: str
    label: str
    fields: dict[str, str]


def clean_markdown_inline(value: str) -> str:
    value = value.strip()
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    return value


def parse_training_log(path: Path) -> list[Entry]:
    entries: list[Entry] = []
    current: Entry | None = None
    current_field: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        entry_match = ENTRY_RE.match(raw_line)
        if entry_match:
            current = Entry(
                date=entry_match.group(1),
                label=entry_match.group(2).strip(),
                fields={},
            )
            entries.append(current)
            current_field = None
            continue

        if current is None:
            continue

        field_match = FIELD_RE.match(raw_line)
        if field_match:
            field = field_match.group(1).strip()
            value = clean_markdown_inline(field_match.group(2))
            current.fields[field] = value
            current_field = field
            continue

        if current_field and raw_line.strip():
            addition = clean_markdown_inline(raw_line.strip())
            previous = current.fields.get(current_field, "")
            current.fields[current_field] = f"{previous} {addition}".strip()

    return entries


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def relative_href(path: Path, output: Path) -> str:
    try:
        return path.resolve().relative_to(output.resolve().parent).as_posix()
    except ValueError:
        return path.as_posix()


def latest_plan_href(prefix: str, output: Path) -> str:
    sources = sorted(MARKDOWN_DIR.glob(f"{prefix}-*.md"))
    if not sources:
        return "index.html"
    source = sources[-1]
    html_path = REPO_ROOT / f"{source.stem}.html"
    return relative_href(html_path, output)


def field_html(field: str, value: str) -> str:
    value = value or "Unknown"
    return f"""
          <div class="field">
            <dt>{esc(field)}</dt>
            <dd>{esc(value)}</dd>
          </div>"""


def entry_html(entry: Entry, index: int, initial_visible: int) -> str:
    fields = "\n".join(field_html(field, entry.fields.get(field, "")) for field in EXPECTED_FIELDS)
    hidden_attr = " hidden" if index >= initial_visible else ""
    return f"""
      <article class="entry" data-entry-index="{index}"{hidden_attr}>
        <div class="entry-head">
          <time datetime="{esc(entry.date)}">{esc(entry.date)}</time>
          <h2>{esc(entry.label)}</h2>
        </div>
        <dl class="fields">
{fields}
        </dl>
      </article>"""


def render_html(entries: list[Entry], source: Path, output: Path) -> str:
    newest_first = list(reversed(entries))
    initial_visible = 5
    rendered_entries = "\n".join(
        entry_html(entry, index, initial_visible) for index, entry in enumerate(newest_first)
    )
    week_href = latest_plan_href("week-plan", output)
    quarter_href = latest_plan_href("quarter-plan", output)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Training Log</title>
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f6f1;
      --paper: #fffdf7;
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

    .page {{
      width: min(1080px, calc(100% - 40px));
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
      max-width: 720px;
      margin: 22px 0 0;
      color: var(--muted);
      font-size: 1.08rem;
    }}

    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px 24px;
      padding: 18px 0 0;
      font-size: 0.93rem;
      font-weight: 700;
    }}

    .entries {{
      padding-top: 16px;
    }}

    .entry {{
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: 32px;
      padding: 28px 0;
      border-bottom: 1px solid var(--line);
    }}

    .entry[hidden] {{
      display: none;
    }}

    .entry-head time {{
      color: var(--accent-2);
      font-size: 0.86rem;
      font-weight: 850;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}

    .entry-head h2 {{
      margin: 7px 0 0;
      font-size: 1.35rem;
      line-height: 1.12;
    }}

    .fields {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 13px;
      margin: 0;
    }}

    .field {{
      display: grid;
      grid-template-columns: 170px minmax(0, 1fr);
      gap: 20px;
      padding-top: 13px;
      border-top: 1px solid var(--line);
    }}

    .field:first-child {{
      padding-top: 0;
      border-top: 0;
    }}

    dt {{
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 850;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    dd {{
      margin: 0;
    }}

    .controls {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      padding-top: 24px;
    }}

    button {{
      appearance: none;
      border: 1px solid var(--ink);
      background: var(--ink);
      color: var(--paper);
      min-height: 42px;
      padding: 0 16px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }}

    button.secondary {{
      background: transparent;
      color: var(--ink);
    }}

    button[hidden] {{
      display: none;
    }}

    .count {{
      color: var(--muted);
      font-size: 0.92rem;
    }}

    footer {{
      padding-top: 24px;
      color: var(--muted);
      font-size: 0.88rem;
    }}

    @media (max-width: 780px) {{
      .page {{
        width: min(100% - 28px, 1080px);
        padding-top: 24px;
      }}

      .entry,
      .field {{
        grid-template-columns: 1fr;
        gap: 8px;
      }}

      .entry {{
        padding: 24px 0;
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

      nav,
      .controls {{
        display: none;
      }}

      .entry {{
        break-inside: avoid;
      }}

      .entry[hidden] {{
        display: grid;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="eyebrow">Training log</p>
      <h1>Recent training, parsed from the durable log fields.</h1>
      <p class="subtitle">Newest entries are shown first. The default view shows the latest five sessions; expand in ten-entry blocks for older history.</p>
      <nav aria-label="Related files">
        <a href="{esc(week_href)}">Current week</a>
        <a href="{esc(quarter_href)}">Quarterly plan</a>
      </nav>
    </header>

    <section class="entries" aria-live="polite">
{rendered_entries}
    </section>

    <div class="controls">
      <button type="button" id="show-more">Show 10 more</button>
      <button type="button" id="collapse" class="secondary">Collapse to latest 5</button>
      <span class="count" id="entry-count"></span>
    </div>
  </main>

  <script>
    const entries = Array.from(document.querySelectorAll(".entry"));
    const showMore = document.getElementById("show-more");
    const collapse = document.getElementById("collapse");
    const count = document.getElementById("entry-count");
    const initialVisible = 5;
    const increment = 10;
    let visible = Math.min(initialVisible, entries.length);

    function render() {{
      entries.forEach((entry, index) => {{
        entry.hidden = index >= visible;
      }});
      const hidden = Math.max(entries.length - visible, 0);
      count.textContent = `${{Math.min(visible, entries.length)}} of ${{entries.length}} entries shown`;
      showMore.hidden = hidden === 0;
      showMore.textContent = hidden > increment ? "Show 10 more" : `Show ${{hidden}} more`;
      collapse.hidden = visible <= initialVisible;
    }}

    showMore.addEventListener("click", () => {{
      visible = Math.min(visible + increment, entries.length);
      render();
    }});

    collapse.addEventListener("click", () => {{
      visible = Math.min(initialVisible, entries.length);
      render();
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }});

    render();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    args = parser.parse_args()

    entries = parse_training_log(args.input)
    args.output.write_text(render_html(entries, args.input, args.output), encoding="utf-8")
    print(f"Wrote {args.output} with {len(entries)} entries.")


if __name__ == "__main__":
    main()
