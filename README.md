# my-website

Minimal website summarizing my experience

## Local dev server

Use the repo-local live-reload server when OMX is running:

```bash
python3 scripts/dev_server.py
```

Then open:

```text
http://127.0.0.1:5501/index.html
```

It live-reloads on changes to:
- `index.html`
- `styles.css`
- `scripts/`
- `images/`
- `resume/`

It ignores OMX/VS Code/git churn under:
- `.omx/`
- `.omc/`
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
