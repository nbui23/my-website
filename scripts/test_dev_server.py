#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import dev_server


class DevServerTests(unittest.TestCase):
    def test_should_ignore_hidden_and_temp_files(self) -> None:
        self.assertTrue(dev_server.should_ignore(Path(".local-state/session.json")))
        self.assertTrue(dev_server.should_ignore(Path("resume/Norman_Bui_Resume.log")))
        self.assertTrue(dev_server.should_ignore(Path("styles.css~")))
        self.assertFalse(dev_server.should_ignore(Path("styles.css")))

    def test_detect_changed_paths_reports_sorted_relative_paths(self) -> None:
        root = Path("/repo")
        previous = {
            root / "styles.css": dev_server.FileSnapshot(mtime_ns=1, size=10),
            root / "index.html": dev_server.FileSnapshot(mtime_ns=1, size=20),
        }
        current = {
            root / "styles.css": dev_server.FileSnapshot(mtime_ns=2, size=10),
            root / "scripts/main.js": dev_server.FileSnapshot(mtime_ns=1, size=30),
        }

        changed = dev_server.detect_changed_paths(previous, current, root)

        self.assertEqual(changed, ("index.html", "scripts/main.js", "styles.css"))

    def test_classify_change_marks_css_only_changes(self) -> None:
        self.assertEqual(dev_server.classify_change(("styles.css", "resume/theme.css")), "css")
        self.assertEqual(dev_server.classify_change(("styles.css", "scripts/main.js")), "reload")
        self.assertEqual(dev_server.classify_change(()), "reload")

    def test_inject_live_reload_before_body_close(self) -> None:
        html = "<html><body><main>Hello</main></body></html>"

        injected = dev_server.inject_live_reload(html)

        self.assertIn(dev_server.LIVE_RELOAD_SNIPPET, injected)
        self.assertLess(injected.index(dev_server.LIVE_RELOAD_SNIPPET), injected.index("</body>"))

    def test_resolve_watch_paths_rejects_escape(self) -> None:
        with self.assertRaises(ValueError):
            dev_server.resolve_watch_paths(dev_server.ROOT, ("../outside",))

    def test_snapshot_files_ignores_hidden_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / "index.html").write_text("ok", encoding="utf-8")
            (root / ".local-state").mkdir()
            (root / ".local-state" / "state.json").write_text("ignore me", encoding="utf-8")
            (root / "styles.css").write_text("body {}", encoding="utf-8")

            config = dev_server.ServerConfig(
                root=root,
                host="127.0.0.1",
                port=5501,
                poll_interval_seconds=0.1,
                watch_paths=dev_server.resolve_watch_paths(root, ("index.html", "styles.css", ".local-state")),
                ignore_dirs=frozenset(dev_server.DEFAULT_IGNORE_DIRS),
                ignore_suffixes=tuple(dev_server.DEFAULT_IGNORE_SUFFIXES),
                open_browser=False,
            )

            snapshot = dev_server.snapshot_files(config)

            relative_paths = {path.relative_to(root).as_posix() for path in snapshot}
            self.assertEqual(relative_paths, {"index.html", "styles.css"})


def main() -> None:
    unittest.main(argv=["test_dev_server.py"])


if __name__ == "__main__":
    main()
