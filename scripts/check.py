#!/usr/bin/env python3
"""Check the built site in public/: internal links and anchors resolve, and
the word "ceremony" appears only in code or in literal commands (/ceremony).

Exits non-zero on a broken internal link or a wording error; anchors that are
missing are errors too unless --warn-anchors. Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
BASE = "https://axlr.underpassai.com"
WORD = re.compile(r"(?<![/\w-])ceremon(y|ies)\b", re.I)
SKIP_TEXT = {"code", "pre", "script", "style", "kbd", "samp"}  # and the .vocab-note on /workflows/


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.text: list[str] = []
        self.depth = 0
        self.skipping: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        for key in ("href", "src"):
            if a.get(key) and tag in ("a", "img", "link", "script"):
                self.links.append(a[key])
        if tag in SKIP_TEXT or "vocab-note" in (a.get("class") or ""):
            self.depth += 1
            self.skipping.append(tag)

    def handle_endtag(self, tag):
        if self.skipping and tag == self.skipping[-1]:
            self.skipping.pop()
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.text.append(data)


def target_file(path: str) -> Path | None:
    p = PUBLIC / unquote(path).lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    if p.is_file():
        return p
    if (p / "index.html").is_file():
        return p / "index.html"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--warn-anchors", action="store_true")
    args = ap.parse_args()
    pages: dict[Path, Page] = {}
    for f in sorted(PUBLIC.rglob("*.html")):
        p = Page()
        p.feed(f.read_text(encoding="utf-8"))
        pages[f] = p
    errors: list[str] = []
    warnings: list[str] = []
    for f, p in pages.items():
        rel = "/" + f.relative_to(PUBLIC).as_posix()
        for link in p.links:
            if link.startswith(BASE):
                link = link[len(BASE):] or "/"
                if link.startswith("#"):
                    link = "/" + link
            u = urlsplit(link)
            if u.scheme or u.netloc or link.startswith(("mailto:", "data:")):
                continue
            if not u.path:
                target = f
            elif u.path.startswith("/"):
                target = target_file(u.path)
            else:
                target = target_file(str((Path(rel).parent / u.path).as_posix()))
            if target is None:
                errors.append(f"{rel}: broken link {link}")
                continue
            if u.fragment and target.suffix == ".html" and target in pages and unquote(u.fragment) not in pages[target].ids:
                (warnings if args.warn_anchors else errors).append(f"{rel}: missing anchor {link}")
        text = " ".join(p.text)
        for m in WORD.finditer(text):
            ctx = text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
            errors.append(f"{rel}: wording 'ceremon…' outside code: …{ctx}…")
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"checked {len(pages)} pages: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
