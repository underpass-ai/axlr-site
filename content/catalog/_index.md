+++
title = "Catalog"
description = "Pre-forged tools for AXLR: tested programs in the exact shape of a forged tool, served from the signed index at registry.underpassai.com and installed from the console with /tools install."
sort_by = "title"
template = "catalog.html"
page_template = "tool.html"
+++

A catalog of pre-forged tools serves tested tools in the exact shape of a [forged tool](@/docs/console.md#forged-tools), so neither the person nor the model writes D'Hondt seat allocation or business-day arithmetic again. The console reads the catalog's `index.json`, signed with an Ed25519 key in minisign format, and installs a tool as a forged tool with an origin: the same `.axlr/tools/<name>/` directory, the same per-workspace registry, the same `axlr_run_tool` and the same refusal when a file changes.

When no tool fits, the model can also forge one: it writes the program into `.axlr/tools/<name>/`, you approve it like a write, and it runs as a `local_exec`; a workspace holds up to 64 tools, each file up to 64 KiB.

The official catalog, `axlr`, is built into the console. Every entry passed a deterministic policy scan and its own tests in a sandbox without network, and a named reviewer approved it. "Reviewed" is a verdict with a reviewer and a time, not a proof that a program is harmless: the install card shows the command and every file before anything is written.
