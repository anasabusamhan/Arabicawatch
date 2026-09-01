# Arabica Watch

Daily monitor for new entries on Arabica (https://arabica.dohainstitute.org),
with automated fact-checking via the Claude API, published as a static
dashboard through GitHub Pages.

## How it works

1. **GitHub Actions cron** runs once a day (`.github/workflows/daily-check.yml`).
2. **`scripts/scrape_entries.py`** fetches the site's homepage
   (`Pages/Default.aspx`) and reads the "أحدث المداخل" (Latest Entries)
   section, which is rendered server-side — a plain `requests.get()` sees the
   real titles and links, no headless browser needed. (The dedicated entry
   *listing* page, `ArticleListing.aspx`, populates its results via
   client-side JS with no visible underlying data endpoint, so it isn't used
   here — the homepage's latest-entries block covers the same need for a
   daily new-entry diff.)
3. The script diffs today's list against `data/seen_entries.json` (committed
   in the repo) to find entries that are new since the last run.
4. **`scripts/factcheck.py`** fetches the full text of each new entry (also
   a plain HTTP request — entry pages render their body in
   `.arabica_article-content`) and sends it to the Claude API (with the web
   search tool enabled) to check factual claims and flag anything
   unsupported, outdated, or contradicted by sources — plus whether cited
   references check out.
5. **`scripts/build_dashboard.py`** turns the results into a static
   `docs/index.html` page.
6. The workflow commits the updated `data/seen_entries.json` and
   `docs/index.html` back to the repo. With GitHub Pages set to serve from
   `docs/`, the dashboard is live at `https://<you>.github.io/<repo>/` and
   you just check it whenever you like — no notifications, no email setup.

All selectors were verified by fetching the live site directly and
inspecting its actual rendered markup, not guessed.

Note: the homepage's latest-entries section shows roughly the 20 most
recently published entries. If more than that get published between two
daily runs, older ones could be missed. Fine for a daily cron under normal
publishing volume; worth revisiting if Arabica ever ships entries in bulk.

## Setup

1. Create a new GitHub repo and push this folder to it (already done if
   you're reading this from the repo).
2. In the repo settings → Pages, set source to "Deploy from branch",
   branch `main`, folder `/docs`.
3. In the repo settings → Secrets and variables → Actions, add:
   - `ANTHROPIC_API_KEY` — your Claude API key.
4. Push a commit — the workflow runs automatically on the schedule
   defined in the workflow file (default: 06:00 UTC daily). You can also
   trigger it manually from the Actions tab (`workflow_dispatch`).

## Local test run

```bash
pip install -r requirements.txt
python scripts/scrape_entries.py
ANTHROPIC_API_KEY=sk-... python scripts/factcheck.py
python scripts/build_dashboard.py
open docs/index.html
```

`scrape_entries.py` and `build_dashboard.py` have no external dependencies
beyond network access and were run end-to-end against the live site while
building this. `factcheck.py`'s HTTP fetch of entry pages was verified the
same way; only the actual Claude API call requires your own key to test.
