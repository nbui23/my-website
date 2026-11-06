#!/usr/bin/env python3

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import build


ROOT = Path(__file__).resolve().parent.parent
PAGES = [ROOT / "index.html", ROOT / "work.html", ROOT / "detailed.html"]
EXPECTED_SECTION_IDS = {
    "index.html": {"about", "reading", "work", "books"},
    "work.html": {"value", "experience", "projects", "skills", "education"},
}


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.element_ids: set[str] = set()
        self.local_assets: list[str] = []
        self.anchor_targets: list[str] = []
        self.target_blank_missing_rel: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        element_id = attr_map.get("id")

        if element_id:
            self.element_ids.add(element_id)

        if tag == "a" and attr_map.get("target") == "_blank" and not attr_map.get("rel"):
            self.target_blank_missing_rel.append(attr_map.get("href") or "")

        for attr_name in ("href", "src"):
            value = attr_map.get(attr_name)
            if not value:
                continue
            if value.startswith("#"):
                self.anchor_targets.append(value[1:])
            else:
                self._maybe_add_local_asset(value)

    def _maybe_add_local_asset(self, value: str) -> None:
        if value.startswith(("http://", "https://", "mailto:", "data:")):
            return
        path = urlparse(value).path.lstrip("/")
        if path:
            self.local_assets.append(path)


def check(page: Path) -> SiteParser:
    parser = SiteParser()
    parser.feed(page.read_text(encoding="utf-8"))

    broken_anchors = sorted({a for a in parser.anchor_targets if a and a not in parser.element_ids})
    if broken_anchors:
        raise SystemExit(f"{page.name}: anchors pointing at missing ids: {broken_anchors}")

    missing_assets = sorted({a for a in parser.local_assets if not (ROOT / a).exists()})
    if missing_assets:
        raise SystemExit(f"{page.name}: missing local assets: {missing_assets}")

    if parser.target_blank_missing_rel:
        raise SystemExit(f"{page.name}: missing rel on target=_blank links: {parser.target_blank_missing_rel}")

    return parser


def main() -> None:
    stale = build.build_all(check=True)
    if stale:
        raise SystemExit(f"Out of date with content/: {stale} (run python3 scripts/build.py)")

    parsers = [check(page) for page in PAGES]

    for page, parser in zip(PAGES, parsers):
        missing_sections = sorted(EXPECTED_SECTION_IDS.get(page.name, set()) - parser.element_ids)
        if missing_sections:
            raise SystemExit(f"{page.name}: missing sections: {missing_sections}")

    print("Site structure OK")
    print(f"Pages checked: {len(PAGES)}")
    print(f"Local assets checked: {sum(len(p.local_assets) for p in parsers)}")


if __name__ == "__main__":
    main()
