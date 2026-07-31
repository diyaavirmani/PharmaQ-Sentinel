from __future__ import annotations

import html
import json
from typing import Any

from app.services.reports.complaint_brief_schema import ComplaintBrief


def _text(value: Any) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return str(value)


def _cell(value: Any) -> str:
    return html.escape(_text(value))


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>Not available.</p>"
    keys = sorted({key for row in rows for key in row})
    head = "".join(f"<th>{html.escape(key.replace('_', ' ').title())}</th>" for key in keys)
    body = "".join(
        "<tr>" + "".join(f"<td><pre>{_cell(row.get(key))}</pre></td>" for key in keys) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_complaint_brief_html(brief: ComplaintBrief) -> str:
    sections = []
    for section in brief.sections:
        fields = "".join(
            f"<div><dt>{html.escape(field.label)}</dt><dd>{_cell(field.value)}</dd></div>"
            for field in section.fields
        )
        notes = "".join(f"<li>{_cell(note)}</li>" for note in section.notes)
        sections.append(
            f"""
            <section>
              <h2>{html.escape(section.title)}</h2>
              {f"<dl>{fields}</dl>" if fields else ""}
              {_table(section.rows) if section.rows else ""}
              {f"<ul>{notes}</ul>" if notes else ""}
            </section>
            """
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(brief.document_identifier)}</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; color: #172033; margin: 32px; line-height: 1.45; }}
    header {{ border-bottom: 2px solid #6d4aff; margin-bottom: 24px; padding-bottom: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    h2 {{ border-bottom: 1px solid #d9deea; font-size: 18px; margin-top: 28px; padding-bottom: 6px; }}
    .disclaimer {{ background: #fff7ed; border: 1px solid #f59e0b; padding: 12px; }}
    dl {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; }}
    dt {{ color: #5b6475; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    dd {{ margin: 2px 0 0; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #d9deea; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f5f7fb; font-size: 12px; }}
    pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(brief.title)}</h1>
    <p><strong>Document:</strong> {html.escape(brief.document_identifier)}</p>
    <p><strong>Generated:</strong> {html.escape(brief.generated_at.isoformat())}</p>
    <p class="disclaimer">{html.escape(brief.disclaimer)}</p>
  </header>
  {''.join(sections)}
</body>
</html>"""
