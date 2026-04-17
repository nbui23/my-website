#!/usr/bin/env python3
"""Update cache-busting version strings in index.html based on file content hashes."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def main():
    css_hash = file_hash(ROOT / 'styles.css')
    js_hash = file_hash(ROOT / 'scripts' / 'main.js')
    favicon_hash = file_hash(ROOT / 'images' / 'logos' / 'baby.jpeg')

    index = ROOT / 'index.html'
    content = index.read_text()

    content = re.sub(r'(styles\.css)\?v=[^"]+', f'\\1?v={css_hash}', content)
    content = re.sub(r'(scripts/main\.js)\?v=[^"]+', f'\\1?v={js_hash}', content)
    content = re.sub(r'(baby\.jpeg)\?v=[^"]+', f'\\1?v={favicon_hash}', content)

    index.write_text(content)
    print(f'styles.css  ?v={css_hash}')
    print(f'main.js     ?v={js_hash}')
    print(f'baby.jpeg   ?v={favicon_hash}')


if __name__ == '__main__':
    main()
