+++
title = "Privacy and data"
description = "What AXLR, this site and the tool registry send, keep and for how long. AXLR has no telemetry; Underpass offers no hosted service."
template = "page.html"
[extra]
eyebrow = "Privacy"
lead = "AXLR is software you install and run yourself. It has no telemetry, and Underpass runs no hosted service that receives your prompts, code or results. This page says what does reach us, and what third parties see, when you use AXLR, this site and the tool registry."
+++

Last updated 12 November 2026. Questions: [contact@underpassai.com](mailto:contact@underpassai.com). Security reports: [security@underpassai.com](mailto:security@underpassai.com), as the [security policy](https://github.com/underpass-ai/AXLR/blob/main/SECURITY.md) says. Underpass AI is being incorporated as a Spanish limited liability company; until then the project is run by its founder.

## AXLR, the software

AXLR sends nothing to Underpass. Your model requests go to the provider you choose (OpenRouter, Anthropic, OpenAI or your own server) under that provider's terms. Jev sends its questions to TypeSafe only when you give it a key. Sessions, traces and logs stay on your machine, owner-only, and traces are deleted after 30 days by default. [Security and data](/docs/security/) lists every destination and every file, with what each holds and how long it is kept.

## This site

`axlr.underpassai.com` is a static site on Amazon S3 behind Amazon CloudFront.

| What | Kept by us |
|:--|:--|
| Cookies, analytics, tracking pixels | None |
| Access logs | None: CloudFront standard logging is off |
| Third parties your browser contacts | Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) for the typefaces, and, on pages with diagrams, jsDelivr (`cdn.jsdelivr.net`) for Mermaid. They receive your IP address and browser details under their own policies |

AWS processes each request (your IP address, the page, your browser's headers) to serve it, as any web host does.

## The tool registry

`registry.underpassai.com` serves the signed catalog that `/tools` installs from; `api.registry.underpassai.com` takes uploads from publishers.

**Reading the catalog** (every AXLR console that browses or installs tools):

| Data | Purpose | Kept |
|:--|:--|:--|
| Request counts per IP address | A rate limit of 1,000 requests per five minutes (AWS WAF) | The counters reset every five minutes |
| A sample of requests (IP address, path, headers) | Diagnosing blocked traffic in AWS WAF | Up to 3 hours, by AWS |
| Aggregate request metrics | Operating the service | Counts only, no IP addresses |

There are no access logs of the catalog.

**Publishing a tool** (only if you enrol as a publisher):

| Data | Purpose | Kept |
|:--|:--|:--|
| Your publisher id, public keys, namespaces and the contact you give | Verifying your signed uploads and reaching you about a review | While you are a publisher |
| The IP address of an enrolment request | A rate limit on enrolments | A one-hour window that expires by itself |
| Request nonces and idempotency records | Refusing replayed or duplicated requests | Expire by themselves |
| Your uploads and their test logs | Review, and the record of what was reviewed | Approved versions indefinitely; rejected uploads 90 days |
| The audit log: time, actor, action, subject, reason | Accountability for every change to the catalog | Indefinitely, append-only |
| Function logs and traces | Operating the service: start, end, duration and errors, without request bodies | Logs until deleted; traces 30 days |

Everything runs in AWS (`eu-west-1` for the API and data, CloudFront worldwide). We do not sell or share any of it.

## Engine downloads

The console downloads the KMP and MADE engines from GitHub releases, and `/repair` works with GitHub on your behalf. Those requests go to GitHub under [GitHub's privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement); Underpass receives nothing from them.

## Security reports

A report to `security@underpassai.com` stays in that mailbox, on our own mail server, for as long as handling the report and its advisory needs.

## Changes

A change to this page is dated above and recorded in the [site's history](https://github.com/underpass-ai/axlr-site/commits/main/content/privacy.md).
