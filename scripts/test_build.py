#!/usr/bin/env python3
from __future__ import annotations

import unittest

import build


class InlineTests(unittest.TestCase):
    def test_emphasis_and_code(self) -> None:
        self.assertEqual(build.render_inline("**a** and *b* and `c*d*`"), "<strong>a</strong> and <em>b</em> and <code>c*d*</code>")

    def test_underscores_inside_words_stay(self) -> None:
        self.assertEqual(build.render_inline("snake_case_name"), "snake_case_name")

    def test_links(self) -> None:
        self.assertEqual(build.render_inline("[home](index.html)"), '<a href="index.html">home</a>')
        self.assertEqual(
            build.render_inline("[gh](https://github.com/a_b_c)"),
            '<a href="https://github.com/a_b_c" target="_blank" rel="noopener noreferrer">gh</a>',
        )
        self.assertIn('target="_blank"', build.render_inline("[cv](resume/cv.pdf)"))

    def test_image(self) -> None:
        self.assertEqual(
            build.render_inline("![a wall](images/wall.jpg)"),
            '<img src="images/wall.jpg" alt="a wall" loading="lazy">',
        )

    def test_inline_html_and_entities_pass_through(self) -> None:
        self.assertEqual(
            build.render_inline('<span class="g-v4">v4</span> &middot; a & b < c'),
            '<span class="g-v4">v4</span> &middot; a &amp; b &lt; c',
        )

    def test_url_ampersands_are_escaped(self) -> None:
        self.assertEqual(build.render_inline("[q](page.html?a=1&b=2)"), '<a href="page.html?a=1&amp;b=2">q</a>')


class BlockTests(unittest.TestCase):
    def test_headings_get_ids(self) -> None:
        out = build.render_markdown("# Title\n\n## About me {#about}\n\n### Some Thing\n\n### Some Thing")
        self.assertIn("<h1>Title</h1>", out)
        self.assertIn('<h2 id="about">About me</h2>', out)
        self.assertIn('<h3 id="some-thing">Some Thing</h3>', out)
        self.assertIn('<h3 id="some-thing-2">Some Thing</h3>', out)

    def test_paragraphs_join_lines(self) -> None:
        self.assertEqual(build.render_markdown("one\ntwo\n\nthree"), "<p>one two</p>\n\n<p>three</p>")

    def test_lists_with_continuations_and_blank_lines(self) -> None:
        out = build.render_markdown("- a\n  more\n- b\n\n- c\n\nafter")
        self.assertEqual(out, "<ul>\n<li>a more</li>\n<li>b</li>\n<li>c</li>\n</ul>\n\n<p>after</p>")
        self.assertEqual(build.render_markdown("1. x\n2. y"), "<ol>\n<li>x</li>\n<li>y</li>\n</ol>")

    def test_comments_are_dropped(self) -> None:
        out = build.render_markdown("keep\n\n<!--\n## Draft\nsecret\n-->\n\nalso <!-- hidden --> kept")
        self.assertNotIn("secret", out)
        self.assertNotIn("Draft", out)
        self.assertIn("<p>also  kept</p>", out)

    def test_html_block_passes_through(self) -> None:
        self.assertEqual(build.render_markdown('<div id="x"></div>\n\ntext'), '<div id="x"></div>\n\n<p>text</p>')

    def test_rule_quote_and_code(self) -> None:
        self.assertEqual(build.render_markdown("---"), "<hr>")
        self.assertEqual(build.render_markdown("> hi"), "<blockquote>\n<p>hi</p>\n</blockquote>")
        self.assertEqual(build.render_markdown("```\n<b>\n```"), "<pre><code>&lt;b&gt;</code></pre>")

    def test_shortcode(self) -> None:
        self.assertIn('id="books"', build.render_markdown("{{goodreads}}"))
        with self.assertRaises(build.BuildError):
            build.render_markdown("{{nope}}")


class PageTests(unittest.TestCase):
    def test_front_matter(self) -> None:
        meta, body = build.parse_front_matter("---\ntitle: Hi: there\n---\n\nbody")
        self.assertEqual(meta, {"title": "Hi: there"})
        self.assertEqual(body.strip(), "body")

    def test_page_needs_title(self) -> None:
        with self.assertRaises(build.BuildError):
            build.render_page("x", "---\ndescription: d\n---\n\nhi")

    def test_render_page_shell(self) -> None:
        page = build.render_page("x", "---\ntitle: A & B\n---\n\n# Hello")
        self.assertIn("<title>A &amp; B</title>", page)
        self.assertIn("<h1>Hello</h1>", page)
        self.assertIn("styles.css?v=", page)

    def test_committed_pages_are_up_to_date(self) -> None:
        self.assertEqual(build.build_all(check=True), [], "run python3 scripts/build.py")


if __name__ == "__main__":
    unittest.main()
