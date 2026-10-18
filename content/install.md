+++
title = "Install AXLR"
description = "Download the AXLR release for Linux, macOS or Windows, verify it, and let the setup assistant configure a model (OpenRouter or a local server) and connect KMP and MADE."
template = "page.html"
[extra]
eyebrow = "Install"
lead = "One archive per platform carries the three binaries: axlr-tui (the console), axlr-serve (the mTLS service) and axlr (the JSON worker). The first launch of the console runs a setup assistant that picks a model and connects KMP and MADE."
+++

## 1. Download and verify

Every release archive contains `axlr`, `axlr-tui`, `axlr-serve`, `VERSION`, `LICENSE`, `NOTICE` and the third-party licence texts, with a sibling `.sha256`. The current release is **AXLR_VERSION**; all releases are on [GitHub](https://github.com/underpass-ai/AXLR/releases).

**Linux and macOS** (`OS` is `linux` or `darwin`, `ARCH` is `amd64` or `arm64`):

```bash
V=AXLR_VERSION; OS=linux; ARCH=amd64
base=https://github.com/underpass-ai/AXLR/releases/download/$V
curl -fsSLO "$base/axlr-$V-$OS-$ARCH.tar.gz"
curl -fsSLO "$base/axlr-$V-$OS-$ARCH.tar.gz.sha256"
sha256sum -c "axlr-$V-$OS-$ARCH.tar.gz.sha256"   # macOS: shasum -a 256 -c …
mkdir -p ~/.local/bin && tar xzf "axlr-$V-$OS-$ARCH.tar.gz" -C ~/.local/bin axlr axlr-tui axlr-serve
axlr-tui --version
```

**Windows** (PowerShell; `ARCH` is `amd64` or `arm64`):

```powershell
$V = 'AXLR_VERSION'; $ARCH = 'amd64'
$base = "https://github.com/underpass-ai/AXLR/releases/download/$V"
Invoke-WebRequest "$base/axlr-$V-windows-$ARCH.zip" -OutFile "axlr-$V-windows-$ARCH.zip"
Invoke-WebRequest "$base/axlr-$V-windows-$ARCH.zip.sha256" -OutFile "axlr-$V-windows-$ARCH.zip.sha256"
(Get-FileHash "axlr-$V-windows-$ARCH.zip" -Algorithm SHA256).Hash.ToLower()   # compare with the .sha256
Expand-Archive "axlr-$V-windows-$ARCH.zip" -DestinationPath "$HOME\axlr"
& "$HOME\axlr\axlr-tui.exe" --version
```

On Windows, use native executable paths and PowerShell environment syntax, and supply an absolute `HOME` or the XDG directories. You need a terminal of at least 50 × 15 cells.

## 2. Run the setup assistant

```bash
axlr-tui --root "$PWD"
```

The first launch, with no `settings.json` yet, runs the setup assistant before the console. It asks two things at most and decides the rest; Enter takes the option marked `*`. `axlr-tui setup` runs it again at any time, for example to add a local model.

1. **Model.** With `OPENROUTER_API_KEY` set nothing is asked: the lightest recommended model becomes the default. Otherwise the assistant looks for OpenAI-compatible servers on this machine's usual ports (8080–8082, 8000, 11434 and 1234) and offers three routes:
   - **OpenRouter**: it asks for a key without echo, checks it against OpenRouter's model list, saves it in `credentials.json` beside `settings.json`, and recommends light models able to call tools.
   - **A local server** such as llama.cpp, vLLM, Ollama or LM Studio: pick a model it found or type a base URL; it reads the context window the server reports and writes a `local_models` entry.
   - **Skip**, and choose with `/model` later.
2. **Jev, optional.** An external judge for final answers; one hidden question, Enter skips.
3. **KMP and MADE.** Installed and configured without a question: the official releases are downloaded and verified, MADE's store and authorization are set up, the console's pinned workflow definitions are published, and both engines are registered. KMP opens the checkout's own `.kernel` inside a git repository.

Without a terminal (a script, a service) the assistant asks nothing: the key comes from the environment and the engines install themselves all the same.

A local model must return native tool calls: run llama.cpp with `--jinja` and a template that declares tools, and vLLM with `--enable-auto-tool-choice` and the parser that matches the model. Ollama truncates long prompts silently unless `OLLAMA_CONTEXT_LENGTH` is set. See [local models](@/docs/console.md#local-models).

## 3. First prompt

New sessions start in `/normal`. Press `F1` for the controls and `Ctrl+P` for the action palette. AXLR asks before tool calls by default; `/approvals` shows the choices you saved.

| Command | Does |
|:--|:--|
| `/model` | change the model |
| `/review`, `/writer`, `/research` | tailor the local tool policy to findings, documentation or evidence gathering |
| `/debug`, `/delivery`, `/incident`, `/plan`, `/repair`, `/improve` | run a built-in [agent workflow](@/workflows.md) on the next prompt |
| `/tools` | list, search, install and publish [catalog tools](@/catalog/_index.md) |
| `/mcp`, `/plugin` | MCP connections and AXLR-managed packages |
| `/update` | install or update the local KMP and MADE engines |

The console sends model requests to OpenRouter or to the local server, and saves sessions under `$XDG_STATE_HOME/axlr/sessions`. Local tools act on the chosen workspace; `exec` and MCP servers use your account's permissions, so run AXLR in an account and workspace you trust. More in [getting started](@/docs/getting-started.md) and the [configuration reference](@/docs/configuration.md).

## The other interfaces

- **The JSON worker** needs no model account: `printf '%s\n' '{"protocol_version":1,"request_id":"hello-1","tool":"read","arguments":{"path":"README.md"}}' | axlr --root "$PWD" --profile trusted-local`. See the [worker contract](@/docs/worker.md).
- **The service**, `axlr-serve`, exposes HTTP, gRPC and MCP with mTLS; deploy it on Kubernetes with the [Helm chart](@/docs/helm.md). See the [service API](@/docs/api.md).
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
