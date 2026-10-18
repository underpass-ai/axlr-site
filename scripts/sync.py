#!/usr/bin/env python3
"""Fetch the site's generated content: the AXLR docs and the tool catalog.

Writes, all ignored by git and rebuilt on every deploy:

  content/docs/*.md        the AXLR repository's docs with Zola front matter
  content/catalog/<n>.md   one page per tool of the registry's signed index
  data/site.json           release, commit and index facts for the templates
  data/docs_nav.json       the docs sidebar, in the order of docs/index.md
  static/docs-assets/      images the synced docs embed

The AXLR source is a local checkout (--axlr-dir, read with `git archive` at
--axlr-ref, so the working tree is never touched) or the GitHub tarball of the
commit that --axlr-ref resolves to. Either way the commit is pinned and
recorded on every page. Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "underpass-ai/AXLR"
GITHUB = f"https://github.com/{REPO}"
INDEX_URL = "https://registry.underpassai.com/index.json"
# The registry's CloudFront answers 403 to any User-Agent not starting with "axlr".
USER_AGENT = "axlr-site-build/1.0 (+https://axlr.underpassai.com)"

# The synced docs: the current guides, the runbooks and the catalog design
# record. Everything else the docs link to is linked on GitHub at the commit.
SYNCED = re.compile(r"^docs/(?:[^/]+\.md|runbooks/[^/]+\.md|plans/2026-10-16-[^/]+\.md)$")
# brand.md documents the retired Spectrum wordmark; the site links it on GitHub.
EXCLUDED = {"docs/brand.md"}

# ---------------------------------------------------------------- fetching


def http_get(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def git(axlr_dir: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(axlr_dir), *args], check=True, capture_output=True).stdout


def fetch_source(args: argparse.Namespace, dest: Path) -> tuple[str, str]:
    """Extracts docs/ and catalog/ of AXLR into dest; returns (sha, version)."""
    if args.axlr_dir:
        d = Path(args.axlr_dir)
        sha = git(d, "rev-parse", f"{args.axlr_ref}^{{commit}}").decode().strip()
        data = git(d, "archive", "--format=tar", sha, "docs", "catalog")
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(dest, filter="data")
        try:
            version = git(d, "describe", "--tags", "--abbrev=0", sha).decode().strip()
        except subprocess.CalledProcessError:
            version = ""
    else:
        ref = args.axlr_ref.removeprefix("origin/")
        info = json.loads(http_get(f"https://api.github.com/repos/{REPO}/commits/{ref}", "application/vnd.github+json"))
        sha = info["sha"]
        data = http_get(f"https://codeload.github.com/{REPO}/tar.gz/{sha}")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = []
            for m in tar.getmembers():
                parts = m.name.split("/", 1)
                if len(parts) == 2 and (parts[1].startswith("docs/") or parts[1].startswith("catalog/")):
                    m.name = parts[1]
                    members.append(m)
            tar.extractall(dest, members=members, filter="data")
        version = ""
    # The newest published release is what people install.
    try:
        rel = json.loads(http_get(f"https://api.github.com/repos/{REPO}/releases/latest", "application/vnd.github+json"))
        version = rel.get("tag_name") or version
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"warning: latest release not read ({err}); using {version or 'none'}", file=sys.stderr)
    return sha, version


# ---------------------------------------------------------------- vocabulary
#
# The site says "agent workflows". MADE's word, "ceremony", stays only inside
# code, inside literal commands (/ceremony …), in identifiers and in URLs.

WORD = re.compile(r"(?<![/\w-])(c|C)eremon(y|ies)(?![\w])")


def workflow_words(text: str) -> str:
    def repl(m: re.Match) -> str:
        first = "W" if m.group(1) == "C" else "w"
        return first + ("orkflow" if m.group(2) == "y" else "orkflows")

    return WORD.sub(repl, text)


# ---------------------------------------------------------------- slugs


def strip_inline(text: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"(\*\*|__|\*)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def github_slug(text: str) -> str:
    text = strip_inline(text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def zola_slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", strip_inline(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def unique(slugs: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for s in slugs:
        if s in seen:
            seen[s] += 1
            out.append(f"{s}-{seen[s]}")
        else:
            seen[s] = 0
            out.append(s)
    return out


# ---------------------------------------------------------------- markdown

FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")


def split_fences(md: str) -> list[tuple[str, str, str]]:
    """Returns [(kind, info, text)] with kind 'prose' or 'code'."""
    out: list[tuple[str, str, str]] = []
    buf: list[str] = []
    lines = md.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i].rstrip("\n"))
        if not m:
            buf.append(lines[i])
            i += 1
            continue
        if buf:
            out.append(("prose", "", "".join(buf)))
            buf = []
        marker, info = m.group(2), m.group(3).strip()
        body = [lines[i]]
        i += 1
        while i < len(lines):
            body.append(lines[i])
            close = FENCE.match(lines[i].rstrip("\n"))
            i += 1
            if close and close.group(2).startswith(marker[0] * len(marker)) and not close.group(3).strip():
                break
        out.append(("code", info, "".join(body)))
    if buf:
        out.append(("prose", "", "".join(buf)))
    return out


def headings(md: str) -> list[str]:
    out = []
    for kind, _, text in split_fences(md):
        if kind != "prose":
            continue
        for line in text.splitlines():
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m:
                out.append(m.group(1))
    return out


CODE_SPAN = re.compile(r"(`+)(.+?)\1", re.S)
LINK = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*<?([^)\s>]+)>?(\s+\"[^\"]*\")?\s*\)")


def protect(text: str, pattern: re.Pattern, store: list[str]) -> str:
    def repl(m: re.Match) -> str:
        store.append(m.group(0))
        return f"\x00{len(store) - 1}\x00"

    return pattern.sub(repl, text)


def restore(text: str, store: list[str]) -> str:
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], text)
    return text


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Zola renders page content through Tera, even code: {{, {% and {# must not
# reach it. Code with them becomes raw HTML with the brace as an entity.
TERA = re.compile(r"\{[{%#]")


def no_tera(text: str) -> str:
    return TERA.sub(lambda m: "&#123;" + m.group(0)[1], text)


def no_tera_prose(text: str) -> str:
    def span(m: re.Match) -> str:
        if not TERA.search(m.group(2)):
            return m.group(0)
        return "<code>" + no_tera(html_escape(m.group(2).strip())) + "</code>"

    return no_tera(CODE_SPAN.sub(span, text))


# ---------------------------------------------------------------- docs


class Docs:
    def __init__(self, src: Path, sha: str, keep_wording: bool):
        self.src = src
        self.sha = sha
        self.keep = keep_wording
        self.files = sorted(
            p.relative_to(src).as_posix()
            for p in (src / "docs").rglob("*.md")
            if SYNCED.match(p.relative_to(src).as_posix()) and p.relative_to(src).as_posix() not in EXCLUDED
        )
        self.text = {f: (src / f).read_text(encoding="utf-8") for f in self.files}
        self.anchor_maps = {f: self._anchor_map(f) for f in self.files}
        self.assets: set[str] = set()
        self.warnings: list[str] = []

    def words(self, text: str) -> str:
        return text if self.keep else workflow_words(text)

    def site_path(self, repo_path: str) -> str:
        rel = repo_path.removeprefix("docs/").removesuffix(".md")
        if rel == "index":
            return "/docs/"
        rel = {"ceremonies": "workflows"}.get(rel, rel)
        if not self.keep:
            rel = re.sub(r"ceremon(y|ies)", lambda m: "workflow" if m.group(1) == "y" else "workflows", rel)
        return "/docs/" + rel + "/"

    def _anchor_map(self, f: str) -> dict[str, str]:
        hs = headings(self.text[f])[1:]  # the H1 becomes the page title
        gh = unique([github_slug(h) for h in hs])
        zo = unique([zola_slug(self.words(h)) for h in hs])
        return dict(zip(gh, zo))

    def rewrite_target(self, current: str, target: str, image: bool) -> str:
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
            return target
        path, _, frag = target.partition("#")
        if not path:
            resolved = current
        else:
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(current), path))
        if resolved.startswith(".."):
            self.warnings.append(f"{current}: link leaves the repository: {target}")
            return target
        if image:
            if resolved.startswith("docs/assets/") and "spectrum" not in resolved:
                self.assets.add(resolved)
                return "/docs-assets/" + resolved.removeprefix("docs/assets/")
            return f"https://raw.githubusercontent.com/{REPO}/{self.sha}/{resolved}"
        if resolved in self.anchor_maps:
            url = self.site_path(resolved)
            if frag:
                mapped = self.anchor_maps[resolved].get(frag)
                if mapped is None:
                    # A stale anchor upstream: link the page itself.
                    self.warnings.append(f"{current}: no heading for #{frag} in {resolved}; linking the page")
                else:
                    url += "#" + mapped
            elif not path:
                return target
            return url
        kind = "tree" if (self.src / resolved).is_dir() or not posixpath.splitext(resolved)[1] else "blob"
        return f"{GITHUB}/{kind}/{self.sha}/{resolved}" + (f"#{frag}" if frag else "")

    def convert(self, f: str) -> tuple[str, str, bool, str]:
        """Returns (title, body, has_mermaid, description)."""
        md = self.text[f]
        title = ""
        mermaid = False
        parts: list[str] = []
        for kind, info, text in split_fences(md):
            if kind == "code":
                if info.split()[:1] == ["mermaid"]:
                    lines = text.splitlines()[1:]
                    if lines and FENCE.match(lines[-1]):
                        lines = lines[:-1]
                    inner = "\n".join(lines).rstrip()
                    parts.append(f'<pre class="mermaid">\n{html_escape(inner)}\n</pre>\n')
                    mermaid = True
                elif TERA.search(text):
                    lines = text.splitlines()[1:]
                    if lines and FENCE.match(lines[-1]):
                        lines = lines[:-1]
                    parts.append("<pre><code>" + no_tera(html_escape("\n".join(lines))) + "</code></pre>\n")
                else:
                    parts.append(text)
                continue
            store: list[str] = []
            t = protect(text, CODE_SPAN, store)

            def link(m: re.Match) -> str:
                bang, label, target, ttl = m.group(1), m.group(2), m.group(3), m.group(4) or ""
                new = self.rewrite_target(f, target, bang == "!")
                label = self.words(label) if not bang else label
                store.append(f"{bang}[{label}]({new}{ttl})")
                return f"\x00{len(store) - 1}\x00"

            t = LINK.sub(link, t)
            t = self.words(t)
            t = restore(t, store)
            parts.append(no_tera_prose(t) if TERA.search(t) else t)
        body = "".join(parts)
        m = re.search(r"^#\s+(.+?)\s*$", body, re.M)
        if m:
            title = strip_inline(m.group(1))
            body = body[: m.start()] + body[m.end():]
        body = body.lstrip("\n")
        desc = ""
        for kind, _, text in split_fences(body):
            if kind == "prose":
                for para in re.split(r"\n\s*\n", text):
                    p = para.strip()
                    if p and not p.startswith(("#", "|", "<", "!", "-", ">")):
                        desc = re.sub(r"\s+", " ", strip_inline(p))
                        break
            if desc:
                break
        if len(desc) > 200:
            desc = desc[:197].rsplit(" ", 1)[0] + "…"
        return title, body, mermaid, desc

    def nav(self) -> list[dict]:
        """The sidebar: the groups and links of docs/index.md, in order."""
        groups: list[dict] = [{"title": "Overview", "links": []}]
        seen: set[str] = set()

        def add(group: dict, repo_path: str) -> None:
            if repo_path in self.anchor_maps and repo_path not in seen:
                seen.add(repo_path)
                group["links"].append(repo_path)

        add(groups[0], "docs/index.md")
        add(groups[0], "docs/product.md")
        for kind, _, text in split_fences(self.text["docs/index.md"]):
            if kind != "prose":
                continue
            for line in text.splitlines():
                h = re.match(r"^##\s+(.*)", line)
                if h:
                    groups.append({"title": self.words(strip_inline(h.group(1))), "links": []})
                    continue
                for m in LINK.finditer(line):
                    target = m.group(3).partition("#")[0]
                    if target and not re.match(r"^[a-z]+:", target):
                        add(groups[-1], posixpath.normpath(posixpath.join("docs", target)))
        rest = {"title": "More", "links": []}
        for f in self.files:
            add(rest, f)
        groups.append(rest)
        return [g for g in groups if g["links"]]


def toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return toml_str(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{toml_str(k)} = {toml_value(x)}" for k, x in v.items()) + " }"
    if v is None:
        return '""'
    raise TypeError(type(v))


def front_matter(fields: dict, extra: dict) -> str:
    lines = ["+++"]
    lines += [f"{k} = {toml_value(v)}" for k, v in fields.items()]
    lines.append("[extra]")
    lines += [f"{toml_str(k)} = {toml_value(v)}" for k, v in extra.items()]
    lines.append("+++")
    return "\n".join(lines) + "\n"


def write_docs(docs: Docs, out: Path, data: Path, static: Path) -> int:
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    nav = docs.nav()
    order = [p for g in nav for p in g["links"]]
    titles: dict[str, str] = {}
    for f in docs.files:
        title, body, mermaid, desc = docs.convert(f)
        title = docs.words(title) or f
        if f == "docs/ceremonies.md" and not docs.keep:
            title = "Agent workflows in the console"  # "Workflows" alone repeats the top-level page
        titles[f] = title
        extra = {"source": f, "source_url": f"{GITHUB}/blob/{docs.sha}/{f}", "mermaid": mermaid}
        if f == "docs/index.md":
            fm = front_matter(
                {"title": "Documentation", "description": desc, "sort_by": "weight", "template": "docs.html",
                 "page_template": "doc.html", "insert_anchor_links": "right"},
                extra,
            )
            (out / "_index.md").write_text(fm + body, encoding="utf-8")
            continue
        weight = order.index(f) + 1 if f in order else 999
        name = f.removeprefix("docs/").removesuffix(".md").replace("/", "--") + ".md"
        fm = front_matter(
            {"title": title, "description": desc, "weight": weight, "path": docs.site_path(f).strip("/") + "/"},
            extra,
        )
        (out / name).write_text(fm + body, encoding="utf-8")
    nav_json = [
        {"title": g["title"], "links": [{"title": "Documentation home" if p == "docs/index.md" else titles[p],
                                         "path": docs.site_path(p)} for p in g["links"]]}
        for g in nav
    ]
    (data / "docs_nav.json").write_text(json.dumps(nav_json, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(static, ignore_errors=True)
    for a in sorted(docs.assets):
        dst = static / a.removeprefix("docs/assets/")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(docs.src / a, dst)
    return len(docs.files)


# ---------------------------------------------------------------- catalog


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_params(schema: dict) -> list[dict]:
    required = set(schema.get("required", []))
    out = []
    for name, prop in (schema.get("properties") or {}).items():
        typ = prop.get("type", "")
        if isinstance(typ, list):
            typ = " | ".join(typ)
        if typ == "array" and isinstance(prop.get("items"), dict) and prop["items"].get("type"):
            typ = f"array of {prop['items']['type']}"
        if typ == "object" and isinstance(prop.get("additionalProperties"), dict):
            typ = f"object of {prop['additionalProperties'].get('type', 'values')}"
        rules = []
        if "enum" in prop:
            rules.append("one of " + ", ".join(json.dumps(e, ensure_ascii=False) for e in prop["enum"]))
        for key, word in (("minimum", "≥"), ("maximum", "≤"), ("minLength", "length ≥"), ("maxLength", "length ≤"),
                          ("minItems", "items ≥"), ("maxItems", "items ≤")):
            if key in prop:
                rules.append(f"{word} {prop[key]}")
        if "pattern" in prop:
            rules.append(f"pattern {prop['pattern']}")
        if "format" in prop:
            rules.append(f"format {prop['format']}")
        out.append({
            "name": name,
            "type": typ,
            "required": name in required,
            "default": json.dumps(prop["default"], ensure_ascii=False) if "default" in prop else "",
            "description": prop.get("description", ""),
            "rules": "; ".join(rules),
        })
    return out


def write_catalog(index_url: str, src: Path, out: Path) -> dict:
    base = index_url.rsplit("/", 1)[0]
    raw = http_get(index_url)
    index = json.loads(raw)
    http_get(index_url + ".minisig")  # the signature must be served beside the index
    for old in out.glob("*.md"):
        if old.name != "_index.md":
            old.unlink()
    revoked = {(r.get("name"), r.get("version")) for r in index.get("revocations", []) if isinstance(r, dict)}
    readmes = {p.parent.name: p for p in (src / "catalog" / "tools").glob("*/*/README.md")}
    tools = []
    for t in index.get("tools", []):
        name, version = t["name"], t["version"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,47}", name):
            raise SystemExit(f"index: refusing tool name {name!r}")
        manifest_raw = http_get(f"{base}/{t['manifest']}")
        if sha256(manifest_raw) != t["manifest_sha256"]:
            raise SystemExit(f"{name} {version}: the manifest does not match the index digest")
        manifest = json.loads(manifest_raw)
        mdir = posixpath.dirname(t["manifest"])
        files = []
        for fname, digest in sorted(t.get("files", {}).items()):
            body = http_get(f"{base}/{mdir}/{fname}")
            if sha256(body) != digest:
                raise SystemExit(f"{name} {version}: {fname} does not match the index digest")
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            files.append({"name": fname, "sha256": digest, "url": f"{base}/{mdir}/{fname}", "text": text})
        cat = manifest.get("catalog", {})
        example = cat.get("example") or {}
        requires = t.get("requires") or {}
        readme = ""
        if name in readmes:
            readme = re.sub(r"\A#\s+.*\n+", "", readmes[name].read_text(encoding="utf-8"))
        extra = {
            "version": version,
            "category": t.get("category", ""),
            "tags": t.get("tags", []),
            "program": t.get("program", ""),
            "args": manifest.get("args", []),
            "program_min_version": requires.get("program_min_version", ""),
            "packages": requires.get("packages", []),
            "network": bool(t.get("network")),
            "license": t.get("license", ""),
            "description": manifest.get("description", ""),
            "source_note": cat.get("source", ""),
            "params": schema_params(manifest.get("input_schema") or {}),
            "schema_json": json.dumps(manifest.get("input_schema") or {}, indent=2, ensure_ascii=False),
            "example_input": json.dumps(example["input"], indent=2, ensure_ascii=False) if "input" in example else "",
            "example_output": json.dumps(example["output"], indent=2, ensure_ascii=False) if "output" in example else "",
            "manifest_url": f"{base}/{t['manifest']}",
            "manifest_sha256": t["manifest_sha256"],
            "files": files,
            "updated_at": t.get("updated_at", ""),
            "publisher": t.get("publisher", ""),
            "publisher_key_id": t.get("publisher_key_id", ""),
            "bundle_sha256": t.get("bundle_sha256", ""),
            "signature": t.get("signature", ""),
            "reviewed_at": t.get("reviewed_at", ""),
            "reviewer": t.get("reviewer", ""),
            "warnings": t.get("warnings", []),
            "revoked": (name, version) in revoked,
        }
        fm = front_matter({"title": name, "description": t.get("summary", ""), "template": "tool.html"}, extra)
        (out / f"{name}.md").write_text(fm + readme, encoding="utf-8")
        tools.append(name)
    return {"index_generated_at": index.get("generated_at", ""), "index_sha256": sha256(raw), "tools": tools,
            "catalog": index.get("catalog", "")}


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--axlr-dir", help="a local AXLR checkout (read with git archive; the working tree is untouched)")
    ap.add_argument("--axlr-ref", default=os.environ.get("AXLR_REF", "main"),
                    help="branch, tag or commit to read (default main; origin/main is a good choice for a checkout)")
    ap.add_argument("--index-url", default=INDEX_URL)
    ap.add_argument("--keep-ceremony-wording", action="store_true",
                    help="keep the docs' word 'ceremony' instead of 'workflow'")
    args = ap.parse_args()

    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        sha, version = fetch_source(args, src)
        docs = Docs(src, sha, args.keep_ceremony_wording)
        n = write_docs(docs, ROOT / "content" / "docs", data, ROOT / "static" / "docs-assets")
        cat = write_catalog(args.index_url, src, ROOT / "content" / "catalog")
    site = {"axlr_version": version, "axlr_commit": sha, "axlr_commit_short": sha[:7],
            "axlr_commit_url": f"{GITHUB}/tree/{sha}", **cat}
    (data / "site.json").write_text(json.dumps(site, indent=1), encoding="utf-8")
    for w in docs.warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"synced {n} docs at {sha[:7]} ({version or 'no release'}), {len(cat['tools'])} tools "
          f"(index {cat['index_generated_at']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
