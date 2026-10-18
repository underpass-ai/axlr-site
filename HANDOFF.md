# Handoff: build and deploy axlr.underpassai.com

Written 18 Oct 2026 for a fresh session. Everything below was decided with Tirso (the owner) and is current. Work in `/home/gx10a/Documents/ai/axlr-site` (this folder: a fresh `git init`, no commits, no remote yet).

## What the site is

The public site of AXLR, Underpass's **agentic execution runtime** (not only a console). It must say, in English, what the product is and give four things: the home, the documentation (rendered from the AXLR repository's `docs/`), the catalog of pre-forged tools (rendered from the registry's signed index) and the agent workflows, plus how to install and how to publish.

The look is decided: **V4 "Developer"**, the artboard in [`design/V4Developer.dc.html`](design/V4Developer.dc.html) (open it as HTML: it is a self-contained page; ignore the `support.js` line and the `<x-dc>`/`sc-for`/`{{…}}` templating, which belongs to the design tool; the inline styles, type, spacing and content are the spec). The other three artboards in `design/` are the directions that were not chosen; keep them only as reference. The design canvas is at https://claude.ai/artifact/5ZH66GAWaczwVUxnB9yiAP (private to the owner).

Design facts to keep exactly:

- Logo: the current emblem, `static/brand/axlr-emblem-light.svg` on light backgrounds and `axlr-emblem-dark.svg` on dark ones (a pixel wordmark with a chevron mark; the older "Spectrum bars" wordmark is retired, do not use it).
- Palette: ink `#1B1411`, copper `#B85C38`, gold `#D97B2D`, brown `#6B4A2E`, sand `#C9B08C`, paper `#FAF8F4`, white, hairline `#E6E0D6`, body text `#4A3A2E`. Fonts: IBM Plex Sans (body, headings) and IBM Plex Mono (commands, names), from Google Fonts.
- Vocabulary: say **agent workflows**, never "ceremonies", on every page; `ceremony` stays only inside literal commands (`/ceremony install …`) and in a one-line note on the workflows page ("MADE calls a workflow definition a ceremony"). The owner asked for the industry-standard name.
- Copy must come from the real documentation, not invention. Read the AXLR repository first: `README.md`, `docs/product.md`, `docs/index.md`, `docs/console.md`, `docs/ceremonies.md`, `docs/api.md`, `docs/worker.md`, `docs/library.md`, `docs/plugins.md`, `docs/helm.md`. Four interfaces: `axlr-tui` (console), `axlr-serve` (HTTP, gRPC and MCP with mTLS; Helm chart), the `axlr` JSON worker, the Go library. Three engines: AXLR executes, KMP remembers, MADE coordinates. Trusted workspace, approval per effect, work modes, built-in workflows (`/debug`, `/delivery`, `/incident`, `/plan`, `/repair`, `/improve`), forged tools, the catalog and `/tools`.

## Where the inputs are

| Input | Location |
|:--|:--|
| AXLR source and docs | `/home/gx10a/Documents/ai/AXLR-catalog` is a clone at `origin/main` (the owner's other checkout `/home/gx10a/Documents/ai/AXLR` is used by another agent: never touch it). GitHub: `underpass-ai/AXLR`. `git -C /home/gx10a/Documents/ai/AXLR-catalog fetch origin main` before reading. |
| Catalog index (production) | `https://registry.underpassai.com/index.json` and `index.json.minisig`; manifests and files under `tools/<name>/<version>/`. **Every request must send a `User-Agent` starting with `axlr`** (for example `axlr-site-build/1.0`), or CloudFront answers 403. Entries today: `seat_allocation` 1.0.0, `business_days` 1.0.0; fields are in the registry repo's `crates/domain/src/index_entry.rs`. |
| Registry repository | `/home/gx10a/Documents/ai/axlr-registry` (GitHub `underpass-ai/axlr-registry`): `docs/architecture.md`, `docs/client-identity.md`, `docs/api.md` describe publishing; the AXLR-side design docs are `docs/plans/2026-10-16-*.md` in the AXLR repo (tool catalog, ceremony catalog with 37 workflows and their tiers, registry design). |
| Tool and workflow catalogs (content for the catalog and workflows pages) | AXLR repo: `docs/plans/2026-10-16-prebuilt-tools-catalog.md`, `docs/plans/2026-10-16-ceremony-catalog.md`, reference entries under `catalog/`. |
| Brand | AXLR repo `docs/brand.md` and `docs/assets/brand/`; the two emblems are already copied into `static/brand/`. |

## Decisions on the build

- **Generator: Zola** (single binary, fast, no Node). `zola` 0.23.6 for linux aarch64 is at `/tmp/claude-1000/-home-gx10a-Documents-ai-AXLR/bbc08fbf-5773-4eb3-a932-afd0285ceee8/scratchpad/zola-dl/zola` on this machine for local builds (a scratch path: download it again from the GitHub release if it is gone); CI installs it with `taiki-e/install-action@v2` (`tool: zola`).
- **Content sync at build**: `scripts/sync.py` (Python 3 stdlib only) fetches the AXLR docs (a checkout or the GitHub tarball of `main`, pinned by commit) into `content/docs/` with Zola front matter, rewriting relative links between docs and dropping the Mermaid blocks into `<pre class="mermaid">` with the Mermaid script loaded only on pages that have one; and fetches the registry index into `content/catalog/<name>.md` (one page per tool: summary, program, licence, category, tags, the install line, publisher, reviewer and review date, file digests, links to the served manifest and files) plus `content/catalog/_index.md`. The workflows section is hand-written content from the ceremony catalog doc, tiered as that doc tiers them (A runs today, B with approximations, C waits for console work).
- **Pages**: `/` (home as V4), `/docs/` with a left sidebar in the order of `docs/index.md`, `/catalog/` and `/catalog/<tool>/`, `/workflows/`, `/install/` (the setup assistant, `axlr-tui setup`, local models or OpenRouter, Linux, macOS, Windows), `/publish/` (keygen, enrol, publish; what a reviewer checks), and `/registry/` (the registry's architecture in one page). A `404.html`. Search: Zola's `build_search_index` with elasticlunr, wired to the header box.
- **Hosting** (same pattern as the registry, cheap): one CloudFormation stack `axlr-site` in **us-east-1** with a private S3 bucket, CloudFront with origin access control, `DefaultRootObject index.html`, a CloudFront Function that maps `/path/` to `/path/index.html` and sends the 404 page, the Route 53 alias `axlr.underpassai.com`, HTTP to HTTPS. Template in `infra/template.yaml`. No WAF: the site is public content; AWS Shield Standard covers it.
- **Deploy**: `.github/workflows/deploy.yml` on push to `main`: sync, `zola build`, `aws cloudformation deploy` the stack, `aws s3 sync public/ s3://<bucket> --delete`, one CloudFront invalidation `/*`. Pull requests only build. Credentials by GitHub OIDC: reuse the IAM role `arn:aws:iam::203918869295:role/axlr-registry-github-deploy` by adding this repository's subject to its trust policy (see below); no long-lived keys.

## AWS facts (account 203918869295, profile `gx10-cli`; never the `inditex` profile)

- Hosted zone `underpassai.com`: `Z0091758WONBBU37UFO7`. No record exists yet for `axlr.underpassai.com`.
- ACM certificate for `axlr.underpassai.com`, **us-east-1**, already ISSUED: `arn:aws:acm:us-east-1:203918869295:certificate/b6a1560b-14ef-479c-823d-b1fb7252f1fb` (validation CNAME already in the zone). Pass it to the stack as a parameter.
- GitHub deploy role `axlr-registry-github-deploy` (PowerUserAccess plus IAM on `axlr-registry-*` roles) trusts the OIDC provider `token.actions.githubusercontent.com` with GitHub's **immutable subject** format, so a new repository's subject is `repo:underpass-ai@225552176/<repo>@<repo id>:ref:refs/heads/main` (read the repo id with `gh api repos/underpass-ai/<repo> -q .id` after creating it). Add that subject to the role's trust policy (`aws iam update-assume-role-policy`); do not widen it to `*`. The stack's resources are named `axlr-site-*`, so the role also needs no new IAM rights (no IAM roles in this stack; a CloudFront Function needs none).
- CloudFront's fixed hosted zone id for Route 53 aliases: `Z2FDTNDATAQYW2`.
- The owner has `gh` logged in as `tgarciai` with rights on the `underpass-ai` organization; create the repository as `underpass-ai/axlr-site`, public, Apache-2.0 (the `LICENSE` file is already here), with `gh repo create --source . --push`.

## Done so far in this folder

`git init`; `LICENSE`; `static/brand/axlr-emblem-{light,dark}.svg`; `design/` with the four artboards; empty `content/`, `templates/`, `sass/`, `infra/`, `scripts/`, `.github/workflows/`. Nothing else: no `config.toml`, no templates, no stack, no commit.

## What done looks like

1. `zola build` passes locally with the synced docs and catalog; the home matches V4; every page works at phone width; links between docs resolve; no "ceremonies" outside commands.
2. The repository `underpass-ai/axlr-site` exists with `main` pushed, the deploy workflow green, the stack created, and `https://axlr.underpassai.com/` serving the site (check `/`, `/docs/`, `/catalog/seat_allocation/`, `/workflows/`, `/404`).
3. A `README.md` that says how to run the sync and the build locally and how the deploy works, and a short line in the AXLR repository is **not** needed (the owner will link it).
4. Report to the owner in Spanish (they write in Spanish; the site is in English), with the live URL and anything you could not verify.

Rules the owner holds to: cheap to run, nothing stuck waiting on an approval (no manual gates in the workflow), no `inditex` AWS profile, build with at most two heavy processes at once on this machine.
