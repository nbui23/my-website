#!/usr/bin/env python3

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
EXPECTED_TABS = ["experience", "education", "projects", "reading"]
EXPECTED_SECTION_IDS = {"experience", "education", "projects", "reading"}
EXPECTED_ENTRY_CARD_COUNT = 13
EXPECTED_DYNAMIC_IDS = {"reading-stats", "reading-charts", "books-grid"}
EXPECTED_EDUCATION_SNIPPETS = [
    '<dt>Theory &amp; Algorithms</dt>',
    '<dd>Algorithms I &amp; II, Discrete Structures I &amp; II, Graph Analytics</dd>',
    '<dt>Systems &amp; Security</dt>',
    '<dd>Operating Systems, Systems Programming, Applied Cryptography</dd>',
    '<dt>Software Engineering</dt>',
    'Software Engineering, Object-Oriented Programming, Software Quality Assurance,',
    '<dt>Data &amp; Applications</dt>',
    '<dd>Database Management Systems, Web Development, Mobile Multimedia</dd>',
    '<dt>Math &amp; Stats</dt>',
    "<strong>Awards:</strong> President's Scholarship, Henry Marshall Tory Scholarship, Chalmers",
]


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tab_ids: list[str] = []
        self.section_ids: set[str] = set()
        self.element_ids: set[str] = set()
        self.entry_card_count = 0
        self.local_assets: list[str] = []
        self.target_blank_missing_rel: list[str] = []
        self.inline_onerror_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        element_id = attr_map.get("id")

        if element_id:
            self.element_ids.add(element_id)

        if tag == "button" and "tab" in classes:
            self.tab_ids.append(attr_map.get("data-tab", ""))

        if tag == "section" and element_id:
            self.section_ids.add(element_id)

        if "entry-card" in classes:
            self.entry_card_count += 1

        if tag == "a" and attr_map.get("target") == "_blank" and not attr_map.get("rel"):
            self.target_blank_missing_rel.append(attr_map.get("href") or "")

        if attr_map.get("onerror"):
            self.inline_onerror_sources.append(attr_map.get("src") or tag)

        for attr_name in ("href", "src"):
            value = attr_map.get(attr_name)
            if value:
                self._maybe_add_local_asset(value)

    def _maybe_add_local_asset(self, value: str) -> None:
        if value.startswith(("http://", "https://", "mailto:", "#", "data:")):
            return
        parsed = urlparse(value)
        path = parsed.path.lstrip("/")
        if path:
            self.local_assets.append(path)


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)

    if parser.tab_ids != EXPECTED_TABS:
        raise SystemExit(f"Unexpected tab order: {parser.tab_ids}")

    if not EXPECTED_SECTION_IDS.issubset(parser.section_ids):
        missing = sorted(EXPECTED_SECTION_IDS - parser.section_ids)
        raise SystemExit(f"Missing sections: {missing}")

    if parser.entry_card_count != EXPECTED_ENTRY_CARD_COUNT:
        raise SystemExit(
            f"Unexpected entry-card count: {parser.entry_card_count} "
            f"(expected {EXPECTED_ENTRY_CARD_COUNT})"
        )

    if not EXPECTED_DYNAMIC_IDS.issubset(parser.element_ids):
        missing = sorted(EXPECTED_DYNAMIC_IDS - parser.element_ids)
        raise SystemExit(f"Missing reading containers: {missing}")

    missing_assets = sorted(
        {
            asset
            for asset in parser.local_assets
            if asset and not (ROOT / asset).exists()
        }
    )
    if missing_assets:
        raise SystemExit(f"Missing local assets: {missing_assets}")

    if parser.target_blank_missing_rel:
        raise SystemExit(
            "Missing rel on target=_blank links: "
            f"{parser.target_blank_missing_rel}"
        )

    if parser.inline_onerror_sources:
        raise SystemExit(
            "Found inline onerror fallbacks: "
            f"{parser.inline_onerror_sources}"
        )

    missing_education_snippets = [
        snippet for snippet in EXPECTED_EDUCATION_SNIPPETS if snippet not in html
    ]
    if missing_education_snippets:
        raise SystemExit(
            "Education section is missing expected grouped-course content: "
            f"{missing_education_snippets}"
        )

    print("Site structure OK")
    print(f"Tabs: {parser.tab_ids}")
    print(f"Entry cards: {parser.entry_card_count}")
    print(f"Local assets checked: {len(parser.local_assets)}")


if __name__ == "__main__":
    main()
