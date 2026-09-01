"""
Fetch Arabica's current list of entries and diff against previously-seen ones.

The entry LISTING page (Pages/ArticleListing.aspx) populates its results via
client-side JS with no plain HTTP-visible data source, so it can't be scraped
with a normal request. Instead we use the site's HOMEPAGE, whose "أحدث
المداخل" (Latest Entries) section is rendered server-side in the initial
HTML - confirmed by fetching it directly and inspecting the markup. It lists
the ~20 most recently published entries, title + URL, which is exactly what
a daily new-entry diff needs.

Selectors below were verified against the live site's actual rendered
markup (not guessed placeholders):

    <div class="arabica_latest">
      ...
      <div class="arabica_featured-content latest-posts">
        <div class="arabica_latest-article">
          <div class="arabica_latest-article-inner">
            ...
            <div class="arabica_latest-article-content">
              <h3 class="arabica_latest-article-title">
                <a href="some-entry-slug.aspx">Entry Title</a>
              </h3>
            </div>
          </div>
        </div>
        ... (repeated per entry)
"""

import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SITE_ROOT = "https://arabica.dohainstitute.org"
HOME_URL = f"{SITE_ROOT}/Pages/Default.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEEN_FILE = DATA_DIR / "seen_entries.json"
NEW_ENTRIES_FILE = DATA_DIR / "new_entries.json"


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen(seen):
    DATA_DIR.mkdir(exist_ok=True)
    SEEN_FILE.write_text(
        json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def scrape_current_entries():
    resp = requests.get(HOME_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    latest_section = soup.select_one(".arabica_latest .latest-posts")
    if latest_section is None:
        raise RuntimeError(
            "Could not find the 'أحدث المداخل' (latest entries) section on "
            "the homepage. The site's markup may have changed - re-check "
            f"{HOME_URL} and update the selectors in this script."
        )

    entries = []
    for article in latest_section.select(".arabica_latest-article"):
        link_el = article.select_one(".arabica_latest-article-title a")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        href = link_el.get("href")
        if not title or not href:
            continue
        url = urljoin(f"{SITE_ROOT}/Pages/", href)
        entries.append({"title": title, "url": url})

    return entries


def main():
    seen = load_seen()
    current = scrape_current_entries()

    new_entries = [e for e in current if e["url"] not in seen]

    print(f"Found {len(current)} total entries, {len(new_entries)} new.")

    DATA_DIR.mkdir(exist_ok=True)
    NEW_ENTRIES_FILE.write_text(
        json.dumps(new_entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Mark everything we saw today as seen, for tomorrow's diff.
    for e in current:
        seen[e["url"]] = {"title": e["title"]}
    save_seen(seen)


if __name__ == "__main__":
    main()
