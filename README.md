# my-website

Minimal personal website.

## Writing

Pages are written in Markdown in `content/`, one file per page:

- `content/index.md` becomes `index.html` (the homepage)
- `content/work.md` becomes `work.html` (work, projects, education)

`index.html` and `work.html` are generated, so don't edit them by hand. `detailed.html`
is a redirect to `work.html` so old links keep working.

The easiest way to write is the editor:

```bash
python3 scripts/dev_server.py --open
```

Then open `http://127.0.0.1:5501/__editor`. It shows the Markdown on the left and the real
page on the right, saves as you type, rebuilds the HTML, and refreshes the preview. Drag or
paste a photo into it to copy it into `images/` and insert it. The **Cheat sheet** button
lists all the formatting. `<!-- ... -->` hides text from the published page, which is handy
for drafts.

You can also edit the `.md` files in any editor while the dev server runs; it rebuilds on save.
Without the dev server, run:

```bash
python3 scripts/build.py
```

Commit the `.md` files and the generated `.html` together. `python3 scripts/verify_site.py`
fails if they are out of sync.

## Local dev server

Use the repo-local live-reload server:

```bash
python3 scripts/dev_server.py
```

Then open:

```text
http://127.0.0.1:5501/index.html
```

It live-reloads on changes to:
- `content/` (rebuilding the pages first)
- `index.html`, `work.html`
- `styles.css`
- `scripts/`
- `images/`
- `resume/`

It ignores editor and git churn under:
- `.git/`
- `.vscode/`

Helpful flags:

```bash
# open the browser automatically
python3 scripts/dev_server.py --open

# add another repo-local path to watch
python3 scripts/dev_server.py --watch some-folder

# choose another preferred port (falls forward if busy)
python3 scripts/dev_server.py --port 5600
```

Behavior:
- CSS-only edits trigger stylesheet refresh without a full page reload
- HTML/JS/image/resume changes trigger a full page reload
- `GET /__health` returns current watcher/server state for debugging
