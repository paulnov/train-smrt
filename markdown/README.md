# Markdown Source

This directory contains the editable source files for the training coach.

- `quarter-plan-YYYY-MM.md`: quarterly goals, constraints, and coach roadmap.
- `week-plan-YYYY-MM-DD.md`: weekly plan plus user-owned report sections.
- `advice-YYYY-MM-DD.md`: daily advice generated when requested.
- `training-log.md`: append-only durable workout history.
- `notes-on-user.md`: lean coach notebook for stable athlete context.
- `archive/`: old weekly plans, advice files, and quarterly plans renamed with an `archive-` prefix.

User-facing HTML files are generated in the repository root. After changing training-facing Markdown, run the relevant renderer in `code/`, then rebuild the homepage with `python3 code/build_index_html.py`.
