#!/usr/bin/env python3
"""Build the site's HTML pages from the Markdown files in content/.

Every content/<name>.md becomes <name>.html at the repo root. A page starts with a
small front matter block:

    ---
    title: Norman Bui
    description: One sentence for search results and link previews.
    type: website            (optional, og:type; defaults to "website")
    head: index.head.html    (optional, extra <head> HTML kept in content/)
    scripts: scripts/main.js (optional, comma-separated module scripts)
    ---

The Markdown supported is a small, predictable subset (see SYNTAX below and the
cheat sheet in the editor). Raw HTML is allowed anywhere, and <!-- comments --> are
dropped from the output, which makes them a good place for drafts.

Usage:
    python3 scripts/build.py           # write any pages that changed
    python3 scripts/build.py --check   # exit 1 if a page is out of date
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
PAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

SYNTAX = """\
# Page title            ## Section {#custom-id}      ### Subsection
**bold**  *italic*  `code`  [link text](https://...)  ![alt text](images/photo.jpg)
- bullet list           1. numbered list            > quote
---                     (a horizontal line)
<!-- hidden draft text, not published -->
{{goodreads}}           (the Goodreads stats, charts and book list)
Raw HTML works too, e.g. <span class="g-v4">v4</span>
"""

# Shortcodes that expand to fixed HTML, written alone on their own line.
SHORTCODES = {
    "goodreads": (
        '<p id="reading-stats" class="meta"></p>\n'
        '<div id="reading-charts"></div>\n'
        '<ul id="books"></ul>'
    ),
}

BLOCK_HTML_TAGS = {
    "address", "article", "aside", "blockquote", "details", "div", "dl", "figure", "footer",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "iframe", "img", "nav", "ol",
    "p", "picture", "pre", "script", "section", "table", "ul", "video", "audio", "style",
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
HEADING_ID_RE = re.compile(r"\s*\{#([A-Za-z][\w-]*)\}\s*$")
HR_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
UL_ITEM_RE = re.compile(r"^\s{0,3}[-*+]\s+(.*)$")
OL_ITEM_RE = re.compile(r"^\s{0,3}\d{1,9}[.)]\s+(.*)$")
QUOTE_RE = re.compile(r"^\s{0,3}>\s?(.*)$")
FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
SHORTCODE_RE = re.compile(r"^\s*\{\{\s*([a-z-]+)\s*\}\}\s*$")
HTML_BLOCK_RE = re.compile(r"^\s{0,3}</?([A-Za-z][A-Za-z0-9]*)[\s>/]")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

INLINE_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")
ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+"([^"]*)")?\s*\)')
LINK_RE = re.compile(r'\[((?:[^\[\]]|\[[^\]]*\])+)\]\(\s*([^)\s]+)(?:\s+"([^"]*)")?\s*\)')
BOLD_RE = re.compile(r"\*\*(\S(?:.*?\S)?)\*\*|__(\S(?:.*?\S)?)__")
ITALIC_RE = re.compile(r"(?<![\w*])\*(\S(?:.*?\S)?)\*(?![\w*])|(?<![\w_])_(\S(?:.*?\S)?)_(?![\w_])")
PLACEHOLDER_RE = re.compile("\x00(\\d+)\x00")


class BuildError(Exception):
    pass


# --------------------------------------------------------------------------- inline


class _Inline:
    """Render one run of inline Markdown. Pieces that must not be touched again
    (code, tags, links) are swapped for placeholders and restored at the end."""

    def __init__(self) -> None:
        self.saved: list[str] = []

    def hold(self, rendered: str) -> str:
        self.saved.append(rendered)
        return f"\x00{len(self.saved) - 1}\x00"

    def restore(self, text: str) -> str:
        while PLACEHOLDER_RE.search(text):
            text = PLACEHOLDER_RE.sub(lambda m: self.saved[int(m.group(1))], text)
        return text

    def escape(self, text: str) -> str:
        # Keep inline HTML and entities the author wrote; escape every other & and <.
        text = INLINE_TAG_RE.sub(lambda m: self.hold(m.group(0)), text)
        text = ENTITY_RE.sub(lambda m: self.hold(m.group(0)), text)
        return text.replace("&", "&amp;").replace("<", "&lt;")

    def emphasis(self, text: str) -> str:
        text = BOLD_RE.sub(lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
        return ITALIC_RE.sub(lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)

    def render(self, text: str) -> str:
        text = CODE_SPAN_RE.sub(
            lambda m: self.hold(f"<code>{html.escape(m.group(2).strip(), quote=False)}</code>"), text
        )
        text = self.escape(text)
        text = IMAGE_RE.sub(self._image, text)
        text = LINK_RE.sub(self._link, text)
        return self.restore(self.emphasis(text))

    def _image(self, m: re.Match[str]) -> str:
        alt, src, title = m.group(1), m.group(2), m.group(3)
        attrs = f'src="{_attr(src)}" alt="{_attr(alt)}"'
        if title:
            attrs += f' title="{_attr(title)}"'
        return self.hold(f"<img {attrs} loading=\"lazy\">")

    def _link(self, m: re.Match[str]) -> str:
        label, href, title = m.group(1), m.group(2), m.group(3)
        attrs = f'href="{_attr(href)}"'
        if title:
            attrs += f' title="{_attr(title)}"'
        target = self.restore(href)
        if re.match(r"https?://", target) or target.lower().split("#")[0].endswith(".pdf"):
            attrs += ' target="_blank" rel="noopener noreferrer"'
        return self.hold(f"<a {attrs}>{self.emphasis(label)}</a>")


def _attr(value: str) -> str:
    # Values here are already &-escaped by _Inline.escape; only quotes need care.
    return value.replace('"', "&quot;")


def render_inline(text: str) -> str:
    return _Inline().render(text)


# --------------------------------------------------------------------------- blocks


@dataclass
class _Slugger:
    seen: set[str] = field(default_factory=set)

    def take(self, wanted: str) -> str:
        slug, n = wanted, 2
        while slug in self.seen:
            slug, n = f"{wanted}-{n}", n + 1
        self.seen.add(slug)
        return slug

    def slugify(self, text: str) -> str:
        plain = re.sub(r"<[^>]+>|&[^;\s]+;", "", text).lower()
        return self.take(re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "section")


def _starts_block(line: str) -> bool:
    return bool(
        HEADING_RE.match(line)
        or HR_RE.match(line)
        or UL_ITEM_RE.match(line)
        or OL_ITEM_RE.match(line)
        or QUOTE_RE.match(line)
        or FENCE_RE.match(line)
        or SHORTCODE_RE.match(line)
        or _is_html_block(line)
    )


def _is_html_block(line: str) -> bool:
    m = HTML_BLOCK_RE.match(line)
    return bool(m and m.group(1).lower() in BLOCK_HTML_TAGS)


def render_blocks(text: str, slugger: _Slugger | None = None) -> str:
    slugger = slugger or _Slugger()
    lines = COMMENT_RE.sub("", text).replace("\r\n", "\n").replace("\t", "    ").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if m := FENCE_RE.match(line):
            fence, body = m.group(1), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(body), quote=False)}</code></pre>")
            continue

        if m := SHORTCODE_RE.match(line):
            name = m.group(1)
            if name not in SHORTCODES:
                raise BuildError(f"unknown shortcode {{{{{name}}}}} (known: {', '.join(SHORTCODES)})")
            out.append(SHORTCODES[name])
            i += 1
            continue

        if m := HEADING_RE.match(line):
            level, content = len(m.group(1)), m.group(2)
            id_attr = ""
            if idm := HEADING_ID_RE.search(content):
                content = content[: idm.start()]
                id_attr = f' id="{slugger.take(idm.group(1))}"'
            elif level > 1:
                id_attr = f' id="{slugger.slugify(content)}"'
            out.append(f"<h{level}{id_attr}>{render_inline(content)}</h{level}>")
            i += 1
            continue

        if HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        if _is_html_block(line):
            body = []
            while i < len(lines) and lines[i].strip():
                body.append(lines[i])
                i += 1
            out.append("\n".join(body))
            continue

        if QUOTE_RE.match(line):
            body = []
            while i < len(lines) and lines[i].strip():
                qm = QUOTE_RE.match(lines[i])
                body.append(qm.group(1) if qm else lines[i])
                i += 1
            out.append(f"<blockquote>\n{render_blocks(chr(10).join(body), slugger)}\n</blockquote>")
            continue

        if UL_ITEM_RE.match(line) or OL_ITEM_RE.match(line):
            ordered = bool(OL_ITEM_RE.match(line))
            item_re = OL_ITEM_RE if ordered else UL_ITEM_RE
            items: list[list[str]] = []
            while i < len(lines):
                cur = lines[i]
                if im := item_re.match(cur):
                    items.append([im.group(1)])
                elif cur.strip() and items and not _starts_block(cur):
                    items[-1].append(cur.strip())  # continuation of the previous item
                elif not cur.strip() and i + 1 < len(lines) and item_re.match(lines[i + 1]):
                    pass  # a blank line between items keeps the list going
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            rendered = "\n".join(f"<li>{render_inline(' '.join(item))}</li>" for item in items)
            out.append(f"<{tag}>\n{rendered}\n</{tag}>")
            continue

        para = []
        while i < len(lines) and lines[i].strip() and (not para or not _starts_block(lines[i])):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{render_inline(' '.join(para))}</p>")

    return "\n\n".join(out)


def render_markdown(text: str) -> str:
    return render_blocks(text)


# --------------------------------------------------------------------------- pages


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    text = text.lstrip("﻿")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        raise BuildError("front matter starts with --- but never closes")
    meta: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            raise BuildError(f"front matter line needs 'key: value': {raw!r}")
        meta[key.strip().lower()] = value.strip()
    body = text[end + 4 :]
    return meta, body.split("\n", 1)[1] if "\n" in body else ""


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def versioned(rel: str) -> str:
    path = ROOT / rel
    return f"{rel}?v={file_hash(path)}" if path.exists() else rel


def render_page(name: str, source: str) -> str:
    meta, body = parse_front_matter(source)
    title = meta.get("title")
    if not title:
        raise BuildError("front matter needs a title")
    description = meta.get("description", "")
    og_type = meta.get("type", "website")

    head = [
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{html.escape(title)}</title>",
    ]
    if description:
        head.append(f'<meta name="description" content="{html.escape(description)}">')
    head += [
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:type" content="{html.escape(og_type)}">',
    ]
    if description:
        head.append(f'<meta property="og:description" content="{html.escape(description)}">')
    head += [
        '<meta name="twitter:card" content="summary">',
        f'<link rel="icon" type="image/jpeg" href="{versioned("images/logos/baby.jpeg")}">',
        f'<link rel="stylesheet" href="{versioned("styles.css")}">',
    ]
    if extra := meta.get("head"):
        extra_path = CONTENT_DIR / extra
        if not extra_path.is_file():
            raise BuildError(f"head file not found: content/{extra}")
        head.append(extra_path.read_text(encoding="utf-8").strip())

    scripts = [s.strip() for s in meta.get("scripts", "").split(",") if s.strip()]
    for script in scripts:
        if not (ROOT / script).is_file():
            raise BuildError(f"script not found: {script}")
    script_tags = "".join(f'\n<script type="module" src="{versioned(s)}"></script>' for s in scripts)

    head_html = "\n".join(f"    {line}" for line in "\n".join(head).split("\n"))
    return (
        "<!DOCTYPE html>\n"
        f"<!-- Generated from content/{name}.md by scripts/build.py. Edit the Markdown, not this file. -->\n"
        '<html lang="en">\n\n'
        f"<head>\n{head_html}\n</head>\n\n"
        f"<body>\n\n{render_markdown(body)}\n{script_tags}\n\n</body>\n\n</html>\n"
    )


def page_names() -> list[str]:
    return sorted(p.stem for p in CONTENT_DIR.glob("*.md") if PAGE_NAME_RE.match(p.stem))


def build_page(name: str, check: bool = False) -> bool:
    """Render one page. Returns True if the output changed (or would change)."""
    source = (CONTENT_DIR / f"{name}.md").read_text(encoding="utf-8")
    try:
        rendered = render_page(name, source)
    except BuildError as error:
        raise BuildError(f"content/{name}.md: {error}") from None
    target = ROOT / f"{name}.html"
    if target.exists() and target.read_text(encoding="utf-8") == rendered:
        return False
    if not check:
        target.write_text(rendered, encoding="utf-8")
    return True


def build_all(check: bool = False) -> list[str]:
    return [f"{name}.html" for name in page_names() if build_page(name, check)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if any page is out of date")
    args = parser.parse_args()
    try:
        changed = build_all(check=args.check)
    except BuildError as error:
        sys.exit(f"build failed: {error}")
    if args.check:
        if changed:
            sys.exit(f"out of date: {', '.join(changed)} (run python3 scripts/build.py)")
        print("all pages up to date")
    else:
        print(f"built: {', '.join(changed)}" if changed else "nothing changed")


if __name__ == "__main__":
    main()
