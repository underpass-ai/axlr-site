# axlr-site

The public site of [AXLR](https://github.com/underpass-ai/AXLR), Underpass's agentic execution runtime, served at **https://axlr.underpassai.com/**.

A [Zola](https://www.getzola.org/) site. The home, the agent workflows, install, publish and registry pages are written here; the documentation and the tool catalog are generated at build time from their sources:

| Content | Source | Written to (ignored by git) |
|:--|:--|:--|
| `/docs/` | `docs/` of `underpass-ai/AXLR` at the commit `main` resolves to (or `--axlr-ref`) | `content/docs/`, `data/docs_nav.json`, `static/docs-assets/` |
| `/catalog/<tool>/` | the signed index at `https://registry.underpassai.com/index.json`, each manifest and file checked against its SHA-256 | `content/catalog/<tool>.md` |
| version and commit shown on pages | the latest AXLR release and the synced commit | `data/site.json` |

The sync renames the docs' "ceremony" to "workflow" outside code, identifiers and literal commands (the site says *agent workflows*; MADE's own word stays in `/ceremony …`). `--keep-ceremony-wording` turns that off.

## Build locally

Python 3.11+ (standard library only) and Zola 0.23.6.

```bash
python3 scripts/sync.py                                   # GitHub tarball of AXLR main
python3 scripts/sync.py --axlr-dir ../AXLR --axlr-ref origin/main   # or a local checkout, read with git archive
zola build                                                # writes public/
python3 scripts/check.py                                  # internal links, anchors, wording
zola serve                                                # http://127.0.0.1:1111
```

The registry answers 403 to any client whose `User-Agent` does not start with `axlr`; the sync sends `axlr-site-build/1.0`. Set `GITHUB_TOKEN` to avoid the GitHub API's anonymous rate limit.

## Deploy

[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) runs on every push to `main`, once a day (to pick up new docs and catalog entries) and on demand. It syncs, builds and checks; then, on `main` only:

1. assumes `arn:aws:iam::203918869295:role/axlr-registry-github-deploy` through GitHub OIDC (this repository's `ref:refs/heads/main` subject is in the role's trust policy; no long-lived keys);
2. `aws cloudformation deploy` of the stack `axlr-site` in **us-east-1** from [`infra/template.yaml`](infra/template.yaml): a private S3 bucket, CloudFront with origin access control, a CloudFront Function that serves `/path/` as `/path/index.html` and redirects `/path` to `/path/`, `/404.html` for missing keys, security headers, and the Route 53 A/AAAA aliases for `axlr.underpassai.com` with the ACM certificate already issued in us-east-1;
3. `aws s3 sync public/ --delete` and one CloudFront invalidation of `/*`.

Pull requests only build and check. Nothing waits on a manual approval.

## Layout

```text
config.toml            Zola configuration (search index, highlighting)
content/               hand-written pages; docs/ and catalog/<tool>.md are generated
templates/             base, home, docs, catalog, tool, page and 404 templates
sass/site.scss         the V4 "Developer" styles (palette and type from design/)
static/                brand emblems, the favicon mark, the search script
scripts/sync.py        docs and catalog sync
scripts/check.py       post-build link and wording check
infra/template.yaml    the CloudFormation stack
design/                the four home artboards; V4Developer is the one built
```

Licensed under Apache-2.0.
