"""
Append today's results to a running history file and render docs/index.html.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
RESULTS_FILE = DATA_DIR / "results.json"
HISTORY_FILE = DOCS_DIR / "history.json"

VERDICT_LABEL = {
    "clean": ("Clean", "#1a7f37"),
    "minor_issues": ("Minor issues", "#9a6700"),
    "significant_issues": ("Significant issues", "#cf222e"),
    "error": ("Check failed", "#57606a"),
}


def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def save_history(history):
    DOCS_DIR.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def render_entry(entry, run_date):
    verdict = entry.get("overall_verdict", "error")
    label, color = VERDICT_LABEL.get(verdict, ("Unknown", "#57606a"))
    flags_html = "".join(
        f"""<li><strong>{f.get('severity','?').upper()}</strong> — {f.get('claim','')}
             <br><span class="issue">{f.get('issue','')}</span></li>"""
        for f in entry.get("flags", [])
    )
    return f"""
    <div class="card">
      <div class="card-head">
        <a href="{entry.get('url','#')}" target="_blank">{entry.get('title','(untitled)')}</a>
        <span class="badge" style="background:{color}">{label}</span>
      </div>
      <div class="meta">Checked: {run_date}</div>
      <p class="summary">{entry.get('summary','')}</p>
      {f'<ul class="flags">{flags_html}</ul>' if flags_html else ''}
    </div>
    """


def main():
    if not RESULTS_FILE.exists():
        today_results = {"date": "", "results": []}
    else:
        today_results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

    history = load_history()
    if today_results["results"]:
        history.insert(0, today_results)
    save_history(history)

    cards = ""
    for run in history[:30]:  # cap dashboard to last 30 runs
        for entry in run["results"]:
            cards += render_entry(entry, run["date"])

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Arabica Watch</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Tahoma, sans-serif; max-width: 900px;
          margin: 40px auto; padding: 0 20px; background: #f6f8fa; color: #1f2328; }}
  h1 {{ font-size: 22px; }}
  .card {{ background: #fff; border: 1px solid #d0d7de; border-radius: 8px;
           padding: 16px; margin-bottom: 14px; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; }}
  .card-head a {{ font-weight: 600; text-decoration: none; color: #0969da; }}
  .badge {{ color: #fff; font-size: 12px; padding: 3px 10px; border-radius: 12px; }}
  .meta {{ font-size: 12px; color: #57606a; margin-top: 4px; }}
  .summary {{ margin: 10px 0 6px; }}
  .flags {{ margin: 8px 0 0; padding-inline-start: 18px; }}
  .flags li {{ margin-bottom: 6px; font-size: 14px; }}
  .issue {{ color: #57606a; font-size: 13px; }}
  .empty {{ color: #57606a; }}
</style>
</head>
<body>
  <h1>Arabica Watch — Daily Fact-Check Dashboard</h1>
  <p class="meta">Auto-updated daily by GitHub Actions. Shows new Arabica entries and Claude's fact-check findings.</p>
  {cards if cards else '<p class="empty">No entries checked yet.</p>'}
</body>
</html>"""

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print("Dashboard written to docs/index.html")


if __name__ == "__main__":
    main()
