+++
title = "The registry"
description = "How registry.underpassai.com serves AXLR's signed tool catalog: a static signed index on S3 and CloudFront, a publish API with signed requests, an admin API behind mTLS, and a sandbox for tests."
template = "page.html"
[extra]
eyebrow = "Registry"
lead = "The registry is the catalog's write side: a serverless Rust service that takes signed uploads, scans and tests them, and publishes a static index the operator signs offline. Everything the console installs from is static."
mermaid = true
+++

## Topology

<pre class="mermaid">
flowchart LR
    Console[AXLR console<br/>/tools install] -->|GET index.json, .minisig, files| CF[CloudFront<br/>registry.underpassai.com]
    CF --> S3pub[(S3 published/<br/>index, manifests, files)]
    Publisher[publisher CLI or console<br/>Ed25519-signed requests] -->|HTTPS| APIpub[HTTP API<br/>publish]
    Reviewer[reviewer or operator CLI<br/>client certificate] -->|mTLS| APIadm[HTTP API<br/>admin]
    APIpub --> Lpub[publish-api<br/>validate · scan · store]
    APIadm --> Ladm[admin-api<br/>publishers · review · yank · publish]
    Lpub --> DDB[(DynamoDB<br/>single table, on-demand)]
    Ladm --> DDB
    Lpub --> S3q[(S3 quarantine/)]
    Lpub -. async .-> Ltest[test-runner<br/>isolated subnet<br/>no NAT, no internet]
    Ltest --> S3q
    Ltest --> DDB
    Ladm -. async .-> Lidx[index-publisher<br/>canonical index]
    Lidx --> S3pub
</pre>

| Part | Does |
|:--|:--|
| `publish-api` | Authenticates the signed request (timestamp, key and publisher status, signature, nonce, rate windows), takes enrolments, validates the bundle, verifies the publisher's signature, runs the policy scan inline and writes the version to quarantine. The only part publishers can reach. |
| `admin-api` | Behind mutual TLS with certificates from a private CA generated offline. Maps the client certificate to a reviewer or operator; approves and suspends publishers, sets rate limits, revokes keys, approves, rejects and yanks versions, accepts the signed index signature. |
| `test-runner` | Runs a version's `tests.json` in a function with no network path: its subnet reaches only the storage endpoints, with no NAT and no internet gateway. |
| `index-publisher` | Writes the canonical unsigned index after every approval or yank. |
| The catalog | `index.json`, `index.json.minisig`, and each version's manifest and files, static on S3 behind CloudFront. |

## Two signatures

- **The publisher's.** Each publisher holds one Ed25519 key, enrolled once and approved by an operator. It signs the bundle digest of every version and every request. A revoked key never verifies again, and the next index carries the revocation.
- **The registry's.** The index is signed in minisign format with a key that never lives in AWS: the registry writes the unsigned index, the operator signs it on their own machine and uploads the `.minisig`. The console ships with the public key and refuses an index whose signature does not verify, so an unsigned publish is harmless.

The index then carries the SHA-256 of each tool's manifest and files. The console verifies the signature, then the manifest and every file against the index, before it shows an install card and again before it writes. One tampered file, manifest or index is caught. The console does not yet read revocations or check the publisher's own signature: today the guarantees it enforces stop at the index signature and the digests.

## Who calls what

| Actor | Through | Can |
|:--|:--|:--|
| Anyone with AXLR | the static catalog | read the index, manifests and files; install after the card |
| A publisher | the publish API, signed requests | enrol, add a key, submit versions inside its namespaces, follow its versions |
| A reviewer | the admin API, mTLS | approve or reject a scanned, tested version of another publisher; yank |
| The operator | the admin API, mTLS | approve, suspend and rate-limit publishers; revoke keys; sign and publish the index |

## Only AXLR clients

The catalog's CloudFront answers 403 to any request whose `User-Agent` does not start with `axlr` (the console sends `AXLR-catalog`). This is identification, not authentication: the signatures and certificates are the real checks; the gate keeps scanners, browsers and misdirected traffic away. A browser that opens a manifest link gets 403, which is why the [catalog pages](@/catalog/_index.md) show each file with its digest instead.

AWS Shield Standard covers CloudFront and Route 53; the catalog carries a web ACL with a per-IP rate rule and AWS's IP reputation list; the APIs are throttled at the stage and every function has reserved concurrency.

## Cost

No servers, no containers to patch, no databases to size: functions, on-demand DynamoDB, S3, CloudFront and Route 53, arm64. The fixed cost is the hosted zone and the domain; everything else scales from zero, and there is no NAT gateway anywhere.

[Publish a tool](@/publish.md) · Source: [underpass-ai/axlr-registry](https://github.com/underpass-ai/axlr-registry)
