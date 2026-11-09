# Live Ollama validation — 9 November 2026

## Environment and changes

Google Colab, Python 3.13, Tesla T4 (15 GiB), Ollama 0.40.15, `gemma4:e4b` (`dc35e8d9c606`, 6.6 GB download). Original source: `0d6080be027d7ee9f002111e1a65f70997ebb530` plus the changes in this branch. Ollama reported 100% GPU execution. Warmup is excluded from agent timing; cold initialization was slow enough to require an explicit warmup outside individual agent timeouts.

The first live run exposed invalid JSON responses in seven of eight specialist calls across the two scenarios. Requests now set `think: false`, keeping the bounded generation budget available for the final JSON answer. After this change, all eight specialist calls completed with valid structured answers. This does not guarantee that their explanations are correct: the deterministic model explorer and replay remain the evidence authority.

| Scenario | Before states | Repaired states | Counterexample transitions | Replay | Specialist responses |
| --- | ---: | ---: | ---: | --- | --- |
| Lost update | 22 | 13 | 6 | Verified | 4/4 completed |
| Lock inversion | 19 | 16 | 2 | Verified | 4/4 completed |

The real Python counter fixture produced 1 instead of 2 before the lock and 2 after the repair. The repaired finite models reported `no-violation-in-model`; this is not a proof about arbitrary source code.

## Tests

Package discovery explicitly includes only the application package, so the Colab notebook directory is not accidentally treated as a second Python package. Both reusable notebooks also pass nbformat validation with explicit cell IDs.

- Python unit/integration suite: 12/12 passed locally and in Colab. The request test checks that optional thinking is disabled.
- DOM integration against real report servers: both scenarios loaded, range selection highlighted the expected row count, Play trace reached the final step, all five roles appeared, and the downloaded report matched the trace. No JavaScript errors were observed.
- The reusable combined notebook's Python cells were syntax-checked. Equivalent operational commands were executed in the saved Colab validation session; a separate fresh Run all of the cleaned repository notebook was not claimed.

Run the DOM test using the Node 24/jsdom command in README. It is also configured in a separate GitHub Actions workflow; inspect Actions for actual CI status.

## Limits

Visual browser QA remains incomplete. Both HTTP dashboards started successfully in Colab, but the cloud browser could not open the authenticated Colab port-proxy URL. DOM tests do not check layout, fonts, responsive rendering, real browser timing, or browser download behavior. No public tunnel, disabled origin check, or exposed Ollama port was used to work around that limitation.

Raw before/after reports accompany this record under `docs/evidence/2026-11-09/`. They contain model-generated explanations and should be read alongside the deterministic evidence, not as independent proof of correctness. No independent evaluation corpus or statistical comparison was performed.

## Follow-up: bounded recovery and notebook UI

The recovery controller now returns actual post-action verification, execution errors, current evidence, and prior attempts to the single/recovery planner for up to three rounds. It stops on successful verification, inference failure, or budget exhaustion. No deterministic fallback is used. `--max-rounds 1` reproduces the previous budget. The legacy results above concern the one-shot controller and must not be presented as measurements of this revision.

The new local suites passed **47 tests and 2 subtests** in total. Coverage includes correcting an incomplete plan from real feedback, enforcing the attempt budget, preserving failed outcomes, and limiting the Colab callback to approved loopback lab API requests. Live Ollama measurements of this revision are pending. ThreadCourt has an isolated embedded evidence viewer with replay and a JSON download; BlackoutLab has a notebook callback transport for its real control UI. Both are included in the reusable notebook.

### Visual browser checks inside Colab

The in-notebook transport loaded the real BlackoutLab dashboard with `Lab connected`. All three runbook scenarios were launched by clicking the UI and recovered with six passing invariants (two orders, two captures, stock 17). Browser interactions verified run history, reopening evidence, the field guide and timeline replay. The evidence download produced a JSON report matching the selected recovered run.

ThreadCourt was rendered using the packaged viewer and the saved actual Gemma reports. Lost-update and lock-inversion both displayed the measured model outcomes; lock-inversion trace playback reached step 2 with row highlighting, and its evidence download produced the matching report. These checks cover the desktop Colab view; they do not establish mobile responsiveness or production safety.

The 47-test suite also passed on a fresh Colab T4 runtime, and both updated GitHub Actions suites passed. Both wheel packages built with the required viewer/module assets.
