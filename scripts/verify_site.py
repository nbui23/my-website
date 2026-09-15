#!/usr/bin/env python3

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
EXPECTED_SECTION_IDS = {"value", "experience", "projects", "skills", "education", "reading"}


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


def main() -> None:
    parser = SiteParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))

    missing_sections = sorted(EXPECTED_SECTION_IDS - parser.element_ids)
    if missing_sections:
        raise SystemExit(f"Missing sections: {missing_sections}")

    if "books" not in parser.element_ids:
        raise SystemExit("Missing Goodreads list container: books")

    broken_anchors = sorted({a for a in parser.anchor_targets if a and a not in parser.element_ids})
    if broken_anchors:
        raise SystemExit(f"Anchors pointing at missing ids: {broken_anchors}")

    missing_assets = sorted({a for a in parser.local_assets if not (ROOT / a).exists()})
    if missing_assets:
        raise SystemExit(f"Missing local assets: {missing_assets}")

    if parser.target_blank_missing_rel:
        raise SystemExit(f"Missing rel on target=_blank links: {parser.target_blank_missing_rel}")

    print("Site structure OK")
    print(f"Local assets checked: {len(parser.local_assets)}")


if __name__ == "__main__":
    main()
