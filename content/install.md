+++
title = "Install AXLR"
description = "Download the AXLR release for Linux, macOS or Windows, verify it, and let the setup assistant configure a model (OpenRouter or a local server) and install and connect KMP and MADE."
template = "page.html"
[extra]
eyebrow = "Install"
lead = "One archive per platform carries the three binaries: axlr-tui (the console), axlr-serve (the mTLS service) and axlr (the JSON worker). The first launch of the console runs a setup assistant that picks a model and, on Linux and Apple-silicon macOS, installs and connects KMP and MADE."
+++

## 1. Download and verify

Every release archive contains `axlr`, `axlr-tui`, `axlr-serve`, `VERSION`, `LICENSE`, `NOTICE`, a short `README.md` and the third-party licence texts (`THIRD_PARTY_LICENSES/`), with a sibling `.sha256`. The current release is **AXLR_VERSION**; all releases are on [GitHub](https://github.com/underpass-ai/AXLR/releases).

**Linux and macOS** (`OS` is `linux` or `darwin`, `ARCH` is `amd64` or `arm64`):

```bash
V=AXLR_VERSION; OS=linux; ARCH=amd64
base=https://github.com/underpass-ai/AXLR/releases/download/$V
curl -fsSLO "$base/axlr-$V-$OS-$ARCH.tar.gz"
curl -fsSLO "$base/axlr-$V-$OS-$ARCH.tar.gz.sha256"
sha256sum -c "axlr-$V-$OS-$ARCH.tar.gz.sha256"   # macOS: shasum -a 256 -c …
mkdir -p ~/.local/bin && tar xzf "axlr-$V-$OS-$ARCH.tar.gz" -C ~/.local/bin axlr axlr-tui axlr-serve
axlr-tui --version   # ~/.local/bin must be on PATH
```

**Windows** (PowerShell; `ARCH` is `amd64` or `arm64`):

```powershell
$V = 'AXLR_VERSION'; $ARCH = 'amd64'
$base = "https://github.com/underpass-ai/AXLR/releases/download/$V"
Invoke-WebRequest "$base/axlr-$V-windows-$ARCH.zip" -OutFile "axlr-$V-windows-$ARCH.zip"
Invoke-WebRequest "$base/axlr-$V-windows-$ARCH.zip.sha256" -OutFile "axlr-$V-windows-$ARCH.zip.sha256"
$want = (Get-Content "axlr-$V-windows-$ARCH.zip.sha256").Split(' ')[0]
if ((Get-FileHash "axlr-$V-windows-$ARCH.zip" -Algorithm SHA256).Hash.ToLower() -ne $want) { throw 'checksum mismatch' }
Expand-Archive "axlr-$V-windows-$ARCH.zip" -DestinationPath "$HOME\axlr"
& "$HOME\axlr\axlr-tui.exe" --version
```

On Windows, use native executable paths and PowerShell environment syntax, and supply an absolute `HOME` or the XDG directories. You need a terminal of at least 50 × 15 cells.

## 2. Run the setup assistant

```bash
axlr-tui --root "$PWD"
```

The first launch in a terminal, with no `settings.json` yet and no `--model`, `--session` or `-c`, runs the setup assistant before the console. It asks two things at most and decides the rest; Enter takes the option marked `*`. `axlr-tui setup` runs it again at any time, for example to add a local model.

1. **Model.** With `OPENROUTER_API_KEY` set nothing is asked: the lightest recommended model becomes the default. Otherwise the assistant looks for OpenAI-compatible servers on this machine's usual ports (8080–8082, 8000, 11434 and 1234) and offers three routes:
   - **OpenRouter**: it asks for a key without echo, checks it against OpenRouter's model list, saves it in `credentials.json` beside `settings.json`, and recommends light models able to call tools.
   - **A local server** such as llama.cpp, vLLM, Ollama or LM Studio: pick a model it found or type a base URL. It reads the context window llama.cpp or vLLM report (for other servers, set `context_tokens` yourself) and writes a `local_models` entry.
   - **Skip**, and choose with `/model` later.
2. **Jev, optional.** TypeSafe's external judge: it checks final answers, answers the model's `axlr_judge` and settles each turn's memory, and that text goes to TypeSafe. With `TYPESAFE_API_KEY` set it is on; otherwise one hidden question, Enter skips.
3. **KMP and MADE.** On Linux (amd64, arm64) and Apple-silicon macOS they are installed without a question: the latest official releases are downloaded and verified, MADE's store and authorization are set up, the console's work grant and its pinned workflow definitions are published, and both engines are registered as MCP servers. On Windows and Intel macOS, connect them by hand with the [KMP runbook](@/docs/runbooks--kmp.md) and the [MADE runbook](@/docs/runbooks--made.md).

Without a terminal (a script, a service) the assistant asks nothing: the key comes from the environment, and on the supported platforms the engines install themselves all the same.

A local model must return native tool calls: run llama.cpp with `--jinja` and a template that declares tools, and vLLM with `--enable-auto-tool-choice` and the parser that matches the model. Ollama truncates long prompts silently unless `OLLAMA_CONTEXT_LENGTH` is set. See [local models](@/docs/console.md#local-models).

## The two engines

**KMP** is local-first agent memory: it keeps what was decided, the evidence it rested on and when it happened, never the transcript. It runs on your machine as one binary with an embedded SQLite store, with no account, service or API key, and it answers from stored evidence or says `UNKNOWN` instead of guessing. At every launch the console opens the checkout's own `.kernel` store inside a git repository, or a per-user store outside one; `/memory save` exports the project's memory to `.kmp/memory.jsonl`, which you may commit, and a new store imports it. ChronoLoom, the read-only local viewer inside the KMP binary, lets you move through that memory in time. Apache-2.0, pre-1.0: [github.com/underpass-ai/kmp](https://github.com/underpass-ai/kmp).

**MADE** coordinates: it runs no agents and calls no model. The console does each step's work, while MADE decides which step may be claimed next, enables a transition only when its guards hold, and records every accepted result in a hash-chained journal that verifies its own integrity and order, not the truth of the work. AXLR uses it locally, as one MCP process (`made-mcp`) over one SQLite file; MADE also runs as a gRPC service. Apache-2.0, pre-1.0: [github.com/underpass-ai/made](https://github.com/underpass-ai/made).

`/update` installs or updates both to their latest releases. The `axlr-serve` image pins its own engine versions.

## 3. First prompt

New sessions start in `/normal`. Press `F1` for the controls and `Ctrl+P` for the action palette. After setup, autonomy is on: tools the work mode permits run without a card, except commands on the destructive list (deletions outside the workspace, `git push`, `reset --hard`, `clean`, `rebase`, branch deletion, network writes), which always ask. Reads never need a card. `/approvals` shows the saved choices.

| Command | Does |
|:--|:--|
| `/model` | change the model |
| `/review`, `/writer`, `/research` | tailor the local tool policy to findings, documentation or evidence gathering |
| `/debug`, `/delivery`, `/incident` | run a built-in [agent workflow](@/workflows.md) on the next prompt |
| `/plan` | open the plans panel; `/plan <goal>` plans that goal in atomic tasks |
| `/repair`, `/improve` | work in a clone opened with `axlr-tui --repair` or `axlr-tui --improve` |
| `/changes`, `/undo` | review this session's file edits as diffs; put back the last turn's files (not what a command or MCP server did) |
| `/tools` | list, search, install and publish [catalog tools](@/catalog/_index.md) |
| `/mcp`, `/plugin` | MCP connections and AXLR-managed packages |
| `/update` | install or update KMP and MADE (Linux, Apple-silicon macOS) |

A turn makes at most 32 tool calls (`turn_tool_calls`, 8–256) before it pauses; send a message to go on. `max_session_usd` caps a session's spend and `/usage` shows tokens and cost. `axlr-tui -c` reopens the workspace's latest session and `--session <id>` a given one.

Commands run with your rights unless you turn on `exec_sandbox`: on Linux it runs every command under bubblewrap with the filesystem read-only except the workspace, optionally without network. It is off by default. Extend AXLR with any MCP server (stdio or Streamable HTTP) and with compatible OpenAI/Codex plugin packages, under the same approvals.

The console sends model requests to OpenRouter or to the local server, and to TypeSafe when Jev is on, and saves sessions under `$XDG_STATE_HOME/axlr/sessions`. Local tools act on the chosen workspace; `exec` and MCP servers use your account's permissions, so run AXLR in an account and workspace you trust. More in [getting started](@/docs/getting-started.md) and the [configuration reference](@/docs/configuration.md).

## The other interfaces

- **The JSON worker** needs no model account; it offers `read`, `write`, `edit`, `exec`, `search`, `list` and the plugin calls: `printf '%s\n' '{"protocol_version":1,"request_id":"hello-1","tool":"read","arguments":{"path":"README.md"}}' | axlr --root "$PWD" --profile trusted-local`. See the [worker contract](@/docs/worker.md).
- **The service**, `axlr-serve`, exposes HTTP, gRPC and MCP with mTLS. It needs remote KMP and MADE, runs normal sessions only (no work modes, workflows or plugin packages) and deploys on Kubernetes with the [Helm chart](@/docs/helm.md) as one replica, with mTLS ending in the pod. See the [service API](@/docs/api.md).
- **The Go library** embeds the executor, the OpenRouter client and the MCP client in your own host. See the [library guide](@/docs/library.md).

## Build from source

With Go 1.26, from a full checkout of [underpass-ai/AXLR](https://github.com/underpass-ai/AXLR):

```bash
GOWORK=off go test ./...
GOWORK=off go -C tui test ./...
GOWORK=off CGO_ENABLED=0 go build -trimpath -o /tmp/axlr ./cmd/axlr
GOWORK=off CGO_ENABLED=0 go -C tui build -trimpath -o /tmp/axlr-tui ./cmd/axlr-tui
/tmp/axlr-tui --root "$PWD"
```
