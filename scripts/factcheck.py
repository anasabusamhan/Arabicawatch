"""
Fetch each new entry's full text and fact-check it via the Claude API
(with the web search tool enabled), producing a structured verdict per entry.
"""

import json
import os
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEW_ENTRIES_FILE = DATA_DIR / "new_entries.json"
RESULTS_FILE = DATA_DIR / "results.json"

MODEL = "claude-sonnet-4-6"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
}

FACTCHECK_PROMPT = """\
You are fact-checking an entry from the Arabica Arabic-language encyclopedia
(published by the Arab Center for Research and Policy Studies). Below is the
entry's title and body text.

Your job:
1. Identify the concrete factual claims in the text (dates, figures, names,
   causal/historical statements).
2. Use web search to verify each one against reliable, independent sources.
3. Flag anything that is unsupported, outdated, contradicted by sources, or
   where the entry's citations don't actually say what's claimed.
4. Note anything that reads as opinion/editorializing rather than neutral
   encyclopedic description.

Respond ONLY with valid JSON, no markdown fences, in this exact shape:
{{
  "overall_verdict": "clean" | "minor_issues" | "significant_issues",
  "summary": "one or two sentence summary in Arabic",
  "flags": [
    {{"claim": "...", "issue": "...", "severity": "low" | "medium" | "high"}}
  ]
}}

Title: {title}

Body:
{body}
"""


def fetch_entry_text(url: str) -> str:
    """Fetch an entry page and extract its body text.

    Selectors verified against the live site's rendered markup:
    the article body lives in `.arabica_article-content`. That container
    also holds a couple of hidden SharePoint editor-chrome elements - an
    accessibility label reading "EncCustomPageContent" (inline
    `style="display:none"`) and an image-delete confirmation dialog hidden
    via a CSS class rather than inline style - which are stripped out below
    so they don't pollute the extracted text.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_el = soup.select_one(".arabica_article-content")
    if content_el is None:
        return ""

    junk_selectors = [
        '[style*="display:none"]',
        '[style*="display: none"]',
        ".del-modal-bg",
        ".del-overlay",
    ]
    for selector in junk_selectors:
        for el in content_el.select(selector):
            el.decompose()

    return content_el.get_text(" ", strip=True)


def factcheck_entry(client, title: str, body: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": FACTCHECK_PROMPT.format(title=title, body=body[:12000]),
            }
        ],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "overall_verdict": "error",
            "summary": "Could not parse model output.",
            "flags": [],
            "raw_output": raw,
        }


def main():
    if not NEW_ENTRIES_FILE.exists():
        print("No new_entries.json found; run scrape_entries.py first.")
        return

    new_entries = json.loads(NEW_ENTRIES_FILE.read_text(encoding="utf-8"))
    if not new_entries:
        print("No new entries to fact-check today.")
        RESULTS_FILE.write_text(
            json.dumps({"date": _today(), "results": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results = []
    for entry in new_entries:
        print(f"Checking: {entry['title']}")
        body = fetch_entry_text(entry["url"])
        verdict = factcheck_entry(client, entry["title"], body)
        results.append({**entry, **verdict})

    RESULTS_FILE.write_text(
        json.dumps({"date": _today(), "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(results)} results to {RESULTS_FILE}")


def _today():
    from datetime import date

    return date.today().isoformat()


if __name__ == "__main__":
    main()
