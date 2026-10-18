+++
title = "Agent workflows"
description = "Multi-step state machines the AXLR console drives and MADE arbitrates and records: six built-in commands, any published definition through /ceremony, and a proposed catalog of 37 workflows in three tiers, one of them written."
template = "page.html"
[extra]
eyebrow = "Workflows"
lead = "Multi-step state machines the console drives and MADE arbitrates and records. Each one has states, guarded transitions, capped loops, the points where a person decides and the judgements the model makes for itself."
mermaid = true
+++

<div class="note vocab-note"><p>MADE calls a workflow a <em>ceremony</em>: the versioned definition is a ceremony definition and each run a ceremony instance. The word survives in commands such as <code>/ceremony</code>.</p></div>

AXLR runs ordinary work directly. A workflow starts only when you ask for one: a work-mode command, `/ceremony` with a definition, or a self-repair or self-improvement the agent requests with evidence the console validates. The console drives the instance and the model does each step's work with AXLR tools; the model never drives a console workflow through direct `made_*` calls. MADE records every accepted step completion and transition in a hash-chained journal, so the result is an instance whose history can be checked, not a state that changed by itself. MADE does not verify the work: that a step did real work is the console's evidence (command exits, revisions, files), which MADE records.

## MADE

MADE is Underpass's open-source coordination engine (Apache-2.0, [github.com/underpass-ai/made](https://github.com/underpass-ai/made), pre-1.0). It runs no agents and, in its local form, calls no model: the console does each step's work, while MADE decides which step may be claimed next and enables a transition only when its guards hold. Its journal verifies its own integrity and order, not the truth of the work, and a person's approval at a human guard is a separate recorded fact that an agent's claim cannot replace. AXLR uses MADE locally, as one MCP process (`made-mcp`) over one SQLite file; MADE also runs as a gRPC service.

## Built in

Six commands start the console's pinned definitions. Selecting `/debug`, `/delivery` or `/incident` does not start an instance; the next prompt does. `/plan` opens the plans panel, and `/repair` and `/improve` run only in a clone that `axlr-tui --repair` or `--improve` prepared. AXLR checks the published definition's semantic digest, starts the instance and claims its first step.

| Command | Definition | Sequence and acceptance |
|:--|:--|:--|
| `/debug` | `axlr_debug` 2.0 | Reproduce with a nonzero command exit → diagnose → repair until the same command exits zero → integrate |
| `/delivery` | `axlr_delivery` 2.0 | Brief with criteria, scope and baseline command → build until that command exits zero → integrate |
| `/incident` | `axlr_incident` 1.0 | Triage → evidence timeline → analysis and actions → draft and fresh-context review → the person's approval → postmortem publication |
| `/plan` | `axlr_plan`, `axlr_task`, `axlr_sync` 1.0 | Decompose a brief into verified atomic tasks → the person's approval → each task in a fresh worker (red for test-first tasks, green, hand-back) → a sync after each wave |
| `/repair` | `axlr_repair` 1.0 | Reproduce → diagnose → repair in a fresh clone → the console commits, pushes and opens the pull request → watches its checks → merge decision (automatic with `repair.auto_merge`, otherwise yours) → squash merge |
| `/improve` | `axlr_improve` 1.0 | Brief with a check that fails in a fresh clone → build until it passes → the console opens the pull request → watches its checks → the person's merge decision → squash merge |

- **Check commands.** A proposed check is `{program, args}` with no implicit shell. The first command, or a changed reproduction command, needs your approval even in full autonomy; once accepted, repair and build always rerun the saved command. Each run has a five-minute timeout.
- **Bounded loops.** Debug reproduction and repair, and delivery build, allow at most three iterations per phase. Exhaustion leads to `BLOCKED`; successful integration to `COMPLETED`. Both return the session to normal mode.
- **What integration proves.** In `/debug` and `/delivery`, integration records the report, `git rev-parse HEAD` and the dirty files; it does not commit, merge or publish. A zero exit proves only what that command checks.
- **Self-repair and self-improvement.** `axlr-tui --repair "<brief>"` and `axlr-tui --improve "<brief or #issue>"` let the console change the configured repository (`repair.repository`, AXLR's own by default) through a pull request it opens with `gh`; an improvement always leaves the merge to you.

The [console's workflow guide](@/docs/ceremonies.md) has the full behaviour, and the [MADE runbook](@/docs/runbooks--made.md) prepares the identity and publishes the pinned definitions.

## Any published definition

`/ceremony` lists the published definitions; `/ceremony <definition> [version] [brief]` runs one through the generic loop. The console claims each step MADE lists as claimable, hands the model the step's own prompt from the definition, completes the step with exactly the fields the model hands back through `axlr_step_done`, applies the transition MADE enables and claims the next step. At a terminal state it writes the outcome to KMP and returns the session to normal mode. A state with no enabled transition and no claimable step, such as a MADE human guard, waits for something outside the console.

`/ceremony publish <file.yaml>` validates and publishes a definition you wrote; a relative path is read from the workspace. A published name and version is immutable: change the version when the content changes, and running instances stay on the version they started with. The model can design definitions; it never publishes one.

```text
/ceremony publish draft_critique_revise-1.0.yaml
/ceremony draft_critique_revise a 300-word release note; criteria: accurate, plain, names every breaking change
```

## The catalog

The catalog packages orchestration patterns that recur across agent frameworks and research (maker-checker, councils, red teams, Delphi rounds, STORM-style research, spec-driven delivery) as MADE definitions the generic loop can run. It is a proposal of 16 October 2026: one reference definition exists, and the console's `/ceremony install` command and the catalog pages per workflow are designed but not built yet. Until then, a catalog definition is published with `/ceremony publish`.

### The reference definition: `draft_critique_revise` 1.0

Write a draft from a brief, critique it against the brief's named criteria, revise; at most three critique rounds (counted by the critic and bounded by MADE's `max_bounces`) and two revision attempts per round (MADE's step `repeat`). Deliver when the critique accepts it, escalate to the person when the rounds run out. It validates as publishable with MADE 0.10.0, with one accepted warning (its loop has no human-controlled state), and its four paths (accepted at once; rejected, revised, accepted; a revision that cannot settle; three rejections) were walked through a real `made-mcp` in a disposable store. [Read the definition](https://github.com/underpass-ai/AXLR/blob/main/catalog/ceremonies/writing/draft_critique_revise-1.0.yaml).

<pre class="mermaid">
stateDiagram-v2
    direction LR
    [*] --> DRAFT
    DRAFT --> CRITIQUE: drafted
    CRITIQUE --> DELIVER: accepted
    CRITIQUE --> REVISE: revision needed
    CRITIQUE --> ESCALATE: critique exhausted
    REVISE --> CRITIQUE: revised
    REVISE --> ESCALATE: rounds exhausted
    DELIVER --> COMPLETED: delivered
    ESCALATE --> BLOCKED: escalated
    COMPLETED --> [*]
    BLOCKED --> [*]
</pre>

### What the generic loop can run today

| Mechanism | Today | Rule for a catalog definition |
|:--|:--|:--|
| Automated guards on step status (`step_status:<step>:COMPLETED`) and on a top-level output field (`output_field:<step>:<field>=<json>`, exact equality) | yes | every judgement is derived into a scalar (`accepted=true`, `decision="approve"`); a numeric threshold is computed by the step and handed back as a boolean |
| Loops: `repeat.max_iterations` on a step or state, `max_transitions` for the whole instance, `max_bounces` per edge | yes | every loop has a cap and a `step_repeat_exhausted` or `state_repeat_exhausted` exit to a terminal or escalation state |
| A person's decision | approximated | a step whose prompt puts the question to the person in the conversation and hands back `decision`, which is the model's output, not a recorded human approval. The generic loop cannot approve a MADE human guard (`type: human`, `check: manual_approval`); the built-in workflows approve theirs through a separate approver identity |
| Independent voices (councils, debaters, blind screeners) | approximated | sequential steps, one per voice, whose prompt tells the model not to rely on earlier voices (marked `see_prior: false`). MADE reads that flag only in its own council handler and the generic loop runs every voice in the same session, so independence rests on the prompt alone |
| Check commands | only in the pinned built-in workflows | the step runs the command through `local_exec` and reports `passed` |
| Budget | per session | `max_session_usd`, the per-request context cap (`prompt_tokens`, 75,000 by default) and `max_transitions` bound the work |

### Tiers

**A** runs in the generic loop today. **B** runs today with the person's decision and parallel voices approximated as above; its page will say so. **C** waits for console features (an approval card in the generic loop, check commands, fan-out) before it is worth publishing. Rounds are always capped; the cap is in the definition.

In the tables below, a "council" is one model given several prompts, not a MADE council of registered agents, and "blind" means a prompt that excludes earlier voices. The snake_case pattern names are MADE's own (`maker_checker`, `broadcast_collect`, `group_chat`, `handoff`, `magentic`, `advisor`) or its `roundtable_fixed_order` preset; catalog definitions approximate them with ordinary sequential states and steps. MADE's `advisor` kind needs MADE 0.10.0.

### Writing and editing

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `draft_critique_revise` | polished text from a brief with named criteria | draft → critique → revise ⟲ → deliver / escalate | ≤ 3 critique rounds, ≤ 2 revision attempts each | maker_checker, Self-Refine | **A** (reference, validated and walked) |
| `editorial_board` | one draft read by fact, style, legal and audience editors, merged by a chief | draft → fact → style → legal → audience → merge → chief verdict | one pass; chief may return once | roundtable_fixed_order | A |
| `translation_backtranslation` | translation checked by a blind back-translation | translate → back-translate (`see_prior: false`) → diff → fix ⟲ → sign-off | fix ≤ 3 | maker_checker | A |
| `writers_room` | story development | premise → pitches (4 sequential voices) → selection → beat sheet → scene drafts → table read → revise | revise ≤ 2 | broadcast_collect | B |

### Research and science

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `literature_review_storm` | cited survey of a topic | perspectives → interviews (one step per perspective) → outline → person's outline decision → draft → citation check → revise ⟲ | revise ≤ 2 | STORM, broadcast_collect | B |
| `systematic_review` | screen studies against inclusion criteria, two blind screeners | protocol → search → screen A → screen B (`see_prior: false`) → conflicts → extraction → bias appraisal → synthesis | conflicts to the person | voting parallelization | B |
| `reproducibility_check` | re-run a paper's claim | claims → environment → run ⟲ → compare → discrepancy report | run ≤ 3 | Reflexion | C (check commands) |
| `peer_review_simulation` | pre-submission critique | three reviews (sequential, `see_prior: false`) → meta-review → rebuttal → revised verdict ⟲ | until scores stop moving, ≤ 2 | AgentReview, debate | B |
| `hypothesis_tournament` | rank candidate hypotheses | generate → pairwise debate ⟲ → ranking → person's pick → experiment design | debate ≤ 3 rounds | Co-Scientist, group_chat | B |

### Software

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `spec_driven_delivery` | idea to feature through reviewed specs | specify → clarify ⟲ → plan → tasks → implement (hands off to `/plan`) → verify → converge | clarify until no ambiguity, ≤ 3 | spec-kit, Kiro, orchestrator-workers | C (approval cards; `/plan` handoff) |
| `security_review_council` | threat model, injection, authorization, secrets and dependency lenses on a diff | scope → five lenses (sequential, `see_prior: false`) → consolidate → rebuttal → verdict → remediation plan | rebuttal once | broadcast_collect, council | B |
| `dependency_upgrade` | upgrade one dependency safely | inventory → changelog digest → branch → fix breakages ⟲ → tests → PR | fix ≤ 5 | Reflexion | C (check commands, PR flow of `/improve`) |
| `code_migration` | migrate in slices with parity checks | survey → strategy (person decides) → slice plan → migrate slice ⟲ → parity → cutover | per slice | plan-and-execute, waves | C |
| `documentation_audit` | find and fix documentation that diverges from code | inventory → claims → verify claims → fix → fresh review | verify per claim | evaluator-optimizer | B |
| `test_first_loop` | TDD on one behaviour | write failing test → red → implement ⟲ → green → refactor | implement ≤ 6 | TDD, Reflexion | C (check commands; `/plan` tasks already do red/green) |
| `release_readiness` | go or no-go | evidence → checklist → risk review → rollback plan → decision | none | prompt chaining with a gate | B |

### Decision-making

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `red_team_review` | attack a plan before committing to it | summary → attacks (3 voices, `see_prior: false`) → defence → severity rating → mitigations ⟲ → sign-off | until no new high finding, ≤ 3 | debate, maker_checker | A |
| `delphi_estimate` | expert-style forecast | question → five estimates (`see_prior: false`) → anonymised feedback → revise ⟲ → aggregate | until spread under the brief's bound, ≤ 3 | Delphi method (methodology source unverified), Mixture of Agents | B |
| `pre_mortem` | how the project fails | assume failure → five failure stories → cluster → rank → mitigations | none | broadcast_collect | A |
| `decision_memo_council` | options memo with a vote and a dissent record | frame → options → analysis per option → five votes (`see_prior: false`, the same model five times) → dissent → decision | vote once | LLM Council, group_chat | A |
| `advisor_checked_task` | a task the executor must clear with an advisor before and after | brief → advice → work ⟲ → advice → deliver | advice loops until no blocking advice, ≤ 3 | MADE `advisor` | A |

### Business and administration

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `rfp_response` | answer a request for proposals | requirements → compliance matrix → draft per section ⟲ → review → price check → sign-off | per section until the review passes | orchestrator-workers | B |
| `procurement_comparison` | compare vendors against the person's criteria | criteria (person decides) → gather → score per vendor → sensitivity check → recommendation | none | parallelization | B |
| `meeting_to_actions` | notes to owned, confirmed actions | extract → owners → confirm with the person → publish | until every item has an owner | prompt chaining | A |
| `okr_review` | quarterly objectives review | collect evidence → score key results → explain gaps → propose next quarter → person decides | none | prompt chaining | A |
| `incident_comms` | customer-facing communications during an incident | facts → audiences → drafts → legal read → approval → publish | legal read ≤ 2 | maker_checker | B |

### Policy and civics

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `policy_brief_stakeholders` | a brief tested against simulated stakeholders | evidence → draft → stakeholder simulation (4–6 personas, sequential) → revise ⟲ → sign-off | until objections are addressed, ≤ 3 | Generative Agents, Habermas | B |
| `legislative_impact` | impact analysis of a bill | summary → affected groups → cost and benefit per group → legal consistency → options → brief | none | prompt chaining, broadcast_collect | A |
| `consultation_synthesis` | synthesis of public comments | cluster → positions → common ground → statement → critique rounds ⟲ → final statement | until approval rises no further, ≤ 3 | Habermas Machine | B |
| `deliberative_minipublic` | a simulated citizens' assembly on one question | briefing → small-group rounds (sequential) → plenary → recommendations → minority report | rounds ≤ 3 | group_chat | B |

### Education and creative

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `lesson_design_with_simulation` | lesson plan tried on simulated students | goals → plan → three students → misconception log → revise ⟲ → exam → validation | until the students pass, ≤ 3 | Self-Refine plus simulation | B |
| `socratic_tutoring` | tutoring that asks, never tells, until the learner explains it back | diagnose → question ⟲ → learner explanation → check → next concept | per concept, ≤ 6 turns | evaluator-optimizer | A |
| `exam_generation` | an exam with validated answers | blueprint → items → blind solve (`see_prior: false`) → disagreement fix ⟲ → key | fix ≤ 2 | maker_checker | A |
| `game_design_loop` | mechanics tested by simulated playtests | pitch → rules → three playtests → findings → revise ⟲ → rulebook | revise ≤ 3 | broadcast_collect, maker_checker | B |

### Data and personal

| Name | Goal | States | Loop | Pattern | Tier |
|:--|:--|:--|:--|:--|:--|
| `analysis_plan_execute_audit` | an analysis with a blind audit | plan → execute → audit (`see_prior: false`) → fix ⟲ → report | fix ≤ 2 | plan-and-execute | B |
| `data_cleaning_gates` | cleaning with validation gates | profile → rules → apply → validate ⟲ → sign-off | until validation passes, ≤ 3 | evaluator-optimizer | C (check commands) |
| `weekly_review` | a personal weekly review | collect → review → prioritise → plan → commit | none | prompt chaining | A |


### First batch

In order of value over the cost of console work: `draft_critique_revise` (done), `decision_memo_council`, `red_team_review`, `pre_mortem`, `editorial_board`, `meeting_to_actions`, `exam_generation`, `socratic_tutoring`, `legislative_impact`, `advisor_checked_task` (all tier A), then the tier B research set (`literature_review_storm`, `security_review_council`, `peer_review_simulation`). `spec_driven_delivery` is the most-adopted pattern in the survey but needs the approval card and a handoff to `/plan`, so it is the first tier C candidate.

The [workflow catalog design](@/docs/plans--2026-10-16-ceremony-catalog.md) has the survey behind these choices, with its sources.
