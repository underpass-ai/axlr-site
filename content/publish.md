+++
title = "Publish a tool"
description = "Forge a tool in an AXLR workspace, enrol once as a publisher with your own Ed25519 key, and publish versions that the registry scans, tests in a sandbox and a reviewer approves into the signed index."
template = "page.html"
[extra]
eyebrow = "Registry / Publish"
lead = "You forge a tool in a workspace, enrol once as a publisher, and publish versions. The registry scans each one, runs its tests in a sandbox with no network, and a reviewer who is not you approves it into the signed index everyone installs from."
+++

## The four steps

```text
/tools keygen
/tools enroll acme acme_* --contact ops@acme.example
/tools publish acme_count
→ scanned · no findings · tests passed
```

The console is one registry client; the `axlr-registry` command line is the other. Both hold one Ed25519 key and sign every request with it. There are no tokens, and reads of the catalog stay unauthenticated behind the index signature. The official catalog's publish API is `https://api.registry.underpassai.com`, already set in the console.

### 1. Create your key

`/tools keygen` creates the console's client key in its private state (`<state>/axlr/registry/client.key`, mode 0600, the same format the CLI's `publisher keygen` writes, so one file serves both) and shows the public key and the key id: the first 16 hex characters of the SHA-256 of the public key. `/tools identity` shows them again. The key never enters a workspace and the registry never sees the private half. A second `keygen` is refused; to rotate, move the file away and enrol the new key. `enroll` and `publish` create the key if you skip this step.

### 2. Enrol as a publisher

```text
/tools enroll <publisher id> <namespace>… --contact <address> [--to <catalog>]
```

The request is signed with the key being enrolled, which proves you hold it. It carries the id (2 to 32 lowercase letters, digits, `_` or `-`), the public key, the namespaces your tools will use (`acme_*`) and a contact the operator can reach (an email address or a `scheme:handle`). The answer is `pending: an operator of <catalog> must approve it`. Until an operator approves, every other request of this key is refused with `403 pending`. The operator checks the contact and the namespaces; when approving, the operator may narrow the namespaces, never widen them.

### 3. Prepare the tool

Forge the tool in the workspace with the model (`axlr_forge_tool`), or write it and let the model forge it. Two files beside it are read at publish time and are never part of the tool:

- `.axlr/tools/<name>/tests.json`: the registry's test cases, a list of `{name, input, expect}` with `expect.exit`, `expect.stdout_json` or `expect.stdout_contains`. Without it a version is accepted but can never be approved.
- `.axlr/tools/<name>/catalog.json`: the manifest's `catalog` block: `version`, `category`, `tags`, `license`, `requires`, `network`, `example`, `source`. The console asks for the missing required fields (version, category, licence) one at a time and saves the answers.

A published tool's files sit directly in its directory (no subdirectories), and publishing needs `forged_tools` on and a catalog with an `api_url`.

### 4. Publish

`/tools publish <name>[@version] [--to <catalog>]` refuses a tool installed from a catalog (it is someone else's), verifies the files against the digests they were forged with (so what is published is what was approved), and shows a card: the catalog, the fields, the files, whether `tests.json` goes along, the bundle digest, your key id and the forge card of the tool as the registry receives it. `y` uploads; any other key sends nothing.

The `201` shows the version's status (`scanned`, or `rejected` with the blocking finding) and the policy scan's findings. The console then follows the version in the background for up to four minutes until the sandbox reports `tests passed` or `tests failed` with the failing cases. A version already uploaded answers `409`: publish it again as a new `@version`.

## What the registry checks

**The request.** Every call carries `X-AXLR-Key`, `X-AXLR-Timestamp`, `X-AXLR-Nonce` and `X-AXLR-Signature`, an Ed25519 signature over `axlr-request-v1`, the method, the path, the query, the SHA-256 of the body, the timestamp and the nonce. A clock more than five minutes off answers `401 stale`, a nonce seen twice `401 replay`, a pending or suspended publisher `403`, and a key over its limit `429` with `Retry-After` (60 requests a minute and 20 uploads a day by default).

**The submission.** The publisher is active and the name is inside its namespaces; the name is unowned or owned by this publisher; the version is greater than the latest; the bundle is valid; the publisher's signature over the bundle digest verifies.

**The policy scan.** Deterministic rules over every file, by the manifest's `program`. The same bundle always yields the same report, so the reviewer can reproduce it.

| Rule | Python | bash | node | Severity |
|:--|:--|:--|:--|:--|
| network | `socket`, `urllib`, `http.client`, `requests`, `ftplib`, `smtplib` | `curl`, `wget`, `nc`, `ssh`, `/dev/tcp` | `require("net"/"http"/"https"/"dns")`, `fetch(` | block when the manifest says `network: false`, warn otherwise |
| process | `subprocess`, `os.system`, `os.exec*`, `os.popen`, `ctypes`, `multiprocessing` | `eval`, `exec` of a variable, `ssh` | `child_process` | block |
| dynamic code | `eval(`, `exec(`, `compile(`, `__import__(`, `importlib` | `eval`, `source <(` | `eval(`, `new Function(` | block |
| obfuscation | base64 or hex blobs of 200+ characters, `\x` escape density | `base64 -d`, blobs | blobs, `Buffer.from(..., "base64")` | block |
| escape the workspace | `os.environ`, `expanduser("~")`, absolute `/home`, `/etc`, `..` segments | `$HOME`, `~`, absolute paths, `rm -rf` | `process.env`, `os.homedir()` | warn |
| binary or oversized file | a NUL byte, more than 256 KiB | | | block |

**The tests.** Your `tests.json` runs in a sandbox with no network path, `PATH` and `HOME` only, a timeout and an output cap. A test that tries the network fails, which is the expected result for a `network: false` tool.

**The reviewer.** A person with the reviewer role, who is never the version's publisher, approves a version that is scanned, clean and whose tests passed. "Reviewed" is a verdict with a reviewer and a time, not a proof: no scanner shows that a Python or bash file is harmless. The registry does what is deterministic. The install card shows the origin, the licence, any warning and every file, but not yet the publisher or the reviewer.

After an approval the registry writes the unsigned canonical index; the operator signs it offline with the registry key, which never lives in AWS, and the console refuses an index without a valid signature. The [registry](@/registry.md) page has the architecture, and the [console guide](@/docs/console.md#publishing-a-tool-to-a-catalog) the full command reference.
