#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import html
import io
import json
import mimetypes
import os
import posixpath
import re
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATCH_PATHS = (
    "index.html",
    "styles.css",
    "scripts",
    "images",
    "resume",
)
DEFAULT_IGNORE_DIRS = {".git", ".omx", ".omc", ".vscode", ".claude", "__pycache__"}
DEFAULT_IGNORE_SUFFIXES = {".aux", ".log", ".out", ".synctex.gz", ".pyc"}
DEFAULT_POLL_INTERVAL_SECONDS = 0.35
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)

LIVE_RELOAD_SNIPPET = """<script>
(() => {
  const eventUrl = `${window.location.protocol}//${window.location.host}/__live`;
  const reconnectDelayMs = 1000;

  function cacheBust(url) {
    const nextUrl = new URL(url, window.location.href);
    nextUrl.searchParams.set("__dev_reload", Date.now().toString());
    return nextUrl.toString();
  }

  function refreshStylesheets() {
    document.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) return;
      link.setAttribute("href", cacheBust(href));
    });
  }

  function connect() {
    const source = new EventSource(eventUrl);

    source.addEventListener("reload", (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.kind === "css") {
          refreshStylesheets();
          return;
        }
      } catch (_) {}

      window.location.reload();
    });

    source.onerror = () => {
      source.close();
      setTimeout(connect, reconnectDelayMs);
    };
  }

  connect();
})();
</script>"""


@dataclass(frozen=True)
class FileSnapshot:
    mtime_ns: int
    size: int


@dataclass(frozen=True)
class ChangeEvent:
    sequence: int
    changed_paths: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class ServerConfig:
    root: Path
    host: str
    port: int
    poll_interval_seconds: float
    watch_paths: tuple[Path, ...]
    ignore_dirs: frozenset[str]
    ignore_suffixes: tuple[str, ...]
    open_browser: bool

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/index.html"


def should_ignore(
    relative_path: Path,
    ignore_dirs: frozenset[str] = frozenset(DEFAULT_IGNORE_DIRS),
    ignore_suffixes: tuple[str, ...] = tuple(DEFAULT_IGNORE_SUFFIXES),
) -> bool:
    if any(part in ignore_dirs for part in relative_path.parts):
        return True

    name = relative_path.name
    if any(name.endswith(suffix) for suffix in ignore_suffixes):
        return True

    return name.startswith(".#") or name.endswith("~")


def resolve_watch_paths(root: Path, raw_watch_paths: Iterable[str]) -> tuple[Path, ...]:
    resolved_root = root.resolve()
    resolved: list[Path] = []
    for raw_path in raw_watch_paths:
        candidate = (resolved_root / raw_path).resolve()
        if candidate == resolved_root or resolved_root in candidate.parents:
            resolved.append(candidate)
        else:
            raise ValueError(f"Watch path escapes project root: {raw_path}")
    return tuple(resolved)


def iter_watch_files(config: ServerConfig) -> Iterable[Path]:
    root = config.root.resolve()
    for target in config.watch_paths:
        if not target.exists():
            continue

        if target.is_file():
            relative_path = target.relative_to(root)
            if not should_ignore(relative_path, config.ignore_dirs, config.ignore_suffixes):
                yield target
            continue

        for current_root, dirnames, filenames in os.walk(target):
            dirnames[:] = [
                dirname for dirname in dirnames if dirname not in config.ignore_dirs
            ]
            current_root_path = Path(current_root)
            for filename in filenames:
                path = current_root_path / filename
                relative_path = path.relative_to(root)
                if should_ignore(relative_path, config.ignore_dirs, config.ignore_suffixes):
                    continue
                yield path


def snapshot_files(config: ServerConfig) -> dict[Path, FileSnapshot]:
    snapshot: dict[Path, FileSnapshot] = {}
    for path in iter_watch_files(config):
        try:
            stat_result = path.stat()
        except FileNotFoundError:
            continue
        snapshot[path] = FileSnapshot(
            mtime_ns=stat_result.st_mtime_ns,
            size=stat_result.st_size,
        )
    return snapshot


def detect_changed_paths(
    previous: dict[Path, FileSnapshot],
    current: dict[Path, FileSnapshot],
    root: Path,
) -> tuple[str, ...]:
    root = root.resolve()
    paths = set(previous) | set(current)
    changed = [
        path.relative_to(root).as_posix()
        for path in paths
        if previous.get(path) != current.get(path)
    ]
    return tuple(sorted(changed))


def classify_change(paths: Iterable[str]) -> str:
    normalized = tuple(paths)
    if normalized and all(path.endswith(".css") for path in normalized):
        return "css"
    return "reload"


def inject_live_reload(html_text: str) -> str:
    if LIVE_RELOAD_SNIPPET in html_text:
        return html_text
    if BODY_CLOSE_RE.search(html_text):
        return BODY_CLOSE_RE.sub(f"{LIVE_RELOAD_SNIPPET}\n</body>", html_text, count=1)
    return html_text + LIVE_RELOAD_SNIPPET


class ReloadState:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._event = ChangeEvent(sequence=0, changed_paths=(), kind="reload")

    def bump(self, changed_paths: tuple[str, ...]) -> None:
        event = ChangeEvent(
            sequence=self._event.sequence + 1,
            changed_paths=changed_paths,
            kind=classify_change(changed_paths),
        )
        with self._condition:
            self._event = event
            self._condition.notify_all()

    def wait_for_change(self, sequence: int, timeout: float = 15.0) -> ChangeEvent:
        with self._condition:
            self._condition.wait_for(lambda: self._event.sequence != sequence, timeout=timeout)
            return self._event

    @property
    def event(self) -> ChangeEvent:
        with self._condition:
            return self._event


class RepoDevServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[SimpleHTTPRequestHandler],
        *,
        config: ServerConfig,
        reload_state: ReloadState,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.config = config
        self.reload_state = reload_state


def watch_for_changes(config: ServerConfig, reload_state: ReloadState) -> None:
    previous = snapshot_files(config)
    while True:
        time.sleep(config.poll_interval_seconds)
        current = snapshot_files(config)
        changed_paths = detect_changed_paths(previous, current, config.root)
        if changed_paths:
            previous = current
            print(f"[dev-server] change detected: {', '.join(changed_paths)}")
            reload_state.bump(changed_paths)


class LiveReloadHandler(SimpleHTTPRequestHandler):
    server_version = "TinyRepoDevServer/2.0"

    @property
    def app(self) -> RepoDevServer:
        return self.server  # type: ignore[return-value]

    @property
    def config(self) -> ServerConfig:
        return self.app.config

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        trailing_slash = path.rstrip().endswith("/")
        normalized = posixpath.normpath(urllib.parse.unquote(path))
        parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]

        resolved = self.config.root
        for part in parts:
            resolved /= part

        if trailing_slash:
            resolved /= ""

        return str(resolved)

    def do_GET(self) -> None:
        if self.path.startswith("/__live"):
            self.handle_live_reload_stream()
            return
        if self.path.startswith("/__health"):
            self.handle_health()
            return
        super().do_GET()

    def handle_health(self) -> None:
        payload = {
            "status": "ok",
            "root": str(self.config.root),
            "watchPaths": [path.relative_to(self.config.root).as_posix() for path in self.config.watch_paths],
            "latestEvent": {
                "sequence": self.app.reload_state.event.sequence,
                "kind": self.app.reload_state.event.kind,
                "changedPaths": list(self.app.reload_state.event.changed_paths),
            },
        }
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def list_directory(self, path: str):
        try:
            entries = sorted(Path(path).iterdir(), key=lambda item: item.name.lower())
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "No permission to list directory")
            return None

        display_path = html.escape(urllib.parse.unquote(self.path))
        output = io.BytesIO()
        output.write(
            (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<title>Directory listing for {display_path}</title></head>"
                f"<body><h1>Directory listing for {display_path}</h1><hr><ul>"
            ).encode("utf-8")
        )
        for entry in entries:
            relative_path = entry.relative_to(self.config.root)
            if should_ignore(relative_path, self.config.ignore_dirs, self.config.ignore_suffixes):
                continue
            name = entry.name + ("/" if entry.is_dir() else "")
            quoted = urllib.parse.quote(name)
            output.write(f"<li><a href=\"{quoted}\">{html.escape(name)}</a></li>".encode("utf-8"))
        output.write(b"</ul><hr></body></html>")
        output.seek(0)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(output.getbuffer())))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return output

    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            for candidate in ("index.html", "index.htm"):
                index_path = path / candidate
                if index_path.exists():
                    path = index_path
                    break
            else:
                return self.list_directory(str(path))

        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            relative_path = path.relative_to(self.config.root)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        if should_ignore(relative_path, self.config.ignore_dirs, self.config.ignore_suffixes):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        content_type = self.guess_type(str(path))
        if path.suffix.lower() == ".html":
            body = inject_live_reload(path.read_text(encoding="utf-8"))
            encoded = body.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return io.BytesIO(encoded)

        file_obj = path.open("rb")
        try:
            fs = os.fstat(file_obj.fileno())
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(fs.st_size))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return file_obj
        except Exception:
            file_obj.close()
            raise

    def handle_live_reload_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        current_event = self.app.reload_state.event
        sequence = current_event.sequence
        try:
            self.wfile.write(b"event: ready\ndata: connected\n\n")
            self.wfile.flush()

            while True:
                next_event = self.app.reload_state.wait_for_change(sequence)
                if next_event.sequence == sequence:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue

                sequence = next_event.sequence
                payload = json.dumps(
                    {
                        "kind": next_event.kind,
                        "changedPaths": list(next_event.changed_paths),
                        "sequence": next_event.sequence,
                    }
                ).encode("utf-8")
                self.wfile.write(b"event: reload\n")
                self.wfile.write(b"data: " + payload + b"\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write(f"[dev-server] {self.address_string()} - {format % args}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repo-local static dev server with live reload that ignores OMX churn."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to.")
    parser.add_argument(
        "--port",
        type=int,
        default=5501,
        help="Preferred port to bind to. Use 0 to auto-pick any free port.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Polling interval in seconds for watched files.",
    )
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        metavar="PATH",
        help="Additional repo-relative path to watch. Can be provided multiple times.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the default browser after the server starts.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> ServerConfig:
    raw_watch_paths = DEFAULT_WATCH_PATHS + tuple(args.watch)
    watch_paths = resolve_watch_paths(ROOT, raw_watch_paths)
    return ServerConfig(
        root=ROOT,
        host=args.host,
        port=args.port,
        poll_interval_seconds=args.poll,
        watch_paths=watch_paths,
        ignore_dirs=frozenset(DEFAULT_IGNORE_DIRS),
        ignore_suffixes=tuple(DEFAULT_IGNORE_SUFFIXES),
        open_browser=args.open,
    )


def bind_server(config: ServerConfig, reload_state: ReloadState) -> RepoDevServer:
    attempts = [config.port] if config.port == 0 else [config.port, *range(config.port + 1, config.port + 20)]
    last_error: OSError | None = None

    for port in attempts:
        try:
            return RepoDevServer(
                (config.host, port),
                LiveReloadHandler,
                config=ServerConfig(
                    root=config.root,
                    host=config.host,
                    port=port,
                    poll_interval_seconds=config.poll_interval_seconds,
                    watch_paths=config.watch_paths,
                    ignore_dirs=config.ignore_dirs,
                    ignore_suffixes=config.ignore_suffixes,
                    open_browser=config.open_browser,
                ),
                reload_state=reload_state,
            )
        except OSError as error:
            last_error = error
            if error.errno != errno.EADDRINUSE or config.port == 0:
                break

    assert last_error is not None
    raise last_error


def maybe_open_browser(config: ServerConfig) -> None:
    if config.open_browser:
        webbrowser.open(config.url)


def main() -> None:
    args = parse_args()
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("image/svg+xml", ".svg")

    config = build_config(args)
    reload_state = ReloadState()
    watcher = threading.Thread(
        target=watch_for_changes,
        args=(config, reload_state),
        daemon=True,
    )
    watcher.start()

    server = bind_server(config, reload_state)
    active_config = server.config
    print(f"Serving {active_config.root} at {active_config.url}")
    print(
        "[dev-server] watching:",
        ", ".join(path.relative_to(active_config.root).as_posix() for path in active_config.watch_paths),
    )
    maybe_open_browser(active_config)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dev server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
