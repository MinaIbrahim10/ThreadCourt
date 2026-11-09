# ThreadCourt ⚖️🧵

**Evidence before verdict.** A local multi-agent laboratory for concurrency bugs, powered by Gemma 4 through Ollama.

ThreadCourt turns a concurrency scenario into an auditable hearing: identify the shared state, propose an interleaving, explore the finite state space, replay a counterexample, and compare a repaired model. Every verdict is backed by deterministic evidence, independently of the language model.

## Google Colab and UI integration tests

[Open the combined Colab notebook](https://colab.research.google.com/github/MinaIbrahim10/ThreadCourt/blob/fix/ollama-colab-validation/notebooks/Colab.ipynb). Select a T4 GPU and run the cells in order. The notebook installs official Ollama, supplies the required `zstd` dependency, warms Gemma before experiments, runs both laboratories, and renders both real dashboards inside the notebook. BlackoutLab uses port 8081 because Colab occupies 8080. Download the JSON evidence before the runtime expires.

Agent requests explicitly disable optional thinking so the bounded generation budget is available for the structured answer. This improves transport/JSON reliability, not factual or planning accuracy. Measured results and limitations are in [the November validation record](docs/VALIDATION_2026-11-09.md).

The frontend has a DOM integration smoke test against a real Python server. It checks application behavior but does not render pixels or replace visual browser QA:

```bash
python -m pip install .
npm install --no-audit --no-fund --prefix /tmp/lab-ui jsdom@31.0.0
NODE_PATH=/tmp/lab-ui/node_modules node tests/ui_smoke.cjs
```

Use Node 24. The `DOM integration` GitHub Actions workflow runs this test independently of the Python suite.

## What works today

- Two explicit, executable transition models: lost counter updates and lock-order inversion.
- Breadth-first state exploration, state deduplication, bounded runs, and shortest counterexamples by transition count.
- Controlled real Python thread counter experiment with a barrier-forced failing interleaving and a lock-protected repair.
- Strict trace replay with state, action, and ownership validation.
- Before/after comparison against lock-based model repairs.
- Four Gemma specialist agents plus a deterministic experimenter, orchestrated sequentially to limit local inference pressure.
- Read-only local dashboard with a step-by-step timeline and downloadable JSON evidence.
- No runtime Python dependencies; no paid APIs required.

This is a **model laboratory MVP**, not a source-code race detector. It does not ingest arbitrary repositories, execute generated code, patch files, review PRs, or prove production code safe. The model-backed agents explain evidence; the deterministic engine owns verdicts. This project is separate from AI PR Review.

## Quick start

Python 3.11 or later:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m threadcourt lost-update --serve
```

Open http://127.0.0.1:8765. This default evidence-only mode makes no model calls and explicitly labels the language-model agents disabled.

```bash
python -m threadcourt lock-inversion --output evidence.json
python -m threadcourt lost-update --max-states 2
python -m unittest discover -s tests -v
```

A truncated search without a discovered violation returns `inconclusive`, never a passing verdict.

## Enable Gemma 4 agents

Install a current Ollama from its official website, start its local service, and pull the model:

```bash
ollama pull gemma4:e4b
python -m threadcourt lost-update --llm --serve
```

The default model is configurable:

```bash
export THREADCOURT_MODEL=gemma4:e4b
export OLLAMA_BASE_URL=http://127.0.0.1:11434
python -m threadcourt lock-inversion --llm --output evidence.json
# Or override the model directly:
python -m threadcourt lost-update --llm --model gemma4:e2b
```

`.env.example` documents settings; environment files are not automatically loaded. Context is limited to 4096 tokens and calls are sequential. Available RAM/VRAM, context, quantization, and Ollama offloading affect performance; full GPU residency on an 8 GB card is not guaranteed. Ollama must run on the same host or be configured at a trusted endpoint. Sending to a remote endpoint transmits the scenario and evidence there.

Each agent requests schema-constrained JSON, has a 120-second HTTP timeout, and records failure without suppressing experimental results. Live Gemma inference on a Colab T4 was validated on 9 November 2026; see the validation record for measured outcomes. The Python suite also tests HTTP integration with mock responses.

## Agent hearing

| Role | Responsibility | Authority |
| --- | --- | --- |
| Investigator | Explain resources and invariants | Hypotheses |
| Adversary | Describe harmful interleavings | Hypotheses |
| Experimenter | Explore original/repaired models and replay traces | Deterministic evidence |
| Repairer | Explain the built-in model repair and tradeoffs | Advice |
| Judge | Summarize evidence and limitations | Narrative only |

All roles share the same model instance configuration. This is structured specialist orchestration, not independent model consensus. The adversary's prose does not drive the scheduler in this release; all enabled transitions are explored independently. Repairs are explicitly authored model variants, not automatically generated source patches.

## Understanding the models

**Lost update:** each worker reads a counter, increments a local register, and writes back. Interleaving both reads before either write loses an increment. The repaired model holds one lock across all three operations. This does not imply Python's `+=` behaves identically across all interpreters and objects.

**Lock inversion:** one worker acquires L0 then L1, while the other acquires L1 then L0. The counterexample ends with each worker owning one lock and waiting for the other. The repair imposes L0 then L1 globally.

State exploration models sequentially consistent atomic transitions. It does not model weak memory, fairness, thread starvation, operating-system scheduling, C++ undefined behavior, or the full Python interpreter. `no-violation-in-model` applies only to the explored model. A state budget can make a result inconclusive.

## Project layout

```text
threadcourt/engine.py       Explicit models, bounded explorer, strict replay
threadcourt/agents.py       Ollama adapter and five-role orchestration
threadcourt/dashboard.py   Loopback-only read-only report server
threadcourt/dashboard.html Interactive trace viewer
threadcourt/__main__.py    Command-line entry point
tests/test_engine.py       Evidence, truncation, replay and adapter tests
examples/                  Reproducible evidence-only reports
```

## Security boundaries

No uploaded or generated code is executed. There is no shell tool exposed to agents and no write/patch endpoint in the dashboard. The server binds only to 127.0.0.1. Agent text is inserted through DOM `textContent`. Reports contain model narrative and experimental evidence; review them before sharing. This release intentionally avoids claiming process isolation or sandboxed execution, since it runs built-in models and an authored counter fixture rather than untrusted programs.

## Roadmap

- Validated schedule DSL for custom finite models.
- Extend the real-thread harness beyond the counter fixture.
- C++ example fixtures with ThreadSanitizer evidence in isolated runners.
- Human-reviewed source-to-model mappings and source patch experiments.
- Independent benchmark corpus with false-positive and coverage metrics.

These are future work, not implemented capabilities.

## References

- [Official Ollama Gemma 4 catalog](https://ollama.com/library/gemma4)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

MIT License. Created for Mina Ibrahim.

### Embedded evidence viewer

`python -m threadcourt lost-update --llm --output report.json --html-output report.html` also creates a self-contained HTML evidence viewer. In Colab, use `display(HTML(render_notebook(report)))` from `threadcourt.dashboard`; it isolates styles and includes trace replay and a JSON download without starting a public server. The combined notebook includes this cell.
